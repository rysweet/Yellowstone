"""
Benchmark orchestration and execution.

This module provides the main benchmark runner that orchestrates query execution,
metrics collection, and result aggregation. It supports running individual queries,
query suites, and comparative benchmarks.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
import platform
import sys

from .benchmark_queries import BenchmarkQueries, QueryComplexity, BenchmarkQuery
from .metrics_collector import MetricsCollector, BenchmarkResults, QueryMetrics
from .report_generator import ReportGenerator, ReportFormat


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark execution.

    Attributes:
        name: Name for this benchmark run
        warmup_iterations: Number of warmup queries before measuring
        iterations_per_query: Number of times to run each query
        enable_cache: Whether to enable query result caching
        parallel_execution: Whether to run queries in parallel
        max_parallel_queries: Maximum number of parallel queries
        timeout_seconds: Timeout for individual query execution
        complexities: List of complexity levels to benchmark
        categories: List of categories to benchmark (None = all)
        query_ids: Specific query IDs to run (None = all in complexities/categories)
        collect_system_metrics: Whether to collect system resource metrics
        compare_with_native_kql: Whether to run native KQL for comparison
    """

    name: str = "default"
    warmup_iterations: int = 3
    iterations_per_query: int = 5
    enable_cache: bool = False
    parallel_execution: bool = False
    max_parallel_queries: int = 10
    timeout_seconds: int = 60
    complexities: list[QueryComplexity] = field(
        default_factory=lambda: [
            QueryComplexity.SIMPLE,
            QueryComplexity.MEDIUM,
            QueryComplexity.COMPLEX,
        ]
    )
    categories: Optional[list[str]] = None
    query_ids: Optional[list[str]] = None
    collect_system_metrics: bool = True
    compare_with_native_kql: bool = False


class BenchmarkRunner:
    """Orchestrates benchmark execution and metrics collection.

    Provides methods for running comprehensive benchmarks, individual queries,
    and comparative performance analysis.
    """

    def __init__(
        self,
        config: Optional[BenchmarkConfig] = None,
        translator: Optional[Any] = None,
        executor: Optional[Callable] = None,
    ) -> None:
        """Initialize the benchmark runner.

        Args:
            config: Benchmark configuration (uses defaults if None)
            translator: Cypher-to-KQL translator instance
            executor: Query executor function (for actual execution)
        """
        self.config = config or BenchmarkConfig()
        self.queries = BenchmarkQueries()
        self.collector = MetricsCollector()
        self.translator = translator
        self.executor = executor
        self._cache: dict[str, tuple[list, float]] = {}

    async def run_all_benchmarks(self) -> BenchmarkResults:
        """Run all configured benchmarks.

        Executes all queries matching the configuration filters and returns
        aggregated results.

        Returns:
            BenchmarkResults with all metrics and summaries

        Example:
            >>> runner = BenchmarkRunner()
            >>> results = await runner.run_all_benchmarks()
            >>> print(f"Completed {results.total_queries} queries")
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()

        # Get queries to benchmark
        queries_to_run = self._select_queries()

        print(f"Starting benchmark run: {self.config.name}")
        print(f"Running {len(queries_to_run)} queries with {self.config.iterations_per_query} iterations each")
        print(f"Warmup iterations: {self.config.warmup_iterations}")

        # Reset metrics and cache
        self.collector.reset()
        if not self.config.enable_cache:
            self._cache.clear()

        # Run warmup
        if self.config.warmup_iterations > 0:
            print("Running warmup...")
            await self._run_warmup(queries_to_run[: min(5, len(queries_to_run))])

        # Run benchmarks
        if self.config.parallel_execution:
            await self._run_parallel(queries_to_run)
        else:
            await self._run_sequential(queries_to_run)

        end_time = datetime.now()

        # Create results
        results = BenchmarkResults(
            run_id=run_id,
            run_name=self.config.name,
            start_time=start_time,
            end_time=end_time,
            query_metrics=self.collector.metrics.copy(),
            configuration=self._export_config(),
            environment=self._collect_environment_info(),
        )

        print(f"\nBenchmark complete!")
        print(f"Total queries: {results.total_queries}")
        print(f"Successful: {results.successful_queries}")
        print(f"Failed: {results.failed_queries}")
        print(f"Duration: {results.duration_seconds:.2f}s")

        return results

    async def run_single_query(
        self, query: BenchmarkQuery, iterations: Optional[int] = None
    ) -> list[QueryMetrics]:
        """Run a single benchmark query multiple times.

        Args:
            query: BenchmarkQuery to execute
            iterations: Number of iterations (uses config default if None)

        Returns:
            List of QueryMetrics for each iteration

        Example:
            >>> query = queries.get_by_id("simple_001")
            >>> metrics = await runner.run_single_query(query, iterations=10)
        """
        iterations = iterations or self.config.iterations_per_query
        metrics = []

        for i in range(iterations):
            metric = await self._execute_query(query, iteration=i)
            metrics.append(metric)

        return metrics

    async def compare_with_baseline(
        self, baseline_results: BenchmarkResults
    ) -> dict:
        """Compare current benchmark with baseline results.

        Args:
            baseline_results: Previous benchmark results to compare against

        Returns:
            Comparison dictionary with improvement metrics

        Example:
            >>> baseline = await runner.run_all_benchmarks()
            >>> # Make changes...
            >>> current = await runner.run_all_benchmarks()
            >>> comparison = await runner.compare_with_baseline(baseline)
        """
        current_results = await self.run_all_benchmarks()

        comparison = self.collector.compare_performance(
            baseline_results.query_metrics, current_results.query_metrics
        )

        comparison["baseline_run"] = {
            "run_id": baseline_results.run_id,
            "run_name": baseline_results.run_name,
            "timestamp": baseline_results.start_time.isoformat(),
        }

        comparison["current_run"] = {
            "run_id": current_results.run_id,
            "run_name": current_results.run_name,
            "timestamp": current_results.start_time.isoformat(),
        }

        return comparison

    async def run_stress_test(self, duration_seconds: int = 60) -> BenchmarkResults:
        """Run stress test for specified duration.

        Continuously executes queries for the specified duration to test
        sustained performance.

        Args:
            duration_seconds: How long to run the stress test

        Returns:
            BenchmarkResults from stress test

        Example:
            >>> results = await runner.run_stress_test(duration_seconds=300)
        """
        run_id = str(uuid.uuid4())
        start_time = datetime.now()
        queries_to_run = self._select_queries()

        print(f"Starting stress test for {duration_seconds} seconds...")

        query_index = 0
        iteration = 0

        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            query = queries_to_run[query_index % len(queries_to_run)]
            await self._execute_query(query, iteration=iteration)

            query_index += 1
            iteration += 1

            if iteration % 100 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"Executed {iteration} queries in {elapsed:.1f}s...")

        end_time = datetime.now()

        results = BenchmarkResults(
            run_id=run_id,
            run_name=f"{self.config.name}_stress_test",
            start_time=start_time,
            end_time=end_time,
            query_metrics=self.collector.metrics.copy(),
            configuration=self._export_config(),
            environment=self._collect_environment_info(),
        )

        print(f"Stress test complete! Executed {iteration} queries")
        return results

    def generate_report(
        self, results: BenchmarkResults, output_path: str, format: ReportFormat = ReportFormat.HTML
    ) -> None:
        """Generate benchmark report.

        Args:
            results: BenchmarkResults to report on
            output_path: Path to write report file
            format: Report format (HTML or JSON)

        Example:
            >>> results = await runner.run_all_benchmarks()
            >>> runner.generate_report(results, "report.html")
        """
        generator = ReportGenerator()

        if format == ReportFormat.HTML:
            generator.generate_html_report(results, output_path)
        elif format == ReportFormat.JSON:
            generator.generate_json_report(results, output_path)
        else:
            raise ValueError(f"Unsupported report format: {format}")

        print(f"Report generated: {output_path}")

    async def _execute_query(
        self, query: BenchmarkQuery, iteration: int = 0
    ) -> QueryMetrics:
        """Execute a single query and collect metrics.

        Args:
            query: BenchmarkQuery to execute
            iteration: Iteration number for this execution

        Returns:
            QueryMetrics for this execution
        """
        # Check cache
        cache_hit = False
        if self.config.enable_cache and query.id in self._cache:
            results, translation_time = self._cache[query.id]
            cache_hit = True
            execution_time = 0.0
        else:
            # Translate query
            translation_start = self.collector.start_query_timer()
            try:
                if self.translator:
                    # Use actual translator
                    kql_query = self._translate_query(query.cypher)
                else:
                    # Use provided KQL for benchmarking
                    kql_query = query.kql
                translation_time = (asyncio.get_event_loop().time() - translation_start[0]) * 1000
            except Exception as e:
                # Translation failed
                return self.collector.record_query_metrics(
                    query_id=query.id,
                    query_name=query.name,
                    cypher_query=query.cypher,
                    kql_query="",
                    translation_time_ms=0.0,
                    execution_start_time=translation_start[0],
                    result_count=0,
                    initial_memory_mb=translation_start[1],
                    error=f"Translation error: {str(e)}",
                    metadata={
                        "complexity": query.complexity.value,
                        "category": query.category,
                        "iteration": iteration,
                    },
                )

            # Execute query
            execution_start = self.collector.start_query_timer()
            try:
                if self.executor:
                    # Use actual executor
                    results = await self._execute_kql(kql_query)
                else:
                    # Simulate execution for testing
                    await asyncio.sleep(0.01)  # Simulate 10ms execution
                    results = []

                result_count = len(results) if isinstance(results, list) else 0

                # Cache results
                if self.config.enable_cache:
                    self._cache[query.id] = (results, translation_time)

            except asyncio.TimeoutError:
                return self.collector.record_query_metrics(
                    query_id=query.id,
                    query_name=query.name,
                    cypher_query=query.cypher,
                    kql_query=kql_query,
                    translation_time_ms=translation_time,
                    execution_start_time=execution_start[0],
                    result_count=0,
                    initial_memory_mb=execution_start[1],
                    error=f"Query timeout after {self.config.timeout_seconds}s",
                    metadata={
                        "complexity": query.complexity.value,
                        "category": query.category,
                        "iteration": iteration,
                    },
                )
            except Exception as e:
                return self.collector.record_query_metrics(
                    query_id=query.id,
                    query_name=query.name,
                    cypher_query=query.cypher,
                    kql_query=kql_query,
                    translation_time_ms=translation_time,
                    execution_start_time=execution_start[0],
                    result_count=0,
                    initial_memory_mb=execution_start[1],
                    error=f"Execution error: {str(e)}",
                    metadata={
                        "complexity": query.complexity.value,
                        "category": query.category,
                        "iteration": iteration,
                    },
                )

        # Record successful execution
        return self.collector.record_query_metrics(
            query_id=query.id,
            query_name=query.name,
            cypher_query=query.cypher,
            kql_query=kql_query if not cache_hit else "",
            translation_time_ms=translation_time,
            execution_start_time=execution_start[0] if not cache_hit else asyncio.get_event_loop().time(),
            result_count=result_count,
            initial_memory_mb=execution_start[1] if not cache_hit else 0.0,
            cache_hit=cache_hit,
            metadata={
                "complexity": query.complexity.value,
                "category": query.category,
                "iteration": iteration,
            },
        )

    def _translate_query(self, cypher: str) -> str:
        """Translate Cypher query to KQL using translator.

        Args:
            cypher: Cypher query string

        Returns:
            KQL query string

        Raises:
            Exception: If translation fails
        """
        if not self.translator:
            raise ValueError("No translator configured")

        # This would use the actual translator
        # For now, return placeholder
        return "// Translated KQL query"

    async def _execute_kql(self, kql: str) -> list:
        """Execute KQL query using executor.

        Args:
            kql: KQL query string

        Returns:
            Query results as list

        Raises:
            Exception: If execution fails
        """
        if not self.executor:
            raise ValueError("No executor configured")

        # This would use the actual executor
        # For now, return empty results
        return []

    async def _run_warmup(self, queries: list[BenchmarkQuery]) -> None:
        """Run warmup iterations.

        Args:
            queries: Queries to use for warmup
        """
        for _ in range(self.config.warmup_iterations):
            for query in queries:
                await self._execute_query(query, iteration=-1)

        # Clear warmup metrics
        self.collector.reset()

    async def _run_sequential(self, queries: list[BenchmarkQuery]) -> None:
        """Run queries sequentially.

        Args:
            queries: Queries to execute
        """
        total = len(queries) * self.config.iterations_per_query
        completed = 0

        for query in queries:
            for i in range(self.config.iterations_per_query):
                await self._execute_query(query, iteration=i)
                completed += 1

                if completed % 10 == 0:
                    print(f"Progress: {completed}/{total} queries ({completed/total*100:.1f}%)")

    async def _run_parallel(self, queries: list[BenchmarkQuery]) -> None:
        """Run queries in parallel.

        Args:
            queries: Queries to execute
        """
        tasks = []

        for query in queries:
            for i in range(self.config.iterations_per_query):
                task = asyncio.create_task(self._execute_query(query, iteration=i))
                tasks.append(task)

                # Limit concurrent tasks
                if len(tasks) >= self.config.max_parallel_queries:
                    await asyncio.gather(*tasks)
                    tasks.clear()
                    print(f"Progress: Running parallel batch...")

        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks)

    def _select_queries(self) -> list[BenchmarkQuery]:
        """Select queries based on configuration filters.

        Returns:
            List of queries matching the configuration
        """
        all_queries = self.queries.get_all()

        # Filter by specific IDs if provided
        if self.config.query_ids:
            return [q for q in all_queries if q.id in self.config.query_ids]

        # Filter by complexity
        queries = [q for q in all_queries if q.complexity in self.config.complexities]

        # Filter by category if specified
        if self.config.categories:
            queries = [q for q in queries if q.category in self.config.categories]

        return queries

    def _export_config(self) -> dict:
        """Export configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "name": self.config.name,
            "warmup_iterations": self.config.warmup_iterations,
            "iterations_per_query": self.config.iterations_per_query,
            "enable_cache": self.config.enable_cache,
            "parallel_execution": self.config.parallel_execution,
            "max_parallel_queries": self.config.max_parallel_queries,
            "timeout_seconds": self.config.timeout_seconds,
            "complexities": [c.value for c in self.config.complexities],
            "categories": self.config.categories,
            "query_ids": self.config.query_ids,
            "collect_system_metrics": self.config.collect_system_metrics,
            "compare_with_native_kql": self.config.compare_with_native_kql,
        }

    def _collect_environment_info(self) -> dict:
        """Collect environment information.

        Returns:
            Dictionary with system information
        """
        return {
            "platform": platform.platform(),
            "python_version": sys.version,
            "processor": platform.processor(),
            "cpu_count": platform.os.cpu_count(),
            "hostname": platform.node(),
        }
