"""
Carbon budget tracker — tracks cumulative carbon savings vs targets.

Provides real-time monitoring of whether the agent is meeting carbon 
reduction goals and flags when the agent is gaming the reward.
"""

import numpy as np
from typing import List, Dict, Optional
from collections import deque


class CarbonBudgetTracker:
    """
    Tracks carbon savings against a fixed historical baseline.
    
    Uses a fixed baseline (not dynamic) to prevent the agent from 
    gaming the reward by artificially inflating local conditions.
    """

    # Fixed historical average carbon intensity per location (gCO₂/kWh)
    # Based on EPA eGRID 2022 annual averages
    HISTORICAL_BASELINE = {
        "CA": 210.0,
        "TX": 410.0,
        "VA": 490.0,
        "OR": 110.0,
        "AZ": 230.0,
    }

    def __init__(self, target_savings_per_episode: float = 5000.0,
                 alert_threshold: float = 0.5):
        """
        Args:
            target_savings_per_episode: Target gCO₂ savings per episode
            alert_threshold: Fraction of target below which we flag a warning
        """
        self.target = target_savings_per_episode
        self.alert_threshold = alert_threshold

        # Cumulative tracking
        self.total_carbon_emitted = 0.0
        self.total_baseline_carbon = 0.0
        self.total_carbon_saved = 0.0
        self.savings_history = deque(maxlen=1000)

        # Per-location tracking
        self.location_carbon = {loc: 0.0 for loc in self.HISTORICAL_BASELINE}
        self.location_jobs = {loc: 0 for loc in self.HISTORICAL_BASELINE}

        # Gaming detection
        self.local_processing_carbon = 0.0
        self.routed_processing_carbon = 0.0

    def record_job(self, origin: str, destination: str,
                   compute_units: float, actual_carbon_intensity: float):
        """Record a job routing decision for carbon tracking."""
        # Baseline: what would have happened if processed locally
        baseline_carbon = compute_units * self.HISTORICAL_BASELINE.get(origin, 300.0) / 1000.0

        # Actual carbon at destination
        actual_carbon = compute_units * actual_carbon_intensity / 1000.0

        # Carbon saved
        saved = baseline_carbon - actual_carbon

        self.total_baseline_carbon += baseline_carbon
        self.total_carbon_emitted += actual_carbon
        self.total_carbon_saved += saved
        self.savings_history.append(saved)

        # Track per-location
        self.location_carbon[destination] = (
            self.location_carbon.get(destination, 0.0) + actual_carbon
        )
        self.location_jobs[destination] = (
            self.location_jobs.get(destination, 0) + 1
        )

        # Track for gaming detection
        if origin == destination:
            self.local_processing_carbon += actual_carbon
        else:
            self.routed_processing_carbon += actual_carbon

    def get_progress(self) -> Dict:
        """Get current carbon budget progress."""
        progress = self.total_carbon_saved / max(self.target, 1e-6)
        return {
            "total_saved_gco2": self.total_carbon_saved,
            "total_emitted_gco2": self.total_carbon_emitted,
            "total_baseline_gco2": self.total_baseline_carbon,
            "progress_fraction": progress,
            "on_track": progress >= self.alert_threshold,
            "reduction_percentage": (
                self.total_carbon_saved / max(self.total_baseline_carbon, 1e-6) * 100
            ),
        }

    def check_gaming(self) -> Dict:
        """
        Detect if the agent might be gaming the reward.
        
        Red flag: if the agent processes most jobs locally during high-carbon 
        hours to inflate the baseline, then routes a few jobs to look good.
        """
        total_processed = self.local_processing_carbon + self.routed_processing_carbon
        if total_processed < 1e-6:
            return {"gaming_detected": False, "local_fraction": 0.0}

        local_fraction = self.local_processing_carbon / total_processed

        # If >80% of carbon comes from local processing, flag it
        gaming_detected = local_fraction > 0.8 and len(self.savings_history) > 50

        return {
            "gaming_detected": gaming_detected,
            "local_fraction": local_fraction,
            "local_carbon": self.local_processing_carbon,
            "routed_carbon": self.routed_processing_carbon,
        }

    def get_rolling_average(self, window: int = 50) -> float:
        """Get rolling average carbon saved per job."""
        if len(self.savings_history) == 0:
            return 0.0
        recent = list(self.savings_history)[-window:]
        return float(np.mean(recent))

    def reset(self):
        """Reset tracker for a new episode."""
        self.total_carbon_emitted = 0.0
        self.total_baseline_carbon = 0.0
        self.total_carbon_saved = 0.0
        self.savings_history.clear()
        self.location_carbon = {loc: 0.0 for loc in self.HISTORICAL_BASELINE}
        self.location_jobs = {loc: 0 for loc in self.HISTORICAL_BASELINE}
        self.local_processing_carbon = 0.0
        self.routed_processing_carbon = 0.0
