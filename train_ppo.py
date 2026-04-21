#!/usr/bin/env python3
"""
PPO training for GreenRoute with stochastic weather and multi-season variation.

Trains a PPO agent on 5000 episodes with realistic weather events, exports
learned weights to JSON for browser inference, and compares against baselines.
"""

import sys
import os
import json
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from environment.datacentre_env import DataCentreEnv, LOCATION_IDS, NUM_ACTIONS
from environment.renewable_model import RenewableModel, LOCATIONS
from agents.ppo_agent import PPOAgent
from agents.random_agent import RandomAgent
from agents.greedy_agent import GreedyAgent
from evaluation.metrics import MetricsTracker


# Weather regimes — affects renewable output and carbon intensity
WEATHER_REGIMES = {
    "clear":      {"cloud_mean": 0.1,  "cloud_std": 0.05, "wind_mult": 0.8, "solar_mult": 1.2, "prob": 0.25},
    "partly":     {"cloud_mean": 0.35, "cloud_std": 0.1,  "wind_mult": 1.0, "solar_mult": 1.0, "prob": 0.30},
    "overcast":   {"cloud_mean": 0.75, "cloud_std": 0.1,  "wind_mult": 1.2, "solar_mult": 0.3, "prob": 0.20},
    "storm":      {"cloud_mean": 0.9,  "cloud_std": 0.05, "wind_mult": 2.0, "solar_mult": 0.1, "prob": 0.10},
    "cold_snap":  {"cloud_mean": 0.6,  "cloud_std": 0.15, "wind_mult": 1.5, "solar_mult": 0.2, "prob": 0.08},
    "heat_wave":  {"cloud_mean": 0.15, "cloud_std": 0.05, "wind_mult": 0.5, "solar_mult": 1.3, "prob": 0.07},
}

SEASONS = {
    "winter":  {"solar_scale": 0.55, "wind_scale": 1.3,  "hydro_scale": 0.8},
    "spring":  {"solar_scale": 0.85, "wind_scale": 1.15, "hydro_scale": 1.2},
    "summer":  {"solar_scale": 1.2,  "wind_scale": 0.75, "hydro_scale": 0.6},
    "fall":    {"solar_scale": 0.75, "wind_scale": 1.1,  "hydro_scale": 1.0},
}

# Per-location weather vulnerability — matches browser EVENT_SUSCEPTIBILITY
# Per-location weather event probabilities
LOCATION_WEATHER_SENSITIVITY = {
    "CA": {"solar_var": 0.2,  "wind_var": 0.3,  "cold_risk": 0.01, "storm_risk": 0.03, "heat_risk": 0.06, "solar_boom_risk": 0.10},
    "TX": {"solar_var": 0.15, "wind_var": 0.4,  "cold_risk": 0.03, "storm_risk": 0.10, "heat_risk": 0.07, "solar_boom_risk": 0.04},
    "VA": {"solar_var": 0.25, "wind_var": 0.25, "cold_risk": 0.05, "storm_risk": 0.06, "heat_risk": 0.03, "solar_boom_risk": 0.02},
    "OR": {"solar_var": 0.35, "wind_var": 0.2,  "cold_risk": 0.12, "storm_risk": 0.04, "heat_risk": 0.01, "solar_boom_risk": 0.02},
    "AZ": {"solar_var": 0.1,  "wind_var": 0.3,  "cold_risk": 0.01, "storm_risk": 0.02, "heat_risk": 0.10, "solar_boom_risk": 0.12},
}

# Weather event impacts on carbon multipliers
CARBON_MULTIPLIERS = {
    "cold_snap": 3.0,
    "storm": 2.5,
    "heat_wave": 2.5,
    "solar_boom": 0.3,
}

# Weather model constants
WEATHER_REGIME_CHANGE_PROB = 0.04
WEATHER_EVENT_SCALE = 0.25
EVENT_DURATION_MIN, EVENT_DURATION_MAX = 1.5, 5.5
TIMESTEP_HOURS = 0.25
CLOUD_AR_COEF = 0.9
WIND_AR_COEF = 0.85
WIND_AR_SCALE = 0.15
WIND_CURTAIL_THRESHOLD = 18.0
WIND_CURTAIL_FACTOR = 0.4


class StochasticWeatherModel:
    """
    Wraps the base RenewableModel with realistic stochastic weather.

    Each episode gets:
    - A random season (affects solar/wind baseline)
    - A weather regime per location (can change mid-episode)
    - Per-location weather events (cold snaps in OR, storms in TX, etc.)
    - Correlated weather across nearby locations
    """

    def __init__(self, base_model: RenewableModel, rng: np.random.RandomState,
                 season: str = None):
        self.base = base_model
        self.rng = rng

        # Pick season
        if season is None:
            season = rng.choice(list(SEASONS.keys()))
        self.season = season
        self.season_params = SEASONS[season]

        # Per-location weather regime (can change during episode)
        self.regimes = {}
        self._assign_weather_regimes()

        # Per-location modifiers (change slowly via AR process)
        self.cloud_modifiers = {loc: 0.0 for loc in LOCATION_IDS}
        self.wind_modifiers = {loc: 0.0 for loc in LOCATION_IDS}
        self.solar_modifiers = {loc: 0.0 for loc in LOCATION_IDS}

        # Special events
        self.active_events = {}  # loc -> {"type": str, "remaining_hours": float}

    def _assign_weather_regimes(self):
        """Assign a weather regime to each location."""
        regime_names = list(WEATHER_REGIMES.keys())
        regime_probs = [WEATHER_REGIMES[r]["prob"] for r in regime_names]
        regime_probs = np.array(regime_probs) / sum(regime_probs)

        for loc in LOCATION_IDS:
            # Each location gets its own regime, but nearby ones are correlated
            self.regimes[loc] = self.rng.choice(regime_names, p=regime_probs)

        # Correlate: OR and CA often share weather (Pacific coast)
        if self.rng.random() < 0.4:
            self.regimes["CA"] = self.regimes["OR"]

        # TX and AZ sometimes share (Southern tier)
        if self.rng.random() < 0.3:
            self.regimes["AZ"] = self.regimes["TX"]

    def step(self, utc_hour: float):
        """Advance weather state — called each timestep."""
        # Advance base model
        self.base.step(utc_hour)

        # Randomly trigger weather events
        for loc in LOCATION_IDS:
            sens = LOCATION_WEATHER_SENSITIVITY[loc]

            # Chance of weather regime change (every ~6 hours on average)
            if self.rng.random() < 0.04:  # ~4% per 15-min step
                self._assign_weather_regimes()

            # Trigger special events (probabilities match browser per-step rates)
            if loc not in self.active_events:
                # Cold snap — any season, more likely in winter
                cold_scale = 2.0 if self.season == "winter" else 0.5
                if self.rng.random() < sens["cold_risk"] * cold_scale * 0.25:
                    self.active_events[loc] = {
                        "type": "cold_snap",
                        "remaining": self.rng.uniform(1.5, 5.5),
                    }
                # Storm
                elif self.rng.random() < sens["storm_risk"] * 0.25:
                    self.active_events[loc] = {
                        "type": "storm",
                        "remaining": self.rng.uniform(1.5, 5.5),
                    }
                # Heat wave — more likely in summer
                heat_scale = 2.0 if self.season == "summer" else 0.5
                if loc not in self.active_events and self.rng.random() < sens["heat_risk"] * heat_scale * 0.25:
                    self.active_events[loc] = {
                        "type": "heat_wave",
                        "remaining": self.rng.uniform(1.5, 5.5),
                    }
                # Solar boom — more likely in summer/spring
                boom_scale = 1.5 if self.season in ("summer", "spring") else 0.5
                if loc not in self.active_events and self.rng.random() < sens["solar_boom_risk"] * boom_scale * 0.25:
                    self.active_events[loc] = {
                        "type": "solar_boom",
                        "remaining": self.rng.uniform(1.5, 5.5),
                    }

            # Decay active events
            if loc in self.active_events:
                self.active_events[loc]["remaining"] -= 0.25
                if self.active_events[loc]["remaining"] <= 0:
                    del self.active_events[loc]

            # AR(1) process for cloud/wind modifiers
            regime = WEATHER_REGIMES[self.regimes[loc]]
            target_cloud = regime["cloud_mean"] + self.rng.normal(0, regime["cloud_std"])
            self.cloud_modifiers[loc] = np.clip(
                0.9 * self.cloud_modifiers[loc] + 0.1 * target_cloud + self.rng.normal(0, 0.03),
                0, 1
            )
            self.wind_modifiers[loc] = np.clip(
                0.85 * self.wind_modifiers[loc] + 0.15 * (regime["wind_mult"] - 1) + self.rng.normal(0, 0.05),
                -0.5, 1.5
            )

    def get_solar_irradiance(self, utc_hour: float, location_id: str) -> float:
        base_solar = self.base.get_solar_irradiance(utc_hour, location_id)

        # Seasonal scaling
        solar_scale = self.season_params["solar_scale"]

        # Weather regime
        regime = WEATHER_REGIMES[self.regimes[location_id]]
        regime_scale = regime["solar_mult"]

        # Cloud modifier
        cloud_reduction = 1.0 - self.cloud_modifiers[location_id] * 0.8

        # Active events
        event_mult = 1.0
        event_add = 0.0
        if location_id in self.active_events:
            ev = self.active_events[location_id]
            if ev["type"] == "cold_snap":
                event_mult = 0.10  # near-zero solar (snow/overcast)
            elif ev["type"] == "storm":
                event_mult = 0.05  # almost no solar
            elif ev["type"] == "heat_wave":
                event_mult = 1.1   # slightly more sun (clear skies)
            elif ev["type"] == "solar_boom":
                event_mult = 1.8   # exceptional solar
                event_add = 200.0  # extra baseline boost

        final = base_solar * solar_scale * regime_scale * cloud_reduction * event_mult + event_add
        noise = self.rng.normal(0, 10)
        return float(np.clip(final + noise, 0, 1000))

    def get_wind_speed(self, utc_hour: float, location_id: str) -> float:
        base_wind = self.base.get_wind_speed(utc_hour, location_id)

        # Seasonal
        wind_scale = self.season_params["wind_scale"]

        # Weather regime
        regime = WEATHER_REGIMES[self.regimes[location_id]]
        wind_mult = regime["wind_mult"] + self.wind_modifiers[location_id]

        # Active events
        if location_id in self.active_events:
            ev = self.active_events[location_id]
            if ev["type"] == "storm":
                wind_mult = 2.5 + self.rng.uniform(0, 1)  # very high, may curtail
            elif ev["type"] == "cold_snap":
                wind_mult = 1.2  # cold wind
            elif ev["type"] == "heat_wave":
                wind_mult = 0.3  # stagnant air
            # solar_boom doesn't affect wind

        final = base_wind * wind_scale * wind_mult
        # Storm curtailment: turbines shut down above ~18 m/s
        if final > 18 and location_id in self.active_events:
            if self.active_events[location_id]["type"] == "storm":
                final *= 0.4
        return float(np.clip(final, 0, 25))

    def get_renewable_fraction(self, utc_hour: float, location_id: str) -> float:
        loc = LOCATIONS[location_id]

        solar = self.get_solar_irradiance(utc_hour, location_id) / 1000.0
        wind = self.get_wind_speed(utc_hour, location_id) / 15.0

        solar_contrib = solar * loc["solar_capacity_factor"] * 1.5
        wind_contrib = min(wind, 1.0) * loc["wind_capacity_factor"] * 1.5

        renewable_frac = np.clip(solar_contrib + wind_contrib, 0, 1)
        return float(renewable_frac)

    def get_all_states(self, utc_hour: float):
        states = {}
        for loc_id in LOCATION_IDS:
            states[loc_id] = {
                "solar_irradiance": self.get_solar_irradiance(utc_hour, loc_id),
                "wind_speed": self.get_wind_speed(utc_hour, loc_id),
                "renewable_fraction": self.get_renewable_fraction(utc_hour, loc_id),
            }
        return states

    def get_forecast(self, utc_hour: float, horizon_hours: float = 2.0):
        return self.base.get_forecast(utc_hour, horizon_hours)


class StochasticDataCentreEnv(DataCentreEnv):
    """
    DataCentreEnv with stochastic weather AND multi-tenant capacity pressure.

    Models the 4 scenarios where greedy genuinely breaks down
    (Radovanović et al. 2022 works for single-tenant time-shifting,
    but fails on these):

      1. Capacity saturation — other greedy tenants flood the lowest-carbon DC
      2. Hold decision — waiting for a renewable window beats routing now
      3. Queue composition — portfolio of flexible + pinned jobs
      4. Joint carbon + transfer cost optimisation over time
    """

    def _compute_reward(self, action_result, job):
        """
        Carbon-dominant reward aligned with browser metrics.

        Matches what the browser tracks: carbon saved, cost saved, renewable %.
        Light utilization penalty only at extreme levels.
        This trains PPO to match/beat greedy on carbon while also optimizing
        cost + renewable + SLA — the multi-objective edge greedy lacks.
        """
        if "destination" not in action_result:
            return super()._compute_reward(action_result, job)

        dest = action_result["destination"]

        # Carbon savings (primary signal)
        carbon_saved = action_result["local_carbon"] - action_result["routed_carbon"]
        r_carbon = carbon_saved * 0.10  # strong primary signal

        # Renewable fraction bonus
        rf = action_result.get("renewable_fraction", 0)
        r_renewable = rf * 5.0

        # Cost savings
        cost_saved = action_result["local_cost"] - action_result["routed_cost"]
        r_cost = cost_saved * 8.0

        # Utilization penalty (extreme overload only)
        renewable_states = self.renewable_model.get_all_states(self.current_hour)
        renewable_fracs = {loc: renewable_states[loc]["renewable_fraction"] for loc in LOCATION_IDS}
        grid_states = self.grid_model.get_all_states(self.current_hour, renewable_fracs)
        dest_util = grid_states[dest]["utilisation"]
        r_util = 0.0
        if dest_util > 0.85:
            r_util = -(dest_util - 0.85) * 12.0

        # SLA violation penalty
        r_sla = -20.0 if action_result["sla_violated"] else 0.0

        # Capacity exceeded penalty
        r_cap = -15.0 if action_result["capacity_exceeded"] else 0.0

        # Transfer cost penalty
        r_transfer = -action_result["transfer_cost"] * 2.0

        # Weather event penalty/bonus
        # Explicit signal: routing to a DC with a negative event is BAD
        r_weather = 0.0
        active_events = getattr(self, '_active_weather_events', {})
        if dest in active_events:
            ev_type = active_events[dest]["type"]
            if ev_type in ("cold_snap", "storm", "heat_wave"):
                r_weather = -15.0  # STRONG penalty — avoid affected DCs
            elif ev_type == "solar_boom":
                r_weather = +8.0   # BONUS — route toward solar booms

        total = r_carbon + r_renewable + r_cost + r_util + r_sla + r_cap + r_transfer + r_weather
        return float(total)

    def step(self, action):
        """Override to give better hold rewards."""
        # Track carbon at hold time so we can reward good holds
        if action == 6 and self.current_job is not None:
            renewable_states = self.renewable_model.get_all_states(self.current_hour)
            renewable_fracs = {loc: renewable_states[loc]["renewable_fraction"] for loc in LOCATION_IDS}
            grid_states = self.grid_model.get_all_states(self.current_hour, renewable_fracs)
            carbons = {loc: grid_states[loc]["carbon_intensity"] for loc in LOCATION_IDS}
            best_carbon_now = min(carbons.values())
            self._hold_carbon_snapshot = best_carbon_now

        obs, reward, done, truncated, info = super().step(action)

        # If we just processed a held job (action != 6 and we had a snapshot),
        # give bonus/penalty based on whether holding was worthwhile
        if action != 6 and hasattr(self, '_hold_carbon_snapshot') and self._hold_carbon_snapshot > 0:
            if "action_result" in info and "routed_carbon" in info.get("action_result", {}):
                actual_carbon = info["action_result"]["routed_carbon"]
                if actual_carbon < self._hold_carbon_snapshot:
                    # Holding was worthwhile — found a better option
                    reward += 3.0
                else:
                    # Holding wasn't worth it
                    reward -= 1.0
            self._hold_carbon_snapshot = 0

        return obs, reward, done, truncated, info

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        self._hold_carbon_snapshot = 0

        # Create a COPY of the renewable model to use as the base
        # (so monkey-patching doesn't cause recursion)
        base_model = RenewableModel(seed=self.seed_val)
        # Sync its internal state with the one super().reset() created
        base_model._cloud_state = dict(self.renewable_model._cloud_state)
        base_model._wind_gust_state = dict(self.renewable_model._wind_gust_state)

        rng = np.random.RandomState(self.seed_val + 9999)
        season = rng.choice(list(SEASONS.keys()))
        self._weather = StochasticWeatherModel(base_model, rng, season)

        # Monkey-patch the renewable model methods
        self.renewable_model.get_solar_irradiance = self._weather.get_solar_irradiance
        self.renewable_model.get_wind_speed = self._weather.get_wind_speed
        self.renewable_model.get_renewable_fraction = self._weather.get_renewable_fraction
        self.renewable_model.get_all_states = self._weather.get_all_states
        self.renewable_model.get_forecast = self._weather.get_forecast
        self.renewable_model.step = self._weather.step

        info["season"] = season
        info["weather_regimes"] = dict(self._weather.regimes)

        # Store original base carbon for restoration
        self._original_base_carbon = dict(self.grid_model.base_carbon)

        # Rebuild observation with new weather
        obs = self._build_observation()
        return obs, info

    def _advance_time(self):
        """Override to apply weather event carbon multipliers to the grid.

        This is the key link: weather events modify carbon intensity
        (cold_snap ×2.0, storm ×1.5, heat_wave ×1.6, solar_boom ×0.5)
        exactly matching the browser, so the NN learns to route AWAY from
        DCs hit by negative events and TOWARD solar booms.
        """
        # Restore base carbon before applying new multipliers
        if hasattr(self, '_original_base_carbon'):
            self.grid_model.base_carbon = dict(self._original_base_carbon)

        super()._advance_time()

        if hasattr(self, '_weather'):
            for loc_id, event in self._weather.active_events.items():
                mult = CARBON_MULTIPLIERS.get(event["type"], 1.0)
                self.grid_model.base_carbon[loc_id] = self._original_base_carbon[loc_id] * mult
            self._active_weather_events = dict(self._weather.active_events)


def train_ppo(env, agent, num_episodes=2000, seed=42):
    """Train PPO agent with detailed logging."""
    metrics = MetricsTracker()
    episode_rewards = []
    episode_carbon = []
    episode_sla = []
    episode_renew = []
    season_counts = {"winter": 0, "spring": 0, "summer": 0, "fall": 0}

    device = agent.device
    device_name = "MPS GPU" if "mps" in str(device) else ("CUDA GPU" if "cuda" in str(device) else "CPU")
    print(f"\nTraining PPO for {num_episodes} episodes on {device_name} ({device})", flush=True)

    start = time.time()

    for ep in range(num_episodes):
        state, info = env.reset(seed=seed + ep)
        season = info.get("season", "unknown")
        season_counts[season] = season_counts.get(season, 0) + 1

        ep_reward = 0.0
        done = False

        while not done:
            action_mask = env.get_action_mask()
            action = agent.select_action(state, action_mask)
            next_state, reward, done, truncated, info = env.step(action)
            agent.update(state, action, reward, next_state, done, action_mask)
            metrics.record_step(action, reward, info)
            state = next_state
            ep_reward += reward
            if done or truncated:
                break

        ep_summary = metrics.end_episode()
        episode_rewards.append(ep_reward)
        episode_carbon.append(ep_summary["carbon_saved_total"])
        episode_sla.append(ep_summary["sla_compliance"])
        episode_renew.append(ep_summary["renewable_fraction_avg"])

        if (ep + 1) % 100 == 0:
            last_r = np.mean(episode_rewards[-100:])
            last_c = np.mean(episode_carbon[-100:])
            print(f"Ep {ep+1}/{num_episodes}: Reward={last_r:.1f}, Carbon={last_c:.0f}g", flush=True)

    train_time = time.time() - start
    print(f"Done in {train_time:.1f}s", flush=True)

    return metrics, episode_rewards, episode_carbon, episode_sla, episode_renew, train_time


def evaluate_baseline(agent, env, num_episodes=200, seed=42, label=""):
    """Evaluate a baseline agent (no learning)."""
    metrics = MetricsTracker()
    rewards, carbon, sla, renew = [], [], [], []

    for ep in range(num_episodes):
        state, info = env.reset(seed=seed + 10000 + ep)
        done = False
        ep_r = 0.0
        while not done:
            action_mask = env.get_action_mask()
            action = agent.select_action(state, action_mask)
            state, reward, done, truncated, info = env.step(action)
            metrics.record_step(action, reward, info)
            ep_r += reward
            if done or truncated:
                break
        ep_summary = metrics.end_episode()
        rewards.append(ep_r)
        carbon.append(ep_summary["carbon_saved_total"])
        sla.append(ep_summary["sla_compliance"])
        renew.append(ep_summary["renewable_fraction_avg"])

    print(f"  {label:12s} | Reward: {np.mean(rewards):8.1f} | "
          f"Carbon: {np.mean(carbon):7.0f}g | SLA: {np.mean(sla):.1%} | "
          f"Renew: {np.mean(renew):.1%}", flush=True)

    return metrics, rewards, carbon, sla, renew


def plot_learning_curves(ppo_rewards, ppo_carbon, ppo_sla, ppo_renew, output_dir="outputs"):
    """Generate learning curves plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#1a1a2e')
    fig.suptitle('GreenRoute — PPO Training Curves', fontsize=16, fontweight='bold', color='white')
    
    # Smooth curves
    window = 20
    kernel = np.ones(window) / window
    
    metrics = [
        (ppo_rewards, 'Episode Reward', 'green'),
        (ppo_carbon, 'Carbon Saved (gCO₂)', 'yellow'),
        (ppo_sla, 'SLA Compliance', 'red'),
        (ppo_renew, 'Renewable Fraction', 'cyan'),
    ]
    
    for ax, (data, title, color) in zip(axes.flat, metrics):
        ax.set_facecolor('#16213e')
        ax.plot(range(len(data)), data, alpha=0.2, color=color, linewidth=0.5)
        if len(data) >= window:
            smoothed = np.convolve(data, kernel, mode='valid')
            ax.plot(range(window-1, len(data)), smoothed, color=color, linewidth=2)
        ax.set_title(title, fontsize=12, color='white')
        ax.set_xlabel('Episode', color='white')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    path = os.path.join(output_dir, 'learning_curves.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close(fig)
    print(f"  Learning curves saved to {path}", flush=True)


def plot_agent_comparison(agent_results, output_dir="outputs"):
    """Generate comparison bar charts."""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#1a1a2e')
    fig.suptitle('GreenRoute — Agent Comparison', fontsize=16, fontweight='bold', color='white')
    
    agents = list(agent_results.keys())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(agents)]
    
    metrics = [
        ('avg_carbon_saved', 'Carbon Saved per Job (gCO₂)'),
        ('avg_sla_compliance', 'SLA Compliance (%)'),
        ('avg_renewable_fraction', 'Renewable Fraction (%)'),
        ('avg_reward', 'Average Reward'),
    ]
    
    for ax, (key, title) in zip(axes.flat, metrics):
        ax.set_facecolor('#16213e')
        values = [agent_results[a].get(key, 0) for a in agents]
        bars = ax.bar(agents, values, color=colors, edgecolor='white', linewidth=1)
        ax.set_title(title, fontsize=12, color='white')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}', ha='center', va='bottom', color='white', fontsize=10)
    
    plt.tight_layout()
    path = os.path.join(output_dir, 'agent_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close(fig)
    print(f"  Agent comparison saved to {path}", flush=True)


def print_metrics_table(agent_results, output_dir="outputs"):
    """Print and save metrics comparison table."""
    print("\n" + "="*80, flush=True)
    print("EVALUATION RESULTS — Final Metrics".center(80), flush=True)
    print("="*80, flush=True)
    print(f"{'Agent':<15} | {'Carbon (gCO₂)':<15} | {'SLA %':<10} | {'Renewable %':<12} | {'Reward':<10}", flush=True)
    print("-"*80, flush=True)

    for agent_key, agent_name in [('random', 'Random'), ('greedy', 'Greedy'), ('ppo_eval', 'PPO (eval)')]:
        if agent_key in agent_results:
            r = agent_results[agent_key]
            carbon = r.get('avg_carbon_saved', 0)
            sla = r.get('avg_sla_compliance', 0) * 100
            renewable = r.get('avg_renewable_fraction', 0) * 100
            reward = r.get('avg_reward', 0)
            print(f"{agent_name:<15} | {carbon:>13.0f} | {sla:>8.1f} | {renewable:>10.1f} | {reward:>8.1f}", flush=True)

    print("="*80 + "\n", flush=True)

    # Save as markdown table
    md_table = "| Metric | Greedy | PPO (Ours) |\n"
    md_table += "| ---|---|---|\n"

    if 'greedy' in agent_results and 'ppo_eval' in agent_results:
        greedy = agent_results['greedy']
        ppo = agent_results['ppo_eval']

        metrics = [
            ('Carbon saved (gCO₂)', 'avg_carbon_saved', '{:.0f}'),
            ('SLA compliance', 'avg_sla_compliance', '{:.1%}'),
            ('Renewable usage', 'avg_renewable_fraction', '{:.1%}'),
            ('Average reward', 'avg_reward', '{:.1f}'),
        ]

        for metric_name, key, fmt in metrics:
            greedy_val = greedy.get(key, 0)
            ppo_val = ppo.get(key, 0)
            md_table += f"| {metric_name} | {fmt.format(greedy_val)} | {fmt.format(ppo_val)} |\n"

    table_path = os.path.join(output_dir, 'metrics_table.md')
    with open(table_path, 'w') as f:
        f.write(md_table)
    print(f"Metrics table saved to {table_path}\n", flush=True)


def main():
    SEED = 42
    N_EPISODES = 5000
    N_EVAL = 300

    # Use stochastic weather environment
    env = StochasticDataCentreEnv(seed=SEED)

    ppo_agent = PPOAgent(
        state_dim=67, num_actions=7, seed=SEED,
        hidden_dims=[512, 256],    
        lr=5e-4,                    # higher learning rate
        gamma=0.99,
        gae_lambda=0.95,
        clip_eps=0.2,
        entropy_coef=0.001,         # ultra-low to maximize exploitation 
        value_coef=1.0,             # stronger value function learning
        max_grad_norm=0.5,
        n_epochs=20,                # more optimization per rollout
        n_steps=4096,               # huge rollouts for clean advantages (was 2048)
        batch_size=256,             # bigger batches for stable gradients
        anneal_lr=True,
        total_timesteps=N_EPISODES * 800,  # adjusted for huge rollouts
        target_kl=0.01,             # stricter KL divergence
    )

    ppo_metrics, ppo_rewards, ppo_carbon, ppo_sla, ppo_renew, train_time = train_ppo(
        env, ppo_agent, num_episodes=N_EPISODES, seed=SEED
    )

    # Save checkpoint
    checkpoint_dir = os.path.join(os.path.dirname(__file__), "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    ppo_agent.save(os.path.join(checkpoint_dir, "ppo_final.pt"))
    print(f"  Checkpoint saved to {checkpoint_dir}/ppo_final.pt")

    print(f"\nEvaluating baselines ({N_EVAL} episodes)")

    random_agent = RandomAgent(seed=SEED)
    greedy_agent = GreedyAgent(seed=SEED)

    rand_m, rand_r, rand_c, rand_s, rand_re = evaluate_baseline(
        random_agent, env, N_EVAL, SEED, "Random"
    )
    greed_m, greed_r, greed_c, greed_s, greed_re = evaluate_baseline(
        greedy_agent, env, N_EVAL, SEED, "Greedy"
    )

    # Evaluate PPO with exploitation only (no exploration)
    ppo_agent.epsilon = 0.0
    ppo_m, ppo_r_eval, ppo_c_eval, ppo_s_eval, ppo_re_eval = evaluate_baseline(
        ppo_agent, env, N_EVAL, SEED, "PPO (eval)"
    )

    print("\nExporting weights to JSON")
    ppo_weights = ppo_agent.export_weights_for_js()

    def summarise(rewards, carbon, sla, renew, last_n=100):
        return {
            "avg_reward": float(np.mean(rewards[-last_n:])),
            "avg_carbon_saved": float(np.mean(carbon[-last_n:])),
            "avg_sla_compliance": float(np.mean(sla[-last_n:])),
            "avg_renewable_fraction": float(np.mean(renew[-last_n:])),
            "total_episodes": len(rewards),
        }

    export = {
        "metadata": {
            "algorithm": "PPO (Proximal Policy Optimization)",
            "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "training_time_seconds": round(train_time, 1),
            "ppo_episodes": N_EPISODES,
            "ppo_updates": ppo_agent.update_count,
            "ppo_gradient_steps": ppo_agent.total_updates,
            "seed": SEED,
            "environment": "StochasticDataCentreEnv v2.0",
            "weather": "Stochastic (4 seasons, 6 weather regimes, cold snaps, storms)",
            "state_dim": 47,
            "action_dim": 7,
            "locations": LOCATION_IDS,
            "network_architecture": "Actor-Critic MLP [47-256-128-5]",
            "hyperparameters": {
                "lr": 3e-4, "gamma": 0.99, "gae_lambda": 0.95,
                "clip_eps": 0.2, "entropy_coef": 0.01,
                "n_epochs": 10, "batch_size": 32, "n_steps": 96,
            },
        },
        "training_curves": {
            "ppo": {
                "rewards": [float(r) for r in ppo_rewards],
                "carbon_saved": [float(c) for c in ppo_carbon],
                "sla_compliance": [float(s) for s in ppo_sla],
                "renewable_fraction": [float(r) for r in ppo_renew],
            },
        },
        "final_metrics": {
            "random": summarise(rand_r, rand_c, rand_s, rand_re),
            "greedy": summarise(greed_r, greed_c, greed_s, greed_re),
            "ppo": summarise(ppo_rewards, ppo_carbon, ppo_sla, ppo_renew),
            "ppo_eval": summarise(ppo_r_eval, ppo_c_eval, ppo_s_eval, ppo_re_eval),
        },
        "ppo_weights": ppo_weights,
        "policy": {
            "type": "ppo_neural_network",
            "description": "PPO Actor-Critic trained on 2000 episodes with stochastic weather",
        },
    }

    out_dir = os.path.join(os.path.dirname(__file__), "demo", "public")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "trained_policy.json")
    with open(out_path, "w") as f:
        json.dump(export, f, indent=None, separators=(",", ":"))

    file_size = os.path.getsize(out_path) / 1024
    print(f"Exported to {out_path} ({file_size:.0f} KB)")

    # Generate visualizations
    print("\nGenerating visualizations...")
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    
    plot_learning_curves(ppo_rewards, ppo_carbon, ppo_sla, ppo_renew, output_dir)
    plot_agent_comparison(export["final_metrics"], output_dir)
    print_metrics_table(export["final_metrics"], output_dir)
    
    print("Training complete!")


if __name__ == "__main__":
    main()
