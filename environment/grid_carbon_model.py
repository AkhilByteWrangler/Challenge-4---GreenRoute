"""
US grid carbon intensity model by region/hour.

Calibrated against EPA eGRID data and ElectricityMap historical averages.
Carbon intensity varies by time of day (demand-driven) and renewable penetration.
"""

import numpy as np
from typing import Dict

# Regional electricity grid parameters from EPA eGRID 2022
BASE_CARBON_INTENSITY = {
    "CA": 200.0,
    "TX": 400.0,
    "VA": 500.0,
    "OR": 280.0,
    "AZ": 220.0,
}

# Energy cost $/kWh base rates (commercial/industrial average)
BASE_ENERGY_COST = {
    "CA": 0.18,
    "TX": 0.09,
    "VA": 0.11,
    "OR": 0.08,
    "AZ": 0.10,
}

# PUE (Power Usage Effectiveness) — lower is better
BASE_PUE = {
    "CA": 1.15,
    "TX": 1.25,
    "VA": 1.20,
    "OR": 1.10,
    "AZ": 1.30,
}

# Compute capacity per data centre (TFLOPS)
COMPUTE_CAPACITY = {
    "CA": 5000.0,
    "TX": 4500.0,
    "VA": 6000.0,
    "OR": 3500.0,
    "AZ": 4000.0,
}

# Carbon intensity model constants
DEMAND_PEAK_HOUR = 17.0
RENEWABLE_OFFSET_FACTOR = 0.6
CARBON_MIN_FLOOR = 20.0
LOCAL_TIMEZONE_OFFSETS = {"CA": -8, "TX": -6, "VA": -5, "OR": -8, "AZ": -7}

# Energy cost model constants
PEAK_HOUR_START = 14
PEAK_HOUR_END = 19
OFF_PEAK_START_HOUR = 22
OFF_PEAK_END_HOUR = 6
PEAK_TOU_FACTOR = 1.5
MID_PEAK_TOU_FACTOR = 1.0
OFF_PEAK_TOU_FACTOR = 0.6
COST_MIN_FLOOR = 0.02

# PUE model constants
PUE_TEMP_FACTOR_AMP = 0.05
PUE_TEMP_DAY_START = 6
PUE_TEMP_DAY_END = 18

# Utilisation constants
UTILISATION_INITIAL_MEAN = 0.3
UTILISATION_INITIAL_STD = 0.2
UTILISATION_MIN = 0.05
UTILISATION_DECAY_RATE = 0.97


class GridCarbonModel:
    """Models time-varying grid carbon intensity and energy costs per location."""

    def __init__(self, seed: int = 42):
        """Initialize grid carbon model with regional base parameters and utilisation tracking."""
        self.rng = np.random.RandomState(seed)
        self.base_carbon = BASE_CARBON_INTENSITY.copy()
        self.base_cost = BASE_ENERGY_COST.copy()
        self.pue = BASE_PUE.copy()
        self.capacity = COMPUTE_CAPACITY.copy()
        self.utilisation = {
            loc: UTILISATION_INITIAL_MEAN + self.rng.uniform(0, UTILISATION_INITIAL_STD)
            for loc in self.base_carbon
        }

    def get_carbon_intensity(self, utc_hour: float, location_id: str,
                             renewable_fraction: float = 0.0) -> float:
        """Get real-time carbon intensity varying with demand and renewable penetration."""
        base = self.base_carbon[location_id]
        local_hour = (utc_hour + LOCAL_TIMEZONE_OFFSETS[location_id]) % 24

        demand_factor = 1.0 + 0.2 * np.exp(-0.5 * ((local_hour - DEMAND_PEAK_HOUR) / 3) ** 2)
        renewable_offset = renewable_fraction * base * RENEWABLE_OFFSET_FACTOR
        noise = self.rng.normal(0, base * 0.05)

        carbon = base * demand_factor - renewable_offset + noise
        return float(max(carbon, CARBON_MIN_FLOOR))

    def get_energy_cost(self, utc_hour: float, location_id: str) -> float:
        """Get real-time energy cost with time-of-use pricing."""
        base = self.base_cost[location_id]
        local_hour = (utc_hour + LOCAL_TIMEZONE_OFFSETS[location_id]) % 24

        if PEAK_HOUR_START <= local_hour <= PEAK_HOUR_END:
            tou_factor = PEAK_TOU_FACTOR
        elif local_hour >= OFF_PEAK_START_HOUR or local_hour <= OFF_PEAK_END_HOUR:
            tou_factor = OFF_PEAK_TOU_FACTOR
        else:
            tou_factor = MID_PEAK_TOU_FACTOR

        cost = base * tou_factor + self.rng.normal(0, base * 0.03)
        return float(max(cost, COST_MIN_FLOOR))

    def get_pue(self, location_id: str, utc_hour: float) -> float:
        """Get cooling efficiency (PUE) varying with temperature proxy."""
        base = self.pue[location_id]
        local_hour = (utc_hour + LOCAL_TIMEZONE_OFFSETS[location_id]) % 24

        if PUE_TEMP_DAY_START <= local_hour <= PUE_TEMP_DAY_END:
            temp_factor = 1.0 + PUE_TEMP_FACTOR_AMP * np.sin(np.pi * (local_hour - PUE_TEMP_DAY_START) / 12)
        else:
            temp_factor = 1.0

        return float(base * temp_factor)

    def get_available_capacity(self, location_id: str) -> float:
        """Get available compute capacity (TFLOPS) at a location."""
        total = self.capacity[location_id]
        used = total * self.utilisation[location_id]
        return float(max(total - used, 0))

    def get_utilisation(self, location_id: str) -> float:
        """Get current server utilisation (0-1) at a location."""
        return float(self.utilisation[location_id])

    def update_utilisation(self, location_id: str, compute_units: float, add: bool = True):
        """Update utilisation when a job is routed to/completed at a location."""
        delta = compute_units / self.capacity[location_id]
        new_util = self.utilisation[location_id] + (delta if add else -delta)
        self.utilisation[location_id] = np.clip(new_util, UTILISATION_MIN, 1.0)

    def decay_utilisation(self):
        """Decay utilisation slightly each step (jobs completing)."""
        for loc in self.utilisation:
            decayed = self.utilisation[loc] * UTILISATION_DECAY_RATE + self.rng.normal(0, 0.01)
            self.utilisation[loc] = max(UTILISATION_MIN, decayed)

    def get_all_states(self, utc_hour: float, renewable_fractions: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Get all grid/capacity metrics for every location."""
        states = {}
        for loc_id in self.base_carbon:
            rf = renewable_fractions.get(loc_id, 0.0)
            states[loc_id] = {
                "carbon_intensity": self.get_carbon_intensity(utc_hour, loc_id, rf),
                "energy_cost": self.get_energy_cost(utc_hour, loc_id),
                "pue": self.get_pue(loc_id, utc_hour),
                "utilisation": self.get_utilisation(loc_id),
                "available_capacity": self.get_available_capacity(loc_id),
            }
        return states
