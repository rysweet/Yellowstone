"""
Load testing framework for concurrent query execution and performance monitoring.

Provides comprehensive load testing capabilities including concurrent query execution,
configurable load profiles, query distribution, real-time resource monitoring, and
performance degradation tracking.
"""

import asyncio
import threading
import time
import psutil
import statistics
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import random
from collections import defaultdict


class QueryType(Enum):
    """Query complexity types."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class LatencyStatistics:
    """Statistics for latency measurements."""
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_dev_ms: float

    def __str__(self) -> str:
        return (
            f"Min: {self.min_ms:.2f}ms, Max: {self.max_ms:.2f}ms, "
            f"Mean: {self.mean_ms:.2f}ms, Median: {self.median_ms:.2f}ms, "
            f"P95: {self.p95_ms:.2f}ms, P99: {self.p99_ms:.2f}ms"
        )


@dataclass
class ResourceSnapshot:
    """Point-in-time resource usage snapshot."""
    timestamp: datetime
    memory_mb: float
    cpu_percent: float
    active_queries: int
    thread_count: int


@dataclass
class LoadTestMetrics:
    """Aggregated metrics from a load test."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    total_duration_seconds: float
    actual_qps: float
    latency_stats: LatencyStatistics
    resource_snapshots: List[ResourceSnapshot] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    query_distribution: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        return (
            f"LoadTestMetrics(\n"
            f"  Total: {self.total_queries}, Successful: {self.successful_queries}, "
            f"Failed: {self.failed_queries}\n"
            f"  Success Rate: {self.success_rate:.1%}\n"
            f"  Duration: {self.total_duration_seconds:.2f}s, "
            f"Actual QPS: {self.actual_qps:.2f}\n"
            f"  Latency: {self.latency_stats}\n"
            f"  Resources - Peak Memory: {self.peak_memory_mb:.2f}MB, "
            f"Peak CPU: {self.peak_cpu_percent:.2f}%\n"
            f")"
        )


@dataclass
class LoadTestResult:
    """Complete result of a load test."""
    profile_name: str
    start_time: datetime
    end_time: datetime
    metrics: LoadTestMetrics
    configuration: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    @property
    def duration_seconds(self) -> float:
        """Test duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    def __str__(self) -> str:
        return (
            f"LoadTestResult(\n"
            f"  Profile: {self.profile_name}\n"
            f"  Duration: {self.duration_seconds:.2f}s\n"
            f"  {self.metrics}\n"
            f")"
        )


class QueryExecutor:
    """Executes individual queries with timing and error handling."""

    def __init__(self, execution_func: Callable[[str, str], Awaitable[Dict[str, Any]]]):
        """Initialize query executor.

        Args:
            execution_func: Async function that executes a query
                          Signature: async def (query: str, complexity: str) -> Dict[str, Any]
        """
        self.execution_func = execution_func
        self.latencies: List[float] = []
        self.errors: List[str] = []
        self._lock = threading.Lock()

    async def execute(self, query: str, complexity: str) -> tuple[bool, float, Optional[str]]:
        """Execute a single query and record timing.

        Args:
            query: Query to execute
            complexity: Query complexity level (simple, medium, complex)

        Returns:
            Tuple of (success: bool, latency_ms: float, error_message: Optional[str])
        """
        start_time = time.time()
        try:
            result = await self.execution_func(query, complexity)
            latency_ms = (time.time() - start_time) * 1000

            with self._lock:
                self.latencies.append(latency_ms)

            return True, latency_ms, None
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            with self._lock:
                self.errors.append(error_msg)
                self.latencies.append(latency_ms)

            return False, latency_ms, error_msg

    def get_statistics(self) -> LatencyStatistics:
        """Get latency statistics.

        Returns:
            LatencyStatistics with aggregated measurements
        """
        with self._lock:
            if not self.latencies:
                return LatencyStatistics(
                    min_ms=0, max_ms=0, mean_ms=0, median_ms=0,
                    p95_ms=0, p99_ms=0, std_dev_ms=0
                )

            sorted_latencies = sorted(self.latencies)
            return LatencyStatistics(
                min_ms=min(sorted_latencies),
                max_ms=max(sorted_latencies),
                mean_ms=statistics.mean(sorted_latencies),
                median_ms=statistics.median(sorted_latencies),
                p95_ms=sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 1 else sorted_latencies[0],
                p99_ms=sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 1 else sorted_latencies[0],
                std_dev_ms=statistics.stdev(sorted_latencies) if len(sorted_latencies) > 1 else 0,
            )


class LoadTester:
    """Main load testing orchestrator.

    Coordinates concurrent query execution, load profile application,
    resource monitoring, and metrics collection.
    """

    def __init__(
        self,
        query_executor: QueryExecutor,
        sample_queries: Dict[str, List[str]],
        resource_sampling_interval: float = 1.0,
    ):
        """Initialize load tester.

        Args:
            query_executor: QueryExecutor instance for executing queries
            sample_queries: Dict mapping complexity level to list of sample queries
            resource_sampling_interval: Seconds between resource samples
        """
        self.query_executor = query_executor
        self.sample_queries = sample_queries
        self.resource_sampling_interval = resource_sampling_interval
        self.resource_snapshots: List[ResourceSnapshot] = []
        self.active_queries = 0
        self.query_results: List[tuple[bool, float, Optional[str], str]] = []
        self._lock = threading.Lock()
        self._stop_flag = threading.Event()
        self._query_counts: Dict[str, int] = defaultdict(int)

    def _get_resource_snapshot(self) -> ResourceSnapshot:
        """Get current resource usage snapshot.

        Returns:
            ResourceSnapshot with current resource metrics
        """
        process = psutil.Process()
        return ResourceSnapshot(
            timestamp=datetime.utcnow(),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            cpu_percent=process.cpu_percent(interval=0.1),
            active_queries=self.active_queries,
            thread_count=threading.active_count(),
        )

    def _monitor_resources(self) -> None:
        """Background thread for monitoring resources."""
        while not self._stop_flag.is_set():
            snapshot = self._get_resource_snapshot()
            with self._lock:
                self.resource_snapshots.append(snapshot)
            time.sleep(self.resource_sampling_interval)

    def _generate_sample_query(self, complexity: str) -> str:
        """Generate a sample query of the given complexity.

        Args:
            complexity: Query complexity level

        Returns:
            Sample query string
        """
        if complexity not in self.sample_queries:
            complexity = "simple"

        return random.choice(self.sample_queries[complexity])

    async def _execute_query_task(self, complexity: str) -> None:
        """Execute a single query task.

        Args:
            complexity: Query complexity level
        """
        with self._lock:
            self.active_queries += 1
            self._query_counts[complexity] += 1

        try:
            query = self._generate_sample_query(complexity)
            success, latency_ms, error = await self.query_executor.execute(query, complexity)

            with self._lock:
                self.query_results.append((success, latency_ms, error, complexity))
        finally:
            with self._lock:
                self.active_queries -= 1

    async def _execute_batch(self, qps: int, batch_duration_seconds: float) -> int:
        """Execute a batch of queries at target QPS.

        Args:
            qps: Target queries per second
            batch_duration_seconds: Duration to maintain this QPS

        Returns:
            Number of queries executed
        """
        queries_executed = 0
        batch_start = time.time()
        distribution = self._calculate_query_distribution()

        # Handle zero QPS (during ramp-up phase)
        if qps <= 0:
            await asyncio.sleep(batch_duration_seconds)
            return 0

        while time.time() - batch_start < batch_duration_seconds:
            batch_size = max(1, qps // 10)  # Execute in smaller batches
            tasks = []

            for _ in range(batch_size):
                complexity = self._select_complexity(distribution)
                tasks.append(self._execute_query_task(complexity))

            await asyncio.gather(*tasks, return_exceptions=True)
            queries_executed += batch_size

            # Throttle to maintain QPS
            elapsed = time.time() - batch_start
            expected_execution_time = queries_executed / qps
            if elapsed < expected_execution_time:
                await asyncio.sleep(expected_execution_time - elapsed)

        return queries_executed

    def _calculate_query_distribution(self) -> Dict[str, int]:
        """Calculate query complexity distribution.

        Returns:
            Dict mapping complexity to percentage
        """
        # Default distribution if not overridden
        return {
            "simple": 60,
            "medium": 30,
            "complex": 10,
        }

    def _select_complexity(self, distribution: Dict[str, int]) -> str:
        """Select a query complexity based on distribution.

        Args:
            distribution: Dict mapping complexity to percentage

        Returns:
            Selected complexity level
        """
        rand = random.randint(1, 100)
        cumulative = 0

        for complexity, percent in distribution.items():
            cumulative += percent
            if rand <= cumulative:
                return complexity

        return "simple"

    async def run_test(self, profile: 'LoadProfile') -> LoadTestResult:
        """Run a load test using the specified profile.

        Args:
            profile: LoadProfile instance defining test parameters

        Returns:
            LoadTestResult with comprehensive metrics

        Example:
            >>> from load_testing import LoadTester, QueryExecutor, get_load_profile
            >>> async def mock_execute(query, complexity):
            ...     await asyncio.sleep(0.01)
            ...     return {"status": "ok"}
            >>> executor = QueryExecutor(mock_execute)
            >>> tester = LoadTester(executor, {"simple": ["q1"], "medium": ["q2"], "complex": ["q3"]})
            >>> profile = get_load_profile("light")
            >>> result = await tester.run_test(profile)
            >>> print(result.metrics.success_rate)
        """
        self._stop_flag.clear()
        self.resource_snapshots.clear()
        self.query_results.clear()
        self._query_counts.clear()

        # Validate profile
        validation_errors = profile.validate()
        if validation_errors:
            raise ValueError(f"Invalid profile: {', '.join(validation_errors)}")

        start_time = datetime.utcnow()

        # Start resource monitor
        monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        monitor_thread.start()

        try:
            elapsed = 0.0
            while elapsed < profile.duration_seconds:
                qps = profile.get_qps_at_time(elapsed)
                # Execute for 1 second intervals
                interval = min(1.0, profile.duration_seconds - elapsed)
                await self._execute_batch(qps, interval)
                elapsed += interval

        finally:
            self._stop_flag.set()
            monitor_thread.join(timeout=5.0)

        end_time = datetime.utcnow()

        # Calculate metrics
        metrics = self._calculate_metrics(start_time, end_time, profile)

        return LoadTestResult(
            profile_name=profile.name,
            start_time=start_time,
            end_time=end_time,
            metrics=metrics,
            configuration={
                "target_qps": profile.target_qps,
                "max_concurrent": profile.max_concurrent_queries,
                "duration_seconds": profile.duration_seconds,
            },
        )

    def _calculate_metrics(self, start_time: datetime, end_time: datetime, profile: 'LoadProfile') -> LoadTestMetrics:
        """Calculate aggregated metrics.

        Args:
            start_time: Test start time
            end_time: Test end time
            profile: LoadProfile used

        Returns:
            LoadTestMetrics with aggregated measurements
        """
        total_duration = (end_time - start_time).total_seconds()
        total_queries = len(self.query_results)
        successful_queries = sum(1 for success, _, _, _ in self.query_results if success)
        failed_queries = total_queries - successful_queries

        latency_stats = self.query_executor.get_statistics()

        # Aggregate errors
        errors_by_type: Dict[str, int] = defaultdict(int)
        for _, _, error, _ in self.query_results:
            if error:
                error_type = error.split(":")[0] if ":" in error else "unknown"
                errors_by_type[error_type] += 1

        # Get peak resource usage
        peak_memory = max((s.memory_mb for s in self.resource_snapshots), default=0.0)
        peak_cpu = max((s.cpu_percent for s in self.resource_snapshots), default=0.0)

        return LoadTestMetrics(
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            success_rate=successful_queries / total_queries if total_queries > 0 else 0.0,
            total_duration_seconds=total_duration,
            actual_qps=total_queries / total_duration if total_duration > 0 else 0.0,
            latency_stats=latency_stats,
            resource_snapshots=self.resource_snapshots,
            peak_memory_mb=peak_memory,
            peak_cpu_percent=peak_cpu,
            errors_by_type=dict(errors_by_type),
            query_distribution=dict(self._query_counts),
        )
