"""Random baseline agent — selects uniformly from valid actions."""

import numpy as np


class RandomAgent:
    """Selects a random valid action each step. Baseline for comparison."""

    def __init__(self, num_actions: int = 7, seed: int = 42):
        self.num_actions = num_actions
        self.rng = np.random.RandomState(seed)
        self.name = "Random"

    def select_action(self, state: np.ndarray, action_mask: np.ndarray = None) -> int:
        if action_mask is not None:
            valid = np.where(action_mask)[0]
            return int(self.rng.choice(valid))
        return int(self.rng.randint(0, self.num_actions))

    def update(self, state, action, reward, next_state, done):
        pass  # No learning

    def save(self, path: str):
        pass

    def load(self, path: str):
        pass
