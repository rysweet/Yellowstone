# Yellowstone Benchmarking Suite

Comprehensive performance benchmarking tools for measuring and comparing Cypher-to-KQL translation and execution performance.

## Overview

The benchmarking suite provides:

- **50+ Curated Queries**: Covering simple to complex security investigation patterns
- **Performance Metrics**: Latency percentiles (P50, P95, P99), throughput, resource usage
- **Comparative Analysis**: Compare Cypher vs native KQL performance
- **Regression Detection**: Automatic detection of performance regressions
- **Rich Reports**: HTML and JSON reports with visualizations

## Target Metrics

- **P50 latency** < 1 second
- **P95 latency** < 3 seconds
- **P99 latency** < 5 seconds
- **Translation overhead**: 2-5x vs native KQL

## Module Structure

```
benchmarks/
├── __init__.py              # Public API exports
├── benchmark_queries.py     # 50+ curated benchmark queries
├── metrics_collector.py     # Performance metrics collection
├── benchmark_runner.py      # Benchmark orchestration
├── report_generator.py      # HTML/JSON report generation
└── tests/
    └── test_benchmarks.py   # 30+ comprehensive tests
```

## Quick Start

### Basic Benchmark Run

```python
from yellowstone.benchmarks import BenchmarkRunner

# Run all benchmarks with default settings
runner = BenchmarkRunner()
results = await runner.run_all_benchmarks()

# Generate HTML report
runner.generate_report(results, "benchmark_report.html")

print(f"Completed {results.total_queries} queries")
print(f"Success rate: {results.success_rate:.1f}%")
```

### Custom Configuration

```python
from yellowstone.benchmarks import BenchmarkRunner, BenchmarkConfig, QueryComplexity

# Configure benchmark
config = BenchmarkConfig(
    name="production_benchmark",
    warmup_iterations=5,
    iterations_per_query=10,
    enable_cache=False,
    complexities=[QueryComplexity.SIMPLE, QueryComplexity.MEDIUM],
    categories=["security", "alerts"],
)

runner = BenchmarkRunner(config=config)
results = await runner.run_all_benchmarks()
```

### Single Query Benchmark

```python
from yellowstone.benchmarks import BenchmarkRunner, BenchmarkQueries

runner = BenchmarkRunner()
queries = BenchmarkQueries()

# Benchmark a specific query
query = queries.get_by_id("simple_001")
metrics = await runner.run_single_query(query, iterations=100)

# Analyze results
avg_latency = sum(m.total_time_ms for m in metrics) / len(metrics)
print(f"Average latency: {avg_latency:.2f}ms")
```

### Performance Comparison

```python
# Run baseline benchmark
baseline = await runner.run_all_benchmarks()

# Make performance improvements...

# Run comparison
comparison = await runner.compare_with_baseline(baseline)

if comparison["regression_detected"]:
    print("⚠ Performance regression detected!")
    print(f"P95 change: {comparison['p95_improvement_percent']:+.1f}%")
else:
    print("✓ Performance improved!")
```

## Benchmark Queries

The suite includes 50+ queries organized by complexity:

### Simple Queries (1 hop, basic filters)
- User lookups
- Alert filtering
- Basic aggregations
- Time-based queries

### Medium Queries (2-3 hops)
- Multi-hop relationships
- Correlation patterns
- Aggregation with grouping
- Behavioral analysis

### Complex Queries (4+ hops, heavy aggregations)
- Attack path reconstruction
- Insider threat detection
- Multi-stage analysis
- Risk scoring

### Stress Queries (Variable-length paths, graph algorithms)
- Deep path exploration
- Community detection
- Centrality calculations
- Graph traversal

## Metrics Collected

### Query Metrics
- **Translation time**: Time to translate Cypher to KQL
- **Execution time**: Time to execute KQL query
- **Total time**: End-to-end latency
- **Result count**: Number of results returned
- **Translation overhead**: Percentage of time spent translating

### Resource Metrics
- **Memory usage**: Peak memory during execution
- **CPU usage**: Average CPU utilization
- **Cache hit rate**: Percentage of cached results

### Statistical Summaries
- **Percentiles**: P50, P95, P99 latency
- **Averages**: Mean latency, throughput
- **Min/Max**: Fastest and slowest queries
- **Success rate**: Percentage of successful executions

## Report Formats

### HTML Report
Rich, interactive report with:
- Performance summary dashboard
- Latency percentile metrics
- Query-by-query breakdown
- Complexity analysis
- Resource usage charts
- Pass/fail indicators for targets

### JSON Report
Machine-readable format including:
- Complete metrics data
- Statistical summaries
- Configuration details
- Environment information
- Suitable for CI/CD integration

## Query Categories

Queries are organized by security use case:

- **security**: Attack detection, threat hunting
- **alerts**: Alert management and analysis
- **network**: Network traffic analysis
- **authentication**: Login and access patterns
- **file_access**: File operation monitoring
- **process**: Process execution chains
- **aggregation**: Statistical analysis
- **correlation**: Event correlation
- **graph_analysis**: Graph algorithms
- **behavior**: User behavior analysis

## Examples

### Filter by Complexity

```python
queries = BenchmarkQueries()

# Get only simple queries
simple_queries = queries.get_by_complexity(QueryComplexity.SIMPLE)

# Get complex queries for stress testing
complex_queries = queries.get_by_complexity(QueryComplexity.COMPLEX)
```

### Filter by Category

```python
# Benchmark only security-related queries
config = BenchmarkConfig(categories=["security", "alerts"])
runner = BenchmarkRunner(config=config)
results = await runner.run_all_benchmarks()
```

### Stress Testing

```python
# Run continuous queries for 5 minutes
results = await runner.run_stress_test(duration_seconds=300)

# Check if targets are still met under load
summary = runner.collector.compute_summary()
if summary.meets_targets():
    print("✓ System handles sustained load")
```

### Regression Testing in CI/CD

```python
import json

# Load baseline from previous run
with open("baseline_results.json") as f:
    baseline_data = json.load(f)

# Run current benchmark
current = await runner.run_all_benchmarks()

# Compare
runner.generate_report(current, "current_report.json", format=ReportFormat.JSON)

# Load and compare
with open("current_report.json") as f:
    current_data = json.load(f)

if current_data["meets_targets"] and not current_data["regression_detected"]:
    print("✓ Benchmark passed")
    exit(0)
else:
    print("✗ Benchmark failed")
    exit(1)
```

## Integration with Yellowstone

The benchmark suite integrates with the main Yellowstone translator:

```python
from yellowstone.translator import CypherToKQLTranslator
from yellowstone.benchmarks import BenchmarkRunner

# Initialize with actual translator
translator = CypherToKQLTranslator()

# Create executor function
async def execute_kql(kql: str):
    # Execute against Azure Data Explorer
    # Return results
    pass

# Run benchmarks with real translation and execution
runner = BenchmarkRunner(translator=translator, executor=execute_kql)
results = await runner.run_all_benchmarks()
```

## Best Practices

1. **Warmup**: Always use warmup iterations to account for cold starts
2. **Multiple Iterations**: Run each query multiple times for statistical significance
3. **Baseline**: Maintain baseline results for comparison
4. **Environment**: Document system specs and configuration
5. **Isolation**: Run benchmarks in isolation without other workloads
6. **Monitoring**: Track trends over time to detect gradual regressions

## Testing

Run the test suite:

```bash
pytest src/yellowstone/benchmarks/tests/test_benchmarks.py -v
```

The test suite includes 30+ tests covering:
- Query collection and filtering
- Metrics collection and aggregation
- Benchmark orchestration
- Report generation
- Performance validation
- Regression detection
- Integration workflows

## Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| P50 Latency | < 1s | Median query time |
| P95 Latency | < 3s | 95th percentile |
| P99 Latency | < 5s | 99th percentile |
| Translation Overhead | 2-5x | Acceptable overhead vs native KQL |
| Success Rate | > 95% | Queries completing successfully |

## Contributing

When adding new benchmark queries:

1. Use descriptive IDs and names
2. Provide both Cypher and equivalent KQL
3. Specify complexity level accurately
4. Add relevant tags for filtering
5. Include expected result counts where applicable
6. Document the query purpose

Example:

```python
BenchmarkQuery(
    id="security_015",
    name="Credential theft detection",
    cypher="MATCH (p:Process)-[:ACCESSED]->(m:Memory) WHERE m.region CONTAINS 'lsass' RETURN p",
    kql="DeviceProcessEvents | where ProcessCommandLine contains 'lsass' | project DeviceName, FileName",
    complexity=QueryComplexity.SIMPLE,
    category="security",
    description="Detect processes accessing LSASS memory for credential theft",
    expected_result_count=None,
    tags=["security", "credential", "process"],
)
```

## License

MIT License - See main project LICENSE file.

## Support

For issues or questions about the benchmarking suite:
- Open an issue on GitHub
- Check the main Yellowstone documentation
- Review test cases for usage examples
