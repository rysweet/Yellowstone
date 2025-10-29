# Security Module

Production-grade security hardening for Yellowstone Cypher query engine.

## Overview

The security module provides comprehensive protection against common attack vectors:

1. **Injection Prevention** - AST-based translation, parameterized queries, input validation
2. **Authorization & Access Control** - Tenant isolation, row-level security, permissions
3. **Audit Logging** - Comprehensive logging of all queries and security events

## Key Principles

### Zero Trust
- Every query is validated
- Every user is authenticated
- Every access is logged
- Every tenant is isolated

### Defense in Depth
- Multiple layers of validation
- Injection detection at multiple points
- Authorization checks before and after query transformation
- Audit trails for forensic analysis

### Never String Concatenation
- All queries built from AST nodes
- All values treated as parameters
- Never embed user input in query strings

## Module Components

### 1. Injection Prevention (`injection_prevention.py`)

Comprehensive protection against injection attacks using:
- **InjectionDetector**: Pattern-based detection of malicious payloads
- **QueryValidator**: Comprehensive query validation with size limits
- **ParameterizedQueryBuilder**: Safe query construction without concatenation

#### Features
- Detects Cypher comment injection (`//`, `/* */`)
- Detects Cypher clause injection (UNION, MATCH, etc.)
- Detects KQL pipeline injection (`|` operators)
- Detects null byte and control character injection
- Detects Unicode escape sequences
- Parameterized queries prevent all injection

#### Usage

```python
from yellowstone.security import InjectionDetector, QueryValidator

# Detect injections
detector = InjectionDetector()
result = detector.validate_cypher_query("MATCH (a) RETURN a")
if not result.is_valid:
    print(f"Injection detected: {result.injection_type}")

# Validate complete queries with parameters
validator = QueryValidator()
result = validator.validate_query(
    query="MATCH (n) WHERE n.id = ? RETURN n",
    query_type="CYPHER",
    parameters={"id": user_input}
)
if not result.is_valid:
    raise ValueError(f"Invalid query: {result.remediation}")

# Build parameterized queries safely
from yellowstone.security import ParameterizedQueryBuilder
builder = ParameterizedQueryBuilder()
clause = builder.build_property_filter({
    "name": user_name,
    "status": user_status,
})
# Returns something like: "name = $param_0 AND status = $param_1"
# Never embeds actual values
```

#### Injection Types

```python
from yellowstone.security import InjectionType

InjectionType.CYPHER_INJECTION          # MATCH, CREATE, DELETE, etc.
InjectionType.KQL_INJECTION             # KQL-specific injection
InjectionType.PARAMETER_INJECTION       # Parameter value injection
InjectionType.ESCAPE_SEQUENCE           # Escape character abuse
InjectionType.COMMENT_INJECTION         # Comment-based injection
InjectionType.NEWLINE_INJECTION         # Newline character abuse
InjectionType.UNICODE_ESCAPE            # Unicode escape sequences
```

### 2. Authorization & Access Control (`authorization.py`)

Comprehensive authorization framework with:
- **AuthorizationManager**: Central authorization enforcement point
- **Permission**: Fine-grained permission system
- **UserContext**: Complete security context for a user
- **RowLevelSecurityPolicy**: RLS policy definition and application

#### Features
- Tenant isolation (automatic filtering)
- Row-level security (customizable policies)
- Role-based access control (RBAC)
- Permission checking
- Audit logging integration

#### Permission Model

```python
from yellowstone.security import Permission

Permission.READ_QUERY          # Can execute read queries
Permission.WRITE_QUERY         # Can execute write queries
Permission.DELETE_QUERY        # Can execute delete queries
Permission.ADMIN_QUERY         # Can execute admin queries
Permission.READ_PROPERTIES     # Can read entity properties
Permission.WRITE_PROPERTIES    # Can write entity properties
Permission.DELETE_ENTITIES     # Can delete entities
Permission.VIEW_AUDIT_LOG      # Can view audit logs
Permission.MANAGE_USERS        # Can manage user permissions
Permission.MANAGE_ROLES        # Can manage roles
```

#### Usage

```python
from yellowstone.security import (
    AuthorizationManager, Permission, UserContext,
    RowLevelSecurityPolicy
)

# Create authorization manager
auth = AuthorizationManager()

# Build user context
user = UserContext(
    user_id="user123",
    tenant_id="tenant456",
    permissions={Permission.READ_QUERY},
    roles=["analyst"],
    source_ip="192.168.1.1",
)

# Check permission
if not auth.has_permission(user, Permission.READ_QUERY):
    raise PermissionError("User lacks READ_QUERY permission")

# Secure a query (tenant filtering + RLS + logging)
secured_query = auth.secure_query(
    query="MATCH (n) RETURN n",
    user=user,
    required_permission=Permission.READ_QUERY,
)
# secured_query now has tenant filter injected automatically

# Define and apply RLS policy
policy = RowLevelSecurityPolicy(
    name="department_filter",
    description="Users see only their department",
    filter_function=lambda u: f"department = '{u.department}'",
    applies_to_roles=["analyst"],
)
auth.add_rls_policy(policy)

# Define roles with permissions
auth.define_role(
    "analyst",
    {Permission.READ_QUERY, Permission.READ_PROPERTIES},
)

# Assign role to user
auth.assign_role("tenant456", "user123", "analyst")

# Build context with inherited role permissions
context = auth.build_user_context("user123", "tenant456")
```

#### Tenant Isolation

Every query automatically includes a tenant filter:

```python
auth = AuthorizationManager()
user = UserContext(user_id="u1", tenant_id="tenant_a")

# Original query
query = "MATCH (n:Person) WHERE n.status = 'active' RETURN n"

# Secured query (tenant filter injected)
secured = auth.inject_tenant_filter(query, user)
# Result: "MATCH (n:Person) WHERE tenant_id = 'tenant_a' AND n.status = 'active' RETURN n"
```

### 3. Audit Logging (`audit_logger.py`)

Comprehensive, immutable audit trail:
- **AuditLogger**: Central audit logging service
- **AuditEvent**: Immutable audit event record
- **SecurityEventType**: Classification of security events

#### Features
- Logs all queries (Cypher + KQL)
- Logs security events (injections, auth failures, permission denials)
- Logs performance metrics
- Thread-safe logging
- File and memory buffering
- Query redaction support
- Forensic analysis support

#### Event Types

```python
from yellowstone.security import SecurityEventType

SecurityEventType.QUERY_SUBMITTED       # Query received
SecurityEventType.QUERY_EXECUTED        # Query executed successfully
SecurityEventType.QUERY_FAILED          # Query execution failed
SecurityEventType.INJECTION_ATTEMPT     # Injection detected
SecurityEventType.AUTH_FAILURE          # Authentication failed
SecurityEventType.PERMISSION_DENIED     # Permission check failed
SecurityEventType.TENANT_VIOLATION      # Cross-tenant access attempt
SecurityEventType.VALIDATION_FAILURE    # Query validation failed
SecurityEventType.PERFORMANCE_WARNING   # Performance threshold exceeded
```

#### Usage

```python
from yellowstone.security import AuditLogger, SecurityEventType

# Create audit logger (file + memory)
logger = AuditLogger(log_file="/var/log/yellowstone/audit.log")

# Log query execution
logger.log_query_executed(
    user_id="user123",
    tenant_id="tenant456",
    query="MATCH (n:Person) RETURN n",
    query_language="CYPHER",
    execution_time_ms=45.2,
    rows_affected=100,
)

# Log injection attempt
logger.log_injection_attempt(
    user_id="attacker",
    tenant_id="tenant456",
    query="MATCH (n) RETURN n // DELETE",
    detected_pattern="comment_injection",
    source_ip="192.168.1.100",
)

# Log permission denial
logger.log_permission_denied(
    user_id="user123",
    tenant_id="tenant456",
    query="MATCH (n:Admin) DELETE (n)",
    required_permission="admin:query",
)

# Retrieve audit trails
user_events = logger.get_events_by_user("user123")
violations = logger.get_security_violations("tenant456")
slow_queries = logger.get_slow_queries(threshold_ms=5000)
injection_attempts = logger.get_events_by_type(
    SecurityEventType.INJECTION_ATTEMPT
)
```

## Integration Example

Complete end-to-end security integration:

```python
from yellowstone.security import (
    AuthorizationManager, InjectionDetector, QueryValidator,
    AuditLogger, Permission, UserContext
)

# Initialize security components
auth = AuthorizationManager()
validator = QueryValidator()
logger = AuditLogger(log_file="/var/log/audit.log")
auth.audit_logger = logger

# Build user from authentication system
user = auth.build_user_context(
    user_id=authenticated_user_id,
    tenant_id=user_tenant_id,
    source_ip=request.remote_addr,
)

# Execute secure query pipeline
try:
    # Step 1: Validate query structure
    validation = validator.validate_query(
        raw_query,
        parameters=user_params,
    )
    if not validation.is_valid:
        logger.log_injection_attempt(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            query=raw_query,
            detected_pattern=validation.detected_pattern,
            source_ip=user.source_ip,
        )
        raise ValueError(f"Query validation failed: {validation.remediation}")

    # Step 2: Apply security controls
    secured_query = auth.secure_query(
        raw_query,
        user=user,
        required_permission=Permission.READ_QUERY,
    )

    # Step 3: Execute secured query
    import time
    start = time.time()
    results = execute_query(secured_query)
    execution_time = (time.time() - start) * 1000

    # Step 4: Log success
    logger.log_query_executed(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        query=raw_query,
        execution_time_ms=execution_time,
        rows_affected=len(results),
        source_ip=user.source_ip,
    )

    return results

except PermissionError as e:
    logger.log_permission_denied(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        query=raw_query,
        required_permission=str(e),
        source_ip=user.source_ip,
    )
    raise

except Exception as e:
    logger.log_query_failed(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        query=raw_query,
        error_message=str(e),
        error_type=type(e).__name__,
        source_ip=user.source_ip,
    )
    raise
```

## Security Best Practices

### 1. Always Use Parameterized Queries
```python
# GOOD - Uses parameters
builder = ParameterizedQueryBuilder()
clause = builder.build_property_filter({"name": user_input})

# BAD - String concatenation
query = f"WHERE name = '{user_input}'"  # NEVER DO THIS
```

### 2. Check Permissions Before Query Execution
```python
# Check permission first
if not auth.check_permission(user, Permission.READ_QUERY):
    raise PermissionError()

# Then execute
result = auth.secure_query(query, user, Permission.READ_QUERY)
```

### 3. Always Inject Tenant Filters
```python
# Apply tenant filter to every query
secured = auth.inject_tenant_filter(query, user)
# Do NOT skip this even if user is trusted
```

### 4. Monitor Audit Logs
```python
# Regular security reviews
violations = logger.get_security_violations()
injection_attempts = logger.get_events_by_type(
    SecurityEventType.INJECTION_ATTEMPT
)

# Implement alerting
for event in violations:
    if event.event_type == SecurityEventType.INJECTION_ATTEMPT:
        send_security_alert(event)
```

### 5. Implement Rate Limiting
```python
# Use audit logs to detect rate limiting violations
user_events = logger.get_events_by_user(user_id)
recent_events = [
    e for e in user_events
    if time_is_recent(e.timestamp, minutes=1)
]

if len(recent_events) > RATE_LIMIT:
    raise RateLimitExceeded()
```

## Testing

Run security tests:

```bash
pytest src/yellowstone/security/tests/test_security.py -v

# Run specific test class
pytest src/yellowstone/security/tests/test_security.py::TestInjectionDetection -v

# Run with coverage
pytest src/yellowstone/security/tests/test_security.py --cov=yellowstone.security
```

## Performance Considerations

### Injection Detection
- Pattern matching: O(n) where n = query length
- Typical overhead: < 1ms for queries < 10KB

### Authorization Checks
- Permission lookup: O(1) hash table access
- Tenant filter injection: O(n) string operation
- Typical overhead: < 0.5ms

### Audit Logging
- In-memory logging: O(1) append
- File logging: Buffered for performance
- Typical overhead: < 0.1ms

## Security Event Response

### Injection Attempt
1. Log event with `log_injection_attempt()`
2. Alert security team
3. Review user activity
4. Consider temporary access suspension

### Permission Denial
1. Log with `log_permission_denied()`
2. Monitor for repeated attempts (possible brute force)
3. Alert if excessive denials from single user

### Tenant Violation
1. Log with `log_tenant_violation()` - CRITICAL
2. Immediately notify security team
3. Disable user account
4. Audit all user queries for data leakage

### Slow Query
1. Log with performance warning
2. Review query optimization
3. Consider query complexity limits

## Compliance & Standards

This security module helps meet:
- OWASP Top 10 (A03:2021 Injection)
- CWE-89 (SQL Injection)
- CWE-90 (Improper Neutralization)
- Data residency requirements (tenant isolation)
- Audit trail requirements (comprehensive logging)

## Troubleshooting

### Query Blocked Due to Injection
```python
# Check what was detected
result = validator.validate_query(query)
print(f"Injection type: {result.injection_type}")
print(f"Detected pattern: {result.detected_pattern}")
print(f"Risk level: {result.risk_level}")
print(f"Remediation: {result.remediation}")
```

### Permission Denied
```python
# Check user permissions
perms = auth.get_user_permissions(tenant_id, user_id)
print(f"Current permissions: {perms}")

# Check user roles
roles = auth.get_user_roles(tenant_id, user_id)
print(f"Current roles: {roles}")

# Check required permission
print(f"Required: {permission}")
```

### Audit Log Missing Events
```python
# Check log file permissions
import os
print(f"Log file readable: {os.access(log_file, os.R_OK)}")
print(f"Log file writable: {os.access(log_file, os.W_OK)}")

# Check in-memory buffer
print(f"Events in buffer: {logger.get_event_count()}")
```

## References

- OWASP: https://owasp.org/www-community/attacks/SQL_Injection
- CWE-89: https://cwe.mitre.org/data/definitions/89.html
- Cypher Injection Prevention: https://neo4j.com/docs/cypher-manual/current/
- KQL Security: https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/index
