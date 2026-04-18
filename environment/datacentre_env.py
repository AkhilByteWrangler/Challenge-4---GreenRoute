"""
Gymnasium-compatible RL environment for GreenRoute.

The agent observes a 47-dimensional state vector and selects one of 7 actions
(route to 5 locations, process locally, or hold in queue).
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Tuple, Optional, List

from .renewable_model import RenewableModel, LOCATIONS
from .grid_carbon_model import GridCarbonModel, BASE_CARBON_INTENSITY
from .job_generator import JobGenerator, Job, JobType
from .network_cost_model import NetworkCostModel

LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]
NUM_LOCATIONS = 5
STATE_DIM = 67  # 47 base + 20 weather event indicators (4 types × 5 DCs)
NUM_ACTIONS = 7  # 5 locations + local + hold


class DataCentreEnv(gym.Env):
    """
    GreenRoute Data Centre Workload Routing Environment.
    
    Observation: 47-dimensional continuous vector
    Action: Discrete(7) — route to CA/TX/VA/OR/AZ, process locally, or hold
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, seed: int = 42, episode_hours: float = 24.0,
                 timestep_hours: float = 0.25, jobs_per_hour: float = 10.0):
        super().__init__()

        self.seed_val = seed
        self.episode_hours = episode_hours
        self.timestep_hours = timestep_hours

        # Sub-models
        self.renewable_model = RenewableModel(seed=seed)
        self.grid_model = GridCarbonModel(seed=seed + 1)
        self.job_generator = JobGenerator(seed=seed + 2, jobs_per_hour=jobs_per_hour)
        self.network_model = NetworkCostModel(seed=seed + 3)

        # Spaces
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        # Episode state
        self.current_hour = 0.0
        self.current_step = 0
        self.max_steps = int(episode_hours / timestep_hours)
        self.current_job: Optional[Job] = None
        self.job_queue: List[Job] = []
        self.hold_queue: List[Tuple[Job, float]] = []  # (job, time_held)

        # Tracking
        self.total_carbon_saved = 0.0
        self.total_cost_saved = 0.0
        self.total_jobs_processed = 0
        self.total_sla_violations = 0
        self.total_renewable_used = 0.0
        self.total_jobs_routed = 0
        self.episode_log: List[Dict] = []

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, dict]:
        """Reset environment for a new episode."""
        if seed is not None:
            self.seed_val = seed

        self.renewable_model = RenewableModel(seed=self.seed_val)
        self.grid_model = GridCarbonModel(seed=self.seed_val + 1)
        self.job_generator = JobGenerator(seed=self.seed_val + 2)
        self.network_model = NetworkCostModel(seed=self.seed_val + 3)

        # Start at a random hour of day for diverse training
        rng = np.random.RandomState(self.seed_val)
        self.current_hour = rng.uniform(0, 24)
        self.current_step = 0

        # Generate initial job queue
        self.job_queue = self.job_generator.generate_batch(self.current_hour, self.timestep_hours)
        self.hold_queue = []

        # Pick first routable job
        self.current_job = self._get_next_routable_job()

        # Reset trackers
        self.total_carbon_saved = 0.0
        self.total_cost_saved = 0.0
        self.total_jobs_processed = 0
        self.total_sla_violations = 0
        self.total_renewable_used = 0.0
        self.total_jobs_routed = 0
        self.episode_log = []

        obs = self._build_observation()
        info = self._build_info()
        return obs, info

    def _get_next_routable_job(self) -> Optional[Job]:
        """Get the next job the agent can route (skip PINNED jobs)."""
        # First, process any pinned jobs locally (agent doesn't see them)
        remaining = []
        for job in self.job_queue:
            if job.job_type == JobType.PINNED:
                self._process_job_locally(job)
            else:
                remaining.append(job)
        self.job_queue = remaining

        # Check hold queue for expired holds
        new_hold = []
        for job, time_held in self.hold_queue:
            if time_held >= 0.5:  # Max hold = 30 min
                remaining.insert(0, job)  # Force process
            else:
                new_hold.append((job, time_held + self.timestep_hours))
        self.hold_queue = new_hold

        if self.job_queue:
            return self.job_queue.pop(0)
        return None

    def _process_job_locally(self, job: Job):
        """Process a pinned/local job at its origin — no routing decision."""
        self.total_jobs_processed += 1
        renewable_states = self.renewable_model.get_all_states(self.current_hour)
        rf = renewable_states[job.origin]["renewable_fraction"]
        self.total_renewable_used += rf
        self.grid_model.update_utilisation(job.origin, job.compute_units)

    def _build_observation(self) -> np.ndarray:
        """
        Build the 47-dimensional state vector.
        
        Per data centre (5 × 7 = 35):
          solar_irradiance, wind_speed, carbon_intensity, utilisation,
          available_capacity, energy_cost, pue
        Global (12):
          time_sin, time_cos, day_sin, day_cos,
          forecast_solar_avg, forecast_wind_avg, forecast_solar_std, forecast_wind_std,
          queue_length, flexible_fraction, transfer_cost_sum, carbon_saved_so_far
        """
        renewable_states = self.renewable_model.get_all_states(self.current_hour)
        renewable_fracs = {loc: renewable_states[loc]["renewable_fraction"] for loc in LOCATION_IDS}
        grid_states = self.grid_model.get_all_states(self.current_hour, renewable_fracs)
        forecast = self.renewable_model.get_forecast(self.current_hour)

        features = []

        # Per-location features (5 × 7 = 35)
        for loc_id in LOCATION_IDS:
            rs = renewable_states[loc_id]
            gs = grid_states[loc_id]
            features.extend([
                rs["solar_irradiance"] / 1000.0,       # Normalise to ~[0, 1]
                rs["wind_speed"] / 25.0,                # Normalise to ~[0, 1]
                gs["carbon_intensity"] / 600.0,         # Normalise to ~[0, 1]
                gs["utilisation"],                      # Already [0, 1]
                gs["available_capacity"] / 6000.0,      # Normalise
                gs["energy_cost"] / 0.30,               # Normalise
                gs["pue"] / 1.5,                        # Normalise
            ])

        # Weather event indicators (5 × 4 = 20)
        # Per location: [is_cold_snap, is_storm, is_heat_wave, is_solar_boom]
        # Base env has no events — all zeros. StochasticDataCentreEnv overrides.
        event_types = ["cold_snap", "storm", "heat_wave", "solar_boom"]
        active_events = getattr(self, '_active_weather_events', {})
        for loc_id in LOCATION_IDS:
            ev = active_events.get(loc_id, {})
            ev_type = ev.get("type", None)
            for et in event_types:
                features.append(1.0 if ev_type == et else 0.0)

        # Global features (12)
        hour_rad = 2 * np.pi * self.current_hour / 24.0
        features.append(np.sin(hour_rad))  # time_sin
        features.append(np.cos(hour_rad))  # time_cos

        # Day of week (simulate as step-based)
        day_frac = (self.current_step * self.timestep_hours) / (24 * 7)
        features.append(np.sin(2 * np.pi * day_frac))  # day_sin
        features.append(np.cos(2 * np.pi * day_frac))  # day_cos

        # Forecast features (next 2 hours)
        solar_forecasts = [forecast[loc]["solar_forecast"] for loc in LOCATION_IDS]
        wind_forecasts = [forecast[loc]["wind_forecast"] for loc in LOCATION_IDS]
        features.append(np.mean(solar_forecasts) / 1000.0)
        features.append(np.mean(wind_forecasts) / 25.0)
        features.append(np.std(solar_forecasts) / 500.0)
        features.append(np.std(wind_forecasts) / 10.0)

        # Queue stats
        all_jobs = self.job_queue + ([self.current_job] if self.current_job else [])
        queue_stats = self.job_generator.get_queue_stats(all_jobs)
        features.append(queue_stats["total"] / 20.0)
        features.append(queue_stats["flexible_fraction"])

        # Network cost sum
        features.append(self.network_model.get_cost_matrix_sum() / 2.0)

        # Carbon saved so far (normalised)
        features.append(self.total_carbon_saved / 10000.0)

        obs = np.array(features, dtype=np.float32)
        assert obs.shape == (STATE_DIM,), f"Expected {STATE_DIM} features, got {obs.shape[0]}"
        return obs

    def _build_info(self) -> dict:
        """Build info dictionary for current state."""
        return {
            "current_hour": self.current_hour,
            "current_step": self.current_step,
            "current_job": self.current_job.to_dict() if self.current_job else None,
            "queue_length": len(self.job_queue),
            "hold_queue_length": len(self.hold_queue),
            "total_carbon_saved": self.total_carbon_saved,
            "total_cost_saved": self.total_cost_saved,
            "total_jobs_processed": self.total_jobs_processed,
            "total_sla_violations": self.total_sla_violations,
            "sla_compliance": (
                1.0 - self.total_sla_violations / max(1, self.total_jobs_processed)
            ),
            "renewable_fraction_avg": (
                self.total_renewable_used / max(1, self.total_jobs_processed)
            ),
        }

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one step: route the current job based on action.
        
        Actions:
          0 = process locally
          1-5 = route to CA, TX, VA, OR, AZ
          6 = hold in queue
        """
        reward = 0.0
        action_result = {}

        if self.current_job is None:
            # No job to route — advance time
            self._advance_time()
            obs = self._build_observation()
            done = self.current_step >= self.max_steps
            return obs, 0.0, done, False, self._build_info()

        job = self.current_job

        if action == 6:
            # Hold job in queue
            if job.max_latency_hours > 0.5:  # Can only hold if SLA allows
                self.hold_queue.append((job, 0.0))
                reward = -0.5  # Small penalty for holding
                action_result = {"held": True, "sla_violated": False,
                                "capacity_exceeded": False, "transfer_cost": 0.0}
            else:
                # Can't hold — process locally as fallback
                action = 0

        if action != 6:
            # Determine destination
            if action == 0:
                destination = job.origin
            else:
                dest_map = {1: "CA", 2: "TX", 3: "VA", 4: "OR", 5: "AZ"}
                destination = dest_map[action]

            # Calculate transfer cost
            transfer_cost = self.network_model.get_transfer_cost(
                job.origin, destination, job.compute_units
            )

            # Check SLA violation
            transfer_latency = self.network_model.get_transfer_latency(job.origin, destination)
            total_time = transfer_latency + job.processing_time_hours
            sla_violated = (
                total_time > job.max_latency_hours if job.max_latency_hours > 0 else False
            )

            # Check capacity
            available = self.grid_model.get_available_capacity(destination)
            capacity_exceeded = job.compute_units > available * 1000  # Scale check

            # Get renewable/carbon data at destination
            renewable_states = self.renewable_model.get_all_states(self.current_hour)
            renewable_fracs = {loc: renewable_states[loc]["renewable_fraction"] for loc in LOCATION_IDS}
            grid_states = self.grid_model.get_all_states(self.current_hour, renewable_fracs)

            local_carbon = grid_states[job.origin]["carbon_intensity"]
            routed_carbon = grid_states[destination]["carbon_intensity"]
            local_cost = grid_states[job.origin]["energy_cost"]
            routed_cost = grid_states[destination]["energy_cost"]
            renewable_frac_dest = renewable_fracs[destination]

            action_result = {
                "destination": destination,
                "sla_violated": sla_violated,
                "capacity_exceeded": capacity_exceeded,
                "transfer_cost": transfer_cost,
                "local_carbon": local_carbon,
                "routed_carbon": routed_carbon,
                "local_cost": local_cost,
                "routed_cost": routed_cost,
                "renewable_fraction": renewable_frac_dest,
            }

            # Compute reward
            reward = self._compute_reward(action_result, job)

            # Update state
            self.grid_model.update_utilisation(destination, job.compute_units)
            self.total_jobs_processed += 1
            self.total_renewable_used += renewable_frac_dest

            if sla_violated:
                self.total_sla_violations += 1

            # Track carbon/cost savings
            carbon_saved = (local_carbon - routed_carbon) * job.compute_units / 1000.0
            cost_saved = (local_cost - routed_cost) * job.compute_units
            self.total_carbon_saved += carbon_saved
            self.total_cost_saved += cost_saved

            if destination != job.origin:
                self.total_jobs_routed += 1

            # Log the decision
            self.episode_log.append({
                "step": self.current_step,
                "hour": self.current_hour,
                "job": job.to_dict(),
                "action": action,
                "destination": destination,
                "carbon_saved": carbon_saved,
                "cost_saved": cost_saved,
                "sla_violated": sla_violated,
                "reward": reward,
            })

        # Advance time and get next job
        self._advance_time()
        self.current_job = self._get_next_routable_job()

        obs = self._build_observation()
        done = self.current_step >= self.max_steps
        truncated = False
        info = self._build_info()
        info["action_result"] = action_result

        return obs, reward, done, truncated, info

    def _compute_reward(self, action_result: dict, job: Job) -> float:
        """
        Multi-objective reward: carbon + cost + renewable - penalties.
        
        R = R_carbon + R_cost + R_renewable + R_latency + R_transfer + R_capacity
        """
        # Carbon saved vs processing locally
        baseline_carbon = job.compute_units * action_result["local_carbon"] / 1000.0
        actual_carbon = job.compute_units * action_result["routed_carbon"] / 1000.0
        r_carbon = (baseline_carbon - actual_carbon) * 0.05

        # Energy cost savings
        baseline_cost = job.compute_units * action_result["local_cost"]
        actual_cost = job.compute_units * action_result["routed_cost"]
        r_cost = (baseline_cost - actual_cost) * 10.0

        # Renewable bonus
        r_renewable = action_result["renewable_fraction"] * 5.0

        # SLA violation penalty
        r_latency = -20.0 if action_result["sla_violated"] else 0.0

        # Transfer cost penalty
        r_transfer = -action_result["transfer_cost"] * 2.0

        # Capacity exceeded penalty
        r_capacity = -15.0 if action_result["capacity_exceeded"] else 0.0

        total = r_carbon + r_cost + r_renewable + r_latency + r_transfer + r_capacity
        return float(total)

    def _advance_time(self):
        """Advance the simulation clock by one timestep."""
        self.current_hour = (self.current_hour + self.timestep_hours) % 24
        self.current_step += 1

        # Update sub-models
        self.renewable_model.step(self.current_hour)
        self.grid_model.decay_utilisation()

        # Generate new jobs
        new_jobs = self.job_generator.generate_batch(self.current_hour, self.timestep_hours)
        self.job_queue.extend(new_jobs)

    def get_valid_actions(self) -> List[int]:
        """Get list of valid actions for the current job (for action masking)."""
        if self.current_job is None:
            return [0]  # Only local processing if no job

        valid = [0]  # Local is always valid
        job = self.current_job

        for action_idx, loc_id in enumerate(LOCATION_IDS, start=1):
            # Check SLA
            if not self.network_model.would_violate_sla(
                job.origin, loc_id, job.max_latency_hours, job.processing_time_hours
            ):
                valid.append(action_idx)

        # Hold action (6) valid only for flexible jobs
        if job.job_type == JobType.FLEXIBLE and job.max_latency_hours > 0.5:
            valid.append(6)

        return valid

    def get_action_mask(self) -> np.ndarray:
        """Get boolean mask of valid actions (True = valid)."""
        mask = np.zeros(NUM_ACTIONS, dtype=bool)
        for a in self.get_valid_actions():
            mask[a] = True
        return mask
