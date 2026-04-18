"""
US grid carbon intensity model by region/hour.

Calibrated against EPA eGRID data and ElectricityMap historical averages.
Carbon intensity varies by time of day (demand-driven) and renewable penetration.
"""

import numpy as np
from typing import Dict

# Base carbon intensity (gCO₂/kWh) for each region — from EPA eGRID 2022
BASE_CARBON_INTENSITY = {
    "CA": 200.0,   # CAMX — California grid, high solar/gas mix
    "TX": 400.0,   # ERCT — Texas (ERCOT), gas/wind/some coal
    "VA": 500.0,   # SRVC — Virginia, coal/gas/nuclear heavy
    "OR": 280.0,   # NWPP — Pacific Northwest, gas + wind mix
    "AZ": 220.0,   # AZNM — Arizona/New Mexico, solar + gas
}

# Energy cost $/kWh base rates (commercial/industrial average)
BASE_ENERGY_COST = {
    "CA": 0.18,
    "TX": 0.09,
    "VA": 0.11,
    "OR": 0.08,
    "AZ": 0.10,
}

# PUE (Power Usage Effectiveness) — lower is better (1.0 = perfect)
BASE_PUE = {
    "CA": 1.15,   # Moderate climate, good cooling
    "TX": 1.25,   # Hot, higher cooling load
    "VA": 1.20,   # Moderate
    "OR": 1.10,   # Cool climate, excellent PUE
    "AZ": 1.30,   # Very hot, highest cooling load
}

# Compute capacity per data centre (TFLOPS)
COMPUTE_CAPACITY = {
    "CA": 5000.0,
    "TX": 4500.0,
    "VA": 6000.0,
    "OR": 3500.0,
    "AZ": 4000.0,
}


class GridCarbonModel:
    """Models time-varying grid carbon intensity and energy costs per location."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.base_carbon = BASE_CARBON_INTENSITY.copy()
        self.base_cost = BASE_ENERGY_COST.copy()
        self.pue = BASE_PUE.copy()
        self.capacity = COMPUTE_CAPACITY.copy()
        # Track current utilisation per data centre
        self.utilisation = {loc: 0.3 + self.rng.uniform(0, 0.2) for loc in self.base_carbon}

    def get_carbon_intensity(self, utc_hour: float, location_id: str,
                             renewable_fraction: float = 0.0) -> float:
        """
        Get real-time carbon intensity (gCO₂/kWh) for a location.
        
        Carbon intensity varies with:
        - Time of day (demand curve — higher during peak hours)
        - Renewable penetration (higher renewables = lower carbon)
        - Random fluctuations (grid events, plant outages)
        """
        base = self.base_carbon[location_id]

        # Demand-driven diurnal pattern: higher carbon during peak demand (2-7pm local)
        # Using a simplified demand curve
        local_offsets = {"CA": -8, "TX": -6, "VA": -5, "OR": -8, "AZ": -7}
        local_hour = (utc_hour + local_offsets[location_id]) % 24

        # Peak demand multiplier (peaks around 5pm local)
        demand_factor = 1.0 + 0.2 * np.exp(-0.5 * ((local_hour - 17) / 3) ** 2)

        # Renewable offset: more renewables = lower marginal carbon
        renewable_offset = renewable_fraction * base * 0.6

        # Small stochastic noise (grid events)
        noise = self.rng.normal(0, base * 0.05)

        carbon = base * demand_factor - renewable_offset + noise
        return float(max(carbon, 20.0))  # Floor at 20 gCO2/kWh

    def get_energy_cost(self, utc_hour: float, location_id: str) -> float:
        """
        Get real-time energy cost ($/kWh) for a location.
        
        Varies with time of day (TOU pricing) and demand.
        """
        base = self.base_cost[location_id]
        local_offsets = {"CA": -8, "TX": -6, "VA": -5, "OR": -8, "AZ": -7}
        local_hour = (utc_hour + local_offsets[location_id]) % 24

        # Time-of-use pricing: peak (2-7pm), off-peak (10pm-6am), mid-peak otherwise
        if 14 <= local_hour <= 19:
            tou_factor = 1.5  # Peak
        elif local_hour >= 22 or local_hour <= 6:
            tou_factor = 0.6  # Off-peak
        else:
            tou_factor = 1.0  # Mid-peak

        noise = self.rng.normal(0, base * 0.03)
        cost = base * tou_factor + noise
        return float(max(cost, 0.02))

    def get_pue(self, location_id: str, utc_hour: float) -> float:
        """
        Get cooling efficiency (PUE) — varies slightly with outside temp proxy.
        
        Higher PUE = more energy wasted on cooling.
        """
        base = self.pue[location_id]
        local_offsets = {"CA": -8, "TX": -6, "VA": -5, "OR": -8, "AZ": -7}
        local_hour = (utc_hour + local_offsets[location_id]) % 24

        # Temperature proxy: hotter during afternoon
        temp_factor = 1.0 + 0.05 * np.sin(np.pi * (local_hour - 6) / 12) if 6 <= local_hour <= 18 else 1.0

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
        if add:
            self.utilisation[location_id] = min(self.utilisation[location_id] + delta, 1.0)
        else:
            self.utilisation[location_id] = max(self.utilisation[location_id] - delta, 0.05)

    def decay_utilisation(self):
        """Decay utilisation slightly each step (jobs completing)."""
        for loc in self.utilisation:
            self.utilisation[loc] = max(0.1, self.utilisation[loc] * 0.97 + self.rng.normal(0, 0.01))

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
