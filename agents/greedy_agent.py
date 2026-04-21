"""Greedy baseline agent — always routes to the lowest carbon intensity location."""

import numpy as np

CARBON_INDEX = 2
FEATURES_PER_LOCATION = 7
NUM_REMOTE_LOCATIONS = 5


class GreedyAgent:
    """Baseline agent that always selects the location with lowest carbon intensity."""

    def __init__(self, num_actions: int = 7, seed: int = 42):
        self.num_actions = num_actions
        self.name = "Greedy"

    def select_action(self, state: np.ndarray, action_mask: np.ndarray = None) -> int:
        """Select location with lowest carbon intensity."""
        carbon_intensities = state[CARBON_INDEX::FEATURES_PER_LOCATION][:NUM_REMOTE_LOCATIONS]

        best_action = 0
        best_carbon = float("inf")

        for action_idx in range(1, NUM_REMOTE_LOCATIONS + 1):
            if action_mask is not None and not action_mask[action_idx]:
                continue
            carbon = carbon_intensities[action_idx - 1]
            if carbon < best_carbon:
                best_carbon = carbon
                best_action = action_idx

        return best_action

    def update(self, state, action, reward, next_state, done):
        pass  # No learning

    def save(self, path: str):
        pass

    def load(self, path: str):
        pass
