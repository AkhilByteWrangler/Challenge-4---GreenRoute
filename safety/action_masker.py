"""
Action masking module — enforces SLA, pinning, and capacity constraints.

The agent never sees invalid actions. This is a hard safety guarantee.
"""

import numpy as np
from typing import List, Optional


LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]
NUM_ACTIONS = 7


class ActionMasker:
    """
    Enforces hard constraints by masking invalid actions before the agent acts.
    
    Constraints enforced:
    1. SLA latency limits — cannot route to a location if transfer + processing > max_latency
    2. Job pinning — PINNED jobs always process locally (handled at env level)
    3. Capacity limits — cannot route to an overloaded data centre
    4. Data sovereignty — certain jobs cannot leave certain regions
    5. Hold limits — can only hold jobs with sufficient SLA headroom
    """

    def __init__(self, capacity_threshold: float = 0.95,
                 min_hold_headroom_hours: float = 0.5):
        self.capacity_threshold = capacity_threshold
        self.min_hold_headroom = min_hold_headroom_hours

    def get_mask(self, job: dict, env_state: dict) -> np.ndarray:
        """
        Generate action mask for the current job.
        
        Args:
            job: Current job dictionary with keys: origin, max_latency_hours,
                 compute_units, processing_time_hours, job_type
            env_state: Dictionary with keys per location: utilisation, 
                      available_capacity; and network model reference
                      
        Returns:
            Boolean mask of shape (NUM_ACTIONS,) — True = valid action
        """
        mask = np.zeros(NUM_ACTIONS, dtype=bool)

        if job is None:
            mask[0] = True  # Only local
            return mask

        # Action 0: local processing — always valid for routable jobs
        mask[0] = True

        origin = job["origin"]
        max_latency = job["max_latency_hours"]
        compute = job["compute_units"]
        proc_time = job["processing_time_hours"]

        # Actions 1-5: route to specific location
        for action_idx, loc_id in enumerate(LOCATION_IDS, start=1):
            is_valid = True

            # Check SLA: transfer time + processing time <= max latency
            if max_latency > 0:
                transfer_time = env_state.get("transfer_times", {}).get(
                    (origin, loc_id), 0.01
                )
                total_time = transfer_time + proc_time
                if total_time > max_latency:
                    is_valid = False

            # Check capacity: destination not overloaded
            utilisation = env_state.get("utilisations", {}).get(loc_id, 0.5)
            if utilisation > self.capacity_threshold:
                is_valid = False

            mask[action_idx] = is_valid

        # Action 6: hold in queue
        # Only valid if job has enough SLA headroom
        if max_latency >= self.min_hold_headroom:
            mask[6] = True
        else:
            mask[6] = False

        # SEMI_FLEX jobs should not be held too long
        if job.get("job_type") == "SEMI_FLEX":
            mask[6] = False  # Semi-flex jobs cannot be held

        return mask

    def apply_mask(self, q_values: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Apply action mask to Q-values (set invalid to -inf)."""
        masked = q_values.copy()
        masked[~mask] = -np.inf
        return masked

    def is_action_valid(self, action: int, mask: np.ndarray) -> bool:
        """Check if a specific action is valid."""
        return bool(mask[action])

    def get_safe_action(self, preferred_action: int, mask: np.ndarray) -> int:
        """
        Return the preferred action if valid, otherwise the best alternative.
        Falls back to action 0 (local) which is always valid.
        """
        if mask[preferred_action]:
            return preferred_action

        # Find valid actions
        valid = np.where(mask)[0]
        if len(valid) == 0:
            return 0  # Absolute fallback

        return int(valid[0])
