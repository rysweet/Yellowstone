"""
Comprehensive audit logging for security tracking.

This module provides comprehensive audit logging capabilities for:
- All queries (Cypher + KQL)
- User tracking
- Performance metrics
- Security events (injection attempts, auth failures, etc.)

The audit logger maintains immutable audit trails for compliance and
forensic analysis.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path
import threading


class SecurityEventType(Enum):
    """Types of security events that can be audited."""
    QUERY_SUBMITTED = "QUERY_SUBMITTED"
    QUERY_EXECUTED = "QUERY_EXECUTED"
    QUERY_FAILED = "QUERY_FAILED"
    INJECTION_ATTEMPT = "INJECTION_ATTEMPT"
    AUTH_FAILURE = "AUTH_FAILURE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TENANT_VIOLATION = "TENANT_VIOLATION"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    PERFORMANCE_WARNING = "PERFORMANCE_WARNING"
    AUDIT_LOG_WRITE = "AUDIT_LOG_WRITE"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    timestamp: str
    event_type: SecurityEventType
    user_id: str
    tenant_id: str
    query: Optional[str] = None
    query_language: Optional[str] = None  # "CYPHER" or "KQL"
    execution_time_ms: Optional[float] = None
    rows_affected: Optional[int] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    security_flags: List[str] = field(default_factory=list)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    result_status: str = "SUCCESS"  # SUCCESS, FAILED, BLOCKED
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling enum conversion."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Comprehensive audit logging for security events.

    This logger maintains immutable audit trails for:
    - Query execution tracking
    - Security event logging
    - Performance monitoring
    - Compliance requirements

    Features:
    - Thread-safe logging
    - Multiple output destinations (file + memory buffer)
    - Structured JSON format for machine processing
    - Query redaction options for sensitive data
    - Automatic log rotation support

    Example:
        >>> logger = AuditLogger(log_file="/var/log/audit.log")
        >>> event = AuditEvent(
        ...     timestamp=datetime.utcnow().isoformat(),
        ...     event_type=SecurityEventType.QUERY_EXECUTED,
        ...     user_id="user123",
        ...     tenant_id="tenant456",
        ...     query="MATCH (a)-[r]->(b) RETURN a, r, b",
        ...     query_language="CYPHER",
        ...     execution_time_ms=45.2,
        ... )
        >>> logger.log_event(event)
        >>> events = logger.get_events_by_user("user123")
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        buffer_size: int = 10000,
        enable_query_redaction: bool = False,
    ):
        """Initialize the audit logger.

        Args:
            log_file: Path to audit log file. If None, uses memory-only buffer.
            buffer_size: Maximum number of events to keep in memory
            enable_query_redaction: If True, redact query contents in some contexts

        Raises:
            PermissionError: If log file cannot be created/written
        """
        self.log_file = log_file
        self.buffer_size = buffer_size
        self.enable_query_redaction = enable_query_redaction
        self.events: List[AuditEvent] = []
        self._lock = threading.RLock()
        self._logger = logging.getLogger("yellowstone.security.audit")

        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Configure file handler
            handler = logging.FileHandler(log_file, mode='a')
            handler.setFormatter(
                logging.Formatter('%(message)s')
            )
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def log_event(self, event: AuditEvent) -> None:
        """Log a security event.

        Args:
            event: The AuditEvent to log

        Raises:
            TypeError: If event is not an AuditEvent instance
        """
        if not isinstance(event, AuditEvent):
            raise TypeError(f"Expected AuditEvent, got {type(event)}")

        with self._lock:
            # Add to in-memory buffer
            self.events.append(event)

            # Maintain buffer size
            if len(self.events) > self.buffer_size:
                self.events = self.events[-self.buffer_size:]

            # Write to file if configured
            if self.log_file:
                self._logger.info(event.to_json())

    def log_query_submitted(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        query_language: str = "CYPHER",
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        security_flags: Optional[List[str]] = None,
    ) -> None:
        """Log a query submission event.

        Args:
            user_id: ID of the user submitting the query
            tenant_id: ID of the tenant
            query: The query string
            query_language: Query language ("CYPHER" or "KQL")
            source_ip: Source IP address
            user_agent: User agent string
            security_flags: List of security flags/warnings
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.QUERY_SUBMITTED,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query if not self.enable_query_redaction else "[REDACTED]",
            query_language=query_language,
            source_ip=source_ip,
            user_agent=user_agent,
            security_flags=security_flags or [],
        )
        self.log_event(event)

    def log_query_executed(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        query_language: str = "CYPHER",
        execution_time_ms: float = 0.0,
        rows_affected: int = 0,
        source_ip: Optional[str] = None,
        security_flags: Optional[List[str]] = None,
    ) -> None:
        """Log a successful query execution.

        Args:
            user_id: ID of the user
            tenant_id: ID of the tenant
            query: The query string
            query_language: Query language
            execution_time_ms: Execution time in milliseconds
            rows_affected: Number of rows affected
            source_ip: Source IP address
            security_flags: Security flags/warnings
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.QUERY_EXECUTED,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query if not self.enable_query_redaction else "[REDACTED]",
            query_language=query_language,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            source_ip=source_ip,
            security_flags=security_flags or [],
            result_status="SUCCESS",
        )
        self.log_event(event)

        # Alert on slow queries
        if execution_time_ms > 5000:  # 5 second threshold
            self.log_performance_warning(
                user_id=user_id,
                tenant_id=tenant_id,
                message=f"Slow query execution: {execution_time_ms}ms",
                query=query,
                execution_time_ms=execution_time_ms,
            )

    def log_query_failed(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        query_language: str = "CYPHER",
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log a query execution failure.

        Args:
            user_id: ID of the user
            tenant_id: ID of the tenant
            query: The query string
            query_language: Query language
            error_message: Error message
            error_type: Type of error
            execution_time_ms: Execution time before failure
            source_ip: Source IP address
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.QUERY_FAILED,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query if not self.enable_query_redaction else "[REDACTED]",
            query_language=query_language,
            error_message=error_message,
            error_type=error_type,
            execution_time_ms=execution_time_ms,
            source_ip=source_ip,
            result_status="FAILED",
        )
        self.log_event(event)

    def log_injection_attempt(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        detected_pattern: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log a suspected injection attack.

        Args:
            user_id: ID of the user
            tenant_id: ID of the tenant
            query: The malicious query string
            detected_pattern: The injection pattern that was detected
            source_ip: Source IP address
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.INJECTION_ATTEMPT,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,  # Log malicious query for forensics
            source_ip=source_ip,
            result_status="BLOCKED",
            additional_context={
                "detected_pattern": detected_pattern,
            },
        )
        self.log_event(event)

    def log_auth_failure(
        self,
        user_id: str,
        tenant_id: str,
        reason: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log an authentication failure.

        Args:
            user_id: ID of the user (if known)
            tenant_id: ID of the tenant
            reason: Reason for auth failure
            source_ip: Source IP address
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.AUTH_FAILURE,
            user_id=user_id,
            tenant_id=tenant_id,
            source_ip=source_ip,
            result_status="BLOCKED",
            additional_context={"reason": reason},
        )
        self.log_event(event)

    def log_permission_denied(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        required_permission: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log a permission denied event.

        Args:
            user_id: ID of the user
            tenant_id: ID of the tenant
            query: The query that was denied
            required_permission: Permission that was required
            source_ip: Source IP address
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.PERMISSION_DENIED,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query if not self.enable_query_redaction else "[REDACTED]",
            source_ip=source_ip,
            result_status="BLOCKED",
            additional_context={"required_permission": required_permission},
        )
        self.log_event(event)

    def log_tenant_violation(
        self,
        user_id: str,
        tenant_id: str,
        accessed_tenant_id: str,
        source_ip: Optional[str] = None,
    ) -> None:
        """Log a tenant isolation violation.

        Args:
            user_id: ID of the user
            tenant_id: ID of the user's tenant
            accessed_tenant_id: ID of the tenant that was illegally accessed
            source_ip: Source IP address
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.TENANT_VIOLATION,
            user_id=user_id,
            tenant_id=tenant_id,
            source_ip=source_ip,
            result_status="BLOCKED",
            additional_context={
                "accessed_tenant_id": accessed_tenant_id,
            },
        )
        self.log_event(event)

    def log_performance_warning(
        self,
        user_id: str,
        tenant_id: str,
        message: str,
        query: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
    ) -> None:
        """Log a performance warning.

        Args:
            user_id: ID of the user
            tenant_id: ID of the tenant
            message: Warning message
            query: The query that triggered the warning
            execution_time_ms: Execution time
        """
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=SecurityEventType.PERFORMANCE_WARNING,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            execution_time_ms=execution_time_ms,
            additional_context={"message": message},
        )
        self.log_event(event)

    def get_events_by_user(
        self,
        user_id: str,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get all events for a specific user.

        Args:
            user_id: The user ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of AuditEvent objects
        """
        with self._lock:
            events = [e for e in self.events if e.user_id == user_id]
            if limit:
                events = events[-limit:]
            return events

    def get_events_by_tenant(
        self,
        tenant_id: str,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get all events for a specific tenant.

        Args:
            tenant_id: The tenant ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of AuditEvent objects
        """
        with self._lock:
            events = [e for e in self.events if e.tenant_id == tenant_id]
            if limit:
                events = events[-limit:]
            return events

    def get_events_by_type(
        self,
        event_type: SecurityEventType,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get all events of a specific type.

        Args:
            event_type: The SecurityEventType to filter by
            limit: Maximum number of events to return

        Returns:
            List of AuditEvent objects
        """
        with self._lock:
            events = [e for e in self.events if e.event_type == event_type]
            if limit:
                events = events[-limit:]
            return events

    def get_security_violations(
        self,
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get all security violation events.

        Args:
            tenant_id: Optional tenant filter
            limit: Maximum number of events to return

        Returns:
            List of security violation events
        """
        violation_types = {
            SecurityEventType.INJECTION_ATTEMPT,
            SecurityEventType.AUTH_FAILURE,
            SecurityEventType.PERMISSION_DENIED,
            SecurityEventType.TENANT_VIOLATION,
        }

        with self._lock:
            events = [
                e for e in self.events
                if e.event_type in violation_types
                and (tenant_id is None or e.tenant_id == tenant_id)
            ]
            if limit:
                events = events[-limit:]
            return events

    def get_slow_queries(
        self,
        threshold_ms: float = 5000,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get queries that exceeded performance threshold.

        Args:
            threshold_ms: Time threshold in milliseconds
            limit: Maximum number of events to return

        Returns:
            List of slow query events
        """
        with self._lock:
            events = [
                e for e in self.events
                if e.execution_time_ms and e.execution_time_ms > threshold_ms
            ]
            if limit:
                events = events[-limit:]
            return events

    def get_user_activity(
        self,
        user_id: str,
        event_types: Optional[List[SecurityEventType]] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get detailed activity for a user.

        Args:
            user_id: The user ID
            event_types: Optional filter by event types
            limit: Maximum number of events to return

        Returns:
            List of AuditEvent objects
        """
        with self._lock:
            events = [e for e in self.events if e.user_id == user_id]

            if event_types:
                events = [e for e in events if e.event_type in event_types]

            if limit:
                events = events[-limit:]

            return events

    def clear_events(self) -> None:
        """Clear all in-memory events.

        Note: This does not affect logged files. Use with caution.
        """
        with self._lock:
            self.events.clear()

    def get_event_count(self) -> int:
        """Get the total number of events in memory.

        Returns:
            Number of events
        """
        with self._lock:
            return len(self.events)

    def get_all_events(self, limit: Optional[int] = None) -> List[AuditEvent]:
        """Get all audit events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of all AuditEvent objects
        """
        with self._lock:
            events = self.events.copy()
            if limit:
                events = events[-limit:]
            return events
