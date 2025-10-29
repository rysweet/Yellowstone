"""
Alert management system for monitoring anomalies and threshold violations.

Provides threshold-based alerts, anomaly detection, alert routing, and integration
with monitoring systems.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import statistics


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Represents a single alert."""
    name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert alert to dictionary.

        Returns:
            Dictionary representation of alert
        """
        return {
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata,
        }


class ThresholdAlert:
    """Generates alerts when metrics exceed thresholds."""

    def __init__(self, name: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Initialize threshold alert.

        Args:
            name: Alert name
            severity: Alert severity level
        """
        self.name = name
        self.severity = severity
        self.threshold: Optional[float] = None
        self.threshold_direction: str = "above"  # "above" or "below"
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown_seconds = 60

    def set_threshold(self, value: float, direction: str = "above") -> None:
        """Set the alert threshold.

        Args:
            value: Threshold value
            direction: "above" or "below"
        """
        self.threshold = value
        self.threshold_direction = direction

    def check(self, current_value: float, metadata: Dict = None) -> Optional[Alert]:
        """Check if current value violates threshold.

        Args:
            current_value: Current metric value
            metadata: Additional metadata for alert

        Returns:
            Alert if threshold violated, None otherwise
        """
        if self.threshold is None:
            return None

        # Check if threshold is violated
        violated = False
        if self.threshold_direction == "above":
            violated = current_value > self.threshold
        else:
            violated = current_value < self.threshold

        if not violated:
            return None

        # Check cooldown to avoid alert spam
        if self.last_alert_time:
            time_since_last = (datetime.utcnow() - self.last_alert_time).total_seconds()
            if time_since_last < self.alert_cooldown_seconds:
                return None

        # Create alert
        self.last_alert_time = datetime.utcnow()

        alert = Alert(
            name=self.name,
            severity=self.severity,
            message=f"{self.name}: {current_value:.2f} ({self.threshold_direction} {self.threshold:.2f})",
            value=current_value,
            threshold=self.threshold,
            metadata=metadata or {},
        )

        return alert


class AnomalyDetector:
    """Detects anomalies using statistical analysis."""

    def __init__(self, name: str, window_size: int = 20, severity: AlertSeverity = AlertSeverity.WARNING):
        """Initialize anomaly detector.

        Args:
            name: Detector name
            window_size: Number of samples to use for baseline
            severity: Alert severity level
        """
        self.name = name
        self.window_size = window_size
        self.severity = severity
        self.values: List[float] = []
        self.std_dev_multiplier = 3.0  # 3-sigma rule
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown_seconds = 60

    def add_value(self, value: float) -> Optional[Alert]:
        """Add value and check for anomalies.

        Args:
            value: Value to add

        Returns:
            Alert if anomaly detected, None otherwise
        """
        self.values.append(value)

        # Keep only recent values
        if len(self.values) > self.window_size * 3:
            self.values = self.values[-self.window_size * 3:]

        if len(self.values) < self.window_size + 5:
            # Not enough data yet
            return None

        # Calculate baseline using older values (exclude last few)
        baseline_values = self.values[:-5]
        if len(baseline_values) < self.window_size:
            return None

        mean = statistics.mean(baseline_values)
        stdev = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0

        if stdev == 0:
            return None

        # Check if current value is anomalous
        z_score = abs(value - mean) / stdev

        if z_score > self.std_dev_multiplier:
            # Check cooldown
            if self.last_alert_time:
                time_since_last = (datetime.utcnow() - self.last_alert_time).total_seconds()
                if time_since_last < self.alert_cooldown_seconds:
                    return None

            self.last_alert_time = datetime.utcnow()

            alert = Alert(
                name=f"{self.name}_anomaly",
                severity=self.severity,
                message=f"Anomaly detected: {value:.2f} (z-score: {z_score:.2f})",
                value=value,
                threshold=mean + (self.std_dev_multiplier * stdev),
                metadata={
                    "mean": mean,
                    "stdev": stdev,
                    "z_score": z_score,
                },
            )
            return alert

        return None

    def get_baseline_stats(self) -> Optional[Dict]:
        """Get current baseline statistics.

        Returns:
            Dictionary with mean, stdev, min, max or None if not enough data
        """
        if len(self.values) < self.window_size:
            return None

        baseline_values = self.values[:-5]
        if len(baseline_values) < 5:
            return None

        return {
            "mean": statistics.mean(baseline_values),
            "stdev": statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0,
            "min": min(baseline_values),
            "max": max(baseline_values),
            "samples": len(baseline_values),
        }


class AlertRouter:
    """Routes alerts to different handlers based on severity and type."""

    def __init__(self):
        """Initialize alert router."""
        self.handlers: Dict[AlertSeverity, List[Callable]] = {
            AlertSeverity.INFO: [],
            AlertSeverity.WARNING: [],
            AlertSeverity.CRITICAL: [],
        }
        self._lock = threading.RLock()

    def register_handler(self, severity: AlertSeverity, handler: Callable) -> None:
        """Register a handler for a severity level.

        Args:
            severity: Severity level to handle
            handler: Callable that takes an Alert
        """
        with self._lock:
            self.handlers[severity].append(handler)

    def route_alert(self, alert: Alert) -> None:
        """Route an alert to appropriate handlers.

        Args:
            alert: Alert to route
        """
        with self._lock:
            handlers = self.handlers.get(alert.severity, [])

        for handler in handlers:
            try:
                handler(alert)
            except Exception:
                pass  # Ignore handler errors


class AlertManager:
    """Central alert management system."""

    def __init__(self):
        """Initialize alert manager."""
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.threshold_alerts: Dict[str, ThresholdAlert] = {}
        self.anomaly_detectors: Dict[str, AnomalyDetector] = {}
        self.router = AlertRouter()
        self._lock = threading.RLock()

    def create_threshold_alert(
        self,
        name: str,
        threshold: float,
        direction: str = "above",
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> ThresholdAlert:
        """Create a threshold-based alert.

        Args:
            name: Alert name
            threshold: Threshold value
            direction: "above" or "below"
            severity: Alert severity

        Returns:
            ThresholdAlert instance
        """
        with self._lock:
            alert = ThresholdAlert(name, severity)
            alert.set_threshold(threshold, direction)
            self.threshold_alerts[name] = alert
            return alert

    def create_anomaly_detector(
        self,
        name: str,
        window_size: int = 20,
        severity: AlertSeverity = AlertSeverity.WARNING,
    ) -> AnomalyDetector:
        """Create an anomaly detector.

        Args:
            name: Detector name
            window_size: Number of samples for baseline
            severity: Alert severity

        Returns:
            AnomalyDetector instance
        """
        with self._lock:
            detector = AnomalyDetector(name, window_size, severity)
            self.anomaly_detectors[name] = detector
            return detector

    def check_threshold_alerts(self, metric_name: str, value: float) -> List[Alert]:
        """Check threshold alerts and generate any active alerts.

        Args:
            metric_name: Name of metric
            value: Current metric value

        Returns:
            List of new alerts
        """
        new_alerts = []

        with self._lock:
            for alert_name, threshold_alert in self.threshold_alerts.items():
                if alert_name.startswith(metric_name):
                    alert = threshold_alert.check(value, {"metric": metric_name})
                    if alert:
                        self.handle_alert(alert)
                        new_alerts.append(alert)

        return new_alerts

    def check_anomalies(self, detector_name: str, value: float) -> Optional[Alert]:
        """Check anomaly detector and generate alert if needed.

        Args:
            detector_name: Name of detector
            value: Value to check

        Returns:
            Alert if anomaly detected, None otherwise
        """
        with self._lock:
            detector = self.anomaly_detectors.get(detector_name)
            if not detector:
                return None

            alert = detector.add_value(value)
            if alert:
                self.handle_alert(alert)

            return alert

    def handle_alert(self, alert: Alert) -> None:
        """Handle a new alert.

        Args:
            alert: Alert to handle
        """
        with self._lock:
            self.active_alerts[alert.name] = alert
            self.alert_history.append(alert)

        # Route alert to handlers
        self.router.route_alert(alert)

    def acknowledge_alert(self, alert_name: str) -> bool:
        """Acknowledge an active alert.

        Args:
            alert_name: Name of alert to acknowledge

        Returns:
            True if alert was acknowledged, False if not found
        """
        with self._lock:
            if alert_name in self.active_alerts:
                self.active_alerts[alert_name].acknowledge()
                return True
            return False

    def resolve_alert(self, alert_name: str) -> bool:
        """Resolve an active alert.

        Args:
            alert_name: Name of alert to resolve

        Returns:
            True if alert was resolved, False if not found
        """
        with self._lock:
            if alert_name in self.active_alerts:
                alert = self.active_alerts.pop(alert_name)
                alert.resolve()
                return True
            return False

    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts.

        Returns:
            List of active alert dictionaries
        """
        with self._lock:
            return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_alert_summary(self) -> Dict:
        """Get summary of alerts.

        Returns:
            Dictionary with alert counts by severity
        """
        with self._lock:
            summary = {
                AlertSeverity.INFO.value: 0,
                AlertSeverity.WARNING.value: 0,
                AlertSeverity.CRITICAL.value: 0,
            }

            for alert in self.active_alerts.values():
                summary[alert.severity.value] += 1

            return {
                "total": len(self.active_alerts),
                "by_severity": summary,
                "total_history": len(self.alert_history),
            }

    def register_alert_handler(self, severity: AlertSeverity, handler: Callable) -> None:
        """Register a handler for alerts.

        Args:
            severity: Severity level to handle
            handler: Callable that takes an Alert
        """
        self.router.register_handler(severity, handler)


# Global alert manager instance
_default_manager: Optional[AlertManager] = None


def get_default_manager() -> AlertManager:
    """Get or create default alert manager.

    Returns:
        Global AlertManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = AlertManager()
    return _default_manager


def set_default_manager(manager: AlertManager) -> None:
    """Set the default alert manager.

    Args:
        manager: AlertManager instance to use as default
    """
    global _default_manager
    _default_manager = manager
