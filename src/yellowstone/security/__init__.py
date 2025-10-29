"""
Security module for Yellowstone.

Provides comprehensive security features:
- Injection attack prevention (AST-based, parameterized queries)
- Authorization and access control (tenant isolation, permissions, RLS)
- Comprehensive audit logging (all queries, security events, performance)

Example:
    >>> from yellowstone.security import (
    ...     InjectionDetector, AuthorizationManager, AuditLogger,
    ...     Permission, UserContext
    ... )
    >>> # Detect injection attacks
    >>> detector = InjectionDetector()
    >>> result = detector.validate_cypher_query("MATCH (a) RETURN a")
    >>> assert result.is_valid
    >>>
    >>> # Manage authorization
    >>> auth = AuthorizationManager()
    >>> user = UserContext(
    ...     user_id="user123",
    ...     tenant_id="tenant456",
    ...     permissions={Permission.READ_QUERY}
    ... )
    >>> auth.check_permission(user, Permission.READ_QUERY)
    True
    >>>
    >>> # Log audit events
    >>> logger = AuditLogger()
    >>> logger.log_query_executed(
    ...     user_id="user123",
    ...     tenant_id="tenant456",
    ...     query="MATCH (a) RETURN a",
    ...     execution_time_ms=45.2
    ... )
"""

from .audit_logger import (
    AuditLogger,
    AuditEvent,
    SecurityEventType,
)
from .authorization import (
    AuthorizationManager,
    Permission,
    UserContext,
    RowLevelSecurityPolicy,
    TenantFilter,
)
from .injection_prevention import (
    InjectionDetector,
    QueryValidator,
    ParameterizedQueryBuilder,
    ValidationResult,
    InjectionType,
    InjectionPattern,
)

__all__ = [
    # Audit logging
    "AuditLogger",
    "AuditEvent",
    "SecurityEventType",
    # Authorization
    "AuthorizationManager",
    "Permission",
    "UserContext",
    "RowLevelSecurityPolicy",
    "TenantFilter",
    # Injection prevention
    "InjectionDetector",
    "QueryValidator",
    "ParameterizedQueryBuilder",
    "ValidationResult",
    "InjectionType",
    "InjectionPattern",
]
