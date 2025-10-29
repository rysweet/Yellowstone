"""
Predefined load profiles for load testing.

Provides standard load profiles including light, medium, heavy, and stress profiles,
as well as dynamic profiles for ramp and spike testing patterns.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable
import time


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class LoadProfile:
    """Base class for load profiles.

    Defines the characteristics of a load pattern including:
    - Target queries per second (QPS)
    - Query distribution mix
    - Duration
    - Ramp-up pattern
    - Resource limits
    """

    name: str
    """Profile name"""

    target_qps: int
    """Target queries per second"""

    duration_seconds: int
    """Test duration in seconds"""

    simple_query_percent: int = 60
    """Percentage of simple queries"""

    medium_query_percent: int = 30
    """Percentage of medium complexity queries"""

    complex_query_percent: int = 10
    """Percentage of complex queries"""

    max_concurrent_queries: int = 100
    """Maximum concurrent queries allowed"""

    ramp_up_seconds: int = 10
    """Ramp-up time to reach target QPS"""

    resource_limits: Dict[str, float] = field(default_factory=lambda: {
        "max_memory_mb": 1024,
        "max_cpu_percent": 80,
        "max_latency_ms": 5000,
    })
    """Resource constraints"""

    description: str = ""
    """Profile description"""

    def get_qps_at_time(self, elapsed_seconds: float) -> int:
        """Calculate QPS at a given elapsed time.

        Args:
            elapsed_seconds: Seconds elapsed since test start

        Returns:
            Queries per second for this moment in time
        """
        if elapsed_seconds < self.ramp_up_seconds:
            # Linear ramp-up
            return int(self.target_qps * (elapsed_seconds / self.ramp_up_seconds))
        return self.target_qps

    def get_query_distribution(self) -> Dict[str, int]:
        """Get query distribution for this profile.

        Returns:
            Dictionary mapping query complexity to count
        """
        return {
            QueryComplexity.SIMPLE.value: self.simple_query_percent,
            QueryComplexity.MEDIUM.value: self.medium_query_percent,
            QueryComplexity.COMPLEX.value: self.complex_query_percent,
        }

    def validate(self) -> List[str]:
        """Validate profile configuration.

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        if self.simple_query_percent + self.medium_query_percent + self.complex_query_percent != 100:
            errors.append("Query percentages must sum to 100")

        if self.target_qps < 1:
            errors.append("target_qps must be at least 1")

        if self.duration_seconds < 1:
            errors.append("duration_seconds must be at least 1")

        if self.max_concurrent_queries < 1:
            errors.append("max_concurrent_queries must be at least 1")

        if self.ramp_up_seconds > self.duration_seconds:
            errors.append("ramp_up_seconds cannot exceed duration_seconds")

        return errors


@dataclass
class LightLoadProfile(LoadProfile):
    """Light load profile: 10 QPS steady state.

    Good for baseline performance testing and continuous monitoring.
    Characteristics:
    - 10 queries per second
    - 60% simple, 30% medium, 10% complex queries
    - 5 minute duration
    - Quick 2 second ramp-up
    """

    def __init__(self):
        super().__init__(
            name="light",
            target_qps=10,
            duration_seconds=300,
            simple_query_percent=60,
            medium_query_percent=30,
            complex_query_percent=10,
            max_concurrent_queries=20,
            ramp_up_seconds=2,
            resource_limits={
                "max_memory_mb": 256,
                "max_cpu_percent": 20,
                "max_latency_ms": 1000,
            },
            description="Light load: 10 QPS, suitable for baseline testing"
        )


@dataclass
class MediumLoadProfile(LoadProfile):
    """Medium load profile: 50 QPS steady state.

    Good for typical production workload simulation.
    Characteristics:
    - 50 queries per second
    - 50% simple, 40% medium, 10% complex queries
    - 10 minute duration
    - 5 second ramp-up
    """

    def __init__(self):
        super().__init__(
            name="medium",
            target_qps=50,
            duration_seconds=600,
            simple_query_percent=50,
            medium_query_percent=40,
            complex_query_percent=10,
            max_concurrent_queries=75,
            ramp_up_seconds=5,
            resource_limits={
                "max_memory_mb": 512,
                "max_cpu_percent": 50,
                "max_latency_ms": 2000,
            },
            description="Medium load: 50 QPS, typical production simulation"
        )


@dataclass
class HeavyLoadProfile(LoadProfile):
    """Heavy load profile: 100 QPS steady state.

    Good for peak load simulation and bottleneck identification.
    Characteristics:
    - 100 queries per second
    - 40% simple, 45% medium, 15% complex queries
    - 15 minute duration
    - 10 second ramp-up
    """

    def __init__(self):
        super().__init__(
            name="heavy",
            target_qps=100,
            duration_seconds=900,
            simple_query_percent=40,
            medium_query_percent=45,
            complex_query_percent=15,
            max_concurrent_queries=150,
            ramp_up_seconds=10,
            resource_limits={
                "max_memory_mb": 1024,
                "max_cpu_percent": 75,
                "max_latency_ms": 3000,
            },
            description="Heavy load: 100 QPS, peak production simulation"
        )


@dataclass
class StressLoadProfile(LoadProfile):
    """Stress load profile: 200+ QPS beyond normal capacity.

    Good for finding system breaking points and limits.
    Characteristics:
    - 200+ queries per second
    - 30% simple, 50% medium, 20% complex queries
    - 20 minute duration
    - 15 second ramp-up to avoid immediate overwhelm
    """

    def __init__(self):
        super().__init__(
            name="stress",
            target_qps=200,
            duration_seconds=1200,
            simple_query_percent=30,
            medium_query_percent=50,
            complex_query_percent=20,
            max_concurrent_queries=300,
            ramp_up_seconds=15,
            resource_limits={
                "max_memory_mb": 2048,
                "max_cpu_percent": 100,
                "max_latency_ms": 5000,
            },
            description="Stress load: 200+ QPS, finding system limits"
        )


@dataclass
class RampLoadProfile(LoadProfile):
    """Ramp load profile: gradually increasing QPS.

    Good for finding the knee of the curve and degradation patterns.
    Characteristics:
    - Ramps from 10 to 150 QPS over 10 minutes
    - 50% simple, 40% medium, 10% complex queries
    """

    def __init__(self):
        super().__init__(
            name="ramp",
            target_qps=150,
            duration_seconds=600,
            simple_query_percent=50,
            medium_query_percent=40,
            complex_query_percent=10,
            max_concurrent_queries=200,
            ramp_up_seconds=600,  # Full duration is ramp-up
            resource_limits={
                "max_memory_mb": 1024,
                "max_cpu_percent": 80,
                "max_latency_ms": 4000,
            },
            description="Ramp load: gradually increasing to 150 QPS"
        )


@dataclass
class SpikeLoadProfile(LoadProfile):
    """Spike load profile: sudden traffic spikes.

    Good for testing recovery and spike handling capability.
    Characteristics:
    - Starts at 10 QPS
    - Spikes to 250 QPS multiple times
    - 15 minute duration with spike intervals
    """

    name: str = "spike"
    target_qps: int = 250
    duration_seconds: int = 900
    simple_query_percent: int = 40
    medium_query_percent: int = 45
    complex_query_percent: int = 15
    max_concurrent_queries: int = 350
    ramp_up_seconds: int = 5
    spike_interval_seconds: int = 60
    spike_duration_seconds: int = 10
    baseline_qps: int = 10
    resource_limits: Dict[str, float] = field(default_factory=lambda: {
        "max_memory_mb": 2048,
        "max_cpu_percent": 100,
        "max_latency_ms": 6000,
    })
    description: str = "Spike load: sudden traffic spikes to 250 QPS"

    def get_qps_at_time(self, elapsed_seconds: float) -> int:
        """Calculate QPS with spike pattern.

        Args:
            elapsed_seconds: Seconds elapsed since test start

        Returns:
            Queries per second for this moment in time
        """
        # Calculate position in spike cycle
        cycle_position = elapsed_seconds % self.spike_interval_seconds

        if cycle_position < self.spike_duration_seconds:
            # During spike phase, ramp up quickly
            return int(self.baseline_qps +
                      (self.target_qps - self.baseline_qps) *
                      (cycle_position / self.spike_duration_seconds))
        else:
            # Between spikes, gradually decrease
            return max(self.baseline_qps,
                      int(self.target_qps *
                         (1.0 - (cycle_position - self.spike_duration_seconds) /
                         (self.spike_interval_seconds - self.spike_duration_seconds))))


# Registry of available load profiles
load_profile_registry: Dict[str, Callable[[], LoadProfile]] = {
    "light": LightLoadProfile,
    "medium": MediumLoadProfile,
    "heavy": HeavyLoadProfile,
    "stress": StressLoadProfile,
    "ramp": RampLoadProfile,
    "spike": SpikeLoadProfile,
}


def get_load_profile(name: str) -> LoadProfile:
    """Get a load profile by name.

    Args:
        name: Profile name (light, medium, heavy, stress, ramp, spike)

    Returns:
        LoadProfile instance

    Raises:
        ValueError: If profile name not found

    Example:
        >>> profile = get_load_profile("medium")
        >>> print(f"Target QPS: {profile.target_qps}")
        Target QPS: 50
    """
    if name not in load_profile_registry:
        available = ", ".join(load_profile_registry.keys())
        raise ValueError(
            f"Unknown load profile '{name}'. Available: {available}"
        )

    profile_class = load_profile_registry[name]
    return profile_class()
