"""
Yellowstone Performance Benchmarking Suite.

This module provides comprehensive performance benchmarking tools for measuring
and comparing Cypher-to-KQL translation and execution performance.

Key Components:
    - BenchmarkRunner: Orchestrates benchmark execution
    - BenchmarkQueries: Curated set of 50+ benchmark queries
    - MetricsCollector: Collects and aggregates performance metrics
    - ReportGenerator: Generates HTML/JSON benchmark reports

Target Metrics:
    - P50 latency < 1s
    - P95 latency < 3s
    - P99 latency < 5s
    - 2-5x overhead vs native KQL

Example:
    >>> from yellowstone.benchmarks import BenchmarkRunner
    >>> runner = BenchmarkRunner()
    >>> results = await runner.run_all_benchmarks()
    >>> runner.generate_report(results, "benchmark_report.html")
"""

from .benchmark_runner import BenchmarkRunner, BenchmarkConfig
from .benchmark_queries import BenchmarkQueries, QueryComplexity, BenchmarkQuery
from .metrics_collector import (
    MetricsCollector,
    QueryMetrics,
    BenchmarkResults,
    PerformanceSummary,
)
from .report_generator import ReportGenerator, ReportFormat

__all__ = [
    # Main orchestrator
    "BenchmarkRunner",
    "BenchmarkConfig",
    # Query definitions
    "BenchmarkQueries",
    "QueryComplexity",
    "BenchmarkQuery",
    # Metrics
    "MetricsCollector",
    "QueryMetrics",
    "BenchmarkResults",
    "PerformanceSummary",
    # Reporting
    "ReportGenerator",
    "ReportFormat",
]

__version__ = "0.1.0"
