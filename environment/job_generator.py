"""
Synthetic workload queue generator for GreenRoute.

Generates realistic data centre job arrivals calibrated against 
Google Cluster Trace (2019) distributions.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class JobType(Enum):
    FLEXIBLE = "FLEXIBLE"       # ML training, batch analytics, backups
    SEMI_FLEX = "SEMI_FLEX"     # Video rendering, ETL pipelines
    PINNED = "PINNED"           # Financial transactions, government DBs


# Job type distribution (from Google Cluster Trace analysis)
JOB_TYPE_PROBS = {
    JobType.FLEXIBLE: 0.45,
    JobType.SEMI_FLEX: 0.30,
    JobType.PINNED: 0.25,
}

# Max latency by job type (in hours)
MAX_LATENCY = {
    JobType.FLEXIBLE: 4.0,
    JobType.SEMI_FLEX: 0.5,
    JobType.PINNED: 0.0,  # Real-time
}

# Compute unit distributions (TFLOPS) by job type
COMPUTE_DISTRIBUTIONS = {
    JobType.FLEXIBLE: {"mean": 300, "std": 150, "min": 50, "max": 800},
    JobType.SEMI_FLEX: {"mean": 150, "std": 80, "min": 20, "max": 400},
    JobType.PINNED: {"mean": 50, "std": 30, "min": 10, "max": 200},
}

# Example job names for display
JOB_NAMES = {
    JobType.FLEXIBLE: [
        "ML Training Batch", "Batch Analytics Pipeline", "Database Backup",
        "Model Retraining Job", "Data Lake ETL", "Genome Sequencing Batch",
        "Video Transcoding Queue", "Large Language Model Fine-tune",
        "Climate Simulation Run", "Scientific Computing Batch",
    ],
    JobType.SEMI_FLEX: [
        "Video Rendering Job", "ETL Pipeline Run", "Report Generation",
        "Image Processing Batch", "Search Index Rebuild", "Data Warehouse Refresh",
        "Log Aggregation Pipeline", "Content Delivery Prep",
    ],
    JobType.PINNED: [
        "Financial Transaction Processing", "Government Database Query",
        "Real-time Fraud Detection", "Healthcare Records Access",
        "Payment Gateway Processing", "Stock Trading Engine",
        "Emergency Services Dispatch", "Regulatory Compliance Check",
    ],
}

LOCATION_IDS = ["CA", "TX", "VA", "OR", "AZ"]


@dataclass
class Job:
    """Represents a single data centre workload."""
    job_id: int
    job_type: JobType
    job_name: str
    origin: str                    # Location ID where job was submitted
    compute_units: float           # TFLOPS required
    max_latency_hours: float       # Maximum acceptable delay
    arrival_time: float            # UTC hour when job arrived
    is_routable: bool              # Whether the agent can route this job
    processing_time_hours: float   # How long the job takes to execute
    priority: int = 1              # 1=low, 2=medium, 3=high

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "job_name": self.job_name,
            "origin": self.origin,
            "compute_units": self.compute_units,
            "max_latency_hours": self.max_latency_hours,
            "arrival_time": self.arrival_time,
            "is_routable": self.is_routable,
            "processing_time_hours": self.processing_time_hours,
            "priority": self.priority,
        }


class JobGenerator:
    """Generates synthetic workload queues with realistic arrival patterns."""

    def __init__(self, seed: int = 42, jobs_per_hour: float = 10.0):
        self.rng = np.random.RandomState(seed)
        self.jobs_per_hour = jobs_per_hour
        self.job_counter = 0

    def _sample_job_type(self) -> JobType:
        types = list(JOB_TYPE_PROBS.keys())
        probs = list(JOB_TYPE_PROBS.values())
        return self.rng.choice(types, p=probs)

    def _sample_origin(self, utc_hour: float) -> str:
        """
        Sample job origin with time-of-day bias.
        
        Virginia gets more traffic during US East business hours.
        California gets more during West Coast hours.
        """
        # Base uniform weights
        weights = {loc: 1.0 for loc in LOCATION_IDS}

        # Business hour boost for East Coast (9am-5pm ET = 14-22 UTC)
        if 14 <= utc_hour <= 22:
            weights["VA"] *= 2.0

        # Business hour boost for West Coast (9am-5pm PT = 17-01 UTC)
        if utc_hour >= 17 or utc_hour <= 1:
            weights["CA"] *= 1.8
            weights["OR"] *= 1.3

        # Texas — steady throughout (energy sector runs 24/7)
        weights["TX"] *= 1.2

        total = sum(weights.values())
        probs = [weights[loc] / total for loc in LOCATION_IDS]
        return self.rng.choice(LOCATION_IDS, p=probs)

    def generate_job(self, utc_hour: float) -> Job:
        """Generate a single job at the given UTC hour."""
        self.job_counter += 1
        job_type = self._sample_job_type()
        origin = self._sample_origin(utc_hour)

        # Sample compute units
        dist = COMPUTE_DISTRIBUTIONS[job_type]
        compute = np.clip(
            self.rng.normal(dist["mean"], dist["std"]),
            dist["min"], dist["max"]
        )

        # Processing time proportional to compute
        proc_time = compute / 500.0 + self.rng.exponential(0.1)

        # Job name
        name = self.rng.choice(JOB_NAMES[job_type])

        # Priority (higher for pinned jobs)
        if job_type == JobType.PINNED:
            priority = 3
        elif job_type == JobType.SEMI_FLEX:
            priority = 2
        else:
            priority = 1

        return Job(
            job_id=self.job_counter,
            job_type=job_type,
            job_name=name,
            origin=origin,
            compute_units=float(compute),
            max_latency_hours=MAX_LATENCY[job_type],
            arrival_time=utc_hour,
            is_routable=(job_type != JobType.PINNED),
            processing_time_hours=float(proc_time),
            priority=priority,
        )

    def generate_batch(self, utc_hour: float, timestep_hours: float = 0.25) -> List[Job]:
        """
        Generate a batch of jobs for a single timestep.
        
        Number of jobs follows a Poisson process with time-of-day modulation.
        """
        # Arrival rate varies by time of day (higher during business hours)
        rate_modifier = 1.0 + 0.5 * np.sin(np.pi * (utc_hour - 6) / 12) if 6 <= utc_hour <= 18 else 0.6
        expected_jobs = self.jobs_per_hour * timestep_hours * rate_modifier
        n_jobs = self.rng.poisson(expected_jobs)
        n_jobs = max(1, min(n_jobs, 20))  # At least 1, at most 20 per step

        jobs = [self.generate_job(utc_hour) for _ in range(n_jobs)]
        return jobs

    def get_queue_stats(self, jobs: List[Job]) -> dict:
        """Get statistics about a job queue."""
        if not jobs:
            return {"total": 0, "flexible_fraction": 0.0, "avg_compute": 0.0}

        flexible_count = sum(1 for j in jobs if j.job_type == JobType.FLEXIBLE)
        semi_flex_count = sum(1 for j in jobs if j.job_type == JobType.SEMI_FLEX)
        pinned_count = sum(1 for j in jobs if j.job_type == JobType.PINNED)

        return {
            "total": len(jobs),
            "flexible": flexible_count,
            "semi_flex": semi_flex_count,
            "pinned": pinned_count,
            "flexible_fraction": (flexible_count + semi_flex_count) / len(jobs),
            "avg_compute": np.mean([j.compute_units for j in jobs]),
        }
