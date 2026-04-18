"""
Inter-region network transfer cost model.

Based on published AWS/GCP inter-region transfer pricing.
"""

import numpy as np
from typing import Dict, Tuple

LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]

# Transfer cost matrix ($/GB) — based on AWS inter-region data transfer pricing
# Diagonal = 0 (local), nearby regions cheaper, cross-country more expensive
TRANSFER_COST_MATRIX = {
    ("CA", "CA"): 0.00,  ("CA", "TX"): 0.04,  ("CA", "VA"): 0.06,  ("CA", "OR"): 0.02,  ("CA", "AZ"): 0.02,
    ("TX", "CA"): 0.04,  ("TX", "TX"): 0.00,  ("TX", "VA"): 0.04,  ("TX", "OR"): 0.05,  ("TX", "AZ"): 0.03,
    ("VA", "CA"): 0.06,  ("VA", "TX"): 0.04,  ("VA", "VA"): 0.00,  ("VA", "OR"): 0.06,  ("VA", "AZ"): 0.05,
    ("OR", "CA"): 0.02,  ("OR", "TX"): 0.05,  ("OR", "VA"): 0.06,  ("OR", "OR"): 0.00,  ("OR", "AZ"): 0.04,
    ("AZ", "CA"): 0.02,  ("AZ", "TX"): 0.03,  ("AZ", "VA"): 0.05,  ("AZ", "OR"): 0.04,  ("AZ", "AZ"): 0.00,
}

# Network latency matrix (milliseconds) — approximate round-trip times
LATENCY_MATRIX = {
    ("CA", "CA"): 1,   ("CA", "TX"): 35,  ("CA", "VA"): 65,  ("CA", "OR"): 15,  ("CA", "AZ"): 20,
    ("TX", "CA"): 35,  ("TX", "TX"): 1,   ("TX", "VA"): 30,  ("TX", "OR"): 45,  ("TX", "AZ"): 25,
    ("VA", "CA"): 65,  ("VA", "TX"): 30,  ("VA", "VA"): 1,   ("VA", "OR"): 60,  ("VA", "AZ"): 50,
    ("OR", "CA"): 15,  ("OR", "TX"): 45,  ("OR", "VA"): 60,  ("OR", "OR"): 1,   ("OR", "AZ"): 35,
    ("AZ", "CA"): 20,  ("AZ", "TX"): 25,  ("AZ", "VA"): 50,  ("AZ", "OR"): 35,  ("AZ", "AZ"): 1,
}

# Data transfer size per compute unit (GB per TFLOP)
DATA_PER_COMPUTE = 0.5  # GB per TFLOP of compute


class NetworkCostModel:
    """Models inter-region transfer costs and network latency."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.transfer_costs = TRANSFER_COST_MATRIX.copy()
        self.latencies = LATENCY_MATRIX.copy()

    def get_transfer_cost(self, origin: str, destination: str, compute_units: float) -> float:
        """
        Calculate the network transfer cost ($) for routing a job.
        
        Cost depends on origin-destination pair and job size.
        """
        if origin == destination:
            return 0.0

        cost_per_gb = self.transfer_costs.get((origin, destination), 0.05)
        data_size_gb = compute_units * DATA_PER_COMPUTE
        total_cost = cost_per_gb * data_size_gb

        # Add small random congestion surcharge
        congestion = self.rng.uniform(0, 0.1) * total_cost
        return float(total_cost + congestion)

    def get_transfer_latency(self, origin: str, destination: str) -> float:
        """Get network latency (hours) for transferring between locations."""
        if origin == destination:
            return 0.0

        latency_ms = self.latencies.get((origin, destination), 50)
        # Convert ms to hours and add transfer time (data size dependent)
        base_latency_hours = latency_ms / (3600 * 1000)
        # Add realistic data transfer time (assume 10 Gbps link)
        transfer_overhead = 0.01  # ~36 seconds base overhead
        return float(base_latency_hours + transfer_overhead)

    def get_cost_matrix_sum(self) -> float:
        """Get the sum of all transfer costs (used as a global state feature)."""
        return float(sum(self.transfer_costs.values()))

    def get_cost_matrix_array(self) -> np.ndarray:
        """Get transfer cost matrix as a 5x5 numpy array."""
        n = len(LOCATION_IDS)
        matrix = np.zeros((n, n))
        for i, loc_i in enumerate(LOCATION_IDS):
            for j, loc_j in enumerate(LOCATION_IDS):
                matrix[i, j] = self.transfer_costs.get((loc_i, loc_j), 0.05)
        return matrix

    def would_violate_sla(self, origin: str, destination: str,
                          max_latency_hours: float, processing_time: float) -> bool:
        """Check if routing this job would violate its latency SLA."""
        transfer_time = self.get_transfer_latency(origin, destination)
        total_time = transfer_time + processing_time
        return total_time > max_latency_hours if max_latency_hours > 0 else (origin != destination)
