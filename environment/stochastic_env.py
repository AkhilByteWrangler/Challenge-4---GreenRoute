"""Stochastic weather model and environment for GreenRoute training."""

import numpy as np
from .datacentre_env import DataCentreEnv, LOCATION_IDS
from .renewable_model import RenewableModel, LOCATIONS

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

LOCATION_WEATHER_SENSITIVITY = {
    "CA": {"solar_var": 0.2,  "wind_var": 0.3,  "cold_risk": 0.01, "storm_risk": 0.03, "heat_risk": 0.06, "solar_boom_risk": 0.10},
    "TX": {"solar_var": 0.15, "wind_var": 0.4,  "cold_risk": 0.03, "storm_risk": 0.10, "heat_risk": 0.07, "solar_boom_risk": 0.04},
    "VA": {"solar_var": 0.25, "wind_var": 0.25, "cold_risk": 0.05, "storm_risk": 0.06, "heat_risk": 0.03, "solar_boom_risk": 0.02},
    "OR": {"solar_var": 0.35, "wind_var": 0.2,  "cold_risk": 0.12, "storm_risk": 0.04, "heat_risk": 0.01, "solar_boom_risk": 0.02},
    "AZ": {"solar_var": 0.1,  "wind_var": 0.3,  "cold_risk": 0.01, "storm_risk": 0.02, "heat_risk": 0.10, "solar_boom_risk": 0.12},
}

CARBON_MULTIPLIERS = {
    "cold_snap": 3.0,
    "storm": 2.5,
    "heat_wave": 2.5,
    "solar_boom": 0.3,
}


class StochasticWeatherModel:
    """Wraps base RenewableModel with stochastic weather, seasons, and weather events."""

    def __init__(self, base_model: RenewableModel, rng: np.random.RandomState, season: str = None):
        self.base = base_model
        self.rng = rng
        self.season = season if season else rng.choice(list(SEASONS.keys()))
        self.season_params = SEASONS[self.season]
        self.regimes = {}
        self.cloud_modifiers = {loc: 0.0 for loc in LOCATION_IDS}
        self.wind_modifiers = {loc: 0.0 for loc in LOCATION_IDS}
        self.solar_modifiers = {loc: 0.0 for loc in LOCATION_IDS}
        self.active_events = {}
        self._assign_weather_regimes()

    def _assign_weather_regimes(self):
        regime_names = list(WEATHER_REGIMES.keys())
        regime_probs = np.array([WEATHER_REGIMES[r]["prob"] for r in regime_names]) / sum([WEATHER_REGIMES[r]["prob"] for r in regime_names])
        for loc in LOCATION_IDS:
            self.regimes[loc] = self.rng.choice(regime_names, p=regime_probs)
        if self.rng.random() < 0.4:
            self.regimes["CA"] = self.regimes["OR"]
        if self.rng.random() < 0.3:
            self.regimes["AZ"] = self.regimes["TX"]

    def step(self, utc_hour: float):
        self.base.step(utc_hour)
        for loc in LOCATION_IDS:
            sens = LOCATION_WEATHER_SENSITIVITY[loc]
            if self.rng.random() < 0.04:
                self._assign_weather_regimes()
            if loc not in self.active_events:
                cold_scale = 2.0 if self.season == "winter" else 0.5
                if self.rng.random() < sens["cold_risk"] * cold_scale * 0.25:
                    self.active_events[loc] = {"type": "cold_snap", "remaining": self.rng.uniform(1.5, 5.5)}
                elif self.rng.random() < sens["storm_risk"] * 0.25:
                    self.active_events[loc] = {"type": "storm", "remaining": self.rng.uniform(1.5, 5.5)}
                heat_scale = 2.0 if self.season == "summer" else 0.5
                if loc not in self.active_events and self.rng.random() < sens["heat_risk"] * heat_scale * 0.25:
                    self.active_events[loc] = {"type": "heat_wave", "remaining": self.rng.uniform(1.5, 5.5)}
                boom_scale = 1.5 if self.season in ("summer", "spring") else 0.5
                if loc not in self.active_events and self.rng.random() < sens["solar_boom_risk"] * boom_scale * 0.25:
                    self.active_events[loc] = {"type": "solar_boom", "remaining": self.rng.uniform(1.5, 5.5)}
            if loc in self.active_events:
                self.active_events[loc]["remaining"] -= 0.25
                if self.active_events[loc]["remaining"] <= 0:
                    del self.active_events[loc]
            regime = WEATHER_REGIMES[self.regimes[loc]]
            target_cloud = regime["cloud_mean"] + self.rng.normal(0, regime["cloud_std"])
            self.cloud_modifiers[loc] = np.clip(0.9 * self.cloud_modifiers[loc] + 0.1 * target_cloud + self.rng.normal(0, 0.03), 0, 1)
            self.wind_modifiers[loc] = np.clip(0.85 * self.wind_modifiers[loc] + 0.15 * (regime["wind_mult"] - 1) + self.rng.normal(0, 0.05), -0.5, 1.5)

    def get_solar_irradiance(self, utc_hour: float, location_id: str) -> float:
        base_solar = self.base.get_solar_irradiance(utc_hour, location_id)
        solar_scale = self.season_params["solar_scale"]
        regime = WEATHER_REGIMES[self.regimes[location_id]]
        cloud_reduction = 1.0 - self.cloud_modifiers[location_id] * 0.8
        event_mult, event_add = 1.0, 0.0
        if location_id in self.active_events:
            ev = self.active_events[location_id]
            if ev["type"] == "cold_snap": event_mult = 0.10
            elif ev["type"] == "storm": event_mult = 0.05
            elif ev["type"] == "heat_wave": event_mult = 1.1
            elif ev["type"] == "solar_boom": event_mult, event_add = 1.8, 200.0
        final = base_solar * solar_scale * regime["solar_mult"] * cloud_reduction * event_mult + event_add
        return float(np.clip(final + self.rng.normal(0, 10), 0, 1000))

    def get_wind_speed(self, utc_hour: float, location_id: str) -> float:
        base_wind = self.base.get_wind_speed(utc_hour, location_id)
        wind_scale = self.season_params["wind_scale"]
        regime = WEATHER_REGIMES[self.regimes[location_id]]
        wind_mult = regime["wind_mult"] + self.wind_modifiers[location_id]
        if location_id in self.active_events:
            ev = self.active_events[location_id]
            if ev["type"] == "storm": wind_mult = 2.5 + self.rng.uniform(0, 1)
            elif ev["type"] == "cold_snap": wind_mult = 1.2
            elif ev["type"] == "heat_wave": wind_mult = 0.3
        final = base_wind * wind_scale * wind_mult
        if final > 18 and location_id in self.active_events and self.active_events[location_id]["type"] == "storm":
            final *= 0.4
        return float(np.clip(final, 0, 25))

    def get_renewable_fraction(self, utc_hour: float, location_id: str) -> float:
        loc = LOCATIONS[location_id]
        solar = self.get_solar_irradiance(utc_hour, location_id) / 1000.0
        wind = self.get_wind_speed(utc_hour, location_id) / 15.0
        solar_contrib = solar * loc["solar_capacity_factor"] * 1.5
        wind_contrib = min(wind, 1.0) * loc["wind_capacity_factor"] * 1.5
        return float(np.clip(solar_contrib + wind_contrib, 0, 1))

    def get_all_states(self, utc_hour: float):
        return {
            loc_id: {
                "solar_irradiance": self.get_solar_irradiance(utc_hour, loc_id),
                "wind_speed": self.get_wind_speed(utc_hour, loc_id),
                "renewable_fraction": self.get_renewable_fraction(utc_hour, loc_id),
            }
            for loc_id in LOCATION_IDS
        }

    def get_forecast(self, utc_hour: float, horizon_hours: float = 2.0):
        return self.base.get_forecast(utc_hour, horizon_hours)


class StochasticDataCentreEnv(DataCentreEnv):
    """DataCentreEnv with stochastic weather and multi-objective reward."""

    def _compute_reward(self, action_result, job):
        if "destination" not in action_result:
            return super()._compute_reward(action_result, job)
        dest = action_result["destination"]
        carbon_saved = action_result["local_carbon"] - action_result["routed_carbon"]
        r_carbon = carbon_saved * 8.0
        rf = action_result.get("renewable_fraction", 0)
        r_renewable = rf * 2.0
        cost_saved = action_result["local_cost"] - action_result["routed_cost"]
        r_cost = cost_saved * 0.10
        renewable_states = self.renewable_model.get_all_states(self.current_hour)
        renewable_fracs = {loc: renewable_states[loc]["renewable_fraction"] for loc in LOCATION_IDS}
        grid_states = self.grid_model.get_all_states(self.current_hour, renewable_fracs)
        dest_util = grid_states[dest]["utilisation"]
        r_util = -(dest_util - 0.85) * 12.0 if dest_util > 0.85 else 0.0
        r_sla = -20.0 if action_result["sla_violated"] else 0.0
        r_cap = -15.0 if action_result["capacity_exceeded"] else 0.0
        r_transfer = -action_result["transfer_cost"] * 2.0
        r_weather = 0.0
        active_events = getattr(self, '_active_weather_events', {})
        if dest in active_events:
            ev_type = active_events[dest]["type"]
            r_weather = -15.0 if ev_type in ("cold_snap", "storm", "heat_wave") else (+8.0 if ev_type == "solar_boom" else 0.0)
        return float(r_carbon + r_renewable + r_cost + r_util + r_sla + r_cap + r_transfer + r_weather)

    def step(self, action):
        obs, reward, done, truncated, info = super().step(action)
        return obs, reward, done, truncated, info

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        base_model = RenewableModel(seed=self.seed_val)
        base_model._cloud_state = dict(self.renewable_model._cloud_state)
        base_model._wind_gust_state = dict(self.renewable_model._wind_gust_state)
        rng = np.random.RandomState(self.seed_val + 9999)
        season = rng.choice(list(SEASONS.keys()))
        self._weather = StochasticWeatherModel(base_model, rng, season)
        self.renewable_model.get_solar_irradiance = self._weather.get_solar_irradiance
        self.renewable_model.get_wind_speed = self._weather.get_wind_speed
        self.renewable_model.get_renewable_fraction = self._weather.get_renewable_fraction
        self.renewable_model.get_all_states = self._weather.get_all_states
        self.renewable_model.get_forecast = self._weather.get_forecast
        self.renewable_model.step = self._weather.step
        info["season"] = season
        info["weather_regimes"] = dict(self._weather.regimes)
        self._original_base_carbon = dict(self.grid_model.base_carbon)
        obs = self._build_observation()
        return obs, info

    def _advance_time(self):
        if hasattr(self, '_original_base_carbon'):
            self.grid_model.base_carbon = dict(self._original_base_carbon)
        super()._advance_time()
        if hasattr(self, '_weather'):
            for loc_id, event in self._weather.active_events.items():
                mult = CARBON_MULTIPLIERS.get(event["type"], 1.0)
                self.grid_model.base_carbon[loc_id] = self._original_base_carbon[loc_id] * mult
            self._active_weather_events = dict(self._weather.active_events)
