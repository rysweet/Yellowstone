"""
Comprehensive tests for the Yellowstone benchmarking suite.

Tests cover:
- Benchmark query collection and filtering
- Metrics collection and aggregation
- Benchmark runner orchestration
- Report generation
- Performance target validation
"""

import pytest
import asyncio
import tempfile
import json
from datetime import datetime, timedelta

from ..benchmark_queries import (
    BenchmarkQueries,
    QueryComplexity,
    BenchmarkQuery,
)
from ..metrics_collector import (
    MetricsCollector,
    QueryMetrics,
    BenchmarkResults,
    PerformanceSummary,
)
from ..benchmark_runner import BenchmarkRunner, BenchmarkConfig
from ..report_generator import ReportGenerator, ReportFormat


# ============================================================================
# Benchmark Queries Tests
# ============================================================================


class TestBenchmarkQueries:
    """Tests for BenchmarkQueries collection."""

    def test_query_collection_initialization(self) -> None:
        """Test that query collection initializes with queries."""
        queries = BenchmarkQueries()
        all_queries = queries.get_all()

        assert len(all_queries) >= 50, "Should have at least 50 benchmark queries"
        assert all(isinstance(q, BenchmarkQuery) for q in all_queries)

    def test_query_has_required_fields(self) -> None:
        """Test that all queries have required fields."""
        queries = BenchmarkQueries()

        for query in queries.get_all():
            assert query.id, "Query must have ID"
            assert query.name, "Query must have name"
            assert query.cypher, "Query must have Cypher query"
            assert query.kql, "Query must have KQL query"
            assert query.complexity, "Query must have complexity"
            assert query.category, "Query must have category"
            assert query.description, "Query must have description"
            assert isinstance(query.tags, list), "Query must have tags list"

    def test_get_by_complexity(self) -> None:
        """Test filtering queries by complexity."""
        queries = BenchmarkQueries()

        simple = queries.get_by_complexity(QueryComplexity.SIMPLE)
        medium = queries.get_by_complexity(QueryComplexity.MEDIUM)
        complex_ = queries.get_by_complexity(QueryComplexity.COMPLEX)
        stress = queries.get_by_complexity(QueryComplexity.STRESS)

        assert len(simple) > 0, "Should have simple queries"
        assert len(medium) > 0, "Should have medium queries"
        assert len(complex_) > 0, "Should have complex queries"
        assert len(stress) > 0, "Should have stress queries"

        # Verify filtering works correctly
        assert all(q.complexity == QueryComplexity.SIMPLE for q in simple)
        assert all(q.complexity == QueryComplexity.MEDIUM for q in medium)

    def test_get_by_category(self) -> None:
        """Test filtering queries by category."""
        queries = BenchmarkQueries()

        security = queries.get_by_category("security")
        aggregation = queries.get_by_category("aggregation")

        assert len(security) > 0, "Should have security queries"
        assert len(aggregation) > 0, "Should have aggregation queries"

        assert all(q.category == "security" for q in security)
        assert all(q.category == "aggregation" for q in aggregation)

    def test_get_by_tags(self) -> None:
        """Test filtering queries by tags."""
        queries = BenchmarkQueries()

        aggregation_queries = queries.get_by_tags(["aggregation"])
        path_queries = queries.get_by_tags(["path"])

        assert len(aggregation_queries) > 0, "Should have aggregation-tagged queries"
        assert len(path_queries) > 0, "Should have path-tagged queries"

        # Verify tag matching
        for query in aggregation_queries:
            assert "aggregation" in query.tags

    def test_get_by_id(self) -> None:
        """Test getting query by ID."""
        queries = BenchmarkQueries()

        query = queries.get_by_id("simple_001")
        assert query is not None
        assert query.id == "simple_001"

        # Test non-existent ID
        missing = queries.get_by_id("nonexistent")
        assert missing is None

    def test_get_summary(self) -> None:
        """Test query collection summary."""
        queries = BenchmarkQueries()
        summary = queries.get_summary()

        assert "total_queries" in summary
        assert "by_complexity" in summary
        assert "by_category" in summary

        assert summary["total_queries"] >= 50
        assert len(summary["by_complexity"]) > 0
        assert len(summary["by_category"]) > 0

    def test_query_complexity_distribution(self) -> None:
        """Test that queries are well-distributed across complexity levels."""
        queries = BenchmarkQueries()

        simple = len(queries.get_by_complexity(QueryComplexity.SIMPLE))
        medium = len(queries.get_by_complexity(QueryComplexity.MEDIUM))
        complex_ = len(queries.get_by_complexity(QueryComplexity.COMPLEX))
        stress = len(queries.get_by_complexity(QueryComplexity.STRESS))

        # Each complexity should have reasonable representation
        assert simple >= 5, "Should have at least 5 simple queries"
        assert medium >= 5, "Should have at least 5 medium queries"
        assert complex_ >= 5, "Should have at least 5 complex queries"
        assert stress >= 5, "Should have at least 5 stress queries"

    def test_security_queries_coverage(self) -> None:
        """Test that security investigation patterns are well-covered."""
        queries = BenchmarkQueries()

        security_queries = queries.get_by_category("security")
        assert len(security_queries) >= 10, "Should have at least 10 security queries"

        # Check for common security patterns
        tags_found = set()
        for query in security_queries:
            tags_found.update(query.tags)

        expected_tags = {"lateral_movement", "credential", "ransomware", "c2"}
        assert len(expected_tags.intersection(tags_found)) > 0, "Should cover key security patterns"


# ============================================================================
# Metrics Collector Tests
# ============================================================================


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_initialization(self) -> None:
        """Test that collector initializes correctly."""
        collector = MetricsCollector()
        assert len(collector.metrics) == 0

    def test_start_query_timer(self) -> None:
        """Test query timer initialization."""
        collector = MetricsCollector()
        start_time, initial_memory, initial_cpu = collector.start_query_timer()

        assert start_time > 0
        assert initial_memory >= 0
        assert initial_cpu >= 0

    def test_record_query_metrics(self) -> None:
        """Test recording query metrics."""
        collector = MetricsCollector()
        start_time, initial_memory, _ = collector.start_query_timer()

        metrics = collector.record_query_metrics(
            query_id="test_001",
            query_name="Test Query",
            cypher_query="MATCH (n) RETURN n",
            kql_query="table | project *",
            translation_time_ms=10.0,
            execution_start_time=start_time,
            result_count=100,
            initial_memory_mb=initial_memory,
            metadata={"complexity": "simple"},
        )

        assert metrics.query_id == "test_001"
        assert metrics.query_name == "Test Query"
        assert metrics.translation_time_ms == 10.0
        assert metrics.result_count == 100
        assert metrics.success is True
        assert len(collector.metrics) == 1

    def test_record_query_with_error(self) -> None:
        """Test recording failed query metrics."""
        collector = MetricsCollector()
        start_time, initial_memory, _ = collector.start_query_timer()

        metrics = collector.record_query_metrics(
            query_id="test_002",
            query_name="Failing Query",
            cypher_query="MATCH (n) RETURN n",
            kql_query="table | project *",
            translation_time_ms=5.0,
            execution_start_time=start_time,
            result_count=0,
            initial_memory_mb=initial_memory,
            error="Execution failed",
        )

        assert metrics.success is False
        assert metrics.error == "Execution failed"
        assert metrics.result_count == 0

    def test_translation_overhead_ratio(self) -> None:
        """Test translation overhead calculation."""
        metrics = QueryMetrics(
            query_id="test",
            query_name="test",
            cypher_query="",
            kql_query="",
            translation_time_ms=25.0,
            execution_time_ms=75.0,
            total_time_ms=100.0,
            result_count=0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
        )

        assert metrics.translation_overhead_ratio == 0.25

    def test_compute_summary_with_metrics(self) -> None:
        """Test computing summary statistics."""
        collector = MetricsCollector()

        # Add sample metrics
        for i in range(10):
            collector.metrics.append(
                QueryMetrics(
                    query_id=f"test_{i}",
                    query_name=f"Test {i}",
                    cypher_query="",
                    kql_query="",
                    translation_time_ms=10.0 + i,
                    execution_time_ms=90.0 + i * 10,
                    total_time_ms=100.0 + i * 11,
                    result_count=100,
                    memory_usage_mb=50.0,
                    cpu_usage_percent=25.0,
                )
            )

        summary = collector.compute_summary()

        assert summary.total_queries == 10
        assert summary.successful_queries == 10
        assert summary.failed_queries == 0
        assert summary.total_time_p50 > 0
        assert summary.total_time_p95 > 0
        assert summary.total_time_avg > 0
        assert summary.throughput_qps > 0

    def test_compute_summary_no_metrics_raises_error(self) -> None:
        """Test that computing summary with no metrics raises error."""
        collector = MetricsCollector()

        with pytest.raises(ValueError, match="No metrics available"):
            collector.compute_summary()

    def test_percentile_calculation(self) -> None:
        """Test percentile calculation accuracy."""
        collector = MetricsCollector()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        p50 = collector._percentile(values, 50)
        p95 = collector._percentile(values, 95)

        assert 5.0 <= p50 <= 6.0, "P50 should be around median"
        assert p95 >= 9.0, "P95 should be near high end"

    def test_get_metrics_by_complexity(self) -> None:
        """Test filtering metrics by complexity."""
        collector = MetricsCollector()

        collector.metrics.append(
            QueryMetrics(
                query_id="test_1",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=10.0,
                execution_time_ms=90.0,
                total_time_ms=100.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                metadata={"complexity": "simple"},
            )
        )

        collector.metrics.append(
            QueryMetrics(
                query_id="test_2",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=10.0,
                execution_time_ms=90.0,
                total_time_ms=100.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
                metadata={"complexity": "complex"},
            )
        )

        simple = collector.get_metrics_by_complexity("simple")
        complex_ = collector.get_metrics_by_complexity("complex")

        assert len(simple) == 1
        assert len(complex_) == 1

    def test_compare_performance(self) -> None:
        """Test performance comparison between two metric sets."""
        collector = MetricsCollector()

        # Baseline metrics (slower)
        baseline = [
            QueryMetrics(
                query_id=f"test_{i}",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=20.0,
                execution_time_ms=180.0,
                total_time_ms=200.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
            )
            for i in range(10)
        ]

        # Current metrics (faster)
        current = [
            QueryMetrics(
                query_id=f"test_{i}",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=10.0,
                execution_time_ms=90.0,
                total_time_ms=100.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
            )
            for i in range(10)
        ]

        comparison = collector.compare_performance(baseline, current)

        assert comparison["p50_improvement_percent"] > 0, "Should show improvement"
        assert comparison["p95_improvement_percent"] > 0, "Should show improvement"
        assert comparison["regression_detected"] is False

    def test_regression_detection(self) -> None:
        """Test that regression is properly detected."""
        collector = MetricsCollector()

        # Baseline metrics (fast)
        baseline = [
            QueryMetrics(
                query_id=f"test_{i}",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=10.0,
                execution_time_ms=90.0,
                total_time_ms=100.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
            )
            for i in range(10)
        ]

        # Current metrics (much slower - regression)
        current = [
            QueryMetrics(
                query_id=f"test_{i}",
                query_name="Test",
                cypher_query="",
                kql_query="",
                translation_time_ms=50.0,
                execution_time_ms=450.0,
                total_time_ms=500.0,
                result_count=0,
                memory_usage_mb=0.0,
                cpu_usage_percent=0.0,
            )
            for i in range(10)
        ]

        comparison = collector.compare_performance(baseline, current)

        assert comparison["regression_detected"] is True

    def test_export_metrics(self) -> None:
        """Test exporting metrics to dictionaries."""
        collector = MetricsCollector()

        collector.metrics.append(
            QueryMetrics(
                query_id="test_1",
                query_name="Test Query",
                cypher_query="MATCH (n) RETURN n",
                kql_query="table | project *",
                translation_time_ms=10.0,
                execution_time_ms=90.0,
                total_time_ms=100.0,
                result_count=50,
                memory_usage_mb=25.0,
                cpu_usage_percent=15.0,
            )
        )

        exported = collector.export_metrics()

        assert len(exported) == 1
        assert exported[0]["query_id"] == "test_1"
        assert exported[0]["translation_time_ms"] == 10.0
        assert isinstance(exported[0]["timestamp"], str)


# ============================================================================
# Performance Summary Tests
# ============================================================================


class TestPerformanceSummary:
    """Tests for PerformanceSummary."""

    def test_meets_targets_with_good_performance(self) -> None:
        """Test target validation with good performance."""
        summary = PerformanceSummary(
            total_queries=100,
            successful_queries=100,
            failed_queries=0,
            total_time_p50=800.0,  # < 1000ms
            total_time_p95=2500.0,  # < 3000ms
            total_time_p99=4500.0,  # < 5000ms
            total_time_avg=1000.0,
            total_time_min=500.0,
            total_time_max=5000.0,
            translation_time_p50=100.0,
            translation_time_p95=200.0,
            translation_time_avg=120.0,
            execution_time_p50=700.0,
            execution_time_p95=2300.0,
            execution_time_avg=880.0,
            translation_overhead_avg=0.12,
            cache_hit_rate=10.0,
            avg_memory_usage_mb=50.0,
            avg_cpu_usage_percent=25.0,
            throughput_qps=10.0,
        )

        assert summary.meets_targets() is True

    def test_meets_targets_with_poor_performance(self) -> None:
        """Test target validation with poor performance."""
        summary = PerformanceSummary(
            total_queries=100,
            successful_queries=100,
            failed_queries=0,
            total_time_p50=1500.0,  # > 1000ms
            total_time_p95=4000.0,  # > 3000ms
            total_time_p99=6000.0,  # > 5000ms
            total_time_avg=2000.0,
            total_time_min=500.0,
            total_time_max=6000.0,
            translation_time_p50=200.0,
            translation_time_p95=400.0,
            translation_time_avg=240.0,
            execution_time_p50=1300.0,
            execution_time_p95=3600.0,
            execution_time_avg=1760.0,
            translation_overhead_avg=0.12,
            cache_hit_rate=10.0,
            avg_memory_usage_mb=50.0,
            avg_cpu_usage_percent=25.0,
            throughput_qps=5.0,
        )

        assert summary.meets_targets() is False

    def test_translation_overhead_within_target(self) -> None:
        """Test translation overhead validation."""
        # Good overhead (30%)
        summary_good = PerformanceSummary(
            total_queries=10,
            successful_queries=10,
            failed_queries=0,
            total_time_p50=100.0,
            total_time_p95=200.0,
            total_time_p99=300.0,
            total_time_avg=100.0,
            total_time_min=50.0,
            total_time_max=300.0,
            translation_time_p50=30.0,
            translation_time_p95=60.0,
            translation_time_avg=30.0,
            execution_time_p50=70.0,
            execution_time_p95=140.0,
            execution_time_avg=70.0,
            translation_overhead_avg=0.30,
            cache_hit_rate=0.0,
            avg_memory_usage_mb=50.0,
            avg_cpu_usage_percent=25.0,
            throughput_qps=10.0,
        )

        assert summary_good.translation_overhead_within_target() is True

        # Bad overhead (80% - too high)
        summary_bad = PerformanceSummary(
            total_queries=10,
            successful_queries=10,
            failed_queries=0,
            total_time_p50=100.0,
            total_time_p95=200.0,
            total_time_p99=300.0,
            total_time_avg=100.0,
            total_time_min=50.0,
            total_time_max=300.0,
            translation_time_p50=80.0,
            translation_time_p95=160.0,
            translation_time_avg=80.0,
            execution_time_p50=20.0,
            execution_time_p95=40.0,
            execution_time_avg=20.0,
            translation_overhead_avg=0.80,
            cache_hit_rate=0.0,
            avg_memory_usage_mb=50.0,
            avg_cpu_usage_percent=25.0,
            throughput_qps=10.0,
        )

        assert summary_bad.translation_overhead_within_target() is False


# ============================================================================
# Benchmark Runner Tests
# ============================================================================


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""

    def test_runner_initialization(self) -> None:
        """Test that runner initializes with default config."""
        runner = BenchmarkRunner()

        assert runner.config is not None
        assert runner.queries is not None
        assert runner.collector is not None

    def test_runner_with_custom_config(self) -> None:
        """Test runner initialization with custom config."""
        config = BenchmarkConfig(
            name="custom_test",
            iterations_per_query=10,
            enable_cache=True,
        )

        runner = BenchmarkRunner(config=config)

        assert runner.config.name == "custom_test"
        assert runner.config.iterations_per_query == 10
        assert runner.config.enable_cache is True

    @pytest.mark.asyncio
    async def test_run_single_query(self) -> None:
        """Test running a single query."""
        runner = BenchmarkRunner()
        queries = BenchmarkQueries()
        query = queries.get_by_id("simple_001")

        metrics = await runner.run_single_query(query, iterations=3)

        assert len(metrics) == 3
        assert all(m.query_id == query.id for m in metrics)

    @pytest.mark.asyncio
    async def test_run_all_benchmarks(self) -> None:
        """Test running full benchmark suite."""
        config = BenchmarkConfig(
            name="test_run",
            warmup_iterations=1,
            iterations_per_query=2,
            complexities=[QueryComplexity.SIMPLE],
        )

        runner = BenchmarkRunner(config=config)
        results = await runner.run_all_benchmarks()

        assert results.run_name == "test_run"
        assert results.total_queries > 0
        assert results.duration_seconds > 0
        assert len(results.query_metrics) > 0

    @pytest.mark.asyncio
    async def test_query_selection_by_complexity(self) -> None:
        """Test that query selection respects complexity filter."""
        config = BenchmarkConfig(
            complexities=[QueryComplexity.SIMPLE],
            iterations_per_query=1,
            warmup_iterations=0,
        )

        runner = BenchmarkRunner(config=config)
        selected = runner._select_queries()

        assert all(q.complexity == QueryComplexity.SIMPLE for q in selected)

    @pytest.mark.asyncio
    async def test_query_selection_by_category(self) -> None:
        """Test that query selection respects category filter."""
        config = BenchmarkConfig(
            categories=["security"],
            iterations_per_query=1,
            warmup_iterations=0,
        )

        runner = BenchmarkRunner(config=config)
        selected = runner._select_queries()

        assert all(q.category == "security" for q in selected)

    @pytest.mark.asyncio
    async def test_query_selection_by_id(self) -> None:
        """Test that query selection respects ID filter."""
        config = BenchmarkConfig(
            query_ids=["simple_001", "simple_002"],
            iterations_per_query=1,
            warmup_iterations=0,
        )

        runner = BenchmarkRunner(config=config)
        selected = runner._select_queries()

        assert len(selected) == 2
        assert all(q.id in ["simple_001", "simple_002"] for q in selected)

    def test_export_config(self) -> None:
        """Test configuration export."""
        config = BenchmarkConfig(name="test", iterations_per_query=5)
        runner = BenchmarkRunner(config=config)

        exported = runner._export_config()

        assert exported["name"] == "test"
        assert exported["iterations_per_query"] == 5
        assert "complexities" in exported

    def test_collect_environment_info(self) -> None:
        """Test environment information collection."""
        runner = BenchmarkRunner()
        env_info = runner._collect_environment_info()

        assert "platform" in env_info
        assert "python_version" in env_info
        assert "cpu_count" in env_info


# ============================================================================
# Report Generator Tests
# ============================================================================


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generator_initialization(self) -> None:
        """Test that generator initializes."""
        generator = ReportGenerator()
        assert generator.collector is not None

    def test_generate_html_report(self) -> None:
        """Test HTML report generation."""
        # Create sample results
        results = self._create_sample_results()

        generator = ReportGenerator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            output_path = f.name

        try:
            generator.generate_html_report(results, output_path)

            # Verify file was created and has content
            with open(output_path, "r") as f:
                content = f.read()
                assert len(content) > 0
                assert "<!DOCTYPE html>" in content
                assert results.run_name in content
                assert "Performance Summary" in content
        finally:
            import os
            os.unlink(output_path)

    def test_generate_json_report(self) -> None:
        """Test JSON report generation."""
        results = self._create_sample_results()

        generator = ReportGenerator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            generator.generate_json_report(results, output_path)

            # Verify file was created and is valid JSON
            with open(output_path, "r") as f:
                data = json.load(f)
                assert data["run_name"] == results.run_name
                assert "summary" in data
                assert "query_metrics" in data
        finally:
            import os
            os.unlink(output_path)

    def test_summary_to_dict(self) -> None:
        """Test converting summary to dictionary."""
        summary = PerformanceSummary(
            total_queries=100,
            successful_queries=95,
            failed_queries=5,
            total_time_p50=800.0,
            total_time_p95=2500.0,
            total_time_p99=4500.0,
            total_time_avg=1000.0,
            total_time_min=500.0,
            total_time_max=5000.0,
            translation_time_p50=100.0,
            translation_time_p95=200.0,
            translation_time_avg=120.0,
            execution_time_p50=700.0,
            execution_time_p95=2300.0,
            execution_time_avg=880.0,
            translation_overhead_avg=0.12,
            cache_hit_rate=10.0,
            avg_memory_usage_mb=50.0,
            avg_cpu_usage_percent=25.0,
            throughput_qps=10.0,
        )

        generator = ReportGenerator()
        summary_dict = generator._summary_to_dict(summary)

        assert summary_dict["total_queries"] == 100
        assert summary_dict["successful_queries"] == 95
        assert "latency" in summary_dict
        assert "targets" in summary_dict

    def _create_sample_results(self) -> BenchmarkResults:
        """Create sample benchmark results for testing."""
        metrics = [
            QueryMetrics(
                query_id=f"test_{i}",
                query_name=f"Test Query {i}",
                cypher_query="MATCH (n) RETURN n",
                kql_query="table | project *",
                translation_time_ms=10.0 + i,
                execution_time_ms=90.0 + i * 10,
                total_time_ms=100.0 + i * 11,
                result_count=100,
                memory_usage_mb=50.0,
                cpu_usage_percent=25.0,
                metadata={"complexity": "simple", "category": "test"},
            )
            for i in range(20)
        ]

        return BenchmarkResults(
            run_id="test-run-123",
            run_name="Test Benchmark",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=60),
            query_metrics=metrics,
            configuration={"test": True},
            environment={"platform": "test"},
        )


# ============================================================================
# Integration Tests
# ============================================================================


class TestBenchmarkIntegration:
    """Integration tests for the complete benchmark suite."""

    @pytest.mark.asyncio
    async def test_end_to_end_benchmark_workflow(self) -> None:
        """Test complete benchmark workflow from execution to report."""
        # Configure benchmark
        config = BenchmarkConfig(
            name="integration_test",
            warmup_iterations=1,
            iterations_per_query=2,
            complexities=[QueryComplexity.SIMPLE],
        )

        # Run benchmark
        runner = BenchmarkRunner(config=config)
        results = await runner.run_all_benchmarks()

        # Verify results
        assert results.total_queries > 0
        assert results.duration_seconds > 0

        # Generate reports
        generator = ReportGenerator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as html_file:
            html_path = html_file.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as json_file:
            json_path = json_file.name

        try:
            generator.generate_html_report(results, html_path)
            generator.generate_json_report(results, json_path)

            # Verify reports exist
            import os
            assert os.path.exists(html_path)
            assert os.path.exists(json_path)
            assert os.path.getsize(html_path) > 0
            assert os.path.getsize(json_path) > 0
        finally:
            import os
            os.unlink(html_path)
            os.unlink(json_path)

    @pytest.mark.asyncio
    async def test_performance_comparison_workflow(self) -> None:
        """Test comparing two benchmark runs."""
        config = BenchmarkConfig(
            name="comparison_test",
            warmup_iterations=0,
            iterations_per_query=5,
            query_ids=["simple_001", "simple_002"],
        )

        runner = BenchmarkRunner(config=config)

        # Run baseline
        baseline = await runner.run_all_benchmarks()

        # Run current (same config for testing)
        current = await runner.run_all_benchmarks()

        # Compare
        comparison = runner.collector.compare_performance(
            baseline.query_metrics, current.query_metrics
        )

        assert "p50_improvement_percent" in comparison
        assert "p95_improvement_percent" in comparison
        assert "regression_detected" in comparison
