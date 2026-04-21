"""Action masking module — enforces SLA, capacity, and hold constraints."""

import numpy as np
from typing import Dict, Optional


LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]
NUM_ACTIONS = 7


class ActionMasker:
    """Enforces hard constraints by masking invalid actions before agent execution."""

    def __init__(self, capacity_threshold: float = 0.95,
                 min_hold_headroom_hours: float = 0.5) -> None:
        """Initialize action masker with capacity and hold constraints."""
        self.capacity_threshold = capacity_threshold
        self.min_hold_headroom = min_hold_headroom_hours

    def get_mask(self, job: Optional[Dict], env_state: Dict) -> np.ndarray:
        """Generate action mask enforcing SLA, capacity, and hold constraints."""
        mask = np.zeros(NUM_ACTIONS, dtype=bool)

        if job is None:
            mask[0] = True
            return mask

        mask[0] = True

        origin = job["origin"]
        max_latency = job["max_latency_hours"]
        proc_time = job["processing_time_hours"]

        for action_idx, loc_id in enumerate(LOCATION_IDS, start=1):
            is_valid = True

            if max_latency > 0:
                transfer_time = env_state.get("transfer_times", {}).get(
                    (origin, loc_id), 0.01
                )
                if transfer_time + proc_time > max_latency:
                    is_valid = False

            utilisation = env_state.get("utilisations", {}).get(loc_id, 0.5)
            if utilisation > self.capacity_threshold:
                is_valid = False

            mask[action_idx] = is_valid

        if max_latency >= self.min_hold_headroom and job.get("job_type") != "SEMI_FLEX":
            mask[6] = True

        return mask

    def apply_mask(self, q_values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Apply action mask to Q-values by setting invalid actions to -inf."""
        masked = q_values.copy()
        masked[~mask] = -np.inf
        return masked

    def is_action_valid(self, action: int, mask: np.ndarray) -> bool:
        """Check if a specific action is valid."""
        return bool(mask[action])

    def get_safe_action(self, preferred_action: int, mask: np.ndarray) -> int:
        """Get preferred action if valid; otherwise return first valid alternative."""
        if mask[preferred_action]:
            return preferred_action

        valid = np.where(mask)[0]
        return int(valid[0]) if len(valid) > 0 else 0
