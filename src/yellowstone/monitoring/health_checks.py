"""
Health check endpoints for operational status monitoring.

Provides liveness probes, readiness probes, dependency checks, and self-diagnostics
to ensure the system is functioning correctly.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class HealthStatus(Enum):
    """Health check result status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0


class HealthChecker:
    """Base class for implementing health checks."""

    def __init__(self, name: str, timeout_seconds: float = 5.0):
        """Initialize health checker.

        Args:
            name: Name of this health check
            timeout_seconds: Maximum time for check to complete
        """
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.last_result: Optional[CheckResult] = None
        self._lock = threading.RLock()

    def check(self) -> CheckResult:
        """Execute the health check.

        Returns:
            CheckResult with status and details

        Raises:
            NotImplementedError: Must be overridden by subclasses
        """
        raise NotImplementedError("Subclasses must implement check()")

    def get_last_result(self) -> Optional[CheckResult]:
        """Get the last check result.

        Returns:
            Last CheckResult, or None if never run
        """
        with self._lock:
            return self.last_result

    def _set_result(self, result: CheckResult) -> None:
        """Store check result.

        Args:
            result: CheckResult to store
        """
        with self._lock:
            self.last_result = result


class LivenessProbe(HealthChecker):
    """Checks if the service is running and responsive.

    A service is considered alive if it can respond to requests without
    crashing or hanging.
    """

    def __init__(self, timeout_seconds: float = 2.0):
        """Initialize liveness probe.

        Args:
            timeout_seconds: Maximum check duration
        """
        super().__init__("liveness", timeout_seconds)
        self.last_heartbeat = datetime.utcnow()
        self.heartbeat_interval_seconds = 30

    def check(self) -> CheckResult:
        """Check if service is alive.

        Returns:
            Healthy if service is responsive
        """
        start_time = time.time()

        try:
            # Update heartbeat
            self.last_heartbeat = datetime.utcnow()

            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Service is alive and responsive",
                details={"heartbeat": self.last_heartbeat.isoformat()},
                duration_ms=duration_ms,
            )
            self._set_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service liveness check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms,
            )
            self._set_result(result)
            return result


class ReadinessProbe(HealthChecker):
    """Checks if the service is ready to accept traffic.

    A service is ready if it has all dependencies initialized and can
    process requests successfully.
    """

    def __init__(self, timeout_seconds: float = 5.0):
        """Initialize readiness probe.

        Args:
            timeout_seconds: Maximum check duration
        """
        super().__init__("readiness", timeout_seconds)
        self.required_dependencies: List[str] = []
        self.initialized_dependencies: Dict[str, bool] = {}

    def register_dependency(self, name: str) -> None:
        """Register a required dependency.

        Args:
            name: Name of the dependency
        """
        self.required_dependencies.append(name)
        self.initialized_dependencies[name] = False

    def mark_dependency_ready(self, name: str) -> None:
        """Mark a dependency as initialized and ready.

        Args:
            name: Name of the dependency
        """
        if name in self.initialized_dependencies:
            self.initialized_dependencies[name] = True

    def check(self) -> CheckResult:
        """Check if service is ready.

        Returns:
            Healthy if all dependencies are ready
        """
        start_time = time.time()

        try:
            # Check all dependencies
            all_ready = all(self.initialized_dependencies.values())

            if all_ready and self.required_dependencies:
                duration_ms = (time.time() - start_time) * 1000
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Service is ready to accept traffic",
                    details={
                        "dependencies": self.initialized_dependencies,
                    },
                    duration_ms=duration_ms,
                )
            elif not self.required_dependencies:
                # No dependencies required
                duration_ms = (time.time() - start_time) * 1000
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Service is ready (no dependencies)",
                    details={"dependencies": self.initialized_dependencies},
                    duration_ms=duration_ms,
                )
            else:
                # Some dependencies not ready
                unready = [k for k, v in self.initialized_dependencies.items() if not v]
                duration_ms = (time.time() - start_time) * 1000
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message=f"Service not ready: dependencies {unready} not initialized",
                    details={
                        "dependencies": self.initialized_dependencies,
                        "unready": unready,
                    },
                    duration_ms=duration_ms,
                )

            self._set_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service readiness check failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms,
            )
            self._set_result(result)
            return result


class DependencyChecker(HealthChecker):
    """Checks the health of external dependencies."""

    def __init__(self, name: str, check_fn: Callable, timeout_seconds: float = 5.0):
        """Initialize dependency checker.

        Args:
            name: Name of the dependency
            check_fn: Callable that performs the check
            timeout_seconds: Maximum check duration
        """
        super().__init__(f"dependency:{name}", timeout_seconds)
        self.dependency_name = name
        self.check_fn = check_fn

    def check(self) -> CheckResult:
        """Check dependency health.

        Returns:
            CheckResult with dependency status
        """
        start_time = time.time()

        try:
            # Call the check function
            is_healthy = self.check_fn()

            duration_ms = (time.time() - start_time) * 1000

            if is_healthy:
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message=f"Dependency '{self.dependency_name}' is healthy",
                    details={"dependency": self.dependency_name},
                    duration_ms=duration_ms,
                )
            else:
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Dependency '{self.dependency_name}' is unhealthy",
                    details={"dependency": self.dependency_name},
                    duration_ms=duration_ms,
                )

            self._set_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Dependency check failed: {str(e)}",
                details={"error": str(e), "dependency": self.dependency_name},
                duration_ms=duration_ms,
            )
            self._set_result(result)
            return result


class SelfDiagnostics(HealthChecker):
    """Performs self-diagnostics on internal systems."""

    def __init__(self, timeout_seconds: float = 5.0):
        """Initialize self-diagnostics.

        Args:
            timeout_seconds: Maximum check duration
        """
        super().__init__("self_diagnostics", timeout_seconds)
        self.diagnostics: Dict[str, Callable] = {}

    def register_diagnostic(self, name: str, check_fn: Callable) -> None:
        """Register a diagnostic check.

        Args:
            name: Name of the diagnostic
            check_fn: Callable that performs the diagnostic
        """
        self.diagnostics[name] = check_fn

    def check(self) -> CheckResult:
        """Run all self-diagnostics.

        Returns:
            CheckResult with combined diagnostic status
        """
        start_time = time.time()

        try:
            diagnostic_results = {}
            any_failed = False

            for name, check_fn in self.diagnostics.items():
                try:
                    result = check_fn()
                    diagnostic_results[name] = {
                        "status": "ok" if result else "failed",
                        "passed": result,
                    }
                    if not result:
                        any_failed = True
                except Exception as e:
                    diagnostic_results[name] = {
                        "status": "error",
                        "error": str(e),
                    }
                    any_failed = True

            duration_ms = (time.time() - start_time) * 1000

            if any_failed:
                failed_diagnostics = [
                    k for k, v in diagnostic_results.items()
                    if v.get("status") != "ok"
                ]
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message=f"Self-diagnostics: {len(failed_diagnostics)} check(s) failed",
                    details={"diagnostics": diagnostic_results},
                    duration_ms=duration_ms,
                )
            else:
                result = CheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="All self-diagnostics passed",
                    details={"diagnostics": diagnostic_results},
                    duration_ms=duration_ms,
                )

            self._set_result(result)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = CheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Self-diagnostics failed: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration_ms,
            )
            self._set_result(result)
            return result


class HealthCheckManager:
    """Central manager for all health checks."""

    def __init__(self):
        """Initialize health check manager."""
        self.liveness = LivenessProbe()
        self.readiness = ReadinessProbe()
        self.dependency_checkers: Dict[str, DependencyChecker] = {}
        self.self_diagnostics = SelfDiagnostics()
        self._lock = threading.RLock()

    def register_dependency(self, name: str, check_fn: Callable) -> None:
        """Register a dependency to check.

        Args:
            name: Name of the dependency
            check_fn: Callable that returns True if healthy
        """
        with self._lock:
            self.dependency_checkers[name] = DependencyChecker(name, check_fn)
            self.readiness.register_dependency(name)

    def mark_dependency_ready(self, name: str) -> None:
        """Mark a dependency as ready.

        Args:
            name: Name of the dependency
        """
        self.readiness.mark_dependency_ready(name)

    def register_diagnostic(self, name: str, check_fn: Callable) -> None:
        """Register a self-diagnostic check.

        Args:
            name: Name of the diagnostic
            check_fn: Callable that returns True if diagnostic passes
        """
        self.self_diagnostics.register_diagnostic(name, check_fn)

    def check_liveness(self) -> CheckResult:
        """Run liveness check.

        Returns:
            CheckResult for liveness
        """
        return self.liveness.check()

    def check_readiness(self) -> CheckResult:
        """Run readiness check.

        Returns:
            CheckResult for readiness
        """
        return self.readiness.check()

    def check_dependencies(self) -> Dict[str, CheckResult]:
        """Run all dependency checks.

        Returns:
            Dictionary mapping dependency names to CheckResults
        """
        with self._lock:
            results = {}
            for name, checker in self.dependency_checkers.items():
                results[name] = checker.check()
            return results

    def check_diagnostics(self) -> CheckResult:
        """Run self-diagnostics.

        Returns:
            CheckResult for diagnostics
        """
        return self.self_diagnostics.check()

    def get_overall_health(self) -> Dict:
        """Get comprehensive health status.

        Returns:
            Dictionary with all health check results
        """
        liveness = self.check_liveness()
        readiness = self.check_readiness()
        dependencies = self.check_dependencies()
        diagnostics = self.check_diagnostics()

        # Determine overall status
        all_results = [liveness, readiness, diagnostics] + list(dependencies.values())
        statuses = [r.status for r in all_results]

        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "liveness": {
                "status": liveness.status.value,
                "message": liveness.message,
                "duration_ms": liveness.duration_ms,
            },
            "readiness": {
                "status": readiness.status.value,
                "message": readiness.message,
                "duration_ms": readiness.duration_ms,
            },
            "dependencies": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                }
                for name, result in dependencies.items()
            },
            "diagnostics": {
                "status": diagnostics.status.value,
                "message": diagnostics.message,
                "duration_ms": diagnostics.duration_ms,
                "details": diagnostics.details.get("diagnostics", {}),
            },
        }


# Global health check manager instance
_default_manager: Optional[HealthCheckManager] = None


def get_default_manager() -> HealthCheckManager:
    """Get or create default health check manager.

    Returns:
        Global HealthCheckManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = HealthCheckManager()
    return _default_manager


def set_default_manager(manager: HealthCheckManager) -> None:
    """Set the default health check manager.

    Args:
        manager: HealthCheckManager instance to use as default
    """
    global _default_manager
    _default_manager = manager
