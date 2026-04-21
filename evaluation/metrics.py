"""
Metrics tracking for GreenRoute evaluation.

Tracks carbon saved, cost saved, SLA compliance, renewable usage,
and generates summary statistics for comparison across agents.
"""

import numpy as np
from typing import Dict, List, Optional

# Action types
ACTION_HOLD = 6
ACTION_LOCAL = 0

# Default episode state template
DEFAULT_EPISODE = {
    "carbon_saved": 0.0,
    "cost_saved": 0.0,
    "total_reward": 0.0,
    "jobs_processed": 0,
    "sla_violations": 0,
    "renewable_fraction_sum": 0.0,
    "jobs_routed": 0,
    "jobs_held": 0,
    "jobs_local": 0,
    "routing_decisions": [],
}


class MetricsTracker:
    """Comprehensive metrics tracking across episodes and agents."""

    def __init__(self) -> None:
        self.episode_metrics: List[Dict] = []
        self.current_episode = DEFAULT_EPISODE.copy()

    def record_step(self, action: int, reward: float, info: Dict) -> None:
        """Record metrics for a single step."""
        ep = self.current_episode
        ep["total_reward"] += reward
        ep["jobs_processed"] += 1

        action_result = info.get("action_result", {})
        if action_result.get("sla_violated", False):
            ep["sla_violations"] += 1

        if action == ACTION_HOLD:
            ep["jobs_held"] += 1
        elif action == ACTION_LOCAL:
            ep["jobs_local"] += 1
        else:
            ep["jobs_routed"] += 1

        ep["carbon_saved"] = info.get("total_carbon_saved", 0.0)
        ep["cost_saved"] = info.get("total_cost_saved", 0.0)
        ep["renewable_fraction_sum"] += action_result.get("renewable_fraction", 0.0)

    def end_episode(self) -> Dict:
        """Finalise and store metrics for the completed episode."""
        ep = self.current_episode
        n = max(ep["jobs_processed"], 1)

        summary = {
            "total_reward": ep["total_reward"],
            "carbon_saved_total": ep["carbon_saved"],
            "carbon_saved_per_job": ep["carbon_saved"] / n,
            "cost_saved_total": ep["cost_saved"],
            "jobs_processed": ep["jobs_processed"],
            "sla_violations": ep["sla_violations"],
            "sla_compliance": 1.0 - ep["sla_violations"] / n,
            "renewable_fraction_avg": ep["renewable_fraction_sum"] / n,
            "jobs_routed": ep["jobs_routed"],
            "jobs_held": ep["jobs_held"],
            "jobs_local": ep["jobs_local"],
            "routing_fraction": ep["jobs_routed"] / n,
            "hold_fraction": ep["jobs_held"] / n,
        }

        self.episode_metrics.append(summary)
        self.current_episode = DEFAULT_EPISODE.copy()

        return summary

    def get_summary(self, last_n: Optional[int] = None) -> Dict:
        """Get aggregate summary across episodes."""
        metrics = self.episode_metrics[-last_n:] if last_n else self.episode_metrics

        if not metrics:
            return {"num_episodes": 0}

        rewards = [m["total_reward"] for m in metrics]
        carbon_totals = [m["carbon_saved_total"] for m in metrics]

        return {
            "num_episodes": len(metrics),
            "avg_reward": np.mean(rewards),
            "avg_carbon_saved": np.mean(carbon_totals),
            "avg_carbon_per_job": np.mean([m["carbon_saved_per_job"] for m in metrics]),
            "avg_sla_compliance": np.mean([m["sla_compliance"] for m in metrics]),
            "avg_renewable_fraction": np.mean([m["renewable_fraction_avg"] for m in metrics]),
            "avg_routing_fraction": np.mean([m["routing_fraction"] for m in metrics]),
            "avg_hold_fraction": np.mean([m["hold_fraction"] for m in metrics]),
            "std_reward": np.std(rewards),
            "std_carbon_saved": np.std(carbon_totals),
        }

    def get_learning_curves(self) -> Dict[str, List[float]]:
        """Get time series for plotting learning curves."""
        return {
            "rewards": [m["total_reward"] for m in self.episode_metrics],
            "carbon_saved": [m["carbon_saved_total"] for m in self.episode_metrics],
            "sla_compliance": [m["sla_compliance"] for m in self.episode_metrics],
            "renewable_fraction": [m["renewable_fraction_avg"] for m in self.episode_metrics],
            "routing_fraction": [m["routing_fraction"] for m in self.episode_metrics],
        }

    @staticmethod
    def compare_agents(agent_metrics: Dict[str, "MetricsTracker"]) -> Dict:
        """Compare summary metrics across multiple agents."""
        return {agent_name: tracker.get_summary() for agent_name, tracker in agent_metrics.items()}
