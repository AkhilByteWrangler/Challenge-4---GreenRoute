"""
Metrics tracking for GreenRoute evaluation.

Tracks carbon saved, cost saved, SLA compliance, renewable usage, 
and generates summary statistics for comparison across agents.
"""

import numpy as np
from typing import Dict, List, Optional
from collections import defaultdict


class MetricsTracker:
    """Comprehensive metrics tracking across episodes and agents."""

    def __init__(self):
        self.episode_metrics: List[Dict] = []
        self.current_episode = {
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

    def record_step(self, action: int, reward: float, info: dict):
        """Record metrics for a single step."""
        self.current_episode["total_reward"] += reward
        self.current_episode["jobs_processed"] += 1

        action_result = info.get("action_result", {})
        if action_result.get("sla_violated", False):
            self.current_episode["sla_violations"] += 1

        if action == 6:
            self.current_episode["jobs_held"] += 1
        elif action == 0:
            self.current_episode["jobs_local"] += 1
        else:
            self.current_episode["jobs_routed"] += 1

        carbon_saved = info.get("total_carbon_saved", 0.0)
        self.current_episode["carbon_saved"] = carbon_saved
        self.current_episode["cost_saved"] = info.get("total_cost_saved", 0.0)

        rf = action_result.get("renewable_fraction", 0.0)
        self.current_episode["renewable_fraction_sum"] += rf

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

        # Reset for next episode
        self.current_episode = {
            "carbon_saved": 0.0, "cost_saved": 0.0, "total_reward": 0.0,
            "jobs_processed": 0, "sla_violations": 0, "renewable_fraction_sum": 0.0,
            "jobs_routed": 0, "jobs_held": 0, "jobs_local": 0,
            "routing_decisions": [],
        }

        return summary

    def get_summary(self, last_n: Optional[int] = None) -> Dict:
        """Get aggregate summary across episodes."""
        metrics = self.episode_metrics
        if last_n is not None:
            metrics = metrics[-last_n:]

        if not metrics:
            return {"num_episodes": 0}

        return {
            "num_episodes": len(metrics),
            "avg_reward": np.mean([m["total_reward"] for m in metrics]),
            "avg_carbon_saved": np.mean([m["carbon_saved_total"] for m in metrics]),
            "avg_carbon_per_job": np.mean([m["carbon_saved_per_job"] for m in metrics]),
            "avg_sla_compliance": np.mean([m["sla_compliance"] for m in metrics]),
            "avg_renewable_fraction": np.mean([m["renewable_fraction_avg"] for m in metrics]),
            "avg_routing_fraction": np.mean([m["routing_fraction"] for m in metrics]),
            "avg_hold_fraction": np.mean([m["hold_fraction"] for m in metrics]),
            "std_reward": np.std([m["total_reward"] for m in metrics]),
            "std_carbon_saved": np.std([m["carbon_saved_total"] for m in metrics]),
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

    def compare_agents(agent_metrics: Dict[str, "MetricsTracker"]) -> Dict:
        """Compare summary metrics across multiple agents."""
        comparison = {}
        for agent_name, tracker in agent_metrics.items():
            comparison[agent_name] = tracker.get_summary()
        return comparison
