"""
Operational metrics collection and aggregation.

This module provides comprehensive metrics collection for query latency, translation
success rates, cache performance, error rates, and resource usage tracking.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import statistics


class MetricType(Enum):
    """Types of metrics collected."""
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class LatencyMetric:
    """Represents a latency measurement."""
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    query_type: str = "unknown"
    strategy: str = "unknown"


@dataclass
class CacheMetric:
    """Represents a cache operation."""
    hit: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    key_size: int = 0
    value_size: int = 0


@dataclass
class ErrorMetric:
    """Represents an error event."""
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: str = "error"  # info, warning, error, critical


@dataclass
class ResourceMetric:
    """Represents resource usage."""
    memory_bytes: int
    cpu_percent: float
    active_queries: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LatencyAggregator:
    """Aggregates latency metrics with percentile calculations."""

    def __init__(self, retention_minutes: int = 60):
        """Initialize latency aggregator.

        Args:
            retention_minutes: How long to keep latency samples in memory
        """
        self.retention_minutes = retention_minutes
        self.latencies: List[LatencyMetric] = []
        self._lock = threading.RLock()

    def record(self, duration_ms: float, query_type: str = "unknown", strategy: str = "unknown") -> None:
        """Record a latency measurement.

        Args:
            duration_ms: Query duration in milliseconds
            query_type: Type of query (e.g., "translation", "parsing")
            strategy: Translation strategy used
        """
        with self._lock:
            metric = LatencyMetric(
                duration_ms=duration_ms,
                query_type=query_type,
                strategy=strategy
            )
            self.latencies.append(metric)
            self._prune_old_entries()

    def get_percentile(self, percentile: float) -> Optional[float]:
        """Get latency percentile.

        Args:
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value in milliseconds, or None if no data
        """
        with self._lock:
            if not self.latencies:
                return None

            sorted_latencies = sorted(m.duration_ms for m in self.latencies)
            index = int(len(sorted_latencies) * percentile / 100)
            index = min(index, len(sorted_latencies) - 1)
            return sorted_latencies[index]

    def get_summary(self) -> Dict[str, float]:
        """Get comprehensive latency summary.

        Returns:
            Dictionary with P50, P95, P99, min, max, avg, and count
        """
        with self._lock:
            if not self.latencies:
                return {
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0,
                }

            durations = [m.duration_ms for m in self.latencies]
            return {
                "p50": statistics.median(durations),
                "p95": self.get_percentile(95) or 0.0,
                "p99": self.get_percentile(99) or 0.0,
                "min": min(durations),
                "max": max(durations),
                "avg": statistics.mean(durations),
                "count": len(durations),
            }

    def _prune_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        self.latencies = [m for m in self.latencies if m.timestamp > cutoff_time]


class CacheMetricsCollector:
    """Tracks cache hit rates and performance."""

    def __init__(self, retention_minutes: int = 60):
        """Initialize cache metrics collector.

        Args:
            retention_minutes: How long to keep cache metrics
        """
        self.retention_minutes = retention_minutes
        self.cache_operations: List[CacheMetric] = []
        self._lock = threading.RLock()

    def record_hit(self, key_size: int = 0, value_size: int = 0) -> None:
        """Record a cache hit.

        Args:
            key_size: Size of cache key in bytes
            value_size: Size of cached value in bytes
        """
        with self._lock:
            metric = CacheMetric(hit=True, key_size=key_size, value_size=value_size)
            self.cache_operations.append(metric)
            self._prune_old_entries()

    def record_miss(self, key_size: int = 0) -> None:
        """Record a cache miss.

        Args:
            key_size: Size of cache key in bytes
        """
        with self._lock:
            metric = CacheMetric(hit=False, key_size=key_size)
            self.cache_operations.append(metric)
            self._prune_old_entries()

    def get_hit_rate(self) -> float:
        """Get cache hit rate as percentage.

        Returns:
            Hit rate from 0.0 to 100.0
        """
        with self._lock:
            if not self.cache_operations:
                return 0.0

            hits = sum(1 for m in self.cache_operations if m.hit)
            return (hits / len(self.cache_operations)) * 100.0

    def get_summary(self) -> Dict[str, float]:
        """Get comprehensive cache metrics summary.

        Returns:
            Dictionary with hit_rate, miss_rate, total_ops, avg_key_size, avg_value_size
        """
        with self._lock:
            if not self.cache_operations:
                return {
                    "hit_rate": 0.0,
                    "miss_rate": 0.0,
                    "total_ops": 0,
                    "avg_key_size": 0,
                    "avg_value_size": 0,
                }

            hits = [m for m in self.cache_operations if m.hit]
            hit_rate = (len(hits) / len(self.cache_operations)) * 100.0

            avg_key_size = statistics.mean(m.key_size for m in self.cache_operations) if self.cache_operations else 0
            avg_value_size = statistics.mean(m.value_size for m in hits) if hits else 0

            return {
                "hit_rate": hit_rate,
                "miss_rate": 100.0 - hit_rate,
                "total_ops": len(self.cache_operations),
                "avg_key_size": avg_key_size,
                "avg_value_size": avg_value_size,
            }

    def _prune_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        self.cache_operations = [m for m in self.cache_operations if m.timestamp > cutoff_time]


class ErrorMetricsCollector:
    """Tracks error rates and error distribution."""

    def __init__(self, retention_minutes: int = 60):
        """Initialize error metrics collector.

        Args:
            retention_minutes: How long to keep error metrics
        """
        self.retention_minutes = retention_minutes
        self.errors: List[ErrorMetric] = []
        self.total_operations = 0
        self._lock = threading.RLock()

    def record_error(self, error_type: str, error_message: str, severity: str = "error") -> None:
        """Record an error event.

        Args:
            error_type: Classification of error (e.g., "parsing_error", "translation_error")
            error_message: Error message text
            severity: Severity level (info, warning, error, critical)
        """
        with self._lock:
            metric = ErrorMetric(
                error_type=error_type,
                error_message=error_message,
                severity=severity
            )
            self.errors.append(metric)
            self._prune_old_entries()

    def record_operation(self, success: bool) -> None:
        """Record operation result for error rate calculation.

        Args:
            success: Whether operation succeeded
        """
        with self._lock:
            self.total_operations += 1

    def get_error_rate(self) -> float:
        """Get error rate as percentage.

        Returns:
            Error rate from 0.0 to 100.0
        """
        with self._lock:
            if self.total_operations == 0:
                return 0.0
            return (len(self.errors) / self.total_operations) * 100.0

    def get_error_distribution(self) -> Dict[str, int]:
        """Get distribution of errors by type.

        Returns:
            Dictionary mapping error types to counts
        """
        with self._lock:
            distribution: Dict[str, int] = {}
            for error in self.errors:
                distribution[error.error_type] = distribution.get(error.error_type, 0) + 1
            return distribution

    def get_summary(self) -> Dict:
        """Get comprehensive error metrics summary.

        Returns:
            Dictionary with error_rate, total_errors, error_distribution, and recent_errors
        """
        with self._lock:
            recent_errors = self.errors[-10:] if self.errors else []

            return {
                "error_rate": self.get_error_rate(),
                "total_errors": len(self.errors),
                "error_distribution": self.get_error_distribution(),
                "recent_errors": [
                    {
                        "type": e.error_type,
                        "message": e.error_message,
                        "severity": e.severity,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in recent_errors
                ],
            }

    def _prune_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        self.errors = [e for e in self.errors if e.timestamp > cutoff_time]


class ResourceMetricsCollector:
    """Tracks resource usage over time."""

    def __init__(self, retention_minutes: int = 60):
        """Initialize resource metrics collector.

        Args:
            retention_minutes: How long to keep resource metrics
        """
        self.retention_minutes = retention_minutes
        self.resources: List[ResourceMetric] = []
        self._lock = threading.RLock()

    def record(self, memory_bytes: int, cpu_percent: float, active_queries: int) -> None:
        """Record resource usage snapshot.

        Args:
            memory_bytes: Memory used in bytes
            cpu_percent: CPU usage percentage (0-100)
            active_queries: Number of active query executions
        """
        with self._lock:
            metric = ResourceMetric(
                memory_bytes=memory_bytes,
                cpu_percent=cpu_percent,
                active_queries=active_queries
            )
            self.resources.append(metric)
            self._prune_old_entries()

    def get_current_usage(self) -> Optional[ResourceMetric]:
        """Get most recent resource usage.

        Returns:
            Latest ResourceMetric, or None if no data
        """
        with self._lock:
            return self.resources[-1] if self.resources else None

    def get_summary(self) -> Dict:
        """Get comprehensive resource usage summary.

        Returns:
            Dictionary with memory, cpu, and queries statistics
        """
        with self._lock:
            if not self.resources:
                return {
                    "memory_bytes": {
                        "current": 0,
                        "avg": 0,
                        "min": 0,
                        "max": 0,
                    },
                    "cpu_percent": {
                        "current": 0.0,
                        "avg": 0.0,
                        "min": 0.0,
                        "max": 0.0,
                    },
                    "active_queries": {
                        "current": 0,
                        "avg": 0,
                        "min": 0,
                        "max": 0,
                    },
                }

            latest = self.resources[-1]
            memory_values = [r.memory_bytes for r in self.resources]
            cpu_values = [r.cpu_percent for r in self.resources]
            query_values = [r.active_queries for r in self.resources]

            return {
                "memory_bytes": {
                    "current": latest.memory_bytes,
                    "avg": int(statistics.mean(memory_values)),
                    "min": min(memory_values),
                    "max": max(memory_values),
                },
                "cpu_percent": {
                    "current": latest.cpu_percent,
                    "avg": statistics.mean(cpu_values),
                    "min": min(cpu_values),
                    "max": max(cpu_values),
                },
                "active_queries": {
                    "current": latest.active_queries,
                    "avg": int(statistics.mean(query_values)),
                    "min": min(query_values),
                    "max": max(query_values),
                },
            }

    def _prune_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
        self.resources = [r for r in self.resources if r.timestamp > cutoff_time]


class MetricsCollector:
    """Central metrics collection point for all operational metrics."""

    def __init__(self, retention_minutes: int = 60):
        """Initialize metrics collector.

        Args:
            retention_minutes: How long to retain metrics in memory
        """
        self.retention_minutes = retention_minutes
        self.latency = LatencyAggregator(retention_minutes)
        self.cache = CacheMetricsCollector(retention_minutes)
        self.errors = ErrorMetricsCollector(retention_minutes)
        self.resources = ResourceMetricsCollector(retention_minutes)
        self._lock = threading.RLock()
        self._callbacks: Dict[MetricType, List[Callable]] = {}

    def record_query_latency(self, duration_ms: float, query_type: str = "unknown", strategy: str = "unknown") -> None:
        """Record query execution latency.

        Args:
            duration_ms: Query duration in milliseconds
            query_type: Type of query (e.g., "translation", "parsing")
            strategy: Translation strategy used
        """
        self.latency.record(duration_ms, query_type, strategy)
        self._trigger_callbacks(MetricType.LATENCY)

    def record_cache_hit(self, key_size: int = 0, value_size: int = 0) -> None:
        """Record a cache hit.

        Args:
            key_size: Size of cache key in bytes
            value_size: Size of cached value in bytes
        """
        self.cache.record_hit(key_size, value_size)
        self._trigger_callbacks(MetricType.CACHE_HIT_RATE)

    def record_cache_miss(self, key_size: int = 0) -> None:
        """Record a cache miss.

        Args:
            key_size: Size of cache key in bytes
        """
        self.cache.record_miss(key_size)
        self._trigger_callbacks(MetricType.CACHE_HIT_RATE)

    def record_success(self) -> None:
        """Record successful operation."""
        self.errors.record_operation(success=True)
        self._trigger_callbacks(MetricType.SUCCESS_RATE)

    def record_error(self, error_type: str, error_message: str, severity: str = "error") -> None:
        """Record an error event.

        Args:
            error_type: Classification of error
            error_message: Error message text
            severity: Severity level
        """
        self.errors.record_error(error_type, error_message, severity)
        self.errors.record_operation(success=False)
        self._trigger_callbacks(MetricType.ERROR_RATE)

    def record_resource_usage(self, memory_bytes: int, cpu_percent: float, active_queries: int) -> None:
        """Record resource usage snapshot.

        Args:
            memory_bytes: Memory used in bytes
            cpu_percent: CPU usage percentage (0-100)
            active_queries: Number of active queries
        """
        self.resources.record(memory_bytes, cpu_percent, active_queries)
        self._trigger_callbacks(MetricType.RESOURCE_USAGE)

    def get_all_metrics(self) -> Dict:
        """Get complete metrics snapshot.

        Returns:
            Dictionary with all metric categories and their summaries
        """
        with self._lock:
            return {
                "latency": self.latency.get_summary(),
                "cache": self.cache.get_summary(),
                "errors": self.errors.get_summary(),
                "resources": self.resources.get_summary(),
            }

    def register_callback(self, metric_type: MetricType, callback: Callable) -> None:
        """Register callback to be triggered when metric is recorded.

        Args:
            metric_type: Type of metric to trigger on
            callback: Function to call when metric is recorded
        """
        with self._lock:
            if metric_type not in self._callbacks:
                self._callbacks[metric_type] = []
            self._callbacks[metric_type].append(callback)

    def _trigger_callbacks(self, metric_type: MetricType) -> None:
        """Trigger all callbacks for a metric type.

        Args:
            metric_type: Type of metric
        """
        with self._lock:
            callbacks = self._callbacks.get(metric_type, [])

        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass  # Ignore callback errors to prevent data loss


# Global metrics collector instance
_default_collector: Optional[MetricsCollector] = None


def get_default_collector() -> MetricsCollector:
    """Get or create default metrics collector.

    Returns:
        Global MetricsCollector instance
    """
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector


def set_default_collector(collector: MetricsCollector) -> None:
    """Set the default metrics collector.

    Args:
        collector: MetricsCollector instance to use as default
    """
    global _default_collector
    _default_collector = collector
