# Load Testing & Stress Testing Framework

Production-ready load testing and stress testing framework for Yellowstone query engine. Provides comprehensive testing capabilities for understanding system performance under various load conditions.

## Features

### Load Testing
- **Concurrent Query Execution**: Execute multiple queries concurrently with configurable concurrency levels
- **Configurable Load Profiles**: Six predefined profiles (light, medium, heavy, stress, ramp, spike)
- **Query Distribution**: Realistic mix of simple, medium, and complex queries
- **Real-time Resource Monitoring**: Track memory, CPU, and active query counts during tests
- **Performance Degradation Tracking**: Identify performance trends and degradation patterns
- **Comprehensive Metrics**: Latency statistics (min, max, mean, median, p95, p99, std dev)

### Stress Testing
- **Breaking Point Detection**: Find where system fails or degrades critically
- **Memory Pressure Testing**: Stress the memory subsystem with complex queries
- **Connection Pool Exhaustion**: Test connection handling under extreme load
- **Spike Testing**: Simulate sudden traffic spikes and measure recovery
- **Sustained Load Testing**: Long-running tests to find memory leaks or degradation
- **Recovery Metrics**: Track time and metrics for system recovery after stress

## Installation

The load testing framework is part of Yellowstone and requires no additional installation:

```python
from yellowstone.load_testing import (
    LoadTester,
    QueryExecutor,
    StressTester,
    get_load_profile,
)
```

## Quick Start

### Basic Load Test

```python
import asyncio
from yellowstone.load_testing import LoadTester, QueryExecutor, get_load_profile

# Define your query execution function
async def execute_query(query: str, complexity: str) -> dict:
    """Execute a query and return results."""
    # Your actual query execution logic
    await asyncio.sleep(0.01)  # Simulate query execution
    return {"status": "success", "rows": 100}

# Create executor
executor = QueryExecutor(execute_query)

# Define sample queries
sample_queries = {
    "simple": [
        "MATCH (n) RETURN n LIMIT 10",
        "MATCH (n:Person) RETURN COUNT(n)",
    ],
    "medium": [
        "MATCH (a:Person)-[:KNOWS]->(b:Person) RETURN a, b LIMIT 100",
        "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
    ],
    "complex": [
        "MATCH (a)-[:KNOWS*1..3]-(b) RETURN a, b",
        "MATCH (n) WHERE n.age > 30 RETURN n ORDER BY n.name",
    ],
}

# Create tester
tester = LoadTester(executor, sample_queries)

# Run test with medium profile (50 QPS)
async def main():
    profile = get_load_profile("medium")
    result = await tester.run_test(profile)
    print(result)
    print(result.metrics)

asyncio.run(main())
```

### Stress Testing

```python
import asyncio
from yellowstone.load_testing import StressTester

async def main():
    # Define query execution
    async def execute_query(query: str, complexity: str) -> dict:
        await asyncio.sleep(0.01)
        return {"status": "success"}

    # Create stress tester
    tester = StressTester(execute_query, sample_queries)

    # Run steady increase stress test
    result = await tester.run_steady_increase_stress(
        start_qps=50,
        increment_qps=25,
        step_duration_seconds=30,
        max_qps=500,
    )

    print(f"Peak QPS: {result.peak_qps}")
    print(f"Breaking points: {result.breaking_points}")
    print(f"Success rate: {result.success_rate:.1%}")

asyncio.run(main())
```

## Load Profiles

### Light Load Profile
- **Target QPS**: 10
- **Duration**: 5 minutes
- **Query Mix**: 60% simple, 30% medium, 10% complex
- **Use Case**: Baseline performance testing, continuous monitoring
- **Concurrency**: 20 max concurrent queries

```python
from yellowstone.load_testing import LightLoadProfile, get_load_profile

# Method 1: Direct instantiation
profile = LightLoadProfile()

# Method 2: From registry
profile = get_load_profile("light")
```

### Medium Load Profile
- **Target QPS**: 50
- **Duration**: 10 minutes
- **Query Mix**: 50% simple, 40% medium, 10% complex
- **Use Case**: Typical production workload simulation
- **Concurrency**: 75 max concurrent queries

### Heavy Load Profile
- **Target QPS**: 100
- **Duration**: 15 minutes
- **Query Mix**: 40% simple, 45% medium, 15% complex
- **Use Case**: Peak load simulation, bottleneck identification
- **Concurrency**: 150 max concurrent queries

### Stress Load Profile
- **Target QPS**: 200+
- **Duration**: 20 minutes
- **Query Mix**: 30% simple, 50% medium, 20% complex
- **Use Case**: Finding system limits
- **Concurrency**: 300 max concurrent queries

### Ramp Load Profile
- **Target QPS**: Ramps to 150 over full test duration
- **Duration**: 10 minutes
- **Query Mix**: 50% simple, 40% medium, 10% complex
- **Use Case**: Finding the knee of the curve, degradation patterns

### Spike Load Profile
- **Baseline QPS**: 10
- **Spike QPS**: 250
- **Spike Count**: Multiple throughout test
- **Use Case**: Traffic spike handling and recovery testing

## Stress Test Scenarios

### Steady Increase Stress Test
Gradually increases QPS until system breaks.

```python
result = await tester.run_steady_increase_stress(
    start_qps=50,          # Starting QPS
    increment_qps=25,      # QPS increase per step
    step_duration_seconds=30,  # Time per step
    max_qps=500,          # Maximum QPS to reach
)

print(f"Breaking points: {result.breaking_points}")
for bp in result.breaking_points:
    print(f"  - QPS: {bp.qps_at_break}, Time: {bp.time_to_break_seconds}s")
```

### Memory Pressure Test
Stress the memory subsystem with complex queries.

```python
result = await tester.run_memory_pressure_test(
    target_qps=100,           # Queries per second
    duration_seconds=120,     # Test duration
    memory_target_mb=1024,    # Memory limit to trigger breaking point
)

print(f"Peak memory: {result.peak_memory_mb:.2f}MB")
print(f"Success rate: {result.success_rate:.1%}")
```

### Spike Storm Test
Multiple sudden traffic spikes to test recovery.

```python
result = await tester.run_spike_storm_test(
    baseline_qps=10,           # QPS between spikes
    spike_qps=300,             # QPS during spikes
    spike_count=5,             # Number of spikes
    spike_duration_seconds=10, # Duration of each spike
    recovery_timeout_seconds=30,  # Max time for recovery
)

print(f"Total spikes handled: {result.peak_qps}")
print(f"Recovery time: {result.recovery_metrics.time_to_recover_seconds:.2f}s")
```

## Metrics Collection

### Load Test Metrics

```python
# After running a load test
result = await tester.run_test(profile)
metrics = result.metrics

# Query counts
print(f"Total queries: {metrics.total_queries}")
print(f"Successful: {metrics.successful_queries}")
print(f"Failed: {metrics.failed_queries}")
print(f"Success rate: {metrics.success_rate:.1%}")

# Performance
print(f"Actual QPS: {metrics.actual_qps:.2f}")
print(f"Duration: {metrics.total_duration_seconds:.2f}s")

# Latency statistics
latency = metrics.latency_stats
print(f"Min latency: {latency.min_ms:.2f}ms")
print(f"Max latency: {latency.max_ms:.2f}ms")
print(f"Mean latency: {latency.mean_ms:.2f}ms")
print(f"P95 latency: {latency.p95_ms:.2f}ms")
print(f"P99 latency: {latency.p99_ms:.2f}ms")
print(f"Std dev: {latency.std_dev_ms:.2f}ms")

# Resource usage
print(f"Peak memory: {metrics.peak_memory_mb:.2f}MB")
print(f"Peak CPU: {metrics.peak_cpu_percent:.2f}%")

# Errors
print(f"Errors by type: {metrics.errors_by_type}")

# Query distribution
print(f"Query mix: {metrics.query_distribution}")
```

## Advanced Usage

### Custom Load Profiles

```python
from yellowstone.load_testing import LoadProfile

custom_profile = LoadProfile(
    name="custom",
    target_qps=75,
    duration_seconds=300,
    simple_query_percent=55,
    medium_query_percent=35,
    complex_query_percent=10,
    max_concurrent_queries=100,
    ramp_up_seconds=15,
    resource_limits={
        "max_memory_mb": 1024,
        "max_cpu_percent": 80,
        "max_latency_ms": 2500,
    },
    description="Custom profile for specific testing scenario",
)

# Validate profile
errors = custom_profile.validate()
if errors:
    print(f"Profile errors: {errors}")
else:
    result = await tester.run_test(custom_profile)
```

### Resource Snapshots

Track resource usage over time:

```python
result = await tester.run_test(profile)

# Analyze resource trend
for snapshot in result.metrics.resource_snapshots:
    print(f"Time: {snapshot.timestamp}")
    print(f"  Memory: {snapshot.memory_mb:.2f}MB")
    print(f"  CPU: {snapshot.cpu_percent:.2f}%")
    print(f"  Active queries: {snapshot.active_queries}")
    print(f"  Threads: {snapshot.thread_count}")
```

### Error Analysis

```python
result = await tester.run_test(profile)

# Analyze errors by type
print(f"Total errors: {result.metrics.failed_queries}")
for error_type, count in result.metrics.errors_by_type.items():
    percentage = (count / result.metrics.total_queries) * 100
    print(f"  {error_type}: {count} ({percentage:.1f}%)")
```

### Breaking Point Analysis

```python
result = await tester.run_steady_increase_stress()

if result.breaking_points:
    for bp in result.breaking_points:
        print(f"Breaking point at QPS {bp.qps_at_break}:")
        print(f"  Time to break: {bp.time_to_break_seconds:.2f}s")
        print(f"  Memory: {bp.memory_mb_at_break:.2f}MB")
        print(f"  CPU: {bp.cpu_percent_at_break:.2f}%")
        print(f"  Reason: {bp.error_message}")
```

## API Reference

### LoadTester

```python
class LoadTester:
    """Main load testing orchestrator."""

    async def run_test(self, profile: LoadProfile) -> LoadTestResult:
        """Run a load test using the specified profile."""
        pass
```

### QueryExecutor

```python
class QueryExecutor:
    """Executes individual queries with timing and error handling."""

    async def execute(
        self,
        query: str,
        complexity: str
    ) -> tuple[bool, float, Optional[str]]:
        """Execute a single query.

        Returns:
            (success, latency_ms, error_message)
        """
        pass

    def get_statistics(self) -> LatencyStatistics:
        """Get latency statistics."""
        pass
```

### StressTester

```python
class StressTester:
    """Stress testing orchestrator."""

    async def run_steady_increase_stress(
        self,
        start_qps: int = 50,
        increment_qps: int = 25,
        step_duration_seconds: int = 30,
        max_qps: int = 500,
    ) -> StressTestResult:
        """Run steady increase stress test."""
        pass

    async def run_memory_pressure_test(
        self,
        target_qps: int = 100,
        duration_seconds: int = 60,
        memory_target_mb: int = 1024,
    ) -> StressTestResult:
        """Run memory pressure test."""
        pass

    async def run_spike_storm_test(
        self,
        baseline_qps: int = 10,
        spike_qps: int = 300,
        spike_count: int = 5,
        spike_duration_seconds: int = 10,
        recovery_timeout_seconds: int = 30,
    ) -> StressTestResult:
        """Run spike storm test."""
        pass
```

### LoadProfile

```python
class LoadProfile:
    """Base class for load profiles."""

    name: str                      # Profile name
    target_qps: int               # Target queries per second
    duration_seconds: int         # Test duration
    simple_query_percent: int     # % of simple queries
    medium_query_percent: int     # % of medium queries
    complex_query_percent: int    # % of complex queries
    max_concurrent_queries: int   # Max concurrent queries
    ramp_up_seconds: int         # Ramp-up time
    resource_limits: Dict          # Resource constraints

    def get_qps_at_time(self, elapsed_seconds: float) -> int:
        """Get QPS at elapsed time (handles ramp-up)."""
        pass

    def get_query_distribution(self) -> Dict[str, int]:
        """Get query distribution."""
        pass

    def validate(self) -> List[str]:
        """Validate profile. Returns list of errors."""
        pass
```

## Testing

Run all tests:

```bash
pytest src/yellowstone/load_testing/tests/
```

Run specific test class:

```bash
pytest src/yellowstone/load_testing/tests/test_load_testing.py::TestLoadTester -v
```

Run with coverage:

```bash
pytest src/yellowstone/load_testing/tests/ --cov=yellowstone.load_testing
```

## Performance Considerations

### Resource Monitoring Overhead
- Resource snapshots are collected in a background thread
- Default sampling interval: 1.0 second
- Can be adjusted during LoadTester/StressTester creation

### Memory Usage
- Query latencies are stored in memory during tests
- For long-running tests with high QPS, consider adjusting resource sampling interval
- Resource snapshots keep fixed memory overhead (~100 bytes each)

### Query Generation
- Sample queries are selected randomly from provided lists
- All query execution is mocked by test functions
- Actual query complexity should be reflected in execution function

## Best Practices

1. **Start Small**: Begin with light profiles before heavy/stress profiles
2. **Isolate Variables**: Run one test at a time to avoid interference
3. **Warm Up**: Allow ramp-up time for JIT compilation and connection pooling
4. **Realistic Queries**: Use actual query patterns in sample_queries
5. **Monitor Systems**: Check system resources during long tests
6. **Repeat Tests**: Run multiple times to identify variance
7. **Document Results**: Save results for trend analysis

## Troubleshooting

### High Memory Usage
- Reduce query execution duration
- Lower target QPS
- Check for query result memory overhead

### Inaccurate QPS
- May occur if query execution is too fast/slow
- Adjust sample queries to be more representative
- Check system load from other processes

### Resource Snapshots Missing
- Ensure resource_sampling_interval is reasonable
- Background monitor thread requires adequate system resources
- Check that monitoring thread wasn't blocked

## Data Model Reference

### LoadTestResult
- `profile_name: str` - Name of load profile used
- `start_time: datetime` - Test start time
- `end_time: datetime` - Test end time
- `metrics: LoadTestMetrics` - Aggregated metrics
- `configuration: Dict` - Test configuration
- `duration_seconds: float` - Total test duration

### LoadTestMetrics
- `total_queries: int` - Total queries executed
- `successful_queries: int` - Successfully executed queries
- `failed_queries: int` - Failed queries
- `success_rate: float` - Success rate (0.0-1.0)
- `actual_qps: float` - Actual queries per second achieved
- `latency_stats: LatencyStatistics` - Latency statistics
- `resource_snapshots: List[ResourceSnapshot]` - Resource history
- `peak_memory_mb: float` - Peak memory usage
- `peak_cpu_percent: float` - Peak CPU usage
- `errors_by_type: Dict[str, int]` - Error type counts
- `query_distribution: Dict[str, int]` - Query complexity distribution

### StressTestResult
- `stress_type: str` - Type of stress test
- `start_time: datetime` - Test start time
- `end_time: datetime` - Test end time
- `peak_qps: int` - Peak QPS reached
- `breaking_points: List[BreakingPoint]` - System breaking points
- `recovery_metrics: Optional[RecoveryMetrics]` - Recovery information
- `total_queries_executed: int` - Total queries run
- `total_errors: int` - Total errors
- `success_rate: float` - Success rate
- `peak_memory_mb: float` - Peak memory usage
- `peak_cpu_percent: float` - Peak CPU usage

### LatencyStatistics
- `min_ms: float` - Minimum latency
- `max_ms: float` - Maximum latency
- `mean_ms: float` - Mean latency
- `median_ms: float` - Median latency
- `p95_ms: float` - 95th percentile latency
- `p99_ms: float` - 99th percentile latency
- `std_dev_ms: float` - Standard deviation

## License

Part of Yellowstone query engine.
