"""Greedy baseline agent — always routes to the lowest carbon intensity location."""

import numpy as np


class GreedyAgent:
    """
    Always routes to the location with the lowest carbon intensity right now.
    
    This is the baseline that looks good in aggregate but makes three critical mistakes:
    1. Ignores the future (overloads the best location)
    2. Ignores forecasts (cannot anticipate renewable windows)
    3. Creates instability (all jobs pile into the same location)
    """

    def __init__(self, num_actions: int = 7, seed: int = 42):
        self.num_actions = num_actions
        self.name = "Greedy"

    def select_action(self, state: np.ndarray, action_mask: np.ndarray = None) -> int:
        """
        Select the location with the lowest carbon intensity.
        
        State layout per location (7 features each):
          [0] solar_irradiance, [1] wind_speed, [2] carbon_intensity,
          [3] utilisation, [4] available_capacity, [5] energy_cost, [6] pue
        """
        # Extract carbon intensity for each of the 5 locations
        carbon_intensities = []
        for i in range(5):
            offset = i * 7  # 7 features per location
            carbon = state[offset + 2]  # carbon_intensity is the 3rd feature
            carbon_intensities.append(carbon)

        # Actions 1-5 correspond to CA, TX, VA, OR, AZ
        # Find the location with minimum carbon intensity among valid actions
        best_action = 0  # Default: local
        best_carbon = float("inf")

        for action_idx in range(1, 6):  # Actions 1 through 5
            loc_idx = action_idx - 1
            if action_mask is not None and not action_mask[action_idx]:
                continue
            if carbon_intensities[loc_idx] < best_carbon:
                best_carbon = carbon_intensities[loc_idx]
                best_action = action_idx

        return best_action

    def update(self, state, action, reward, next_state, done):
        pass  # No learning

    def save(self, path: str):
        pass

    def load(self, path: str):
        pass
