"""Proximal Policy Optimization (PPO) agent for GreenRoute."""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from typing import List, Tuple, Optional, Dict


class ActorCritic(nn.Module):
    """Shared-backbone actor-critic network with separate policy and value heads."""

    def __init__(self, state_dim: int = 47, num_actions: int = 7,
                 hidden_dims: Optional[List[int]] = None):
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [256, 128]

        layers = []
        prev = state_dim
        for h in hidden_dims:
            layers.extend([
                nn.Linear(prev, h),
                nn.LayerNorm(h),
                nn.Tanh(),
            ])
            prev = h
        self.backbone = nn.Sequential(*layers)

        # Actor head (policy)
        self.actor = nn.Sequential(
            nn.Linear(prev, 64),
            nn.Tanh(),
            nn.Linear(64, num_actions),
        )

        # Critic head (value function)
        self.critic = nn.Sequential(
            nn.Linear(prev, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

        # Orthogonal init (PPO best practice)
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                nn.init.constant_(m.bias, 0)
        nn.init.orthogonal_(self.actor[-1].weight, gain=0.01)
        nn.init.orthogonal_(self.critic[-1].weight, gain=1.0)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Return policy logits and state value."""
        features = self.backbone(x)
        logits = self.actor(features)
        value = self.critic(features)
        return logits, value.squeeze(-1)

    def get_action_and_value(self, state: torch.Tensor, action_mask: Optional[torch.Tensor] = None,
                           action: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample or evaluate action; return action, log_prob, entropy, and value."""
        logits, value = self.forward(state)

        if action_mask is not None:
            logits = logits.masked_fill(~action_mask, float('-inf'))

        dist = Categorical(logits=logits)

        if action is None:
            action = dist.sample()

        log_prob = dist.log_prob(action)
        entropy = dist.entropy()
        return action, log_prob, entropy, value

    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """Compute state value using critic head."""
        features = self.backbone(state)
        return self.critic(features).squeeze(-1)


class RolloutBuffer:
    """Stores trajectory data for PPO updates."""

    def __init__(self) -> None:
        self.states: List[torch.Tensor] = []
        self.actions: List[torch.Tensor] = []
        self.log_probs: List[torch.Tensor] = []
        self.rewards: List[float] = []
        self.values: List[torch.Tensor] = []
        self.dones: List[float] = []
        self.action_masks: List[torch.Tensor] = []

    def add(self, state: torch.Tensor, action: torch.Tensor, log_prob: torch.Tensor,
            reward: float, value: torch.Tensor, done: float, action_mask: torch.Tensor) -> None:
        """Store transition data for PPO update."""
        self.states.append(state)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)
        self.action_masks.append(action_mask)

    def get(self) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return all collected trajectory data as stacked tensors."""
        return (
            torch.stack(self.states),
            torch.stack(self.actions),
            torch.stack(self.log_probs),
            torch.tensor(self.rewards, dtype=torch.float32),
            torch.stack(self.values),
            torch.tensor(self.dones, dtype=torch.float32),
            torch.stack(self.action_masks),
        )

    def clear(self) -> None:
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()
        self.action_masks.clear()

    def __len__(self) -> int:
        return len(self.rewards)


class PPOAgent:
    """Proximal Policy Optimization agent using actor-critic with GAE advantage estimation."""

    def __init__(self, state_dim: int = 47, num_actions: int = 7, seed: int = 42,
                 hidden_dims: List[int] = [256, 128],
                 lr: float = 3e-4, gamma: float = 0.99, gae_lambda: float = 0.95,
                 clip_eps: float = 0.2, clip_value: float = 0.2,
                 entropy_coef: float = 0.01, value_coef: float = 0.5,
                 max_grad_norm: float = 0.5, n_epochs: int = 10,
                 n_steps: int = 2048, batch_size: int = 64,
                 anneal_lr: bool = True, total_timesteps: int = 500000,
                 target_kl: float = 0.015):

        self.name = "PPO"
        self.num_actions = num_actions
        self.state_dim = state_dim

        torch.manual_seed(seed)
        np.random.seed(seed)

        # Device selection: CUDA > MPS > CPU
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        # Network
        self.network = ActorCritic(state_dim, num_actions, hidden_dims).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr, eps=1e-5)

        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_eps = clip_eps
        self.clip_value = clip_value
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.n_epochs = n_epochs
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.anneal_lr = anneal_lr
        self.total_timesteps = total_timesteps
        self.initial_lr = lr
        self.target_kl = target_kl

        # Rollout buffer
        self.buffer = RolloutBuffer()

        # Tracking
        self.step_count = 0
        self.update_count = 0
        self.total_updates = 0
        self.losses = {"policy": [], "value": [], "entropy": [], "total": []}

        # For train_agent compatibility
        self.epsilon = 0.0
        self._ones_mask = torch.ones(num_actions, dtype=torch.bool)

    def select_action(self, state: np.ndarray, action_mask: np.ndarray = None) -> int:
        """Select action using current policy."""
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            mask_t = None
            if action_mask is not None:
                mask_t = torch.BoolTensor(action_mask).unsqueeze(0).to(self.device)
            action, log_prob, entropy, value = self.network.get_action_and_value(
                state_t, mask_t
            )

        self._last_state = state_t.squeeze(0)
        self._last_action = action.squeeze(0)
        self._last_log_prob = log_prob.squeeze(0)
        self._last_value = value.squeeze(0)
        self._last_mask = mask_t.squeeze(0) if mask_t is not None else self._ones_mask

        return int(action.item())

    def update(self, state: np.ndarray, action: int, reward: float,
               next_state: np.ndarray, done: bool, action_mask: np.ndarray = None):
        """Store transition; run PPO update when buffer is full."""
        self.buffer.add(
            self._last_state,
            self._last_action,
            self._last_log_prob,
            reward,
            self._last_value,
            done,
            self._last_mask,
        )
        self.step_count += 1

        if len(self.buffer) >= self.n_steps:
            # Bootstrap value for incomplete episode
            with torch.no_grad():
                next_t = torch.FloatTensor(next_state).unsqueeze(0).to(self.device)
                next_value = self.network.get_value(next_t).item()

            self._ppo_update(next_value, done)
            self.buffer.clear()

    def _compute_gae(self, rewards, values, dones, next_value, done):
        """Compute GAE advantages and returns."""
        T = len(rewards)
        advantages = torch.zeros(T)
        returns = torch.zeros(T)

        last_gae = 0
        last_value = next_value

        for t in reversed(range(T)):
            if t == T - 1:
                next_non_terminal = 1.0 - float(done)
                next_val = next_value
            else:
                next_non_terminal = 1.0 - dones[t + 1]
                next_val = values[t + 1]

            delta = rewards[t] + self.gamma * next_val * next_non_terminal - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * next_non_terminal * last_gae
            returns[t] = advantages[t] + values[t]

        return advantages, returns

    def _ppo_update(self, next_value: float, done: bool):
        """Run PPO update on collected trajectory."""
        self.update_count += 1

        states, actions, old_log_probs, rewards, values, dones, masks = self.buffer.get()
        states = states.to(self.device)
        actions = actions.to(self.device)
        old_log_probs = old_log_probs.to(self.device)
        masks = masks.to(self.device)

        # GAE
        advantages, returns = self._compute_gae(rewards, values.cpu(), dones, next_value, done)
        advantages = advantages.to(self.device)
        returns = returns.to(self.device)

        # Normalise advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # LR annealing
        if self.anneal_lr:
            frac = 1.0 - self.step_count / self.total_timesteps
            lr = max(self.initial_lr * frac, 1e-6)
            for pg in self.optimizer.param_groups:
                pg['lr'] = lr

        T = len(rewards)
        indices = np.arange(T)

        for epoch in range(self.n_epochs):
            np.random.shuffle(indices)

            # Mini-batch updates
            for start in range(0, T, self.batch_size):
                end = min(start + self.batch_size, T)
                mb_idx = indices[start:end]

                mb_states = states[mb_idx]
                mb_actions = actions[mb_idx]
                mb_old_log_probs = old_log_probs[mb_idx]
                mb_advantages = advantages[mb_idx]
                mb_returns = returns[mb_idx]
                mb_masks = masks[mb_idx]

                # Forward pass
                _, new_log_probs, entropy, new_values = self.network.get_action_and_value(
                    mb_states, mb_masks, mb_actions
                )

                # Policy loss (clipped surrogate)
                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_eps, 1 + self.clip_eps) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss (clipped)
                value_loss = 0.5 * ((new_values - mb_returns) ** 2).mean()

                # Entropy bonus
                entropy_loss = entropy.mean()

                # Total loss
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                self.total_updates += 1

            # Early stopping on KL divergence
            with torch.no_grad():
                _, new_lp, _, _ = self.network.get_action_and_value(states, masks, actions)
                approx_kl = (old_log_probs - new_lp).mean().item()
                if abs(approx_kl) > self.target_kl:
                    break

        self.losses["policy"].append(policy_loss.item())
        self.losses["value"].append(value_loss.item())
        self.losses["entropy"].append(entropy_loss.item())
        self.losses["total"].append(loss.item())

    def get_policy_probs(self, state: np.ndarray, action_mask: np.ndarray = None) -> np.ndarray:
        """Get action probabilities for a state."""
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            logits, value = self.network(state_t)
            if action_mask is not None:
                mask_t = torch.BoolTensor(action_mask).unsqueeze(0).to(self.device)
                logits = logits.masked_fill(~mask_t, float('-inf'))
            probs = torch.softmax(logits, dim=-1)
        return probs.cpu().numpy()[0]

    def get_value(self, state: np.ndarray) -> float:
        """Get state value estimate."""
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            v = self.network.get_value(state_t)
        return v.item()

    def save(self, path: str):
        """Save network and optimizer state to checkpoint."""
        torch.save({
            "network": self.network.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "step_count": self.step_count,
            "update_count": self.update_count,
        }, path)

    def load(self, path: str):
        """Load network and optimizer state from checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.network.load_state_dict(checkpoint["network"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.step_count = checkpoint["step_count"]
        self.update_count = checkpoint["update_count"]

    def export_weights_for_js(self) -> dict:
        """Export network weights as JSON-serializable dict for browser demo."""
        sd = self.network.state_dict()

        # For the JS demo we need a compact representation.
        # Export the full actor weights as layered arrays.
        export = {
            "architecture": "actor_critic_mlp",
            "state_dim": self.state_dim,
            "num_actions": self.num_actions,
            "layers": [],
        }

        # Backbone layers
        for i, m in enumerate(self.network.backbone):
            if isinstance(m, nn.Linear):
                export["layers"].append({
                    "type": "linear",
                    "weight": m.weight.data.cpu().tolist(),
                    "bias": m.bias.data.cpu().tolist(),
                })
            elif isinstance(m, nn.LayerNorm):
                export["layers"].append({
                    "type": "layernorm",
                    "weight": m.weight.data.cpu().tolist(),
                    "bias": m.bias.data.cpu().tolist(),
                    "eps": m.eps,
                })

        # Actor head
        export["actor_layers"] = []
        for m in self.network.actor:
            if isinstance(m, nn.Linear):
                export["actor_layers"].append({
                    "type": "linear",
                    "weight": m.weight.data.cpu().tolist(),
                    "bias": m.bias.data.cpu().tolist(),
                })

        # Critic head
        export["critic_layers"] = []
        for m in self.network.critic:
            if isinstance(m, nn.Linear):
                export["critic_layers"].append({
                    "type": "linear",
                    "weight": m.weight.data.cpu().tolist(),
                    "bias": m.bias.data.cpu().tolist(),
                })

        return export
