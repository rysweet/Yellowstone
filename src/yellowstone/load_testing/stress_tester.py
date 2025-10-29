"""
Stress testing framework for finding system limits and breaking points.

Provides capabilities for pushing systems to their limits, identifying breaking points,
testing memory pressure scenarios, connection pool exhaustion, and recovery behavior.
"""

import asyncio
import threading
import time
import psutil
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any, Awaitable
from datetime import datetime
from enum import Enum
import random


class StressType(Enum):
    """Types of stress tests."""
    STEADY_INCREASE = "steady_increase"
    CONNECTION_POOL_EXHAUSTION = "connection_pool_exhaustion"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_INTENSIVE = "cpu_intensive"
    SPIKE_STORM = "spike_storm"
    SUSTAINED_SPIKE = "sustained_spike"


@dataclass
class BreakingPoint:
    """Represents a system breaking point.

    Identifies when the system fails or degradation reaches critical levels.
    """
    qps_at_break: int
    """Queries per second when system broke"""

    time_to_break_seconds: float
    """Seconds elapsed before breaking point"""

    memory_mb_at_break: float
    """Memory usage at breaking point"""

    cpu_percent_at_break: float
    """CPU usage at breaking point"""

    error_message: str
    """Error or reason for breaking"""

    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __str__(self) -> str:
        return (
            f"BreakingPoint(QPS: {self.qps_at_break}, "
            f"Time: {self.time_to_break_seconds:.2f}s, "
            f"Memory: {self.memory_mb_at_break:.2f}MB, "
            f"CPU: {self.cpu_percent_at_break:.2f}%, "
            f"Error: {self.error_message})"
        )


@dataclass
class RecoveryMetrics:
    """Metrics related to system recovery after stress.

    Tracks how quickly a system recovers from stress conditions.
    """
    recovery_start_time: datetime
    """When recovery started"""

    time_to_recover_seconds: float
    """Seconds to return to normal operation"""

    error_rate_before: float
    """Error rate before recovery"""

    error_rate_after: float
    """Error rate after recovery"""

    latency_before_ms: float
    """Average latency before recovery"""

    latency_after_ms: float
    """Average latency after recovery"""

    successful: bool
    """Whether recovery was successful"""

    def __str__(self) -> str:
        status = "Successful" if self.successful else "Failed"
        return (
            f"RecoveryMetrics({status}, "
            f"Recovery Time: {self.time_to_recover_seconds:.2f}s, "
            f"Error Rate: {self.error_rate_before:.1%} -> {self.error_rate_after:.1%}, "
            f"Latency: {self.latency_before_ms:.2f}ms -> {self.latency_after_ms:.2f}ms)"
        )


@dataclass
class StressTestResult:
    """Complete result of a stress test."""
    stress_type: str
    start_time: datetime
    end_time: datetime
    peak_qps: int
    breaking_points: List[BreakingPoint] = field(default_factory=list)
    recovery_metrics: Optional[RecoveryMetrics] = None
    total_queries_executed: int = 0
    total_errors: int = 0
    success_rate: float = 0.0
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    notes: str = ""

    @property
    def duration_seconds(self) -> float:
        """Test duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def __str__(self) -> str:
        breaking_str = "\n  ".join(str(bp) for bp in self.breaking_points)
        recovery_str = str(self.recovery_metrics) if self.recovery_metrics else "No recovery measured"

        return (
            f"StressTestResult(\n"
            f"  Type: {self.stress_type}\n"
            f"  Duration: {self.duration_seconds:.2f}s\n"
            f"  Peak QPS: {self.peak_qps}, Total: {self.total_queries_executed}\n"
            f"  Success Rate: {self.success_rate:.1%}\n"
            f"  Peak Memory: {self.peak_memory_mb:.2f}MB, Peak CPU: {self.peak_cpu_percent:.2f}%\n"
            f"  Breaking Points:\n    {breaking_str}\n"
            f"  Recovery: {recovery_str}\n"
            f")"
        )


class StressTester:
    """Stress testing orchestrator.

    Coordinates different stress test scenarios, pushing system to limits,
    and measuring recovery capabilities.
    """

    def __init__(
        self,
        execution_func: Callable[[str, str], Awaitable[Dict[str, Any]]],
        sample_queries: Dict[str, List[str]],
        resource_sampling_interval: float = 0.5,
    ):
        """Initialize stress tester.

        Args:
            execution_func: Async function for executing queries
                          Signature: async def (query: str, complexity: str) -> Dict[str, Any]
            sample_queries: Dict mapping complexity to list of sample queries
            resource_sampling_interval: Seconds between resource samples
        """
        self.execution_func = execution_func
        self.sample_queries = sample_queries
        self.resource_sampling_interval = resource_sampling_interval
        self.active_queries = 0
        self.total_queries = 0
        self.total_errors = 0
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self.resource_history: List[tuple[datetime, float, float]] = []

    def _get_resource_usage(self) -> tuple[float, float]:
        """Get current memory and CPU usage.

        Returns:
            Tuple of (memory_mb, cpu_percent)
        """
        process = psutil.Process()
        return (
            process.memory_info().rss / 1024 / 1024,
            process.cpu_percent(interval=0.05),
        )

    def _monitor_resources_background(self) -> None:
        """Background thread for monitoring resources."""
        while not self._stop_flag.is_set():
            memory_mb, cpu_percent = self._get_resource_usage()
            with self._lock:
                self.resource_history.append((datetime.utcnow(), memory_mb, cpu_percent))
            time.sleep(self.resource_sampling_interval)

    def _generate_sample_query(self, complexity: str = "complex") -> str:
        """Generate a sample query.

        Args:
            complexity: Query complexity level

        Returns:
            Sample query string
        """
        if complexity not in self.sample_queries:
            complexity = "simple"

        return random.choice(self.sample_queries[complexity])

    async def _execute_stress_query(self) -> tuple[bool, float]:
        """Execute a single query during stress test.

        Returns:
            Tuple of (success: bool, latency_ms: float)
        """
        with self._lock:
            self.active_queries += 1
            self.total_queries += 1

        start_time = time.time()
        try:
            query = self._generate_sample_query("complex")
            result = await asyncio.wait_for(
                self.execution_func(query, "complex"),
                timeout=5.0
            )
            latency_ms = (time.time() - start_time) * 1000
            return True, latency_ms
        except asyncio.TimeoutError:
            with self._lock:
                self.total_errors += 1
            return False, (time.time() - start_time) * 1000
        except Exception as e:
            with self._lock:
                self.total_errors += 1
            return False, (time.time() - start_time) * 1000
        finally:
            with self._lock:
                self.active_queries -= 1

    def _check_for_breaking_point(
        self,
        qps: int,
        success_rate: float,
        error_threshold: float = 0.1,
    ) -> Optional[BreakingPoint]:
        """Check if a breaking point has been reached.

        Args:
            qps: Current queries per second
            success_rate: Current success rate
            error_threshold: Error rate threshold to trigger breaking point

        Returns:
            BreakingPoint if system is breaking, None otherwise
        """
        error_rate = 1.0 - success_rate
        memory_mb, cpu_percent = self._get_resource_usage()

        # Check for various breaking conditions
        if error_rate > error_threshold:
            return BreakingPoint(
                qps_at_break=qps,
                time_to_break_seconds=len(self.resource_history) * self.resource_sampling_interval,
                memory_mb_at_break=memory_mb,
                cpu_percent_at_break=cpu_percent,
                error_message=f"Error rate exceeded: {error_rate:.1%}"
            )

        if memory_mb > 2048:  # 2GB limit
            return BreakingPoint(
                qps_at_break=qps,
                time_to_break_seconds=len(self.resource_history) * self.resource_sampling_interval,
                memory_mb_at_break=memory_mb,
                cpu_percent_at_break=cpu_percent,
                error_message=f"Memory limit exceeded: {memory_mb:.2f}MB"
            )

        if cpu_percent > 95:
            return BreakingPoint(
                qps_at_break=qps,
                time_to_break_seconds=len(self.resource_history) * self.resource_sampling_interval,
                memory_mb_at_break=memory_mb,
                cpu_percent_at_break=cpu_percent,
                error_message=f"CPU limit exceeded: {cpu_percent:.2f}%"
            )

        return None

    async def run_steady_increase_stress(
        self,
        start_qps: int = 50,
        increment_qps: int = 25,
        step_duration_seconds: int = 30,
        max_qps: int = 500,
    ) -> StressTestResult:
        """Run steady increase stress test.

        Gradually increases QPS until system breaks.

        Args:
            start_qps: Starting queries per second
            increment_qps: QPS increment per step
            step_duration_seconds: Duration of each step
            max_qps: Maximum QPS to reach

        Returns:
            StressTestResult with findings

        Example:
            >>> async def mock_execute(query, complexity):
            ...     await asyncio.sleep(0.01)
            ...     return {"status": "ok"}
            >>> tester = StressTester(mock_execute, {"complex": ["q1"]})
            >>> result = await tester.run_steady_increase_stress()
            >>> print(f"Peak QPS: {result.peak_qps}")
        """
        self._stop_flag.clear()
        self.total_queries = 0
        self.total_errors = 0
        self.resource_history.clear()

        start_time = datetime.utcnow()
        breaking_points = []

        # Start resource monitor
        monitor_thread = threading.Thread(target=self._monitor_resources_background, daemon=True)
        monitor_thread.start()

        try:
            current_qps = start_qps
            while current_qps <= max_qps and not self._stop_flag.is_set():
                step_start = datetime.utcnow()
                step_queries = 0
                step_errors = 0

                # Execute queries for the step
                while (datetime.utcnow() - step_start).total_seconds() < step_duration_seconds:
                    batch_size = max(1, current_qps // 10)
                    tasks = [
                        self._execute_stress_query()
                        for _ in range(batch_size)
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    step_queries += len(results)
                    step_errors += sum(1 for r in results if isinstance(r, tuple) and not r[0])

                    # Throttle to maintain QPS
                    await asyncio.sleep(0.1)

                # Check for breaking point
                success_rate = 1.0 - (step_errors / step_queries if step_queries > 0 else 0)
                breaking_point = self._check_for_breaking_point(current_qps, success_rate)

                if breaking_point:
                    breaking_points.append(breaking_point)
                    break

                current_qps += increment_qps

        finally:
            self._stop_flag.set()
            monitor_thread.join(timeout=5.0)

        end_time = datetime.utcnow()

        # Calculate metrics
        peak_memory = max((m for _, m, _ in self.resource_history), default=0.0)
        peak_cpu = max((c for _, _, c in self.resource_history), default=0.0)

        return StressTestResult(
            stress_type=StressType.STEADY_INCREASE.value,
            start_time=start_time,
            end_time=end_time,
            peak_qps=current_qps - increment_qps,
            breaking_points=breaking_points,
            total_queries_executed=self.total_queries,
            total_errors=self.total_errors,
            success_rate=1.0 - (self.total_errors / self.total_queries if self.total_queries > 0 else 0),
            peak_memory_mb=peak_memory,
            peak_cpu_percent=peak_cpu,
        )

    async def run_memory_pressure_test(
        self,
        target_qps: int = 100,
        duration_seconds: int = 60,
        memory_target_mb: int = 1024,
    ) -> StressTestResult:
        """Run memory pressure stress test.

        Executes complex queries to stress memory subsystem.

        Args:
            target_qps: Target queries per second
            duration_seconds: Test duration
            memory_target_mb: Memory limit to trigger breaking point

        Returns:
            StressTestResult with memory pressure findings
        """
        self._stop_flag.clear()
        self.total_queries = 0
        self.total_errors = 0
        self.resource_history.clear()

        start_time = datetime.utcnow()
        breaking_points = []

        # Start resource monitor
        monitor_thread = threading.Thread(target=self._monitor_resources_background, daemon=True)
        monitor_thread.start()

        try:
            elapsed = 0
            while elapsed < duration_seconds and not self._stop_flag.is_set():
                batch_size = max(1, target_qps // 10)
                tasks = [
                    self._execute_stress_query()
                    for _ in range(batch_size)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
                success_rate = success_count / len(results) if results else 1.0

                # Check for breaking point
                memory_mb, cpu_percent = self._get_resource_usage()
                if memory_mb > memory_target_mb:
                    breaking_points.append(BreakingPoint(
                        qps_at_break=target_qps,
                        time_to_break_seconds=elapsed,
                        memory_mb_at_break=memory_mb,
                        cpu_percent_at_break=cpu_percent,
                        error_message=f"Memory limit exceeded: {memory_mb:.2f}MB"
                    ))
                    break

                elapsed += 0.1
                await asyncio.sleep(0.1)

        finally:
            self._stop_flag.set()
            monitor_thread.join(timeout=5.0)

        end_time = datetime.utcnow()

        # Calculate metrics
        peak_memory = max((m for _, m, _ in self.resource_history), default=0.0)
        peak_cpu = max((c for _, _, c in self.resource_history), default=0.0)

        return StressTestResult(
            stress_type=StressType.MEMORY_PRESSURE.value,
            start_time=start_time,
            end_time=end_time,
            peak_qps=target_qps,
            breaking_points=breaking_points,
            total_queries_executed=self.total_queries,
            total_errors=self.total_errors,
            success_rate=1.0 - (self.total_errors / self.total_queries if self.total_queries > 0 else 0),
            peak_memory_mb=peak_memory,
            peak_cpu_percent=peak_cpu,
        )

    async def run_spike_storm_test(
        self,
        baseline_qps: int = 10,
        spike_qps: int = 300,
        spike_count: int = 5,
        spike_duration_seconds: int = 10,
        recovery_timeout_seconds: int = 30,
    ) -> StressTestResult:
        """Run spike storm stress test.

        Creates multiple sudden traffic spikes to test spike handling and recovery.

        Args:
            baseline_qps: Baseline queries per second between spikes
            spike_qps: Queries per second during spikes
            spike_count: Number of spikes to execute
            spike_duration_seconds: Duration of each spike
            recovery_timeout_seconds: Maximum time allowed for recovery

        Returns:
            StressTestResult with spike storm findings
        """
        self._stop_flag.clear()
        self.total_queries = 0
        self.total_errors = 0
        self.resource_history.clear()

        start_time = datetime.utcnow()
        breaking_points = []

        # Start resource monitor
        monitor_thread = threading.Thread(target=self._monitor_resources_background, daemon=True)
        monitor_thread.start()

        try:
            for spike_num in range(spike_count):
                if self._stop_flag.is_set():
                    break

                # Execute spike
                spike_start = datetime.utcnow()
                while (datetime.utcnow() - spike_start).total_seconds() < spike_duration_seconds:
                    batch_size = max(1, spike_qps // 10)
                    tasks = [
                        self._execute_stress_query()
                        for _ in range(batch_size)
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.sleep(0.1)

                # Wait for recovery
                recovery_start = datetime.utcnow()
                while (datetime.utcnow() - recovery_start).total_seconds() < recovery_timeout_seconds:
                    batch_size = max(1, baseline_qps // 10)
                    tasks = [
                        self._execute_stress_query()
                        for _ in range(batch_size)
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
                    success_rate = success_count / len(results) if results else 1.0

                    if success_rate > 0.9:  # System recovered
                        break

                    await asyncio.sleep(0.1)

        finally:
            self._stop_flag.set()
            monitor_thread.join(timeout=5.0)

        end_time = datetime.utcnow()

        # Calculate metrics
        peak_memory = max((m for _, m, _ in self.resource_history), default=0.0)
        peak_cpu = max((c for _, _, c in self.resource_history), default=0.0)

        return StressTestResult(
            stress_type=StressType.SPIKE_STORM.value,
            start_time=start_time,
            end_time=end_time,
            peak_qps=spike_qps,
            breaking_points=breaking_points,
            total_queries_executed=self.total_queries,
            total_errors=self.total_errors,
            success_rate=1.0 - (self.total_errors / self.total_queries if self.total_queries > 0 else 0),
            peak_memory_mb=peak_memory,
            peak_cpu_percent=peak_cpu,
        )
