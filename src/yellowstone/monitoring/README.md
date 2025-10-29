# Yellowstone Monitoring & Observability

Production-grade monitoring and observability infrastructure for the Yellowstone Cypher Query Engine. Provides comprehensive metrics collection, health checks, alerting, and diagnostics.

## Overview

The monitoring system consists of three integrated subsystems:

1. **Metrics Collection** - Operational metrics tracking with latency percentiles, cache performance, error rates, and resource usage
2. **Health Checks** - Liveness probes, readiness probes, dependency checks, and self-diagnostics
3. **Alerting** - Threshold-based alerts, anomaly detection, alert routing, and integration

## Quick Start

```python
from yellowstone.monitoring import (
    get_default_collector,
    get_default_health_manager,
    get_default_alert_manager,
)

# Record metrics
collector = get_default_collector()
collector.record_query_latency(150.0, query_type="translation")
collector.record_cache_hit(key_size=100, value_size=5000)
collector.record_success()

# Check health
health_manager = get_default_health_manager()
health = health_manager.get_overall_health()
print(health["overall_status"])  # "healthy", "degraded", or "unhealthy"

# Create alerts
alert_manager = get_default_alert_manager()
error_rate_alert = alert_manager.create_threshold_alert(
    "error_rate",
    threshold=5.0,
    direction="above",
)

# Check metrics
summary = collector.get_all_metrics()
print(summary["latency"])  # P50, P95, P99, min, max, avg, count
print(summary["cache"])    # Hit rate, miss rate, operation counts
print(summary["errors"])   # Error rate, distribution
print(summary["resources"]) # Memory, CPU, active queries
```

## Metrics Collection

### Core Concepts

- **Retention**: Metrics are kept in memory with automatic pruning based on retention window
- **Thread-Safe**: All metric collection is protected by locks for concurrent access
- **Efficient**: Uses statistical aggregation for minimal memory footprint
- **Callback Support**: Register callbacks to be triggered when specific metrics are recorded

### Latency Tracking

```python
collector = MetricsCollector()

# Record individual latency measurements
collector.record_query_latency(100.5, query_type="translation", strategy="fast_path")
collector.record_query_latency(50.0, query_type="translation", strategy="fast_path")

# Get comprehensive latency statistics
summary = collector.latency.get_summary()
# {
#   "p50": 75.25,
#   "p95": 100.0,
#   "p99": 101.0,
#   "min": 50.0,
#   "max": 100.5,
#   "avg": 75.25,
#   "count": 2
# }
```

### Cache Performance

```python
# Record cache operations
collector.record_cache_hit(key_size=100, value_size=5000)
collector.record_cache_hit(key_size=200, value_size=10000)
collector.record_cache_miss(key_size=150)

# Get cache metrics
summary = collector.cache.get_summary()
# {
#   "hit_rate": 66.67,
#   "miss_rate": 33.33,
#   "total_ops": 3,
#   "avg_key_size": 150,
#   "avg_value_size": 7500
# }
```

### Error Tracking

```python
# Record operations and errors
collector.record_success()
collector.record_success()
collector.record_error("parse_error", "Invalid Cypher syntax")

# Get error metrics
summary = collector.errors.get_summary()
# {
#   "error_rate": 33.33,
#   "total_errors": 1,
#   "error_distribution": {"parse_error": 1},
#   "recent_errors": [
#     {
#       "type": "parse_error",
#       "message": "Invalid Cypher syntax",
#       "severity": "error",
#       "timestamp": "2025-10-29T08:00:00"
#     }
#   ]
# }
```

### Resource Usage

```python
import os
import psutil

# Record resource snapshots
process = psutil.Process(os.getpid())
collector.record_resource_usage(
    memory_bytes=process.memory_info().rss,
    cpu_percent=process.cpu_percent(),
    active_queries=10
)

# Get resource summary
summary = collector.resources.get_summary()
# {
#   "memory_bytes": {"current": 100000000, "avg": 95000000, "min": 90000000, "max": 105000000},
#   "cpu_percent": {"current": 25.0, "avg": 22.5, "min": 20.0, "max": 30.0},
#   "active_queries": {"current": 10, "avg": 8, "min": 5, "max": 10}
# }
```

### Metric Callbacks

```python
def on_latency_recorded():
    print("Latency metric recorded!")

collector.register_callback(MetricType.LATENCY, on_latency_recorded)
collector.record_query_latency(100.0)  # Triggers callback
```

## Health Checks

### Liveness Probe

Checks if the service is running and responsive.

```python
from yellowstone.monitoring import get_default_health_manager

manager = get_default_health_manager()
result = manager.check_liveness()

print(result.status)      # HealthStatus.HEALTHY
print(result.message)     # "Service is alive and responsive"
print(result.duration_ms) # Time taken to check
```

### Readiness Probe

Checks if the service is ready to accept traffic.

```python
# Register dependencies
manager.register_dependency("database")
manager.register_dependency("cache")

# Mark dependencies as ready
manager.mark_dependency_ready("database")
manager.mark_dependency_ready("cache")

result = manager.check_readiness()
print(result.status)  # HealthStatus.HEALTHY
```

### Dependency Checks

```python
# Check external dependencies
def check_database():
    try:
        # Test database connection
        return True
    except Exception:
        return False

manager.register_dependency("database", check_database)

results = manager.check_dependencies()
print(results["database"].status)  # HealthStatus of database
```

### Self-Diagnostics

```python
# Register diagnostic checks
manager.register_diagnostic("memory", lambda: psutil.virtual_memory().percent < 80)
manager.register_diagnostic("parser", lambda: check_parser_integrity())

result = manager.check_diagnostics()
print(result.status)
print(result.details["diagnostics"])
```

### Overall Health

```python
# Get comprehensive health status
health = manager.get_overall_health()
# {
#   "overall_status": "healthy",  # or "degraded", "unhealthy"
#   "timestamp": "2025-10-29T08:00:00",
#   "liveness": {...},
#   "readiness": {...},
#   "dependencies": {...},
#   "diagnostics": {...}
# }
```

## Alerting

### Threshold-Based Alerts

```python
from yellowstone.monitoring import get_default_alert_manager, AlertSeverity

manager = get_default_alert_manager()

# Create threshold alert
error_alert = manager.create_threshold_alert(
    name="high_error_rate",
    threshold=5.0,
    direction="above",  # Alert when exceeds 5%
    severity=AlertSeverity.CRITICAL
)

# Check threshold
alerts = manager.check_threshold_alerts("error_rate", 6.5)
# Returns list of new alerts if threshold exceeded
```

### Anomaly Detection

```python
# Create anomaly detector
detector = manager.create_anomaly_detector(
    name="query_latency",
    window_size=20,
    severity=AlertSeverity.WARNING
)

# Add values and check for anomalies
for latency in latencies:
    alert = manager.check_anomalies("query_latency", latency)
    if alert:
        print(f"Anomaly detected: {alert.message}")
```

### Alert Management

```python
# Get active alerts
active = manager.get_active_alerts()
# Returns list of alert dictionaries

# Get alert summary
summary = manager.get_alert_summary()
# {
#   "total": 3,
#   "by_severity": {
#       "info": 0,
#       "warning": 2,
#       "critical": 1
#   },
#   "total_history": 10
# }

# Acknowledge an alert
manager.acknowledge_alert("high_error_rate")

# Resolve an alert
manager.resolve_alert("high_error_rate")
```

### Alert Routing

```python
# Register handlers for different severities
def handle_warning(alert):
    logger.warning(f"Alert: {alert.message}")

def handle_critical(alert):
    send_pagerduty(alert)
    logger.critical(f"CRITICAL: {alert.message}")

manager.register_alert_handler(AlertSeverity.WARNING, handle_warning)
manager.register_alert_handler(AlertSeverity.CRITICAL, handle_critical)

# Alerts are automatically routed to handlers
```

## Integration Patterns

### Complete Monitoring Setup

```python
from yellowstone.monitoring import (
    MetricsCollector,
    get_default_health_manager,
    get_default_alert_manager,
    AlertSeverity,
)
import logging

logger = logging.getLogger(__name__)

# Initialize monitoring
collector = MetricsCollector(retention_minutes=60)
health_manager = get_default_health_manager()
alert_manager = get_default_alert_manager()

# Register dependencies
health_manager.register_dependency("translator", lambda: check_translator_loaded())
health_manager.register_dependency("cache", lambda: check_cache_active())

# Create threshold alerts
alert_manager.create_threshold_alert("error_rate", 10.0, "above", AlertSeverity.CRITICAL)
alert_manager.create_threshold_alert("cache_hit_rate", 70.0, "below", AlertSeverity.WARNING)

# Register alert handlers
alert_manager.register_alert_handler(
    AlertSeverity.CRITICAL,
    lambda alert: logger.critical(alert.message)
)

# Track translation
def translate_with_monitoring(query):
    start = time.time()
    try:
        result = translator.translate(query)
        duration_ms = (time.time() - start) * 1000
        collector.record_query_latency(duration_ms, "translation")
        collector.record_success()
        return result
    except Exception as e:
        collector.record_error(str(type(e)), str(e))
        raise

# Check health periodically
def health_check_worker():
    while True:
        health = health_manager.get_overall_health()
        metrics = collector.get_all_metrics()

        # Check alerts
        alerts = alert_manager.get_active_alerts()

        # Log or send to monitoring system
        logger.info(f"Health: {health['overall_status']}")
        logger.info(f"Error rate: {metrics['errors']['error_rate']:.2f}%")

        time.sleep(60)
```

### Metrics Export

```python
def export_metrics_to_prometheus():
    """Export metrics to Prometheus format"""
    metrics = collector.get_all_metrics()

    lines = [
        f"# HELP query_latency_p50 Query latency P50 in ms",
        f"# TYPE query_latency_p50 gauge",
        f"query_latency_p50 {metrics['latency']['p50']}",

        f"# HELP query_latency_p99 Query latency P99 in ms",
        f"# TYPE query_latency_p99 gauge",
        f"query_latency_p99 {metrics['latency']['p99']}",

        f"# HELP cache_hit_rate Cache hit rate percentage",
        f"# TYPE cache_hit_rate gauge",
        f"cache_hit_rate {metrics['cache']['hit_rate']}",

        f"# HELP error_rate Error rate percentage",
        f"# TYPE error_rate gauge",
        f"error_rate {metrics['errors']['error_rate']}",
    ]

    return "\n".join(lines)
```

## Architecture

### Metrics Collector

- **LatencyAggregator**: Tracks query latency with percentile calculations
- **CacheMetricsCollector**: Monitors cache hit/miss rates and sizes
- **ErrorMetricsCollector**: Tracks error rates and distributions
- **ResourceMetricsCollector**: Monitors memory, CPU, and active queries
- **MetricsCollector**: Central point for all metrics

### Health Checks

- **HealthChecker**: Base class for implementing checks
- **LivenessProbe**: Checks if service is alive
- **ReadinessProbe**: Checks if service is ready for traffic
- **DependencyChecker**: Checks external dependencies
- **SelfDiagnostics**: Runs internal diagnostic checks
- **HealthCheckManager**: Coordinates all health checks

### Alerting

- **Alert**: Represents a single alert
- **ThresholdAlert**: Generates alerts on threshold violations
- **AnomalyDetector**: Detects anomalies using statistical analysis
- **AlertRouter**: Routes alerts to appropriate handlers
- **AlertManager**: Central alert management

## Global Instances

For convenience, default global instances are provided:

```python
from yellowstone.monitoring import (
    get_default_collector,
    get_default_health_manager,
    get_default_alert_manager,
)

# Use defaults
collector = get_default_collector()
health = get_default_health_manager()
alerts = get_default_alert_manager()

# Or set custom instances
from yellowstone.monitoring import (
    set_default_collector,
    set_default_health_manager,
    set_default_alert_manager,
)

custom_collector = MetricsCollector(retention_minutes=120)
set_default_collector(custom_collector)
```

## Performance Characteristics

- **Metric Recording**: O(1) append operation
- **Percentile Calculation**: O(n log n) sorting when summary requested
- **Alert Checking**: O(1) threshold comparison
- **Anomaly Detection**: O(n) for baseline statistics
- **Memory**: Automatic pruning keeps memory bounded

## Thread Safety

All components are thread-safe and use locks to protect shared state:

```python
# Safe to call from multiple threads
from threading import Thread

def worker():
    collector.record_query_latency(100.0)
    collector.record_cache_hit()

threads = [Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Testing

Comprehensive test suite with 59+ tests covering:

- Metrics aggregation and percentile calculation
- Health check execution and status determination
- Alert generation and routing
- Thread safety and concurrent access
- Integration scenarios

Run tests:

```bash
pytest src/yellowstone/monitoring/tests/test_monitoring.py -v
```

## Best Practices

1. **Record Metrics Consistently**: Always record both success and failure for accurate error rates
2. **Monitor Dependencies**: Register all external dependencies for readiness checks
3. **Set Appropriate Thresholds**: Base alert thresholds on baseline measurements
4. **Use Callbacks Sparingly**: Keep callbacks fast to avoid impacting metric recording
5. **Retain Appropriate Duration**: Balance data freshness with memory usage
6. **Handle Anomalies**: Give anomaly detectors enough data before relying on alerts
7. **Monitor the Monitor**: Check health of monitoring system itself
8. **Export Metrics**: Integrate with external monitoring systems (Prometheus, DataDog, etc.)

## Future Enhancements

- Distributed tracing support
- Metrics export to multiple backends
- Custom metric types and collectors
- Machine learning-based anomaly detection
- Histogram bucketing for latency distributions
- Correlation analysis across metrics
