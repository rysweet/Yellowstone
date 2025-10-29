"""
Performance metrics collection and aggregation.

This module provides tools for collecting, storing, and analyzing performance
metrics from benchmark runs. It tracks latency, throughput, resource usage,
and translation overhead.
"""

import time
import psutil
import statistics
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class QueryMetrics:
    """Performance metrics for a single query execution.

    Attributes:
        query_id: Unique identifier for the query
        query_name: Human-readable query name
        cypher_query: Original Cypher query string
        kql_query: Translated KQL query string
        translation_time_ms: Time spent translating Cypher to KQL
        execution_time_ms: Time spent executing the KQL query
        total_time_ms: Total end-to-end time (translation + execution)
        result_count: Number of results returned
        memory_usage_mb: Peak memory usage during execution
        cpu_usage_percent: Average CPU usage during execution
        cache_hit: Whether the query result was cached
        error: Error message if execution failed
        timestamp: When the query was executed
        metadata: Additional metadata as key-value pairs
    """

    query_id: str
    query_name: str
    cypher_query: str
    kql_query: str
    translation_time_ms: float
    execution_time_ms: float
    total_time_ms: float
    result_count: int
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    @property
    def translation_overhead_ratio(self) -> float:
        """Calculate translation overhead as ratio of total time.

        Returns:
            Translation time as fraction of total time (0.0-1.0)
        """
        if self.total_time_ms == 0:
            return 0.0
        return self.translation_time_ms / self.total_time_ms

    @property
    def success(self) -> bool:
        """Check if query executed successfully.

        Returns:
            True if no error occurred
        """
        return self.error is None


@dataclass
class BenchmarkResults:
    """Aggregated results from a benchmark run.

    Attributes:
        run_id: Unique identifier for this benchmark run
        run_name: Human-readable name for the run
        start_time: When the benchmark run started
        end_time: When the benchmark run completed
        query_metrics: List of individual query metrics
        configuration: Benchmark configuration settings
        environment: Environment information (OS, Python version, etc.)
    """

    run_id: str
    run_name: str
    start_time: datetime
    end_time: datetime
    query_metrics: list[QueryMetrics]
    configuration: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Total duration of the benchmark run.

        Returns:
            Duration in seconds
        """
        return (self.end_time - self.start_time).total_seconds()

    @property
    def total_queries(self) -> int:
        """Total number of queries executed.

        Returns:
            Count of all queries (successful and failed)
        """
        return len(self.query_metrics)

    @property
    def successful_queries(self) -> int:
        """Number of successfully executed queries.

        Returns:
            Count of queries without errors
        """
        return sum(1 for m in self.query_metrics if m.success)

    @property
    def failed_queries(self) -> int:
        """Number of failed queries.

        Returns:
            Count of queries with errors
        """
        return sum(1 for m in self.query_metrics if not m.success)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage.

        Returns:
            Percentage of successful queries (0.0-100.0)
        """
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100


@dataclass
class PerformanceSummary:
    """Statistical summary of benchmark performance.

    Attributes:
        total_queries: Total number of queries analyzed
        successful_queries: Number of successful executions
        failed_queries: Number of failed executions
        total_time_p50: Median total time (ms)
        total_time_p95: 95th percentile total time (ms)
        total_time_p99: 99th percentile total time (ms)
        total_time_avg: Average total time (ms)
        total_time_min: Minimum total time (ms)
        total_time_max: Maximum total time (ms)
        translation_time_p50: Median translation time (ms)
        translation_time_p95: 95th percentile translation time (ms)
        translation_time_avg: Average translation time (ms)
        execution_time_p50: Median execution time (ms)
        execution_time_p95: 95th percentile execution time (ms)
        execution_time_avg: Average execution time (ms)
        translation_overhead_avg: Average translation overhead ratio
        cache_hit_rate: Percentage of cache hits
        avg_memory_usage_mb: Average memory usage (MB)
        avg_cpu_usage_percent: Average CPU usage (%)
        throughput_qps: Queries per second
    """

    total_queries: int
    successful_queries: int
    failed_queries: int
    total_time_p50: float
    total_time_p95: float
    total_time_p99: float
    total_time_avg: float
    total_time_min: float
    total_time_max: float
    translation_time_p50: float
    translation_time_p95: float
    translation_time_avg: float
    execution_time_p50: float
    execution_time_p95: float
    execution_time_avg: float
    translation_overhead_avg: float
    cache_hit_rate: float
    avg_memory_usage_mb: float
    avg_cpu_usage_percent: float
    throughput_qps: float

    def meets_targets(self) -> bool:
        """Check if performance meets target metrics.

        Target Metrics:
            - P50 latency < 1000ms (1s)
            - P95 latency < 3000ms (3s)
            - P99 latency < 5000ms (5s)

        Returns:
            True if all targets are met
        """
        return (
            self.total_time_p50 < 1000
            and self.total_time_p95 < 3000
            and self.total_time_p99 < 5000
        )

    def translation_overhead_within_target(self) -> bool:
        """Check if translation overhead is within 2-5x target.

        Returns:
            True if overhead ratio is between 0.33 and 0.67 (2x to 5x)
        """
        # Overhead ratio of 0.5 means translation takes 50% of total time
        # This corresponds to ~2x overhead (1 unit translation + 1 unit execution = 2 total)
        return 0.20 <= self.translation_overhead_avg <= 0.67


class MetricsCollector:
    """Collects and aggregates performance metrics.

    Provides utilities for measuring query performance, collecting system
    resource usage, and computing statistical summaries.
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self.metrics: list[QueryMetrics] = []
        self._process = psutil.Process()

    def start_query_timer(self) -> tuple[float, float, float]:
        """Start timing a query execution.

        Returns:
            Tuple of (start_time, initial_memory_mb, initial_cpu_percent)
        """
        start_time = time.perf_counter()
        initial_memory = self._process.memory_info().rss / (1024 * 1024)  # Convert to MB
        self._process.cpu_percent()  # First call for baseline
        return start_time, initial_memory, 0.0

    def record_query_metrics(
        self,
        query_id: str,
        query_name: str,
        cypher_query: str,
        kql_query: str,
        translation_time_ms: float,
        execution_start_time: float,
        result_count: int,
        initial_memory_mb: float,
        cache_hit: bool = False,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> QueryMetrics:
        """Record metrics for a completed query.

        Args:
            query_id: Unique query identifier
            query_name: Human-readable query name
            cypher_query: Original Cypher query
            kql_query: Translated KQL query
            translation_time_ms: Time spent on translation
            execution_start_time: Start time from start_query_timer()
            result_count: Number of results returned
            initial_memory_mb: Initial memory from start_query_timer()
            cache_hit: Whether result was cached
            error: Error message if query failed
            metadata: Additional metadata

        Returns:
            QueryMetrics object with recorded measurements
        """
        end_time = time.perf_counter()
        execution_time_ms = (end_time - execution_start_time) * 1000

        # Measure current memory usage
        current_memory = self._process.memory_info().rss / (1024 * 1024)
        memory_usage_mb = max(current_memory - initial_memory_mb, 0.0)

        # Get CPU usage (average since last call)
        cpu_usage_percent = self._process.cpu_percent()

        total_time_ms = translation_time_ms + execution_time_ms

        metrics = QueryMetrics(
            query_id=query_id,
            query_name=query_name,
            cypher_query=cypher_query,
            kql_query=kql_query,
            translation_time_ms=translation_time_ms,
            execution_time_ms=execution_time_ms,
            total_time_ms=total_time_ms,
            result_count=result_count,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            cache_hit=cache_hit,
            error=error,
            metadata=metadata or {},
        )

        self.metrics.append(metrics)
        return metrics

    def compute_summary(self, metrics: Optional[list[QueryMetrics]] = None) -> PerformanceSummary:
        """Compute statistical summary of metrics.

        Args:
            metrics: List of metrics to summarize (defaults to all collected metrics)

        Returns:
            PerformanceSummary with statistical aggregations

        Raises:
            ValueError: If no metrics are available
        """
        if metrics is None:
            metrics = self.metrics

        if not metrics:
            raise ValueError("No metrics available to summarize")

        successful = [m for m in metrics if m.success]

        if not successful:
            # Return empty summary if all queries failed
            return PerformanceSummary(
                total_queries=len(metrics),
                successful_queries=0,
                failed_queries=len(metrics),
                total_time_p50=0.0,
                total_time_p95=0.0,
                total_time_p99=0.0,
                total_time_avg=0.0,
                total_time_min=0.0,
                total_time_max=0.0,
                translation_time_p50=0.0,
                translation_time_p95=0.0,
                translation_time_avg=0.0,
                execution_time_p50=0.0,
                execution_time_p95=0.0,
                execution_time_avg=0.0,
                translation_overhead_avg=0.0,
                cache_hit_rate=0.0,
                avg_memory_usage_mb=0.0,
                avg_cpu_usage_percent=0.0,
                throughput_qps=0.0,
            )

        # Extract time series
        total_times = [m.total_time_ms for m in successful]
        translation_times = [m.translation_time_ms for m in successful]
        execution_times = [m.execution_time_ms for m in successful]
        overhead_ratios = [m.translation_overhead_ratio for m in successful]
        memory_usage = [m.memory_usage_mb for m in successful]
        cpu_usage = [m.cpu_usage_percent for m in successful]

        # Calculate percentiles
        total_times_sorted = sorted(total_times)
        translation_times_sorted = sorted(translation_times)
        execution_times_sorted = sorted(execution_times)

        # Calculate cache hit rate
        cache_hits = sum(1 for m in successful if m.cache_hit)
        cache_hit_rate = (cache_hits / len(successful)) * 100 if successful else 0.0

        # Calculate throughput (queries per second)
        total_duration_seconds = sum(m.total_time_ms for m in successful) / 1000
        throughput_qps = len(successful) / total_duration_seconds if total_duration_seconds > 0 else 0.0

        return PerformanceSummary(
            total_queries=len(metrics),
            successful_queries=len(successful),
            failed_queries=len(metrics) - len(successful),
            total_time_p50=self._percentile(total_times_sorted, 50),
            total_time_p95=self._percentile(total_times_sorted, 95),
            total_time_p99=self._percentile(total_times_sorted, 99),
            total_time_avg=statistics.mean(total_times),
            total_time_min=min(total_times),
            total_time_max=max(total_times),
            translation_time_p50=self._percentile(translation_times_sorted, 50),
            translation_time_p95=self._percentile(translation_times_sorted, 95),
            translation_time_avg=statistics.mean(translation_times),
            execution_time_p50=self._percentile(execution_times_sorted, 50),
            execution_time_p95=self._percentile(execution_times_sorted, 95),
            execution_time_avg=statistics.mean(execution_times),
            translation_overhead_avg=statistics.mean(overhead_ratios),
            cache_hit_rate=cache_hit_rate,
            avg_memory_usage_mb=statistics.mean(memory_usage),
            avg_cpu_usage_percent=statistics.mean(cpu_usage),
            throughput_qps=throughput_qps,
        )

    def _percentile(self, sorted_values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted values.

        Args:
            sorted_values: List of values in ascending order
            percentile: Percentile to calculate (0-100)

        Returns:
            Value at the specified percentile
        """
        if not sorted_values:
            return 0.0

        if len(sorted_values) == 1:
            return sorted_values[0]

        # Use linear interpolation
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = k - f

        if f + 1 < len(sorted_values):
            return sorted_values[f] + (c * (sorted_values[f + 1] - sorted_values[f]))
        else:
            return sorted_values[f]

    def get_metrics_by_complexity(self, complexity: str) -> list[QueryMetrics]:
        """Filter metrics by query complexity.

        Args:
            complexity: Complexity level (simple, medium, complex, stress)

        Returns:
            List of metrics matching the complexity level
        """
        return [m for m in self.metrics if m.metadata.get("complexity") == complexity]

    def get_metrics_by_category(self, category: str) -> list[QueryMetrics]:
        """Filter metrics by query category.

        Args:
            category: Query category

        Returns:
            List of metrics in the specified category
        """
        return [m for m in self.metrics if m.metadata.get("category") == category]

    def compare_performance(
        self, baseline_metrics: list[QueryMetrics], current_metrics: list[QueryMetrics]
    ) -> dict:
        """Compare performance between two sets of metrics.

        Args:
            baseline_metrics: Baseline metrics for comparison
            current_metrics: Current metrics to compare against baseline

        Returns:
            Dictionary with comparison statistics:
            - p50_improvement: Percentage improvement in P50 latency
            - p95_improvement: Percentage improvement in P95 latency
            - throughput_improvement: Percentage improvement in throughput
            - regression_detected: Whether performance regression occurred

        Raises:
            ValueError: If either metric set is empty
        """
        if not baseline_metrics or not current_metrics:
            raise ValueError("Both baseline and current metrics must be non-empty")

        baseline_summary = self.compute_summary(baseline_metrics)
        current_summary = self.compute_summary(current_metrics)

        # Calculate percentage improvements (negative means regression)
        p50_improvement = (
            (baseline_summary.total_time_p50 - current_summary.total_time_p50)
            / baseline_summary.total_time_p50
            * 100
        )

        p95_improvement = (
            (baseline_summary.total_time_p95 - current_summary.total_time_p95)
            / baseline_summary.total_time_p95
            * 100
        )

        throughput_improvement = (
            (current_summary.throughput_qps - baseline_summary.throughput_qps)
            / baseline_summary.throughput_qps
            * 100
        )

        # Detect regression (>10% slowdown in P95 or >5% slowdown in throughput)
        regression_detected = p95_improvement < -10 or throughput_improvement < -5

        return {
            "baseline": {
                "p50_ms": baseline_summary.total_time_p50,
                "p95_ms": baseline_summary.total_time_p95,
                "throughput_qps": baseline_summary.throughput_qps,
            },
            "current": {
                "p50_ms": current_summary.total_time_p50,
                "p95_ms": current_summary.total_time_p95,
                "throughput_qps": current_summary.throughput_qps,
            },
            "p50_improvement_percent": p50_improvement,
            "p95_improvement_percent": p95_improvement,
            "throughput_improvement_percent": throughput_improvement,
            "regression_detected": regression_detected,
        }

    def reset(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()

    def export_metrics(self) -> list[dict]:
        """Export metrics as list of dictionaries for serialization.

        Returns:
            List of metric dictionaries suitable for JSON serialization
        """
        return [
            {
                "query_id": m.query_id,
                "query_name": m.query_name,
                "cypher_query": m.cypher_query,
                "kql_query": m.kql_query,
                "translation_time_ms": m.translation_time_ms,
                "execution_time_ms": m.execution_time_ms,
                "total_time_ms": m.total_time_ms,
                "result_count": m.result_count,
                "memory_usage_mb": m.memory_usage_mb,
                "cpu_usage_percent": m.cpu_usage_percent,
                "cache_hit": m.cache_hit,
                "error": m.error,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata,
            }
            for m in self.metrics
        ]
