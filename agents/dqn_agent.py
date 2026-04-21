"""Deep Q-Network (DQN) agent for GreenRoute."""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
from typing import Optional, Tuple


class QNetwork(nn.Module):
    """Dueling DQN architecture with layer normalisation."""

    def __init__(self, state_dim: int = 47, num_actions: int = 7, hidden_dim: int = 256):
        super().__init__()

        # Shared feature extractor
        self.feature = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
        )

        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, num_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Compute Q-values using dueling architecture: V(s) + A(s,a) - mean(A(s,:))."""
        features = self.feature(x)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        q_values = value + advantage - advantage.mean(dim=-1, keepdim=True)
        return q_values


class ReplayBuffer:
    """Experience replay buffer for DQN training."""

    def __init__(self, capacity: int = 50000) -> None:
        self.buffer: deque = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float,
             next_state: np.ndarray, done: bool, action_mask: Optional[np.ndarray] = None) -> None:
        """Store a transition in the replay buffer."""
        self.buffer.append((state, action, reward, next_state, done, action_mask))

    def sample(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple]:
        """Sample a random batch of transitions from the buffer."""
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones, masks = zip(*batch)
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards, dtype=np.float32),
            np.array(next_states),
            np.array(dones, dtype=np.float32),
            masks,
        )

    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    """
    Deep Q-Network agent with:
    - Dueling architecture
    - Experience replay
    - Target network (soft update)
    - Action masking for safety constraints
    - Epsilon-greedy exploration with decay
    """

    def __init__(self, state_dim: int = 47, num_actions: int = 7, seed: int = 42,
                 hidden_dim: int = 256, learning_rate: float = 1e-4,
                 discount_factor: float = 0.99, epsilon_start: float = 1.0,
                 epsilon_end: float = 0.02, epsilon_decay: float = 0.998,
                 batch_size: int = 64, buffer_size: int = 50000,
                 target_update_tau: float = 0.005, update_every: int = 4):
        self.name = "DQN"
        self.num_actions = num_actions
        self.state_dim = state_dim
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Networks
        self.q_network = QNetwork(state_dim, num_actions, hidden_dim).to(self.device)
        self.target_network = QNetwork(state_dim, num_actions, hidden_dim).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()

        # Optimiser and loss
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.loss_fn = nn.SmoothL1Loss()

        # Replay buffer
        self.replay_buffer = ReplayBuffer(buffer_size)

        # Hyperparameters
        self.gamma = discount_factor
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.tau = target_update_tau
        self.update_every = update_every

        # Step counter
        self.step_count = 0
        self.total_updates = 0
        self.losses = []

    def select_action(self, state: np.ndarray, action_mask: Optional[np.ndarray] = None) -> int:
        """Epsilon-greedy action selection with action masking."""
        if random.random() < self.epsilon:
            if action_mask is not None:
                valid = np.where(action_mask)[0]
                return int(np.random.choice(valid))
            return int(np.random.randint(0, self.num_actions))

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor).cpu().numpy()[0]

        if action_mask is not None:
            q_values[~action_mask] = -np.inf

        return int(np.argmax(q_values))

    def update(self, state: np.ndarray, action: int, reward: float,
               next_state: np.ndarray, done: bool, action_mask: Optional[np.ndarray] = None) -> None:
        """Store transition and learn if enough samples."""
        self.replay_buffer.push(state, action, reward, next_state, done, action_mask)
        self.step_count += 1

        if len(self.replay_buffer) < self.batch_size:
            return

        if self.step_count % self.update_every == 0:
            self._learn()

        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def _learn(self) -> None:
        """Sample from replay buffer and update Q-network."""
        states, actions, rewards, next_states, dones, _ = self.replay_buffer.sample(self.batch_size)

        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards_t = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t = torch.FloatTensor(dones).unsqueeze(1).to(self.device)

        current_q = self.q_network(states_t).gather(1, actions_t)

        with torch.no_grad():
            next_actions = self.q_network(next_states_t).argmax(1, keepdim=True)
            next_q = self.target_network(next_states_t).gather(1, next_actions)
            target_q = rewards_t + self.gamma * next_q * (1 - dones_t)

        loss = self.loss_fn(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 10.0)
        self.optimizer.step()

        self._soft_update()

        self.total_updates += 1
        self.losses.append(loss.item())

    def _soft_update(self) -> None:
        """Soft update target network: θ_target = (1-τ)*θ_target + τ*θ_online"""
        for target_param, online_param in zip(
            self.target_network.parameters(), self.q_network.parameters()
        ):
            target_param.data.lerp_(online_param.data, self.tau)

    def get_q_values(self, state: np.ndarray) -> np.ndarray:
        """Get Q-values for a state."""
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.q_network(state_tensor).cpu().numpy()[0]
        return q_values

    def save(self, path: str) -> None:
        """Save model checkpoint."""
        torch.save({
            "q_network": self.q_network.state_dict(),
            "target_network": self.target_network.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "step_count": self.step_count,
            "total_updates": self.total_updates,
        }, path)

    def load(self, path: str) -> None:
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.q_network.load_state_dict(checkpoint["q_network"])
        self.target_network.load_state_dict(checkpoint["target_network"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.epsilon = checkpoint["epsilon"]
        self.step_count = checkpoint["step_count"]
        self.total_updates = checkpoint["total_updates"]
