#!/usr/bin/env python3
"""
GreenRoute — Reinforcement Learning for Renewable-Aware Data Centre Workload Shifting

Main training and evaluation script.

Usage:
    python greenroute_rl.py                          # Default Q-learning, 500 episodes
    python greenroute_rl.py --agent dqn --episodes 1000
    python greenroute_rl.py --compare-all
"""

import argparse
import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.datacentre_env import DataCentreEnv
from agents.random_agent import RandomAgent
from agents.greedy_agent import GreedyAgent
from agents.q_table_agent import QTableAgent
from agents.dqn_agent import DQNAgent
from safety.carbon_budget_tracker import CarbonBudgetTracker
from safety.equity_auditor import EquityAuditor
from evaluation.metrics import MetricsTracker
from evaluation.visualise import Visualiser

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]
ACTION_NAMES = ["Local", "→ CA ☀️", "→ TX 💨", "→ VA 🏭", "→ OR 💧", "→ AZ ☀️", "Hold ⏸️"]


def create_agent(agent_type: str, seed: int = 42):
    """Factory function to create an agent by name."""
    agents = {
        "random": lambda: RandomAgent(seed=seed),
        "greedy": lambda: GreedyAgent(seed=seed),
        "q_learning": lambda: QTableAgent(seed=seed),
        "dqn": lambda: DQNAgent(seed=seed),
    }
    if agent_type not in agents:
        raise ValueError(f"Unknown agent: {agent_type}. Choose from: {list(agents.keys())}")
    return agents[agent_type]()


def train_agent(agent, env, num_episodes: int = 500, verbose: bool = True,
                seed: int = 42) -> MetricsTracker:
    """Train an agent on the DataCentre environment."""
    metrics = MetricsTracker()
    carbon_tracker = CarbonBudgetTracker()
    equity_auditor = EquityAuditor()
    best_reward = -float("inf")

    console = Console() if RICH_AVAILABLE else None

    if verbose and console:
        console.print(Panel(f"[bold green]Training {agent.name} Agent[/bold green] — {num_episodes} episodes",
                          border_style="green"))

    iterator = range(num_episodes)
    if verbose and TQDM_AVAILABLE and not RICH_AVAILABLE:
        iterator = tqdm(iterator, desc=f"Training {agent.name}")

    for episode in iterator:
        episode_seed = seed + episode
        state, info = env.reset(seed=episode_seed)
        carbon_tracker.reset()
        equity_auditor.reset()

        done = False
        episode_reward = 0.0
        steps = 0

        while not done:
            # Get action mask for safety
            action_mask = env.get_action_mask()

            # Agent selects action
            action = agent.select_action(state, action_mask)

            # Environment step
            next_state, reward, done, truncated, info = env.step(action)

            # Agent learns
            if hasattr(agent, "update"):
                if agent.name == "DQN":
                    agent.update(state, action, reward, next_state, done, action_mask)
                else:
                    agent.update(state, action, reward, next_state, done)

            # Track metrics
            metrics.record_step(action, reward, info)

            # Track carbon and equity
            action_result = info.get("action_result", {})
            if "destination" in action_result:
                carbon_tracker.record_job(
                    origin=info.get("current_job", {}).get("origin", "VA") if info.get("current_job") else "VA",
                    destination=action_result["destination"],
                    compute_units=100.0,
                    actual_carbon_intensity=action_result.get("routed_carbon", 300.0),
                )
                equity_auditor.record_routing(action_result["destination"], 100.0)

            state = next_state
            episode_reward += reward
            steps += 1

            if done or truncated:
                break

        # End episode metrics
        ep_summary = metrics.end_episode()

        if episode_reward > best_reward:
            best_reward = episode_reward

        # Periodic logging
        if verbose and (episode + 1) % 50 == 0:
            summary = metrics.get_summary(last_n=50)
            if console:
                table = Table(title=f"Episode {episode + 1}/{num_episodes}")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                table.add_row("Avg Reward (last 50)", f"{summary['avg_reward']:.1f}")
                table.add_row("Avg Carbon Saved", f"{summary['avg_carbon_saved']:.0f} gCO₂")
                table.add_row("SLA Compliance", f"{summary['avg_sla_compliance']:.1%}")
                table.add_row("Renewable Usage", f"{summary['avg_renewable_fraction']:.1%}")
                table.add_row("Epsilon", f"{getattr(agent, 'epsilon', 'N/A')}")
                table.add_row("Best Reward", f"{best_reward:.1f}")
                console.print(table)
            else:
                print(f"[Episode {episode+1}] Avg Reward: {summary['avg_reward']:.1f} | "
                      f"Carbon: {summary['avg_carbon_saved']:.0f} | "
                      f"SLA: {summary['avg_sla_compliance']:.1%} | "
                      f"Renewable: {summary['avg_renewable_fraction']:.1%}")

    return metrics


def compare_all_agents(num_episodes: int = 200, seed: int = 42, verbose: bool = True):
    """Train and compare all agents side by side."""
    console = Console() if RICH_AVAILABLE else None

    if console:
        console.print(Panel("[bold yellow]GreenRoute — Agent Comparison[/bold yellow]",
                          subtitle="Training all agents...", border_style="yellow"))

    agent_types = ["random", "greedy", "q_learning", "dqn"]
    results = {}

    for agent_type in agent_types:
        if console:
            console.print(f"\n[bold cyan]Training {agent_type.upper()} agent...[/bold cyan]")
        else:
            print(f"\nTraining {agent_type.upper()} agent...")

        agent = create_agent(agent_type, seed=seed)
        env = DataCentreEnv(seed=seed)
        metrics = train_agent(agent, env, num_episodes=num_episodes,
                            verbose=verbose, seed=seed)
        results[agent.name] = metrics

    # Print comparison table
    if console:
        table = Table(title="GreenRoute — Final Comparison")
        table.add_column("Agent", style="bold cyan")
        table.add_column("Avg Reward", style="green")
        table.add_column("Carbon Saved (gCO₂)", style="yellow")
        table.add_column("SLA Compliance", style="red")
        table.add_column("Renewable %", style="blue")
        table.add_column("Routing %", style="magenta")

        for agent_name, metrics in results.items():
            summary = metrics.get_summary(last_n=50)
            table.add_row(
                agent_name,
                f"{summary.get('avg_reward', 0):.1f}",
                f"{summary.get('avg_carbon_saved', 0):.0f}",
                f"{summary.get('avg_sla_compliance', 0):.1%}",
                f"{summary.get('avg_renewable_fraction', 0):.1%}",
                f"{summary.get('avg_routing_fraction', 0):.1%}",
            )
        console.print(table)
    else:
        print("\n=== Final Comparison ===")
        for agent_name, metrics in results.items():
            summary = metrics.get_summary(last_n=50)
            print(f"{agent_name:12s} | Reward: {summary.get('avg_reward', 0):7.1f} | "
                  f"Carbon: {summary.get('avg_carbon_saved', 0):6.0f} | "
                  f"SLA: {summary.get('avg_sla_compliance', 0):.1%} | "
                  f"Renewable: {summary.get('avg_renewable_fraction', 0):.1%}")

    # Generate comparison plots
    vis = Visualiser()
    agent_summaries = {name: m.get_summary(last_n=50) for name, m in results.items()}
    vis.plot_agent_comparison(agent_summaries)

    # Plot learning curves for each agent
    for agent_name, metrics in results.items():
        curves = metrics.get_learning_curves()
        vis.plot_learning_curves(curves, agent_name=agent_name)

    if console:
        console.print("[bold green]✅ Plots saved to outputs/ directory[/bold green]")

    return results


def run_demo_episode(agent, env, verbose: bool = True):
    """Run a single demo episode with detailed step-by-step output."""
    console = Console() if RICH_AVAILABLE else None

    state, info = env.reset(seed=42)
    done = False
    step = 0

    if console:
        console.print(Panel("[bold green]GreenRoute — Live Demo Episode[/bold green]",
                          border_style="green"))

    while not done and step < 50:  # Show first 50 steps
        action_mask = env.get_action_mask()
        action = agent.select_action(state, action_mask)
        next_state, reward, done, truncated, info = env.step(action)

        if verbose and info.get("current_job"):
            job = info["current_job"]
            ar = info.get("action_result", {})

            if console:
                console.print(f"\n[dim]Step {step + 1} | Hour {info['current_hour']:.1f} UTC[/dim]")
                console.print(f"  Job: [cyan]{job.get('job_name', 'Unknown')}[/cyan]")
                console.print(f"  Origin: [yellow]{job.get('origin', '?')}[/yellow] | "
                            f"Compute: {job.get('compute_units', 0):.0f} TFLOPS")
                console.print(f"  Action: [bold green]{ACTION_NAMES[action]}[/bold green] | "
                            f"Reward: {reward:+.2f}")
                if "destination" in ar:
                    console.print(f"  Carbon: {ar.get('local_carbon', 0):.0f} → "
                                f"{ar.get('routed_carbon', 0):.0f} gCO₂/kWh")
            else:
                print(f"Step {step+1} | {job.get('job_name', '?')} from {job.get('origin', '?')} "
                      f"→ {ACTION_NAMES[action]} | Reward: {reward:+.2f}")

        state = next_state
        step += 1

    # Final summary
    if console:
        console.print(Panel(
            f"Carbon saved: [green]{info.get('total_carbon_saved', 0):.0f} gCO₂[/green]\n"
            f"SLA compliance: [{'green' if info.get('sla_compliance', 0) > 0.9 else 'red'}]"
            f"{info.get('sla_compliance', 0):.1%}[/]\n"
            f"Renewable usage: [blue]{info.get('renewable_fraction_avg', 0):.1%}[/blue]",
            title="Episode Summary", border_style="green"
        ))

    return env.episode_log


def main():
    parser = argparse.ArgumentParser(description="GreenRoute — RL for Renewable-Aware Workload Shifting")
    parser.add_argument("--agent", type=str, default="q_learning",
                       choices=["random", "greedy", "q_learning", "dqn"],
                       help="Agent type to train (default: q_learning)")
    parser.add_argument("--episodes", type=int, default=500,
                       help="Number of training episodes (default: 500)")
    parser.add_argument("--compare-all", action="store_true",
                       help="Train and compare all agents")
    parser.add_argument("--demo", action="store_true",
                       help="Run a single demo episode with verbose output")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed (default: 42)")
    parser.add_argument("--no-rich", action="store_true",
                       help="Disable rich console output")
    args = parser.parse_args()

    console = Console() if RICH_AVAILABLE and not args.no_rich else None

    if console:
        console.print(Panel.fit(
            "[bold green]☀️  GreenRoute RL[/bold green]\n"
            "[dim]Renewable-Aware Data Centre Workload Shifting[/dim]\n"
            "[dim italic]\"Why move energy to the computation — when you can move the computation to the energy?\"[/dim italic]",
            border_style="green"
        ))

    if args.compare_all:
        compare_all_agents(num_episodes=args.episodes, seed=args.seed)
        return

    # Create environment and agent
    env = DataCentreEnv(seed=args.seed)
    agent = create_agent(args.agent, seed=args.seed)

    if args.demo:
        # Quick demo — train briefly then show one episode
        if args.agent in ("q_learning", "dqn"):
            if console:
                console.print("[dim]Pre-training for 100 episodes...[/dim]")
            train_agent(agent, env, num_episodes=100, verbose=False, seed=args.seed)
        episode_log = run_demo_episode(agent, env)

        # Generate routing map
        vis = Visualiser()
        vis.plot_routing_map(episode_log)
        if console:
            console.print("[green]Routing map saved to outputs/routing_map.png[/green]")
    else:
        # Full training
        metrics = train_agent(agent, env, num_episodes=args.episodes, seed=args.seed)

        # Generate plots
        vis = Visualiser()
        curves = metrics.get_learning_curves()
        vis.plot_learning_curves(curves, agent_name=agent.name)

        # Final summary
        summary = metrics.get_summary()
        if console:
            table = Table(title=f"Final Results — {agent.name}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Episodes", str(summary["num_episodes"]))
            table.add_row("Avg Reward", f"{summary['avg_reward']:.1f} ± {summary['std_reward']:.1f}")
            table.add_row("Avg Carbon Saved", f"{summary['avg_carbon_saved']:.0f} gCO₂")
            table.add_row("SLA Compliance", f"{summary['avg_sla_compliance']:.1%}")
            table.add_row("Renewable Usage", f"{summary['avg_renewable_fraction']:.1%}")
            table.add_row("Routing Fraction", f"{summary['avg_routing_fraction']:.1%}")
            console.print(table)
        else:
            print(f"\n=== {agent.name} Final Results ===")
            print(f"Episodes: {summary['num_episodes']}")
            print(f"Avg Reward: {summary['avg_reward']:.1f}")
            print(f"Avg Carbon Saved: {summary['avg_carbon_saved']:.0f} gCO₂")
            print(f"SLA Compliance: {summary['avg_sla_compliance']:.1%}")
            print(f"Renewable Usage: {summary['avg_renewable_fraction']:.1%}")

        # Save model
        model_dir = "models"
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, f"{agent.name.lower()}_model.pt")
        agent.save(model_path)
        if console:
            console.print(f"[green]Model saved to {model_path}[/green]")


if __name__ == "__main__":
    main()
