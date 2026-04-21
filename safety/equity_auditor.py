"""Equity auditor — monitors workload distribution and flags imbalances."""

import numpy as np
from typing import Dict
from collections import defaultdict


class EquityAuditor:
    """Audits workload distribution to prevent location starvation or overloading."""

    def __init__(self, num_locations: int = 5,
                 min_utilisation_floor: float = 0.15,
                 max_utilisation_ceiling: float = 0.90,
                 imbalance_threshold: float = 0.4) -> None:
        """Initialize auditor with utilisation thresholds and imbalance limits."""
        self.num_locations = num_locations
        self.min_floor = min_utilisation_floor
        self.max_ceiling = max_utilisation_ceiling
        self.imbalance_threshold = imbalance_threshold

        self.location_ids = ["CA", "TX", "VA", "OR", "AZ"]
        self.jobs_routed_to: defaultdict = defaultdict(int)
        self.total_compute_to: defaultdict = defaultdict(float)

    def record_routing(self, destination: str, compute_units: float) -> None:
        """Record routing decision for distribution tracking."""
        self.jobs_routed_to[destination] += 1
        self.total_compute_to[destination] += compute_units

    def audit(self, utilisations: Dict[str, float]) -> Dict:
        """Audit current workload distribution and return audit report."""
        util_values = [utilisations.get(loc, 0.0) for loc in self.location_ids]
        min_util = min(util_values)
        max_util = max(util_values)
        imbalance = max_util - min_util

        starved = [loc for loc in self.location_ids if utilisations.get(loc, 0.0) < self.min_floor]
        overloaded = [loc for loc in self.location_ids if utilisations.get(loc, 0.0) > self.max_ceiling]

        total_jobs = sum(self.jobs_routed_to.values())
        if total_jobs > 0:
            job_shares = np.array([
                self.jobs_routed_to.get(loc, 0) / total_jobs
                for loc in self.location_ids
            ])
            gini = self._gini_coefficient(job_shares)
        else:
            gini = 0.0

        warnings = []
        if starved:
            warnings.append(f"Starved locations (util < {self.min_floor:.0%}): {starved}")
        if overloaded:
            warnings.append(f"Overloaded locations (util > {self.max_ceiling:.0%}): {overloaded}")
        if imbalance > self.imbalance_threshold:
            warnings.append(f"High imbalance: {imbalance:.2f} (threshold: {self.imbalance_threshold})")

        return {
            "imbalance": imbalance,
            "min_utilisation": min_util,
            "max_utilisation": max_util,
            "starved_locations": starved,
            "overloaded_locations": overloaded,
            "gini_coefficient": gini,
            "job_distribution": dict(self.jobs_routed_to),
            "warnings": warnings,
            "is_equitable": len(warnings) == 0,
        }

    def _gini_coefficient(self, shares: np.ndarray) -> float:
        """Compute Gini coefficient from distribution shares (0=equal, 1=unequal)."""
        if len(shares) == 0 or np.sum(shares) == 0:
            return 0.0
        sorted_shares = np.sort(shares)
        n = len(sorted_shares)
        index = np.arange(1, n + 1)
        return float(((2 * index - n - 1) * sorted_shares).sum() / (n * sorted_shares.sum()))

    def get_equity_reward_modifier(self, utilisations: Dict[str, float]) -> float:
        """Get reward modifier penalizing imbalanced or overloaded distribution."""
        audit = self.audit(utilisations)
        modifier = 0.0

        if audit["starved_locations"]:
            modifier -= 2.0 * len(audit["starved_locations"])

        if audit["overloaded_locations"]:
            modifier -= 3.0 * len(audit["overloaded_locations"])

        if audit["imbalance"] > self.imbalance_threshold:
            modifier -= audit["imbalance"] * 5.0

        return modifier

    def reset(self) -> None:
        """Reset auditor for new episode."""
        self.jobs_routed_to.clear()
        self.total_compute_to.clear()
