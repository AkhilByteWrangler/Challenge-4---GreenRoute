"""
Visualisation module for GreenRoute.

Generates training curves, comparison charts, and US map visualisations.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List
from collections import defaultdict
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
    "CA": "#FFB300",
    "TX": "#00BCD4",
    "VA": "#F44336",
    "OR": "#4CAF50",
    "AZ": "#FF9800",
}

DC_LABELS = {
    "CA": "California",
    "TX": "Texas",
    "VA": "Virginia",
    "OR": "Oregon",
    "AZ": "Arizona",
}

# Plotting constants
FIGURE_DPI = 150
PLOT_ALPHA_RAW = 0.3
PLOT_ALPHA_OUTLINE = 0.1
PLOT_ALPHA_MAX = 0.8
LINEWIDTH_THIN = 0.5
LINEWIDTH_THICK = 2
FONT_SIZE_TITLE = 16
FONT_SIZE_SUBTITLE = 12
FONT_SIZE_LABEL = 10
FONT_SIZE_TICK = 8

# Colour palette
COLOR_PRIMARY = "#00E676"
COLOR_ACCENT_YELLOW = "#FFD740"
COLOR_ACCENT_RED = "#FF5252"
COLOR_ACCENT_BLUE = "#40C4FF"
COLOR_AGENT_1 = "#FF6B6B"
COLOR_AGENT_2 = "#4ECDC4"
COLOR_AGENT_3 = "#45B7D1"
COLOR_AGENT_4 = "#96CEB4"
COLOR_AGENT_5 = "#FFEAA7"
AGENT_COLORS = [COLOR_AGENT_1, COLOR_AGENT_2, COLOR_AGENT_3, COLOR_AGENT_4, COLOR_AGENT_5]

# US map bounds and outline
US_MAP_LON_MIN, US_MAP_LON_MAX = -130, -70
US_MAP_LAT_MIN, US_MAP_LAT_MAX = 25, 50
US_OUTLINE_X = [-125, -120, -115, -110, -105, -100, -95, -90, -85, -80, -75, -70,
                -70, -80, -85, -90, -95, -100, -105, -110, -115, -120, -125]
US_OUTLINE_Y = [48, 49, 49, 45, 49, 49, 47, 47, 45, 40, 40, 42,
                30, 25, 30, 29, 26, 26, 32, 32, 33, 34, 42]
US_OUTLINE_ALPHA = 0.1

# Routing arc visualization
ARC_ALPHA_MIN = 0.1
ARC_ALPHA_RANGE = 0.7
ARC_WIDTH_MIN = 0.5
ARC_WIDTH_MAX = 2.5
SCATTER_SIZE = 300

# Dark theme colors
BG_DARK = "#0d1117"
BG_DARKER = "#1a1a2e"
BG_DARK_SECONDARY = "#16213e"

# Timestamps
TIMESTEP_HOURS = 0.25


class Visualiser:
    """Generates plots for training analysis and results presentation."""

    def __init__(self, output_dir: str = "outputs") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        sns.set_theme(style="darkgrid")
        plt.rcParams.update({"figure.facecolor": BG_DARKER, "axes.facecolor": BG_DARK_SECONDARY,
                            "text.color": "white", "axes.labelcolor": "white",
                            "xtick.color": "white", "ytick.color": "white"})

    def plot_learning_curves(self, curves: Dict[str, List[float]],
                            agent_name: str = "DQN", window: int = 20) -> str:
        """Plot training learning curves with smoothing."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"GreenRoute — {agent_name} Training Curves", fontsize=FONT_SIZE_TITLE, fontweight="bold")

        metrics = [
            ("rewards", "Episode Reward", COLOR_PRIMARY),
            ("carbon_saved", "Carbon Saved (gCO₂)", COLOR_ACCENT_YELLOW),
            ("sla_compliance", "SLA Compliance", COLOR_ACCENT_RED),
            ("renewable_fraction", "Renewable Fraction", COLOR_ACCENT_BLUE),
        ]

        kernel = np.ones(window) / window
        for ax, (key, title, color) in zip(axes.flat, metrics):
            data = curves.get(key, [])
            if not data:
                continue

            ax.plot(range(len(data)), data, alpha=PLOT_ALPHA_RAW, color=color, linewidth=LINEWIDTH_THIN)
            if len(data) >= window:
                smoothed = np.convolve(data, kernel, mode="valid")
                ax.plot(range(window - 1, len(data)), smoothed, color=color, linewidth=LINEWIDTH_THICK)

            ax.set_title(title, fontsize=FONT_SIZE_SUBTITLE)
            ax.set_xlabel("Episode")

        plt.tight_layout()
        path = os.path.join(self.output_dir, f"learning_curves_{agent_name.lower()}.png")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_agent_comparison(self, agent_summaries: Dict[str, Dict]) -> str:
        """Bar chart comparing all agents across key metrics."""
        fig, axes = plt.subplots(1, 4, figsize=(18, 5))
        fig.suptitle("GreenRoute — Agent Comparison", fontsize=FONT_SIZE_TITLE, fontweight="bold")

        metrics = [
            ("avg_carbon_per_job", "Carbon Saved per Job (gCO₂)", COLOR_ACCENT_YELLOW),
            ("avg_sla_compliance", "SLA Compliance", COLOR_ACCENT_RED),
            ("avg_renewable_fraction", "Renewable Energy Used", COLOR_ACCENT_BLUE),
            ("avg_reward", "Average Reward", COLOR_PRIMARY),
        ]

        agents = list(agent_summaries.keys())
        agent_colors = AGENT_COLORS[:len(agents)]

        for ax, (key, title, _) in zip(axes, metrics):
            values = [agent_summaries[a].get(key, 0) for a in agents]
            bars = ax.bar(agents, values, color=agent_colors, edgecolor="white", linewidth=LINEWIDTH_THIN)
            ax.set_title(title, fontsize=FONT_SIZE_LABEL)

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                       f"{val:.2f}", ha="center", va="bottom", fontsize=FONT_SIZE_TICK, color="white")

        plt.tight_layout()
        path = os.path.join(self.output_dir, "agent_comparison.png")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_routing_map(self, episode_log: List[Dict], title: str = "Routing Decisions") -> str:
        """Plot a simplified US map showing routing decisions."""
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.set_xlim(US_MAP_LON_MIN, US_MAP_LON_MAX)
        ax.set_ylim(US_MAP_LAT_MIN, US_MAP_LAT_MAX)
        ax.set_title(f"GreenRoute — {title}", fontsize=FONT_SIZE_TITLE, fontweight="bold")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        ax.fill(US_OUTLINE_X, US_OUTLINE_Y, alpha=US_OUTLINE_ALPHA, color="white", edgecolor="white", linewidth=1)

        for loc_id, (lon, lat) in DC_COORDS.items():
            color = DC_COLOURS[loc_id]
            ax.scatter(lon, lat, s=SCATTER_SIZE, c=color, edgecolors="white", linewidth=LINEWIDTH_THICK, zorder=5)
            ax.annotate(DC_LABELS[loc_id], (lon, lat), textcoords="offset points",
                       xytext=(10, 10), fontsize=FONT_SIZE_LABEL, color=color, fontweight="bold")

        route_counts = defaultdict(int)
        for entry in episode_log:
            origin = entry.get("job", {}).get("origin", "")
            dest = entry.get("destination", "")
            if origin and dest and origin != dest:
                route_counts[(origin, dest)] += 1

        max_count = max(route_counts.values()) if route_counts else 1
        for (origin, dest), count in route_counts.items():
            if origin in DC_COORDS and dest in DC_COORDS:
                ox, oy = DC_COORDS[origin]
                dx, dy = DC_COORDS[dest]
                normalized = count / max_count
                alpha = min(PLOT_ALPHA_MAX, ARC_ALPHA_MIN + ARC_ALPHA_RANGE * normalized)
                width = ARC_WIDTH_MIN + ARC_WIDTH_MAX * normalized
                ax.annotate("", xy=(dx, dy), xytext=(ox, oy),
                           arrowprops=dict(arrowstyle="->", color=COLOR_PRIMARY,
                                         alpha=alpha, lw=width,
                                         connectionstyle="arc3,rad=0.2"))

        ax.set_facecolor(BG_DARK)
        fig.patch.set_facecolor(BG_DARK)

        path = os.path.join(self.output_dir, "routing_map.png")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path

    def plot_carbon_timeline(self, baseline_carbon: List[float],
                            agent_carbon: List[float],
                            agent_name: str = "DQN") -> str:
        """Plot cumulative carbon comparison over simulated hours."""
        fig, ax = plt.subplots(figsize=(12, 6))

        hours = np.arange(len(baseline_carbon)) * TIMESTEP_HOURS
        baseline_cum = np.cumsum(baseline_carbon)
        agent_cum = np.cumsum(agent_carbon)

        ax.fill_between(hours, baseline_cum, agent_cum, alpha=PLOT_ALPHA_RAW, color=COLOR_PRIMARY,
                        label="Carbon saved")
        ax.plot(hours, baseline_cum, color=COLOR_ACCENT_RED, linewidth=LINEWIDTH_THICK, label="Baseline (local)")
        ax.plot(hours, agent_cum, color=COLOR_PRIMARY, linewidth=LINEWIDTH_THICK, label=f"{agent_name} agent")

        ax.set_title("GreenRoute — Cumulative Carbon Emissions Over 24h", fontsize=FONT_SIZE_TITLE, fontweight="bold")
        ax.set_xlabel("Simulated Hour")
        ax.set_ylabel("Cumulative CO₂ (grams)")
        ax.legend(loc="upper left")

        path = os.path.join(self.output_dir, "carbon_timeline.png")
        fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close(fig)
        return path
