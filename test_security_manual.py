#!/usr/bin/env python
"""
Manual test of security module to verify functionality.
"""

from src.yellowstone.security import (
    AuditLogger, AuthorizationManager, InjectionDetector, QueryValidator,
    ParameterizedQueryBuilder, Permission, UserContext, SecurityEventType
)
from datetime import datetime

def test_injection_detection():
    """Test injection detection."""
    print("\n=== Testing Injection Detection ===")
    detector = InjectionDetector()

    # Valid query
    result = detector.validate_cypher_query("MATCH (n:Person) RETURN n")
    assert result.is_valid, "Valid query should pass"
    print("✓ Valid query passed validation")

    # Comment injection
    result = detector.validate_cypher_query("MATCH (n) RETURN n // DELETE")
    assert not result.is_valid, "Comment injection should be detected"
    print("✓ Comment injection detected")

    # Null byte injection
    result = detector.validate_parameter("user\x00admin")
    assert not result.is_valid, "Null byte injection should be detected"
    print("✓ Null byte injection detected")

    print("✓ All injection detection tests passed")

def test_authorization():
    """Test authorization."""
    print("\n=== Testing Authorization ===")
    auth = AuthorizationManager()

    # Create user with READ permission
    user = UserContext(
        user_id="user123",
        tenant_id="tenant456",
        permissions={Permission.READ_QUERY},
    )

    # Check permission
    assert auth.has_permission(user, Permission.READ_QUERY)
    print("✓ Permission check passed")

    # Tenant isolation
    assert auth.check_tenant_isolation(user, "tenant456")
    assert not auth.check_tenant_isolation(user, "other_tenant")
    print("✓ Tenant isolation working")

    # Inject tenant filter
    query = "MATCH (n) RETURN n"
    filtered = auth.inject_tenant_filter(query, user)
    assert "tenant456" in filtered
    print("✓ Tenant filter injection working")

    # Define role
    auth.define_role("analyst", {Permission.READ_QUERY, Permission.READ_PROPERTIES})
    auth.assign_role("tenant456", "user123", "analyst")

    context = auth.build_user_context("user123", "tenant456")
    assert Permission.READ_QUERY in context.permissions
    assert Permission.READ_PROPERTIES in context.permissions
    print("✓ Role-based permissions working")

    print("✓ All authorization tests passed")

def test_audit_logging():
    """Test audit logging."""
    print("\n=== Testing Audit Logging ===")
    logger = AuditLogger()

    # Log query execution
    logger.log_query_executed(
        user_id="user123",
        tenant_id="tenant456",
        query="MATCH (n) RETURN n",
        execution_time_ms=45.2,
        rows_affected=100,
    )
    print("✓ Query execution logged")

    # Log injection attempt
    logger.log_injection_attempt(
        user_id="attacker",
        tenant_id="tenant456",
        query="MATCH (n) RETURN n // DELETE",
        detected_pattern="comment_injection",
    )
    print("✓ Injection attempt logged")

    # Log permission denial
    logger.log_permission_denied(
        user_id="user123",
        tenant_id="tenant456",
        query="DELETE (n)",
        required_permission="delete:query",
    )
    print("✓ Permission denial logged")

    # Retrieve events
    events = logger.get_events_by_user("user123")
    assert len(events) >= 2  # Query + permission denial
    print(f"✓ Retrieved {len(events)} events for user123")

    violations = logger.get_security_violations()
    assert len(violations) >= 2  # Injection + permission denial
    print(f"✓ Found {len(violations)} security violations")

    print("✓ All audit logging tests passed")

def test_query_validator():
    """Test query validator."""
    print("\n=== Testing Query Validator ===")
    validator = QueryValidator()

    # Valid query
    result = validator.validate_query("MATCH (n) WHERE n.id = ? RETURN n")
    assert result.is_valid
    print("✓ Valid query passed")

    # Query with injection
    result = validator.validate_query("MATCH (n) RETURN n // DELETE")
    assert not result.is_valid
    print("✓ Injection detected in validation")

    # Query with parameters
    result = validator.validate_query(
        "MATCH (n) WHERE n.name = ? RETURN n",
        parameters={"name": "Alice"}
    )
    assert result.is_valid
    print("✓ Query with parameters validated")

    print("✓ All query validator tests passed")

def test_parameterized_builder():
    """Test parameterized query builder."""
    print("\n=== Testing Parameterized Query Builder ===")
    builder = ParameterizedQueryBuilder()

    # Build property filter
    clause = builder.build_property_filter({"name": "Alice", "age": 30})
    assert "Alice" not in clause  # Value should be parameterized
    assert "$param_" in clause
    print("✓ Property filter built with parameters")

    # Build node match
    builder.reset()
    pattern = builder.build_node_match(
        variable="person",
        label="Person",
        properties={"status": "active"}
    )
    assert "person:Person" in pattern
    assert "active" not in pattern  # Value parameterized
    print("✓ Node match built with parameters")

    # Check parameters
    params = builder.get_parameters()
    assert len(params) > 0
    print(f"✓ Built query with {len(params)} parameters")

    print("✓ All parameterized builder tests passed")

def test_integration():
    """Test complete security pipeline."""
    print("\n=== Testing Complete Security Pipeline ===")

    # Setup
    auth = AuthorizationManager()
    logger = AuditLogger()
    validator = QueryValidator()

    auth.audit_logger = logger

    # Create authenticated user
    user = UserContext(
        user_id="analyst1",
        tenant_id="tenant_prod",
        permissions={Permission.READ_QUERY},
        source_ip="192.168.1.100",
    )

    # Raw query from user
    raw_query = "MATCH (n:Person) WHERE n.status = 'active' RETURN n"

    # Step 1: Validate query
    validation = validator.validate_query(raw_query)
    assert validation.is_valid
    print("✓ Query validation passed")

    # Step 2: Check permission
    assert auth.has_permission(user, Permission.READ_QUERY)
    print("✓ Permission check passed")

    # Step 3: Secure query (inject tenant filter)
    secured_query = auth.secure_query(
        raw_query,
        user=user,
        required_permission=Permission.READ_QUERY,
    )
    assert "tenant_prod" in secured_query
    print("✓ Tenant filter injected")

    # Step 4: Simulate execution and log
    logger.log_query_executed(
        user_id=user.user_id,
        tenant_id=user.tenant_id,
        query=raw_query,
        execution_time_ms=25.5,
        rows_affected=42,
        source_ip=user.source_ip,
    )
    print("✓ Query execution logged")

    # Verify audit trail
    events = logger.get_events_by_user("analyst1")
    assert len(events) > 0

    # Find the query execution event (most recent with execution time)
    event = None
    for e in reversed(events):
        if e.execution_time_ms is not None:
            event = e
            break

    assert event is not None, "Should have logged query execution"
    assert event.user_id == "analyst1"
    assert abs(event.execution_time_ms - 25.5) < 0.01  # Float comparison
    print(f"✓ Audit trail contains query with {event.rows_affected} rows")

    print("✓ Complete security pipeline working")

def main():
    """Run all tests."""
    print("=" * 60)
    print("Security Module Functionality Tests")
    print("=" * 60)

    try:
        test_injection_detection()
        test_authorization()
        test_audit_logging()
        test_query_validator()
        test_parameterized_builder()
        test_integration()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
