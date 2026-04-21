"""
Solar + Wind simulation models for GreenRoute.

Generates realistic renewable energy availability for each data centre location
based on NREL published statistical distributions. No downloads required.
"""

import numpy as np
from typing import Dict

# Data centre locations with their renewable profiles
LOCATIONS = {
    "CA": {"lat": 37.33, "lon": -121.89, "name": "California",  "primary": "solar",
            "peak_solar_start": 11, "peak_solar_end": 15, "avg_wind": 4.5,
            "solar_capacity_factor": 0.28, "wind_capacity_factor": 0.12},
    "TX": {"lat": 32.78, "lon": -96.80,  "name": "Texas",       "primary": "wind",
            "peak_solar_start": 11, "peak_solar_end": 15, "avg_wind": 7.8,
            "solar_capacity_factor": 0.24, "wind_capacity_factor": 0.35},
    "VA": {"lat": 39.04, "lon": -77.49,  "name": "Virginia",    "primary": "mixed",
            "peak_solar_start": 11, "peak_solar_end": 14, "avg_wind": 3.2,
            "solar_capacity_factor": 0.16, "wind_capacity_factor": 0.08},
    "OR": {"lat": 45.52, "lon": -122.68, "name": "Oregon",      "primary": "wind",
            "peak_solar_start": 12, "peak_solar_end": 15, "avg_wind": 6.5,
            "solar_capacity_factor": 0.14, "wind_capacity_factor": 0.30},
    "AZ": {"lat": 33.45, "lon": -112.07, "name": "Arizona",     "primary": "solar",
            "peak_solar_start": 10, "peak_solar_end": 16, "avg_wind": 3.8,
            "solar_capacity_factor": 0.32, "wind_capacity_factor": 0.10},
}

# UTC offsets for each location (standard time)
UTC_OFFSETS = {"CA": -8, "TX": -6, "VA": -5, "OR": -8, "AZ": -7}

# Solar model constants
SUNRISE_HOUR = 6.0
SUNSET_HOUR = 20.0
SOLAR_NOON = 13.0
SOLAR_IRRADIANCE_MAX = 1000.0
SOLAR_REFERENCE_CF = 0.28

# Wind model constants
WEIBULL_SHAPE_K = 2.0
WEIBULL_MEAN_SCALE = 0.886
WIND_GUST_MULTIPLIER = 3.0
WIND_SPEED_MAX = 25.0


class RenewableModel:
    """Simulates solar irradiance and wind speed for each data centre location."""

    def __init__(self, seed: int = 42):
        """Initialize renewable model with location profiles and stochastic weather state."""
        self.rng = np.random.RandomState(seed)
        self.locations = LOCATIONS
        self.utc_offsets = UTC_OFFSETS
        # Pre-generate cloud cover patterns (changes slowly over hours)
        self._cloud_state = {loc: 0.0 for loc in LOCATIONS}
        self._wind_gust_state = {loc: 0.0 for loc in LOCATIONS}

    def _local_hour(self, utc_hour: float, location_id: str) -> float:
        """Convert UTC hour to local solar time for a location."""
        return (utc_hour + self.utc_offsets[location_id]) % 24

    def get_solar_irradiance(self, utc_hour: float, location_id: str) -> float:
        """Calculate solar irradiance (W/m²) using sinusoidal model calibrated to NREL data."""
        local_hour = self._local_hour(utc_hour, location_id)

        if local_hour < SUNRISE_HOUR or local_hour > SUNSET_HOUR:
            return 0.0

        loc = self.locations[location_id]
        day_length = SUNSET_HOUR - SUNRISE_HOUR
        phase = (local_hour - SUNRISE_HOUR) / day_length * np.pi
        base_irradiance = np.sin(phase) * SOLAR_IRRADIANCE_MAX * loc["solar_capacity_factor"] / SOLAR_REFERENCE_CF

        cloud_factor = 1.0 - self._cloud_state[location_id] * 0.7
        irradiance = np.clip(base_irradiance * cloud_factor + self.rng.normal(0, 15), 0, SOLAR_IRRADIANCE_MAX)
        return float(irradiance)

    def get_wind_speed(self, utc_hour: float, location_id: str) -> float:
        """Calculate wind speed (m/s) using Weibull distribution with diurnal modulation."""
        local_hour = self._local_hour(utc_hour, location_id)
        diurnal_factor = 1.0 + 0.3 * np.cos(2 * np.pi * (local_hour - 3) / 24)

        loc = self.locations[location_id]
        scale_c = loc["avg_wind"] / WEIBULL_MEAN_SCALE
        base_wind = self.rng.weibull(WEIBULL_SHAPE_K) * scale_c * diurnal_factor
        base_wind += self._wind_gust_state[location_id] * WIND_GUST_MULTIPLIER

        return float(np.clip(base_wind, 0, WIND_SPEED_MAX))

    def get_renewable_fraction(self, utc_hour: float, location_id: str) -> float:
        """Estimate renewable fraction (0-1) combining solar, wind, and hydro."""
        loc = self.locations[location_id]

        solar = self.get_solar_irradiance(utc_hour, location_id) / 1000.0
        wind = self.get_wind_speed(utc_hour, location_id) / 15.0

        solar_contrib = solar * loc["solar_capacity_factor"] * 1.5
        wind_contrib = min(wind, 1.0) * loc["wind_capacity_factor"] * 1.5

        hydro_contrib = loc.get("hydro_base", 0.0)

        renewable_frac = np.clip(solar_contrib + wind_contrib + hydro_contrib, 0, 1)
        return float(renewable_frac)

    def step(self, utc_hour: float) -> None:
        """Advance stochastic weather state: cloud cover and wind gusts via AR(1) process."""
        for loc_id in self.locations:
            self._cloud_state[loc_id] = np.clip(
                0.85 * self._cloud_state[loc_id] + self.rng.normal(0, 0.15),
                0, 1
            )
            self._wind_gust_state[loc_id] = np.clip(
                0.7 * self._wind_gust_state[loc_id] + self.rng.normal(0, 0.2),
                0, 1
            )

    def get_all_states(self, utc_hour: float) -> Dict[str, Dict[str, float]]:
        """Get solar, wind, and renewable fraction for all locations."""
        states = {}
        for loc_id in self.locations:
            states[loc_id] = {
                "solar_irradiance": self.get_solar_irradiance(utc_hour, loc_id),
                "wind_speed": self.get_wind_speed(utc_hour, loc_id),
                "renewable_fraction": self.get_renewable_fraction(utc_hour, loc_id),
            }
        return states

    def get_forecast(self, utc_hour: float, horizon_hours: float = 2.0) -> Dict[str, Dict[str, float]]:
        """Forecast solar and wind at future hour with ±15% uncertainty."""
        forecast = {}
        future_hour = (utc_hour + horizon_hours) % 24
        for loc_id in self.locations:
            solar_forecast = self.get_solar_irradiance(future_hour, loc_id)
            wind_forecast = self.get_wind_speed(future_hour, loc_id)
            solar_forecast *= (1 + self.rng.normal(0, 0.15))
            wind_forecast *= (1 + self.rng.normal(0, 0.15))
            forecast[loc_id] = {
                "solar_forecast": max(0, solar_forecast),
                "wind_forecast": max(0, wind_forecast),
            }
        return forecast
