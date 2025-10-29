"""
Comprehensive tests for load testing and stress testing frameworks.

Tests cover:
- Load profile configuration and validation
- Query executor functionality
- Load testing execution and metrics collection
- Stress testing scenarios
- Resource monitoring
- Recovery metrics
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from ..load_profiles import (
    LoadProfile,
    LightLoadProfile,
    MediumLoadProfile,
    HeavyLoadProfile,
    StressLoadProfile,
    RampLoadProfile,
    SpikeLoadProfile,
    QueryComplexity,
    get_load_profile,
    load_profile_registry,
)

from ..load_tester import (
    LoadTester,
    QueryExecutor,
    LoadTestResult,
    LoadTestMetrics,
    LatencyStatistics,
    QueryType,
    ResourceSnapshot,
)

from ..stress_tester import (
    StressTester,
    StressTestResult,
    BreakingPoint,
    RecoveryMetrics,
    StressType,
)


# ============================================================================
# Load Profile Tests (6 tests)
# ============================================================================

class TestLoadProfiles:
    """Tests for load profile implementations."""

    def test_light_load_profile(self):
        """Test light load profile configuration."""
        profile = LightLoadProfile()
        assert profile.name == "light"
        assert profile.target_qps == 10
        assert profile.duration_seconds == 300
        assert profile.max_concurrent_queries == 20

    def test_medium_load_profile(self):
        """Test medium load profile configuration."""
        profile = MediumLoadProfile()
        assert profile.name == "medium"
        assert profile.target_qps == 50
        assert profile.duration_seconds == 600
        assert profile.max_concurrent_queries == 75

    def test_heavy_load_profile(self):
        """Test heavy load profile configuration."""
        profile = HeavyLoadProfile()
        assert profile.name == "heavy"
        assert profile.target_qps == 100
        assert profile.duration_seconds == 900
        assert profile.max_concurrent_queries == 150

    def test_stress_load_profile(self):
        """Test stress load profile configuration."""
        profile = StressLoadProfile()
        assert profile.name == "stress"
        assert profile.target_qps == 200
        assert profile.duration_seconds == 1200
        assert profile.max_concurrent_queries == 300

    def test_ramp_load_profile(self):
        """Test ramp load profile with linear ramp-up."""
        profile = RampLoadProfile()
        assert profile.name == "ramp"
        assert profile.target_qps == 150
        # Ramp-up time equals duration, full ramp over test period
        assert profile.ramp_up_seconds == profile.duration_seconds

    def test_spike_load_profile(self):
        """Test spike load profile with traffic spikes."""
        profile = SpikeLoadProfile()
        assert profile.name == "spike"
        assert profile.target_qps == 250
        assert profile.baseline_qps == 10
        assert profile.spike_duration_seconds == 10


# ============================================================================
# Load Profile Behavior Tests (5 tests)
# ============================================================================

class TestLoadProfileBehavior:
    """Tests for load profile behavior and calculations."""

    def test_qps_ramp_up(self):
        """Test QPS ramp-up during initial phase."""
        profile = LightLoadProfile()
        assert profile.get_qps_at_time(0) == 0
        assert profile.get_qps_at_time(1) < profile.target_qps
        assert profile.get_qps_at_time(profile.ramp_up_seconds) == profile.target_qps

    def test_qps_steady_state(self):
        """Test QPS during steady state after ramp-up."""
        profile = LightLoadProfile()
        steady_qps = profile.get_qps_at_time(profile.ramp_up_seconds + 10)
        assert steady_qps == profile.target_qps

    def test_spike_profile_qps_pattern(self):
        """Test spike profile generates correct QPS pattern."""
        profile = SpikeLoadProfile()
        # During spike phase
        spike_qps = profile.get_qps_at_time(5)
        assert spike_qps > profile.baseline_qps
        assert spike_qps <= profile.target_qps

    def test_query_distribution(self):
        """Test query distribution calculation."""
        profile = MediumLoadProfile()
        dist = profile.get_query_distribution()
        assert dist["simple"] == 50
        assert dist["medium"] == 40
        assert dist["complex"] == 10
        assert sum(dist.values()) == 100

    def test_profile_validation_success(self):
        """Test profile validation passes for valid profiles."""
        profile = MediumLoadProfile()
        errors = profile.validate()
        assert len(errors) == 0

    def test_profile_validation_invalid_percentages(self):
        """Test profile validation catches invalid percentages."""
        profile = LoadProfile(
            name="invalid",
            target_qps=50,
            duration_seconds=300,
            simple_query_percent=50,
            medium_query_percent=30,
            complex_query_percent=15,  # Sum != 100
        )
        errors = profile.validate()
        assert len(errors) > 0
        assert "sum to 100" in errors[0]


# ============================================================================
# Load Profile Registry Tests (2 tests)
# ============================================================================

class TestLoadProfileRegistry:
    """Tests for load profile registry and retrieval."""

    def test_get_load_profile(self):
        """Test retrieving profiles from registry."""
        for profile_name in ["light", "medium", "heavy", "stress", "ramp", "spike"]:
            profile = get_load_profile(profile_name)
            assert profile.name == profile_name

    def test_invalid_profile_name(self):
        """Test error when requesting unknown profile."""
        with pytest.raises(ValueError):
            get_load_profile("invalid_profile_name")


# ============================================================================
# Query Executor Tests (5 tests)
# ============================================================================

class TestQueryExecutor:
    """Tests for query execution and timing."""

    @pytest.mark.asyncio
    async def test_successful_query_execution(self):
        """Test successful query execution records latency."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.01)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        success, latency_ms, error = await executor.execute("SELECT *", "simple")

        assert success is True
        assert latency_ms >= 10
        assert error is None

    @pytest.mark.asyncio
    async def test_failed_query_execution(self):
        """Test failed query execution records error."""
        async def mock_execute(query, complexity):
            raise ValueError("Test error")

        executor = QueryExecutor(mock_execute)
        success, latency_ms, error = await executor.execute("SELECT *", "simple")

        assert success is False
        assert latency_ms > 0
        assert error is not None
        assert "Test error" in error

    @pytest.mark.asyncio
    async def test_latency_statistics(self):
        """Test latency statistics calculation."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.01)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)

        # Execute multiple queries
        for _ in range(10):
            await executor.execute("SELECT *", "simple")

        stats = executor.get_statistics()
        assert stats.min_ms > 0
        assert stats.max_ms >= stats.min_ms
        assert stats.mean_ms > 0
        assert stats.median_ms > 0
        assert stats.p95_ms > 0
        assert stats.p99_ms > 0

    def test_latency_statistics_empty(self):
        """Test latency statistics with no data."""
        async def mock_execute(query, complexity):
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        stats = executor.get_statistics()

        assert stats.min_ms == 0
        assert stats.max_ms == 0
        assert stats.mean_ms == 0

    @pytest.mark.asyncio
    async def test_thread_safe_execution(self):
        """Test concurrent query execution is thread-safe."""
        call_count = 0
        lock = asyncio.Lock()

        async def mock_execute(query, complexity):
            nonlocal call_count
            async with lock:
                call_count += 1
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)

        # Execute multiple queries concurrently
        tasks = [
            executor.execute("SELECT *", "simple")
            for _ in range(20)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert call_count == 20
        assert all(r[0] for r in results)  # All successful


# ============================================================================
# Load Test Result Tests (3 tests)
# ============================================================================

class TestLoadTestResult:
    """Tests for load test result tracking."""

    def test_load_test_result_creation(self):
        """Test creating load test result."""
        start = datetime.utcnow()
        end = start + timedelta(seconds=60)

        metrics = LoadTestMetrics(
            total_queries=1000,
            successful_queries=950,
            failed_queries=50,
            success_rate=0.95,
            total_duration_seconds=60,
            actual_qps=16.67,
            latency_stats=LatencyStatistics(
                min_ms=1.0,
                max_ms=100.0,
                mean_ms=50.0,
                median_ms=45.0,
                p95_ms=90.0,
                p99_ms=95.0,
                std_dev_ms=20.0,
            ),
        )

        result = LoadTestResult(
            profile_name="medium",
            start_time=start,
            end_time=end,
            metrics=metrics,
        )

        assert result.profile_name == "medium"
        assert result.duration_seconds == 60
        assert result.metrics.success_rate == 0.95

    def test_load_test_result_string_representation(self):
        """Test string representation of load test result."""
        start = datetime.utcnow()
        end = start + timedelta(seconds=60)

        metrics = LoadTestMetrics(
            total_queries=100,
            successful_queries=100,
            failed_queries=0,
            success_rate=1.0,
            total_duration_seconds=60,
            actual_qps=1.67,
            latency_stats=LatencyStatistics(
                min_ms=1.0, max_ms=10.0, mean_ms=5.0, median_ms=5.0,
                p95_ms=9.0, p99_ms=9.5, std_dev_ms=2.0,
            ),
        )

        result = LoadTestResult(
            profile_name="light",
            start_time=start,
            end_time=end,
            metrics=metrics,
        )

        result_str = str(result)
        assert "medium" in result_str.lower() or "light" in result_str.lower()

    def test_latency_statistics_string_representation(self):
        """Test string representation of latency statistics."""
        stats = LatencyStatistics(
            min_ms=1.0, max_ms=100.0, mean_ms=50.0, median_ms=45.0,
            p95_ms=90.0, p99_ms=95.0, std_dev_ms=20.0,
        )

        stats_str = str(stats)
        assert "Min" in stats_str
        assert "Max" in stats_str
        assert "Mean" in stats_str


# ============================================================================
# Load Tester Tests (6 tests)
# ============================================================================

class TestLoadTester:
    """Tests for load testing orchestration."""

    @pytest.mark.asyncio
    async def test_load_tester_initialization(self):
        """Test load tester initialization."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {
            "simple": ["q1", "q2"],
            "medium": ["q3", "q4"],
            "complex": ["q5", "q6"],
        }

        tester = LoadTester(executor, sample_queries)
        assert tester.active_queries == 0
        assert len(tester.resource_snapshots) == 0

    @pytest.mark.asyncio
    async def test_run_load_test_light_profile(self):
        """Test running load test with light profile."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {
            "simple": ["q1"],
            "medium": ["q2"],
            "complex": ["q3"],
        }

        tester = LoadTester(executor, sample_queries, resource_sampling_interval=5.0)
        profile = LightLoadProfile()

        result = await tester.run_test(profile)

        assert result.profile_name == "light"
        assert result.metrics.total_queries > 0
        assert result.metrics.success_rate >= 0.5

    @pytest.mark.asyncio
    async def test_load_test_with_failures(self):
        """Test load test with some query failures."""
        call_count = 0

        async def mock_execute(query, complexity):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise ValueError("Simulated failure")
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {"simple": ["q1"], "medium": ["q2"], "complex": ["q3"]}

        tester = LoadTester(executor, sample_queries, resource_sampling_interval=5.0)
        profile = LightLoadProfile()

        result = await tester.run_test(profile)

        assert result.metrics.failed_queries > 0
        assert result.metrics.success_rate < 1.0

    @pytest.mark.asyncio
    async def test_resource_monitoring(self):
        """Test resource monitoring during load test."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {"simple": ["q1"], "medium": ["q2"], "complex": ["q3"]}

        tester = LoadTester(executor, sample_queries, resource_sampling_interval=0.5)
        profile = LightLoadProfile()

        result = await tester.run_test(profile)

        assert result.metrics.peak_memory_mb > 0
        assert len(result.metrics.resource_snapshots) > 0

    @pytest.mark.asyncio
    async def test_query_distribution_tracking(self):
        """Test query distribution tracking."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {"simple": ["q1"], "medium": ["q2"], "complex": ["q3"]}

        tester = LoadTester(executor, sample_queries, resource_sampling_interval=5.0)
        profile = MediumLoadProfile()

        result = await tester.run_test(profile)

        # Check query distribution was tracked
        assert "simple" in result.metrics.query_distribution
        assert result.metrics.query_distribution["simple"] > 0

    @pytest.mark.asyncio
    async def test_invalid_profile_raises_error(self):
        """Test invalid profile raises validation error."""
        async def mock_execute(query, complexity):
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {"simple": ["q1"]}

        tester = LoadTester(executor, sample_queries)

        # Create invalid profile
        invalid_profile = LoadProfile(
            name="invalid",
            target_qps=50,
            duration_seconds=300,
            simple_query_percent=50,
            medium_query_percent=30,
            complex_query_percent=15,  # Invalid: sum != 100
        )

        with pytest.raises(ValueError):
            await tester.run_test(invalid_profile)


# ============================================================================
# Stress Tester Tests (5 tests)
# ============================================================================

class TestStressTester:
    """Tests for stress testing orchestration."""

    def test_stress_tester_initialization(self):
        """Test stress tester initialization."""
        async def mock_execute(query, complexity):
            return {"status": "success"}

        sample_queries = {"complex": ["q1"]}

        tester = StressTester(mock_execute, sample_queries)
        assert tester.active_queries == 0
        assert tester.total_queries == 0
        assert tester.total_errors == 0

    @pytest.mark.asyncio
    async def test_steady_increase_stress(self):
        """Test steady increase stress test."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        sample_queries = {"complex": ["q1"]}

        tester = StressTester(mock_execute, sample_queries, resource_sampling_interval=5.0)
        result = await tester.run_steady_increase_stress(
            start_qps=10,
            increment_qps=10,
            step_duration_seconds=1,
            max_qps=50,
        )

        assert result.stress_type == StressType.STEADY_INCREASE.value
        assert result.total_queries_executed > 0
        assert result.peak_qps > 0

    @pytest.mark.asyncio
    async def test_memory_pressure_test(self):
        """Test memory pressure stress test."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        sample_queries = {"complex": ["q1"]}

        tester = StressTester(mock_execute, sample_queries, resource_sampling_interval=5.0)
        result = await tester.run_memory_pressure_test(
            target_qps=20,
            duration_seconds=2,
            memory_target_mb=999999,  # Very high to avoid triggering
        )

        assert result.stress_type == StressType.MEMORY_PRESSURE.value
        assert result.total_queries_executed > 0

    @pytest.mark.asyncio
    async def test_spike_storm_test(self):
        """Test spike storm stress test."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        sample_queries = {"complex": ["q1"]}

        tester = StressTester(mock_execute, sample_queries, resource_sampling_interval=5.0)
        result = await tester.run_spike_storm_test(
            baseline_qps=5,
            spike_qps=20,
            spike_count=2,
            spike_duration_seconds=1,
            recovery_timeout_seconds=1,
        )

        assert result.stress_type == StressType.SPIKE_STORM.value
        assert result.total_queries_executed > 0

    @pytest.mark.asyncio
    async def test_stress_test_with_failures(self):
        """Test stress test handles query failures."""
        call_count = 0

        async def mock_execute(query, complexity):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise ValueError("Simulated failure")
            await asyncio.sleep(0.001)
            return {"status": "success"}

        sample_queries = {"complex": ["q1"]}

        tester = StressTester(mock_execute, sample_queries, resource_sampling_interval=5.0)
        result = await tester.run_steady_increase_stress(
            start_qps=10,
            increment_qps=5,
            step_duration_seconds=1,
            max_qps=30,
        )

        assert result.total_errors > 0
        assert result.success_rate < 1.0


# ============================================================================
# Stress Result Tests (3 tests)
# ============================================================================

class TestStressTestResult:
    """Tests for stress test result tracking."""

    def test_stress_test_result_creation(self):
        """Test creating stress test result."""
        start = datetime.utcnow()
        end = start + timedelta(seconds=60)

        result = StressTestResult(
            stress_type=StressType.STEADY_INCREASE.value,
            start_time=start,
            end_time=end,
            peak_qps=500,
            total_queries_executed=1000,
            total_errors=50,
            success_rate=0.95,
            peak_memory_mb=512.0,
            peak_cpu_percent=75.0,
        )

        assert result.stress_type == StressType.STEADY_INCREASE.value
        assert result.duration_seconds == 60
        assert result.peak_qps == 500

    def test_breaking_point_creation(self):
        """Test creating breaking point."""
        bp = BreakingPoint(
            qps_at_break=300,
            time_to_break_seconds=45.5,
            memory_mb_at_break=1024.5,
            cpu_percent_at_break=95.0,
            error_message="Error rate exceeded: 15%",
        )

        assert bp.qps_at_break == 300
        assert bp.time_to_break_seconds == 45.5
        assert "Error rate exceeded" in bp.error_message

    def test_recovery_metrics_creation(self):
        """Test creating recovery metrics."""
        recovery = RecoveryMetrics(
            recovery_start_time=datetime.utcnow(),
            time_to_recover_seconds=30.0,
            error_rate_before=0.15,
            error_rate_after=0.01,
            latency_before_ms=1000.0,
            latency_after_ms=100.0,
            successful=True,
        )

        assert recovery.time_to_recover_seconds == 30.0
        assert recovery.error_rate_before > recovery.error_rate_after
        assert recovery.successful is True


# ============================================================================
# Resource Monitoring Tests (2 tests)
# ============================================================================

class TestResourceMonitoring:
    """Tests for resource monitoring functionality."""

    def test_resource_snapshot_creation(self):
        """Test creating resource snapshot."""
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            memory_mb=256.5,
            cpu_percent=45.0,
            active_queries=10,
            thread_count=5,
        )

        assert snapshot.memory_mb == 256.5
        assert snapshot.cpu_percent == 45.0
        assert snapshot.active_queries == 10

    @pytest.mark.asyncio
    async def test_resource_monitoring_accuracy(self):
        """Test resource monitoring records values over time."""
        async def mock_execute(query, complexity):
            await asyncio.sleep(0.001)
            return {"status": "success"}

        executor = QueryExecutor(mock_execute)
        sample_queries = {"simple": ["q1"]}

        tester = LoadTester(executor, sample_queries, resource_sampling_interval=0.2)
        profile = LightLoadProfile()

        result = await tester.run_test(profile)

        # Verify multiple samples were collected
        assert len(result.metrics.resource_snapshots) > 1

        # Verify snapshots have monotonic timestamps
        for i in range(1, len(result.metrics.resource_snapshots)):
            ts1 = result.metrics.resource_snapshots[i - 1].timestamp
            ts2 = result.metrics.resource_snapshots[i].timestamp
            assert ts2 >= ts1
