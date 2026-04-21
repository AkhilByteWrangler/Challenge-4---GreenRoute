#!/usr/bin/env python3
"""
Unified training script for all agents (PPO, Q-Learning, DQN) with stochastic weather.
Trains independently, evaluates comparatively, saves individual checkpoints.
"""

import sys
import os
import json
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.stochastic_env import StochasticDataCentreEnv
from environment.datacentre_env import DataCentreEnv, LOCATION_IDS
from agents.ppo_agent import PPOAgent
from agents.q_table_agent import QTableAgent
from agents.dqn_agent import DQNAgent
from agents.random_agent import RandomAgent
from agents.greedy_agent import GreedyAgent
from evaluation.metrics import MetricsTracker


class UnifiedTrainer:
    """Single training framework for all agent types."""

    def __init__(self, env, seed=42, output_dir="outputs", checkpoint_dir="checkpoints"):
        self.env = env
        self.seed = seed
        self.output_dir = output_dir
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        self.results = {}

    def train_agent(self, agent, name, num_episodes, logging_interval=100):
        """Train any agent type with consistent logging."""
        metrics = MetricsTracker()
        rewards, carbon, sla, renewable = [], [], [], []

        device = getattr(agent, 'device', 'CPU')
        device_name = "MPS GPU" if "mps" in str(device) else ("CUDA GPU" if "cuda" in str(device) else "CPU")
        print(f"\nTraining {name} for {num_episodes} episodes on {device_name}", flush=True)

        start = time.time()
        for ep in range(num_episodes):
            state, info = self.env.reset(seed=self.seed + ep)
            done = False
            ep_reward = 0.0

            while not done:
                action_mask = self.env.get_action_mask()
                action = agent.select_action(state, action_mask)
                next_state, reward, done, truncated, info = self.env.step(action)

                # Agent-specific update
                if hasattr(agent, 'update'):
                    if agent.name == "DQN":
                        agent.update(state, action, reward, next_state, done, action_mask)
                    else:
                        agent.update(state, action, reward, next_state, done)

                metrics.record_step(action, reward, info)
                state = next_state
                ep_reward += reward
                if done or truncated:
                    break

            ep_summary = metrics.end_episode()
            rewards.append(ep_reward)
            carbon.append(ep_summary['carbon_saved_total'])
            sla.append(ep_summary['sla_compliance'])
            renewable.append(ep_summary['renewable_fraction_avg'])

            if (ep + 1) % logging_interval == 0:
                last_r = np.mean(rewards[-logging_interval:])
                last_c = np.mean(carbon[-logging_interval:])
                print(f"  Ep {ep+1}/{num_episodes}: Reward={last_r:.1f}, Carbon={last_c:.0f}g", flush=True)

        train_time = time.time() - start

        # Save checkpoint
        if hasattr(agent, 'save'):
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{name.lower().replace(' ', '_')}.pt")
            agent.save(checkpoint_path)
            print(f"  Checkpoint saved to {checkpoint_path}")

        # Store results
        self.results[name] = {
            'rewards': rewards,
            'carbon': carbon,
            'sla': sla,
            'renewable': renewable,
            'train_time': train_time,
            'metrics': metrics,
        }

        return rewards, carbon, sla, renewable

    def evaluate_agent(self, agent, name, num_episodes=300, seed_offset=10000):
        """Evaluate agent on test set."""
        metrics = MetricsTracker()
        rewards, carbon, sla, renewable = [], [], [], []

        print(f"  Evaluating {name} ({num_episodes} episodes)...", flush=True)

        for ep in range(num_episodes):
            state, info = self.env.reset(seed=self.seed + seed_offset + ep)
            done = False
            ep_reward = 0.0

            while not done:
                action_mask = self.env.get_action_mask()
                action = agent.select_action(state, action_mask)
                state, reward, done, truncated, info = self.env.step(action)
                metrics.record_step(action, reward, info)
                ep_reward += reward
                if done or truncated:
                    break

            ep_summary = metrics.end_episode()
            rewards.append(ep_reward)
            carbon.append(ep_summary['carbon_saved_total'])
            sla.append(ep_summary['sla_compliance'])
            renewable.append(ep_summary['renewable_fraction_avg'])

        return {
            'avg_reward': float(np.mean(rewards)),
            'avg_carbon_saved': float(np.mean(carbon)),
            'avg_sla_compliance': float(np.mean(sla)),
            'avg_renewable_fraction': float(np.mean(renewable)),
        }

    def plot_training_curves(self):
        """Visualize training progress for all agents."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.patch.set_facecolor('#1a1a2e')
        fig.suptitle('GreenRoute — Training Curves (All Agents)', fontsize=16, fontweight='bold', color='white')

        metrics_to_plot = [
            ('rewards', 'Episode Reward', 'green'),
            ('carbon', 'Carbon Saved (gCO₂)', 'yellow'),
            ('sla', 'SLA Compliance', 'red'),
            ('renewable', 'Renewable Fraction', 'cyan'),
        ]

        colors_per_agent = {
            'PPO': '#45B7D1',
            'Q-Learning': '#FF6B6B',
            'DQN': '#96CEB4',
        }

        for ax, (key, title, _) in zip(axes.flat, metrics_to_plot):
            ax.set_facecolor('#16213e')
            for agent_name, data in self.results.items():
                if key in agent_name.lower() or agent_name in self.results:
                    values = data[key]
                    # Smooth with window
                    window = 20
                    if len(values) >= window:
                        kernel = np.ones(window) / window
                        smoothed = np.convolve(values, kernel, mode='valid')
                        ax.plot(range(window-1, len(values)), smoothed,
                               label=agent_name, color=colors_per_agent.get(agent_name, 'white'),
                               linewidth=2)
                    ax.plot(range(len(values)), values, alpha=0.1, color='gray', linewidth=0.5)

            ax.set_title(title, fontsize=12, color='white')
            ax.set_xlabel('Episode', color='white')
            ax.legend(loc='best', facecolor='#16213e', edgecolor='white')
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.2)

        plt.tight_layout()
        path = os.path.join(self.output_dir, 'training_curves.png')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
        plt.close(fig)
        print(f"  Training curves saved to {path}", flush=True)

    def plot_comparison(self, eval_results):
        """Compare agents on evaluation metrics."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.patch.set_facecolor('#1a1a2e')
        fig.suptitle('GreenRoute — Agent Comparison', fontsize=16, fontweight='bold', color='white')

        agents = list(eval_results.keys())
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFE66D'][:len(agents)]

        metrics = [
            ('avg_carbon_saved', 'Carbon Saved (gCO₂)'),
            ('avg_sla_compliance', 'SLA Compliance (%)'),
            ('avg_renewable_fraction', 'Renewable Fraction (%)'),
            ('avg_reward', 'Average Reward'),
        ]

        for ax, (key, title) in zip(axes.flat, metrics):
            ax.set_facecolor('#16213e')
            values = [eval_results[a].get(key, 0) for a in agents]

            # Scale SLA and renewable to percentages for display
            if 'compliance' in key or 'fraction' in key:
                values = [v * 100 if v < 2 else v for v in values]

            bars = ax.bar(agents, values, color=colors, edgecolor='white', linewidth=1)
            ax.set_title(title, fontsize=12, color='white')
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(axis='x', rotation=45)

            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{val:.1f}', ha='center', va='bottom', color='white', fontsize=10)

        plt.tight_layout()
        path = os.path.join(self.output_dir, 'agent_comparison.png')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
        plt.close(fig)
        print(f"  Agent comparison saved to {path}", flush=True)

    def print_metrics_table(self, eval_results):
        """Print and save metrics table."""
        print("\n" + "="*100, flush=True)
        print("EVALUATION RESULTS — Agent Comparison".center(100), flush=True)
        print("="*100, flush=True)

        # Print table
        header = f"{'Agent':<15} | {'Carbon (gCO₂)':<15} | {'SLA %':<10} | {'Renewable %':<12} | {'Reward':<10}"
        print(header, flush=True)
        print("-"*100, flush=True)

        for agent_name, metrics in eval_results.items():
            carbon = metrics.get('avg_carbon_saved', 0)
            sla = metrics.get('avg_sla_compliance', 0) * 100
            renewable = metrics.get('avg_renewable_fraction', 0) * 100
            reward = metrics.get('avg_reward', 0)
            print(f"{agent_name:<15} | {carbon:>13.0f} | {sla:>8.1f} | {renewable:>10.1f} | {reward:>8.1f}", flush=True)

        print("="*100 + "\n", flush=True)

        # Save markdown table
        md_table = "| Agent | Carbon (gCO₂) | SLA % | Renewable % | Reward |\n"
        md_table += "|---|---|---|---|---|\n"
        for agent_name, metrics in eval_results.items():
            carbon = metrics.get('avg_carbon_saved', 0)
            sla = metrics.get('avg_sla_compliance', 0) * 100
            renewable = metrics.get('avg_renewable_fraction', 0) * 100
            reward = metrics.get('avg_reward', 0)
            md_table += f"| {agent_name} | {carbon:.0f} | {sla:.1f} | {renewable:.1f} | {reward:.1f} |\n"

        table_path = os.path.join(self.output_dir, 'metrics_table.md')
        with open(table_path, 'w') as f:
            f.write(md_table)
        print(f"Metrics table saved to {table_path}\n", flush=True)


def main():
    SEED = 42
    N_PPO = 5000
    N_QLEARN = 5000
    N_DQN = 5000
    N_EVAL = 5000

    # Use stochastic weather environment
    env = StochasticDataCentreEnv(seed=SEED)
    trainer = UnifiedTrainer(env, seed=SEED)

    # Train PPO
    ppo_agent = PPOAgent(
        state_dim=67, num_actions=7, seed=SEED,
        hidden_dims=[256, 256],
        lr=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_eps=0.2,
        entropy_coef=0.005,
        value_coef=0.5,
        max_grad_norm=0.5,
        n_epochs=10,
        n_steps=2048,
        batch_size=64,
        anneal_lr=True,
        total_timesteps=N_PPO * 400,
        target_kl=0.02,
    )
    trainer.train_agent(ppo_agent, "PPO", N_PPO, logging_interval=100)

    # Train Q-Learning
    q_agent = QTableAgent(seed=SEED, epsilon_start=1.0, epsilon_end=0.05,
                         epsilon_decay=0.995, learning_rate=0.1)
    trainer.train_agent(q_agent, "Q-Learning", N_QLEARN, logging_interval=50)

    # Train DQN
    dqn_agent = DQNAgent(state_dim=67, num_actions=7, seed=SEED,
                        epsilon_start=1.0, epsilon_end=0.02,
                        epsilon_decay=0.998, learning_rate=1e-4)
    trainer.train_agent(dqn_agent, "DQN", N_DQN, logging_interval=50)

    # Train baselines (no learning, but run through environment)
    random_agent = RandomAgent(seed=SEED)
    greedy_agent = GreedyAgent(seed=SEED)
    trainer.train_agent(random_agent, "Random", N_PPO, logging_interval=100)
    trainer.train_agent(greedy_agent, "Greedy", N_PPO, logging_interval=100)

    # Evaluate all agents
    print(f"\nEvaluating all agents ({N_EVAL} episodes each)")
    eval_results = {}

    # Disable learning for evaluation
    ppo_agent.epsilon = 0.0
    q_agent.epsilon = 0.0
    dqn_agent.epsilon = 0.0
    random_agent.epsilon = 0.0
    greedy_agent.epsilon = 0.0

    for agent, name in [(ppo_agent, "PPO"), (q_agent, "Q-Learning"), (dqn_agent, "DQN"),
                        (random_agent, "Random"), (greedy_agent, "Greedy")]:
        eval_results[name] = trainer.evaluate_agent(agent, name, N_EVAL)

    # Generate outputs
    print("\nGenerating visualizations...", flush=True)
    trainer.plot_training_curves()
    trainer.plot_comparison(eval_results)
    trainer.print_metrics_table(eval_results)

    # Export final metrics
    export = {
        "metadata": {
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "environment": "StochasticDataCentreEnv v2.0",
            "state_dim": 67,
            "action_dim": 7,
            "locations": LOCATION_IDS,
        },
        "final_metrics": eval_results,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "demo", "public")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "all_agents_results.json")
    with open(out_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"Exported results to {out_path}")

    print("Training and evaluation complete!")


if __name__ == "__main__":
    main()
