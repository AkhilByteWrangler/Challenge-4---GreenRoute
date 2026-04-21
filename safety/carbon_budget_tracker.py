"""Carbon budget tracker — monitors savings vs targets and detects reward gaming."""

import numpy as np
from typing import Dict
from collections import deque


class CarbonBudgetTracker:
    """Tracks carbon savings against fixed historical baseline."""

    HISTORICAL_BASELINE = {
        "CA": 210.0,
        "TX": 410.0,
        "VA": 490.0,
        "OR": 110.0,
        "AZ": 230.0,
    }

    def __init__(self, target_savings_per_episode: float = 5000.0,
                 alert_threshold: float = 0.5) -> None:
        """Initialize tracker with savings target and alert threshold."""
        self.target = target_savings_per_episode
        self.alert_threshold = alert_threshold

        self.total_carbon_emitted = 0.0
        self.total_baseline_carbon = 0.0
        self.total_carbon_saved = 0.0
        self.savings_history: deque = deque(maxlen=1000)

        self.location_carbon = {loc: 0.0 for loc in self.HISTORICAL_BASELINE}
        self.location_jobs = {loc: 0 for loc in self.HISTORICAL_BASELINE}

        self.local_processing_carbon = 0.0
        self.routed_processing_carbon = 0.0

    def record_job(self, origin: str, destination: str,
                   compute_units: float, actual_carbon_intensity: float) -> None:
        """Record job routing decision for carbon tracking and gaming detection."""
        baseline_carbon = compute_units * self.HISTORICAL_BASELINE.get(origin, 300.0) / 1000.0
        actual_carbon = compute_units * actual_carbon_intensity / 1000.0
        saved = baseline_carbon - actual_carbon

        self.total_baseline_carbon += baseline_carbon
        self.total_carbon_emitted += actual_carbon
        self.total_carbon_saved += saved
        self.savings_history.append(saved)

        self.location_carbon[destination] = self.location_carbon.get(destination, 0.0) + actual_carbon
        self.location_jobs[destination] = self.location_jobs.get(destination, 0) + 1

        if origin == destination:
            self.local_processing_carbon += actual_carbon
        else:
            self.routed_processing_carbon += actual_carbon

    def get_progress(self) -> Dict:
        """Get current carbon budget progress metrics."""
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
        """Detect if agent is gaming reward by routing only during favorable times."""
        total_processed = self.local_processing_carbon + self.routed_processing_carbon
        if total_processed < 1e-6:
            return {"gaming_detected": False, "local_fraction": 0.0}

        local_fraction = self.local_processing_carbon / total_processed
        gaming_detected = local_fraction > 0.8 and len(self.savings_history) > 50

        return {
            "gaming_detected": gaming_detected,
            "local_fraction": local_fraction,
            "local_carbon": self.local_processing_carbon,
            "routed_carbon": self.routed_processing_carbon,
        }

    def get_rolling_average(self, window: int = 50) -> float:
        """Get rolling average carbon saved per job over recent window."""
        if len(self.savings_history) == 0:
            return 0.0
        recent = list(self.savings_history)[-window:]
        return float(np.mean(recent))

    def reset(self) -> None:
        """Reset tracker for new episode."""
        self.total_carbon_emitted = 0.0
        self.total_baseline_carbon = 0.0
        self.total_carbon_saved = 0.0
        self.savings_history.clear()
        self.location_carbon = {loc: 0.0 for loc in self.HISTORICAL_BASELINE}
        self.location_jobs = {loc: 0 for loc in self.HISTORICAL_BASELINE}
        self.local_processing_carbon = 0.0
        self.routed_processing_carbon = 0.0
