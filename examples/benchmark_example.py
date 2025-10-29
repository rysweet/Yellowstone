#!/usr/bin/env python3
"""
Example demonstrating the Yellowstone benchmarking suite.

This script shows how to:
1. Run benchmarks with different configurations
2. Generate reports
3. Compare performance
4. Filter queries by complexity and category
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yellowstone.benchmarks import (
    BenchmarkRunner,
    BenchmarkConfig,
    BenchmarkQueries,
    QueryComplexity,
    ReportFormat,
)


async def example_basic_benchmark():
    """Run a basic benchmark with default settings."""
    print("=" * 70)
    print("Example 1: Basic Benchmark")
    print("=" * 70)

    # Create runner with default config
    runner = BenchmarkRunner()

    # Run benchmarks (using only simple queries for quick demo)
    config = BenchmarkConfig(
        name="basic_demo",
        warmup_iterations=1,
        iterations_per_query=3,
        complexities=[QueryComplexity.SIMPLE],
    )
    runner.config = config

    results = await runner.run_all_benchmarks()

    print(f"\nResults Summary:")
    print(f"  Total queries: {results.total_queries}")
    print(f"  Successful: {results.successful_queries}")
    print(f"  Failed: {results.failed_queries}")
    print(f"  Success rate: {results.success_rate:.1f}%")
    print(f"  Duration: {results.duration_seconds:.2f}s")

    # Compute performance summary
    summary = runner.collector.compute_summary()
    print(f"\nPerformance Metrics:")
    print(f"  P50 latency: {summary.total_time_p50:.2f}ms")
    print(f"  P95 latency: {summary.total_time_p95:.2f}ms")
    print(f"  P99 latency: {summary.total_time_p99:.2f}ms")
    print(f"  Avg latency: {summary.total_time_avg:.2f}ms")
    print(f"  Throughput: {summary.throughput_qps:.1f} QPS")
    print(f"  Translation overhead: {summary.translation_overhead_avg * 100:.1f}%")

    # Check if targets are met
    if summary.meets_targets():
        print(f"\n✓ Performance targets MET")
    else:
        print(f"\n✗ Performance targets NOT MET")

    return results


async def example_filtered_benchmark():
    """Run benchmark filtered by category."""
    print("\n" + "=" * 70)
    print("Example 2: Filtered Benchmark (Security Queries Only)")
    print("=" * 70)

    config = BenchmarkConfig(
        name="security_focused",
        categories=["security"],
        iterations_per_query=5,
        warmup_iterations=1,
    )

    runner = BenchmarkRunner(config=config)
    results = await runner.run_all_benchmarks()

    print(f"\nSecurity Query Results:")
    print(f"  Queries executed: {results.total_queries}")
    print(f"  Success rate: {results.success_rate:.1f}%")

    return results


async def example_single_query():
    """Run a single query multiple times."""
    print("\n" + "=" * 70)
    print("Example 3: Single Query Benchmark")
    print("=" * 70)

    queries = BenchmarkQueries()
    query = queries.get_by_id("simple_001")

    print(f"\nQuery: {query.name}")
    print(f"Category: {query.category}")
    print(f"Complexity: {query.complexity.value}")
    print(f"\nCypher:")
    print(f"  {query.cypher}")

    runner = BenchmarkRunner()
    metrics = await runner.run_single_query(query, iterations=10)

    # Calculate statistics
    latencies = [m.total_time_ms for m in metrics]
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)

    print(f"\nResults (10 iterations):")
    print(f"  Avg latency: {avg_latency:.2f}ms")
    print(f"  Min latency: {min_latency:.2f}ms")
    print(f"  Max latency: {max_latency:.2f}ms")


async def example_report_generation():
    """Generate HTML and JSON reports."""
    print("\n" + "=" * 70)
    print("Example 4: Report Generation")
    print("=" * 70)

    # Run quick benchmark
    config = BenchmarkConfig(
        name="report_demo",
        iterations_per_query=3,
        warmup_iterations=1,
        complexities=[QueryComplexity.SIMPLE],
    )

    runner = BenchmarkRunner(config=config)
    results = await runner.run_all_benchmarks()

    # Generate HTML report
    html_path = "benchmark_report_demo.html"
    runner.generate_report(results, html_path, format=ReportFormat.HTML)
    print(f"\n✓ HTML report generated: {html_path}")

    # Generate JSON report
    json_path = "benchmark_report_demo.json"
    runner.generate_report(results, json_path, format=ReportFormat.JSON)
    print(f"✓ JSON report generated: {json_path}")

    print("\nReports can be viewed in a browser (HTML) or parsed programmatically (JSON)")


async def example_query_exploration():
    """Explore available queries."""
    print("\n" + "=" * 70)
    print("Example 5: Query Exploration")
    print("=" * 70)

    queries = BenchmarkQueries()
    summary = queries.get_summary()

    print(f"\nBenchmark Query Suite:")
    print(f"  Total queries: {summary['total_queries']}")

    print(f"\nBy Complexity:")
    for complexity, count in summary['by_complexity'].items():
        print(f"  {complexity.capitalize()}: {count} queries")

    print(f"\nBy Category:")
    for category, count in sorted(summary['by_category'].items()):
        print(f"  {category}: {count} queries")

    # Show some security queries
    print(f"\nSample Security Queries:")
    security_queries = queries.get_by_category("security")[:5]
    for i, q in enumerate(security_queries, 1):
        print(f"  {i}. {q.name}")
        print(f"     {q.description}")


async def example_performance_comparison():
    """Compare two benchmark runs."""
    print("\n" + "=" * 70)
    print("Example 6: Performance Comparison")
    print("=" * 70)

    config = BenchmarkConfig(
        name="comparison",
        iterations_per_query=5,
        warmup_iterations=1,
        complexities=[QueryComplexity.SIMPLE],
    )

    # Run baseline
    print("\nRunning baseline benchmark...")
    runner = BenchmarkRunner(config=config)
    baseline = await runner.run_all_benchmarks()

    # Run current (in real scenario, this would be after changes)
    print("Running current benchmark...")
    current = await runner.run_all_benchmarks()

    # Compare
    comparison = runner.collector.compare_performance(
        baseline.query_metrics,
        current.query_metrics
    )

    print(f"\nPerformance Comparison:")
    print(f"  P50 change: {comparison['p50_improvement_percent']:+.1f}%")
    print(f"  P95 change: {comparison['p95_improvement_percent']:+.1f}%")
    print(f"  Throughput change: {comparison['throughput_improvement_percent']:+.1f}%")

    if comparison['regression_detected']:
        print(f"\n⚠ Performance regression detected!")
    else:
        print(f"\n✓ No significant regression")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Yellowstone Benchmarking Suite - Examples")
    print("=" * 70)

    try:
        # Example 1: Basic benchmark
        await example_basic_benchmark()

        # Example 2: Filtered benchmark
        await example_filtered_benchmark()

        # Example 3: Single query
        await example_single_query()

        # Example 4: Report generation
        await example_report_generation()

        # Example 5: Query exploration
        await example_query_exploration()

        # Example 6: Performance comparison
        await example_performance_comparison()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
