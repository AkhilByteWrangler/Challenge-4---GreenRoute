"""Tabular Q-Learning agent for GreenRoute."""

import numpy as np
import pickle
from collections import defaultdict
from typing import Optional


class QTableAgent:
    """
    Tabular Q-Learning agent with state discretisation.
    
    Since the state space is continuous (47 dimensions), we discretise 
    key features into bins for the Q-table lookup.
    """

    def __init__(self, num_actions: int = 7, seed: int = 42,
                 learning_rate: float = 0.1, discount_factor: float = 0.99,
                 epsilon_start: float = 1.0, epsilon_end: float = 0.05,
                 epsilon_decay: float = 0.995, num_bins: int = 10):
        self.num_actions = num_actions
        self.rng = np.random.RandomState(seed)
        self.name = "Q-Learning"

        # Hyperparameters
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.num_bins = num_bins

        # Q-table as a dictionary of state_key -> action_values
        self.q_table = defaultdict(lambda: np.zeros(num_actions))

        # Bin edges for key state features (learned from first few episodes)
        self.bin_edges = None
        self.state_buffer = []
        self.warmup_steps = 500

        # Stats
        self.total_updates = 0

    def _discretise_state(self, state: np.ndarray) -> tuple:
        """
        Discretise the continuous state into a hashable key.
        
        We use a subset of the most important features:
        - Carbon intensity for each location (5 features)
        - Solar irradiance for each location (5 features)
        - Time of day (2 features: sin, cos)
        - Queue length (1 feature)
        Total: 13 features discretised into bins
        """
        # Select key features
        key_indices = [
            0, 7, 14, 21, 28,    # Solar irradiance per location
            2, 9, 16, 23, 30,    # Carbon intensity per location
            35, 36,               # Time sin/cos
            43,                   # Queue length
        ]
        key_features = state[key_indices]

        if self.bin_edges is None:
            # During warmup, collect states to build bin edges
            self.state_buffer.append(key_features)
            if len(self.state_buffer) >= self.warmup_steps:
                self._build_bins()
            # Use simple rounding during warmup
            return tuple(np.round(key_features * self.num_bins).astype(int))

        # Digitise into bins
        discretised = []
        for i, val in enumerate(key_features):
            bin_idx = np.digitize(val, self.bin_edges[i]) - 1
            bin_idx = np.clip(bin_idx, 0, self.num_bins - 1)
            discretised.append(int(bin_idx))

        return tuple(discretised)

    def _build_bins(self):
        """Build bin edges from collected state samples."""
        states = np.array(self.state_buffer)
        self.bin_edges = []
        for i in range(states.shape[1]):
            percentiles = np.linspace(0, 100, self.num_bins + 1)[1:-1]
            edges = np.percentile(states[:, i], percentiles)
            # Ensure unique edges
            edges = np.unique(edges)
            if len(edges) == 0:
                edges = np.array([0.5])
            self.bin_edges.append(edges)

    def select_action(self, state: np.ndarray, action_mask: np.ndarray = None) -> int:
        """Epsilon-greedy action selection with action masking."""
        if self.rng.random() < self.epsilon:
            if action_mask is not None:
                valid = np.where(action_mask)[0]
                return int(self.rng.choice(valid))
            return int(self.rng.randint(0, self.num_actions))

        state_key = self._discretise_state(state)
        q_values = self.q_table[state_key]

        if action_mask is not None:
            q_values = q_values.copy()
            q_values[~action_mask] = -np.inf

        return int(np.argmax(q_values))

    def update(self, state: np.ndarray, action: int, reward: float,
               next_state: np.ndarray, done: bool):
        """Q-learning update: Q(s,a) <- Q(s,a) + lr * (r + gamma*max_a'Q(s',a') - Q(s,a))"""
        state_key = self._discretise_state(state)
        next_state_key = self._discretise_state(next_state)

        current_q = self.q_table[state_key][action]
        next_max_q = np.max(self.q_table[next_state_key]) if not done else 0.0

        td_target = reward + self.gamma * next_max_q
        self.q_table[state_key][action] += self.lr * (td_target - current_q)

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        self.total_updates += 1

    def save(self, path: str):
        """Save Q-table to file."""
        data = {
            "q_table": dict(self.q_table),
            "bin_edges": self.bin_edges,
            "epsilon": self.epsilon,
            "total_updates": self.total_updates,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str):
        """Load Q-table from file."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.q_table = defaultdict(lambda: np.zeros(self.num_actions), data["q_table"])
        self.bin_edges = data["bin_edges"]
        self.epsilon = data["epsilon"]
        self.total_updates = data["total_updates"]
