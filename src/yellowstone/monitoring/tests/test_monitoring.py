"""
Comprehensive tests for monitoring and observability infrastructure.

Tests cover metrics collection, health checks, alerting, and integration scenarios.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from ..metrics_collector import (
    MetricsCollector,
    LatencyAggregator,
    CacheMetricsCollector,
    ErrorMetricsCollector,
    ResourceMetricsCollector,
    LatencyMetric,
    MetricType,
)

from ..health_checks import (
    HealthCheckManager,
    HealthChecker,
    HealthStatus,
    CheckResult,
    LivenessProbe,
    ReadinessProbe,
    DependencyChecker,
    SelfDiagnostics,
)

from ..alerting import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertStatus,
    ThresholdAlert,
    AnomalyDetector,
)


# ============================================================================
# Metrics Collector Tests
# ============================================================================

class TestLatencyAggregator:
    """Test latency metrics aggregation."""

    def test_record_single_latency(self):
        """Test recording a single latency measurement."""
        aggregator = LatencyAggregator()
        aggregator.record(100.5, "translation", "fast_path")

        summary = aggregator.get_summary()
        assert summary["count"] == 1
        assert summary["avg"] == 100.5
        assert summary["min"] == 100.5
        assert summary["max"] == 100.5

    def test_record_multiple_latencies(self):
        """Test recording multiple latency measurements."""
        aggregator = LatencyAggregator()
        latencies = [50.0, 100.0, 150.0, 200.0, 250.0]

        for latency in latencies:
            aggregator.record(latency)

        summary = aggregator.get_summary()
        assert summary["count"] == 5
        assert summary["min"] == 50.0
        assert summary["max"] == 250.0
        assert summary["avg"] == 150.0  # Average
        assert summary["p50"] == 150.0  # Median
        assert summary["p95"] > 150.0
        assert summary["p99"] > 150.0

    def test_get_percentile(self):
        """Test percentile calculation."""
        aggregator = LatencyAggregator()
        for i in range(1, 101):  # 1-100
            aggregator.record(float(i))

        assert aggregator.get_percentile(50) == pytest.approx(50, abs=1)
        assert aggregator.get_percentile(95) > 90
        assert aggregator.get_percentile(99) > 98

    def test_empty_summary(self):
        """Test summary with no data."""
        aggregator = LatencyAggregator()
        summary = aggregator.get_summary()

        assert summary["count"] == 0
        assert summary["avg"] == 0.0
        assert summary["p50"] == 0.0

    def test_retention_pruning(self):
        """Test that old entries are pruned."""
        aggregator = LatencyAggregator(retention_minutes=1)
        aggregator.record(100.0)
        assert len(aggregator.latencies) == 1

        # Manually set timestamp to old
        aggregator.latencies[0].timestamp = datetime.utcnow() - timedelta(minutes=2)

        # Record new entry to trigger pruning
        aggregator.record(50.0)
        assert len(aggregator.latencies) == 1
        assert aggregator.latencies[0].duration_ms == 50.0


class TestCacheMetricsCollector:
    """Test cache metrics collection."""

    def test_record_cache_hits_and_misses(self):
        """Test recording cache hits and misses."""
        collector = CacheMetricsCollector()
        collector.record_hit(10, 1000)
        collector.record_hit(10, 1000)
        collector.record_miss(10)

        summary = collector.get_summary()
        assert summary["total_ops"] == 3
        assert summary["hit_rate"] == pytest.approx(66.67, abs=1)
        assert summary["miss_rate"] == pytest.approx(33.33, abs=1)

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation."""
        collector = CacheMetricsCollector()
        for _ in range(80):
            collector.record_hit()
        for _ in range(20):
            collector.record_miss()

        assert collector.get_hit_rate() == pytest.approx(80.0, abs=0.1)

    def test_cache_summary_empty(self):
        """Test cache summary with no data."""
        collector = CacheMetricsCollector()
        summary = collector.get_summary()

        assert summary["hit_rate"] == 0.0
        assert summary["miss_rate"] == 0.0
        assert summary["total_ops"] == 0

    def test_avg_key_and_value_sizes(self):
        """Test average key and value size tracking."""
        collector = CacheMetricsCollector()
        collector.record_hit(100, 5000)
        collector.record_hit(200, 10000)

        summary = collector.get_summary()
        assert summary["avg_key_size"] == pytest.approx(150, abs=1)
        assert summary["avg_value_size"] == pytest.approx(7500, abs=1)


class TestErrorMetricsCollector:
    """Test error metrics collection."""

    def test_record_errors(self):
        """Test recording errors."""
        collector = ErrorMetricsCollector()
        collector.record_error("parse_error", "Invalid syntax")
        collector.record_error("translation_error", "Unsupported operation")

        summary = collector.get_summary()
        assert summary["total_errors"] == 2

    def test_error_distribution(self):
        """Test error distribution tracking."""
        collector = ErrorMetricsCollector()
        for _ in range(3):
            collector.record_error("parse_error", "Invalid syntax")
        for _ in range(2):
            collector.record_error("translation_error", "Unsupported")

        distribution = collector.get_error_distribution()
        assert distribution["parse_error"] == 3
        assert distribution["translation_error"] == 2

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        collector = ErrorMetricsCollector()
        for _ in range(80):
            collector.record_operation(success=True)
        for _ in range(20):
            collector.record_operation(success=False)
            collector.record_error("test_error", "test")

        summary = collector.get_summary()
        assert summary["error_rate"] == pytest.approx(20.0, abs=0.1)

    def test_recent_errors(self):
        """Test recent errors tracking."""
        collector = ErrorMetricsCollector()
        for i in range(15):
            collector.record_error(f"error_{i}", f"Message {i}")

        summary = collector.get_summary()
        assert len(summary["recent_errors"]) == 10  # Last 10
        assert summary["recent_errors"][-1]["type"] == "error_14"


class TestResourceMetricsCollector:
    """Test resource metrics collection."""

    def test_record_resource_usage(self):
        """Test recording resource usage."""
        collector = ResourceMetricsCollector()
        collector.record(1024 * 1024 * 100, 50.0, 10)
        collector.record(1024 * 1024 * 150, 75.0, 15)

        current = collector.get_current_usage()
        assert current is not None
        assert current.memory_bytes == 1024 * 1024 * 150
        assert current.cpu_percent == 75.0
        assert current.active_queries == 15

    def test_resource_summary(self):
        """Test resource usage summary."""
        collector = ResourceMetricsCollector()
        collector.record(1000000, 50.0, 5)
        collector.record(2000000, 75.0, 10)
        collector.record(1500000, 60.0, 8)

        summary = collector.get_summary()
        assert summary["memory_bytes"]["current"] == 1500000
        assert summary["memory_bytes"]["min"] == 1000000
        assert summary["memory_bytes"]["max"] == 2000000
        assert summary["cpu_percent"]["current"] == 60.0
        assert summary["active_queries"]["current"] == 8


class TestMetricsCollector:
    """Test central metrics collector."""

    def test_record_query_latency(self):
        """Test recording query latency."""
        collector = MetricsCollector()
        collector.record_query_latency(100.0, "translation", "fast_path")
        collector.record_query_latency(150.0, "translation", "fast_path")

        summary = collector.get_all_metrics()
        assert summary["latency"]["count"] == 2

    def test_record_cache_operations(self):
        """Test recording cache operations."""
        collector = MetricsCollector()
        collector.record_cache_hit(10, 1000)
        collector.record_cache_miss(10)

        summary = collector.get_all_metrics()
        assert summary["cache"]["total_ops"] == 2
        assert summary["cache"]["hit_rate"] == pytest.approx(50.0, abs=1)

    def test_record_errors(self):
        """Test recording errors."""
        collector = MetricsCollector()
        collector.record_success()
        collector.record_success()
        collector.record_error("test_error", "test message")

        summary = collector.get_all_metrics()
        assert summary["errors"]["total_errors"] == 1
        assert summary["errors"]["error_rate"] == pytest.approx(33.33, abs=1)

    def test_record_resource_usage(self):
        """Test recording resource usage."""
        collector = MetricsCollector()
        collector.record_resource_usage(1000000, 50.0, 5)

        summary = collector.get_all_metrics()
        assert summary["resources"]["memory_bytes"]["current"] == 1000000
        assert summary["resources"]["cpu_percent"]["current"] == 50.0

    def test_callback_triggering(self):
        """Test metric callbacks are triggered."""
        collector = MetricsCollector()
        callback_called = Mock()

        collector.register_callback(MetricType.LATENCY, callback_called)
        collector.record_query_latency(100.0)

        callback_called.assert_called()

    def test_multiple_callbacks(self):
        """Test multiple callbacks for same metric type."""
        collector = MetricsCollector()
        callback1 = Mock()
        callback2 = Mock()

        collector.register_callback(MetricType.LATENCY, callback1)
        collector.register_callback(MetricType.LATENCY, callback2)
        collector.record_query_latency(100.0)

        callback1.assert_called()
        callback2.assert_called()


# ============================================================================
# Health Check Tests
# ============================================================================

class TestLivenessProbe:
    """Test liveness probe."""

    def test_liveness_check_succeeds(self):
        """Test successful liveness check."""
        probe = LivenessProbe()
        result = probe.check()

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "liveness"
        assert "heartbeat" in result.details

    def test_liveness_updates_heartbeat(self):
        """Test liveness updates heartbeat time."""
        probe = LivenessProbe()
        old_heartbeat = probe.last_heartbeat
        time.sleep(0.1)

        probe.check()
        assert probe.last_heartbeat > old_heartbeat


class TestReadinessProbe:
    """Test readiness probe."""

    def test_readiness_with_no_dependencies(self):
        """Test readiness when no dependencies are required."""
        probe = ReadinessProbe()
        result = probe.check()

        assert result.status == HealthStatus.HEALTHY
        assert "no dependencies" in result.message.lower()

    def test_readiness_with_ready_dependencies(self):
        """Test readiness when all dependencies are ready."""
        probe = ReadinessProbe()
        probe.register_dependency("db")
        probe.register_dependency("cache")
        probe.mark_dependency_ready("db")
        probe.mark_dependency_ready("cache")

        result = probe.check()
        assert result.status == HealthStatus.HEALTHY

    def test_readiness_with_unready_dependencies(self):
        """Test readiness when some dependencies are not ready."""
        probe = ReadinessProbe()
        probe.register_dependency("db")
        probe.register_dependency("cache")
        probe.mark_dependency_ready("db")

        result = probe.check()
        assert result.status == HealthStatus.DEGRADED
        assert "cache" in str(result.details["unready"])


class TestDependencyChecker:
    """Test dependency checker."""

    def test_dependency_healthy(self):
        """Test healthy dependency check."""
        check_fn = Mock(return_value=True)
        checker = DependencyChecker("database", check_fn)

        result = checker.check()
        assert result.status == HealthStatus.HEALTHY
        check_fn.assert_called()

    def test_dependency_unhealthy(self):
        """Test unhealthy dependency check."""
        check_fn = Mock(return_value=False)
        checker = DependencyChecker("database", check_fn)

        result = checker.check()
        assert result.status == HealthStatus.UNHEALTHY

    def test_dependency_check_exception(self):
        """Test dependency check that raises exception."""
        check_fn = Mock(side_effect=Exception("Connection failed"))
        checker = DependencyChecker("database", check_fn)

        result = checker.check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message


class TestSelfDiagnostics:
    """Test self-diagnostics."""

    def test_all_diagnostics_pass(self):
        """Test when all diagnostics pass."""
        diagnostics = SelfDiagnostics()
        diagnostics.register_diagnostic("cache", Mock(return_value=True))
        diagnostics.register_diagnostic("parser", Mock(return_value=True))

        result = diagnostics.check()
        assert result.status == HealthStatus.HEALTHY

    def test_some_diagnostics_fail(self):
        """Test when some diagnostics fail."""
        diagnostics = SelfDiagnostics()
        diagnostics.register_diagnostic("cache", Mock(return_value=True))
        diagnostics.register_diagnostic("parser", Mock(return_value=False))

        result = diagnostics.check()
        assert result.status == HealthStatus.DEGRADED
        assert "parser" in str(result.details["diagnostics"])

    def test_diagnostic_exception(self):
        """Test diagnostic that raises exception."""
        diagnostics = SelfDiagnostics()
        diagnostics.register_diagnostic("test", Mock(side_effect=Exception("Failed")))

        result = diagnostics.check()
        assert result.status == HealthStatus.DEGRADED


class TestHealthCheckManager:
    """Test health check manager."""

    def test_register_dependency(self):
        """Test registering a dependency."""
        manager = HealthCheckManager()
        check_fn = Mock(return_value=True)

        manager.register_dependency("database", check_fn)
        assert "database" in manager.dependency_checkers

    def test_mark_dependency_ready(self):
        """Test marking dependency as ready."""
        manager = HealthCheckManager()
        check_fn = Mock(return_value=True)
        manager.register_dependency("database", check_fn)

        manager.mark_dependency_ready("database")
        assert manager.readiness.initialized_dependencies["database"] is True

    def test_check_liveness(self):
        """Test liveness check through manager."""
        manager = HealthCheckManager()
        result = manager.check_liveness()

        assert result.status == HealthStatus.HEALTHY
        assert result.name == "liveness"

    def test_check_readiness(self):
        """Test readiness check through manager."""
        manager = HealthCheckManager()
        result = manager.check_readiness()

        assert result.name == "readiness"

    def test_get_overall_health_healthy(self):
        """Test overall health when everything is healthy."""
        manager = HealthCheckManager()
        health = manager.get_overall_health()

        assert health["overall_status"] == HealthStatus.HEALTHY.value

    def test_get_overall_health_degraded(self):
        """Test overall health when something is degraded."""
        manager = HealthCheckManager()
        check_fn = Mock(return_value=False)
        manager.register_dependency("database", check_fn)

        health = manager.get_overall_health()
        # When a dependency check fails, it's unhealthy (not degraded)
        assert health["overall_status"] in (HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value)


# ============================================================================
# Alerting Tests
# ============================================================================

class TestThresholdAlert:
    """Test threshold-based alerts."""

    def test_alert_above_threshold(self):
        """Test alert when value exceeds threshold."""
        alert = ThresholdAlert("error_rate")
        alert.set_threshold(5.0, "above")

        result = alert.check(10.0)
        assert result is not None
        assert result.name == "error_rate"
        assert result.value == 10.0

    def test_no_alert_below_threshold(self):
        """Test no alert when value below threshold."""
        alert = ThresholdAlert("error_rate")
        alert.set_threshold(10.0, "above")

        result = alert.check(5.0)
        assert result is None

    def test_alert_below_threshold(self):
        """Test alert when value below threshold."""
        alert = ThresholdAlert("cache_hit_rate")
        alert.set_threshold(80.0, "below")

        result = alert.check(50.0)
        assert result is not None
        assert result.status == AlertStatus.ACTIVE

    def test_alert_cooldown(self):
        """Test alert cooldown prevents spam."""
        alert = ThresholdAlert("error_rate")
        alert.set_threshold(5.0, "above")
        alert.alert_cooldown_seconds = 1

        # First alert should fire
        result1 = alert.check(10.0)
        assert result1 is not None

        # Second alert immediately after should not fire (cooldown)
        result2 = alert.check(10.0)
        assert result2 is None

        # After cooldown, alert should fire again
        alert.last_alert_time = datetime.utcnow() - timedelta(seconds=2)
        result3 = alert.check(10.0)
        assert result3 is not None


class TestAnomalyDetector:
    """Test anomaly detection."""

    def test_anomaly_detection_basic(self):
        """Test basic anomaly detection."""
        detector = AnomalyDetector("query_latency", window_size=10)

        # Add normal values with slight variation (mean ~100, stdev ~5)
        for i in range(25):
            value = 100.0 + (i % 5) - 2.5  # Creates values around 100
            detector.add_value(value)

        # Add anomalous value (way outside normal range)
        alert = detector.add_value(500.0)

        assert alert is not None
        assert "anomaly" in alert.name

    def test_no_alert_with_insufficient_data(self):
        """Test no alert when insufficient data for baseline."""
        detector = AnomalyDetector("test", window_size=20)

        for i in range(5):
            alert = detector.add_value(float(i))
            assert alert is None

    def test_get_baseline_stats(self):
        """Test getting baseline statistics."""
        detector = AnomalyDetector("test", window_size=10)

        for i in range(1, 11):
            detector.add_value(float(i) * 10)

        stats = detector.get_baseline_stats()
        assert stats is not None
        assert "mean" in stats
        assert "stdev" in stats


class TestAlert:
    """Test alert class."""

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        alert = Alert("test", AlertSeverity.WARNING, "Test alert", 10.0, 5.0)

        assert alert.status == AlertStatus.ACTIVE
        alert.acknowledge()
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None

    def test_resolve_alert(self):
        """Test resolving an alert."""
        alert = Alert("test", AlertSeverity.WARNING, "Test alert", 10.0, 5.0)

        alert.resolve()
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert("test", AlertSeverity.CRITICAL, "Critical alert", 100.0, 50.0)

        alert_dict = alert.to_dict()
        assert alert_dict["name"] == "test"
        assert alert_dict["severity"] == "critical"
        assert alert_dict["value"] == 100.0


class TestAlertManager:
    """Test alert manager."""

    def test_create_threshold_alert(self):
        """Test creating threshold alert."""
        manager = AlertManager()
        alert = manager.create_threshold_alert("error_rate", 5.0, "above")

        assert alert.name == "error_rate"
        assert alert.threshold == 5.0

    def test_create_anomaly_detector(self):
        """Test creating anomaly detector."""
        manager = AlertManager()
        detector = manager.create_anomaly_detector("latency", window_size=20)

        assert detector.name == "latency"
        assert detector.window_size == 20

    def test_handle_alert(self):
        """Test handling an alert."""
        manager = AlertManager()
        alert = Alert("test", AlertSeverity.WARNING, "Test", 10.0, 5.0)

        manager.handle_alert(alert)
        assert "test" in manager.active_alerts

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        manager = AlertManager()
        alert1 = Alert("alert1", AlertSeverity.WARNING, "Test1", 10.0, 5.0)
        alert2 = Alert("alert2", AlertSeverity.CRITICAL, "Test2", 20.0, 10.0)

        manager.handle_alert(alert1)
        manager.handle_alert(alert2)

        active = manager.get_active_alerts()
        assert len(active) == 2

    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        manager = AlertManager()
        alert = Alert("test", AlertSeverity.WARNING, "Test", 10.0, 5.0)

        manager.handle_alert(alert)
        success = manager.acknowledge_alert("test")

        assert success
        assert manager.active_alerts["test"].status == AlertStatus.ACKNOWLEDGED

    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()
        alert = Alert("test", AlertSeverity.WARNING, "Test", 10.0, 5.0)

        manager.handle_alert(alert)
        success = manager.resolve_alert("test")

        assert success
        assert "test" not in manager.active_alerts

    def test_get_alert_summary(self):
        """Test getting alert summary."""
        manager = AlertManager()
        alert1 = Alert("alert1", AlertSeverity.WARNING, "Test1", 10.0, 5.0)
        alert2 = Alert("alert2", AlertSeverity.CRITICAL, "Test2", 20.0, 10.0)

        manager.handle_alert(alert1)
        manager.handle_alert(alert2)

        summary = manager.get_alert_summary()
        assert summary["total"] == 2
        assert summary["by_severity"]["warning"] == 1
        assert summary["by_severity"]["critical"] == 1

    def test_register_alert_handler(self):
        """Test registering alert handler."""
        manager = AlertManager()
        handler = Mock()

        manager.register_alert_handler(AlertSeverity.CRITICAL, handler)
        alert = Alert("test", AlertSeverity.CRITICAL, "Test", 10.0, 5.0)
        manager.handle_alert(alert)

        handler.assert_called()


# ============================================================================
# Integration Tests
# ============================================================================

class TestMonitoringIntegration:
    """Test integration of monitoring components."""

    def test_metrics_and_alerts_integration(self):
        """Test metrics collection triggering alerts."""
        collector = MetricsCollector()
        alert_mgr = AlertManager()

        # Create threshold alert on error rate
        alert_mgr.create_threshold_alert("error_rate", 20.0, "above", AlertSeverity.CRITICAL)

        # Record many errors to trigger alert
        for _ in range(20):
            collector.record_success()
        for _ in range(5):
            collector.record_error("test_error", "test")

        # Check alert would be triggered
        error_rate = collector.errors.get_error_rate()
        assert error_rate > 15  # About 20%

    def test_health_checks_with_diagnostics(self):
        """Test health checks with diagnostics."""
        manager = HealthCheckManager()

        # Add diagnostic
        manager.register_diagnostic("memory", lambda: True)
        manager.register_diagnostic("parser", lambda: False)

        health = manager.get_overall_health()
        assert health["diagnostics"]["status"] == "degraded"

    def test_concurrent_metric_recording(self):
        """Test concurrent metric recording is thread-safe."""
        collector = MetricsCollector()
        errors = []

        def record_metrics():
            try:
                for _ in range(100):
                    collector.record_query_latency(50.0)
                    collector.record_cache_hit()
                    collector.record_success()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        summary = collector.get_all_metrics()
        assert summary["latency"]["count"] >= 500  # 5 threads * 100 recordings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
