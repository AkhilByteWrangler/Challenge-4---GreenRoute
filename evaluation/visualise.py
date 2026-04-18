"""
Visualisation module for GreenRoute.

Generates training curves, comparison charts, and US map visualisations.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from typing import Dict, List, Optional
import os


# Data centre coordinates (lon, lat) for map plotting
DC_COORDS = {
    "CA": (-121.89, 37.33),
    "TX": (-96.80, 32.78),
    "VA": (-77.49, 39.04),
    "OR": (-122.68, 45.52),
    "AZ": (-112.07, 33.45),
}

DC_COLOURS = {
    "CA": "#FFB300",  # Amber/Gold (solar)
    "TX": "#00BCD4",  # Cyan (wind)
    "VA": "#F44336",  # Red-grey (mixed/fossil)
    "OR": "#4CAF50",  # Green (hydro)
    "AZ": "#FF9800",  # Orange (solar)
}

DC_LABELS = {
    "CA": "☀️ California",
    "TX": "💨 Texas",
    "VA": "🏭 Virginia",
    "OR": "💧 Oregon",
    "AZ": "☀️ Arizona",
}


class Visualiser:
    """Generates plots for training analysis and results presentation."""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        sns.set_theme(style="darkgrid")
        plt.rcParams.update({"figure.facecolor": "#1a1a2e", "axes.facecolor": "#16213e",
                            "text.color": "white", "axes.labelcolor": "white",
                            "xtick.color": "white", "ytick.color": "white"})

    def plot_learning_curves(self, curves: Dict[str, List[float]],
                            agent_name: str = "DQN", window: int = 20):
        """Plot training learning curves with smoothing."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"GreenRoute — {agent_name} Training Curves", fontsize=16, fontweight="bold")

        metrics = [
            ("rewards", "Episode Reward", "#00E676"),
            ("carbon_saved", "Carbon Saved (gCO₂)", "#FFD740"),
            ("sla_compliance", "SLA Compliance", "#FF5252"),
            ("renewable_fraction", "Renewable Fraction", "#40C4FF"),
        ]

        for ax, (key, title, colour) in zip(axes.flat, metrics):
            data = curves.get(key, [])
            if not data:
                continue

            episodes = range(len(data))
            ax.plot(episodes, data, alpha=0.3, color=colour, linewidth=0.5)

            # Smoothed line
            if len(data) >= window:
                smoothed = np.convolve(data, np.ones(window) / window, mode="valid")
                ax.plot(range(window - 1, len(data)), smoothed, color=colour, linewidth=2)

            ax.set_title(title, fontsize=12)
            ax.set_xlabel("Episode")

        plt.tight_layout()
        path = os.path.join(self.output_dir, f"learning_curves_{agent_name.lower()}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_agent_comparison(self, agent_summaries: Dict[str, Dict]):
        """Bar chart comparing all agents across key metrics."""
        fig, axes = plt.subplots(1, 4, figsize=(18, 5))
        fig.suptitle("GreenRoute — Agent Comparison", fontsize=16, fontweight="bold")

        metrics = [
            ("avg_carbon_per_job", "Carbon Saved per Job (gCO₂)", "#FFD740"),
            ("avg_sla_compliance", "SLA Compliance", "#FF5252"),
            ("avg_renewable_fraction", "Renewable Energy Used", "#40C4FF"),
            ("avg_reward", "Average Reward", "#00E676"),
        ]

        agents = list(agent_summaries.keys())
        colours_per_agent = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]

        for ax, (key, title, _) in zip(axes, metrics):
            values = [agent_summaries[a].get(key, 0) for a in agents]
            bars = ax.bar(agents, values, color=colours_per_agent[:len(agents)], edgecolor="white", linewidth=0.5)
            ax.set_title(title, fontsize=10)

            # Add value labels
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                       f"{val:.2f}", ha="center", va="bottom", fontsize=8, color="white")

        plt.tight_layout()
        path = os.path.join(self.output_dir, "agent_comparison.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_routing_map(self, episode_log: List[Dict], title: str = "Routing Decisions"):
        """Plot a simplified US map showing routing decisions."""
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.set_xlim(-130, -70)
        ax.set_ylim(25, 50)
        ax.set_title(f"GreenRoute — {title}", fontsize=16, fontweight="bold")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        # Draw US outline (simplified polygon)
        us_outline_x = [-125, -120, -115, -110, -105, -100, -95, -90, -85, -80, -75, -70,
                        -70, -80, -85, -90, -95, -100, -105, -110, -115, -120, -125]
        us_outline_y = [48, 49, 49, 45, 49, 49, 47, 47, 45, 40, 40, 42,
                        30, 25, 30, 29, 26, 26, 32, 32, 33, 34, 42]
        ax.fill(us_outline_x, us_outline_y, alpha=0.1, color="white", edgecolor="white", linewidth=1)

        # Draw data centre nodes
        for loc_id, (lon, lat) in DC_COORDS.items():
            colour = DC_COLOURS[loc_id]
            ax.scatter(lon, lat, s=300, c=colour, edgecolors="white", linewidth=2, zorder=5)
            ax.annotate(DC_LABELS[loc_id], (lon, lat), textcoords="offset points",
                       xytext=(10, 10), fontsize=10, color=colour, fontweight="bold")

        # Draw routing arcs
        route_counts = {}
        for entry in episode_log:
            origin = entry.get("job", {}).get("origin", "")
            dest = entry.get("destination", "")
            if origin and dest and origin != dest:
                key = (origin, dest)
                route_counts[key] = route_counts.get(key, 0) + 1

        max_count = max(route_counts.values()) if route_counts else 1
        for (origin, dest), count in route_counts.items():
            if origin in DC_COORDS and dest in DC_COORDS:
                ox, oy = DC_COORDS[origin]
                dx, dy = DC_COORDS[dest]
                alpha = min(0.8, 0.1 + 0.7 * count / max_count)
                width = 0.5 + 2.5 * count / max_count
                ax.annotate("", xy=(dx, dy), xytext=(ox, oy),
                           arrowprops=dict(arrowstyle="->", color="#00E676",
                                         alpha=alpha, lw=width,
                                         connectionstyle="arc3,rad=0.2"))

        ax.set_facecolor("#0d1117")
        fig.patch.set_facecolor("#0d1117")

        path = os.path.join(self.output_dir, "routing_map.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_carbon_timeline(self, baseline_carbon: List[float],
                            agent_carbon: List[float],
                            agent_name: str = "DQN"):
        """Plot cumulative carbon comparison over simulated hours."""
        fig, ax = plt.subplots(figsize=(12, 6))

        hours = np.arange(len(baseline_carbon)) * 0.25  # 15-min timesteps
        baseline_cum = np.cumsum(baseline_carbon)
        agent_cum = np.cumsum(agent_carbon)

        ax.fill_between(hours, baseline_cum, agent_cum, alpha=0.3, color="#00E676",
                        label="Carbon saved")
        ax.plot(hours, baseline_cum, color="#FF5252", linewidth=2, label="Baseline (local)")
        ax.plot(hours, agent_cum, color="#00E676", linewidth=2, label=f"{agent_name} agent")

        ax.set_title("GreenRoute — Cumulative Carbon Emissions Over 24h", fontsize=14, fontweight="bold")
        ax.set_xlabel("Simulated Hour")
        ax.set_ylabel("Cumulative CO₂ (grams)")
        ax.legend(loc="upper left")

        path = os.path.join(self.output_dir, "carbon_timeline.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path
