"""
Authorization and access control.

This module provides:
- Tenant isolation (inject tenant filters into queries)
- Row-level security (RLS)
- User permission checking
- Audit logging for all queries

Key principle: Every query is automatically filtered to the user's
tenant and respects their permissions. Tenant data is never leaked.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Set, Any, Callable
from abc import ABC, abstractmethod

from .audit_logger import AuditLogger, SecurityEventType


class Permission(Enum):
    """User permissions in the system."""
    READ_QUERY = "read:query"
    WRITE_QUERY = "write:query"
    DELETE_QUERY = "delete:query"
    ADMIN_QUERY = "admin:query"
    READ_PROPERTIES = "read:properties"
    WRITE_PROPERTIES = "write:properties"
    DELETE_ENTITIES = "delete:entities"
    VIEW_AUDIT_LOG = "view:audit_log"
    MANAGE_USERS = "manage:users"
    MANAGE_ROLES = "manage:roles"


@dataclass
class UserContext:
    """Security context for a user."""
    user_id: str
    tenant_id: str
    permissions: Set[Permission] = field(default_factory=set)
    roles: List[str] = field(default_factory=list)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission.

        Args:
            permission: The permission to check

        Returns:
            True if user has permission, False otherwise
        """
        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has any permission, False otherwise
        """
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if user has all permissions, False otherwise
        """
        return all(p in self.permissions for p in permissions)


@dataclass
class TenantFilter:
    """Represents a tenant isolation filter to inject into queries."""
    tenant_id: str
    filter_clause: str  # e.g., "WHERE tenant_id = $tenant_id"
    parameter_name: str = "tenant_id"
    parameter_value: str = None

    def __post_init__(self):
        """Initialize parameter value if not set."""
        if self.parameter_value is None:
            self.parameter_value = self.tenant_id


@dataclass
class RowLevelSecurityPolicy:
    """Defines row-level security rules for data access."""
    name: str
    description: str
    filter_function: Callable[[UserContext], str]  # Returns WHERE clause
    applies_to_roles: List[str] = field(default_factory=list)
    applies_to_permissions: List[Permission] = field(default_factory=list)

    def get_filter(self, user_context: UserContext) -> Optional[str]:
        """Get the RLS filter for this user.

        Args:
            user_context: The user's security context

        Returns:
            WHERE clause to append to query, or None if not applicable
        """
        # Check if policy applies to user's roles
        if self.applies_to_roles and not any(
            role in user_context.roles for role in self.applies_to_roles
        ):
            return None

        # Check if policy applies to user's permissions
        if self.applies_to_permissions and not user_context.has_any_permission(
            self.applies_to_permissions
        ):
            return None

        # Apply the filter function
        return self.filter_function(user_context)


class AuthorizationManager:
    """Manages authorization, permissions, and access control.

    This manager:
    - Enforces tenant isolation
    - Checks user permissions
    - Applies row-level security
    - Logs all access for audit

    Example:
        >>> auth = AuthorizationManager()
        >>> user = UserContext(
        ...     user_id="user123",
        ...     tenant_id="tenant456",
        ...     permissions={Permission.READ_QUERY},
        ... )
        >>> # Check permission
        >>> assert auth.has_permission(user, Permission.READ_QUERY)
        >>> # Add RLS policy
        >>> policy = RowLevelSecurityPolicy(
        ...     name="department_filter",
        ...     description="Users can only see their department",
        ...     filter_function=lambda u: f"WHERE department = '{u.department}'",
        ... )
        >>> auth.add_rls_policy(policy)
    """

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """Initialize the authorization manager.

        Args:
            audit_logger: Optional AuditLogger for logging access events
        """
        self.audit_logger = audit_logger
        self.rls_policies: Dict[str, RowLevelSecurityPolicy] = {}
        self.user_permissions: Dict[str, Dict[str, Set[Permission]]] = {}  # tenant -> user -> perms
        self.user_roles: Dict[str, Dict[str, List[str]]] = {}  # tenant -> user -> roles
        self.role_permissions: Dict[str, Set[Permission]] = {}  # role -> perms

    def has_permission(
        self,
        user: UserContext,
        permission: Permission,
    ) -> bool:
        """Check if user has a specific permission.

        Args:
            user: User security context
            permission: The permission to check

        Returns:
            True if user has permission, False otherwise
        """
        return user.has_permission(permission)

    def check_permission(
        self,
        user: UserContext,
        permission: Permission,
        query: str,
    ) -> bool:
        """Check permission and log the result.

        Args:
            user: User security context
            permission: The permission to check
            query: The query being attempted (for logging)

        Returns:
            True if user has permission, False otherwise
        """
        has_perm = self.has_permission(user, permission)

        if not has_perm and self.audit_logger:
            self.audit_logger.log_permission_denied(
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                query=query,
                required_permission=permission.value,
                source_ip=user.source_ip,
            )

        return has_perm

    def check_tenant_isolation(
        self,
        user: UserContext,
        accessed_tenant_id: str,
    ) -> bool:
        """Check if user can access a specific tenant.

        Args:
            user: User security context
            accessed_tenant_id: Tenant being accessed

        Returns:
            True if access allowed, False otherwise

        Raises:
            ValueError: If tenant violation is detected
        """
        if user.tenant_id != accessed_tenant_id:
            if self.audit_logger:
                self.audit_logger.log_tenant_violation(
                    user_id=user.user_id,
                    tenant_id=user.tenant_id,
                    accessed_tenant_id=accessed_tenant_id,
                    source_ip=user.source_ip,
                )
            return False
        return True

    def inject_tenant_filter(
        self,
        query: str,
        user: UserContext,
    ) -> str:
        """Inject tenant isolation filter into query.

        This automatically adds a WHERE clause to limit query results
        to the user's tenant. This is the fundamental mechanism that
        prevents cross-tenant data leakage.

        Args:
            query: Original query string
            user: User security context

        Returns:
            Modified query with tenant filter injected

        Example:
            >>> manager = AuthorizationManager()
            >>> user = UserContext(user_id="u1", tenant_id="t1")
            >>> query = "MATCH (n) RETURN n"
            >>> filtered = manager.inject_tenant_filter(query, user)
            >>> assert "tenant_id" in filtered or "t1" in filtered
        """
        # Format: append tenant filter before RETURN clause
        # This is simplified - real implementation would use AST manipulation

        # If query already has WHERE, append with AND
        if " WHERE " in query.upper():
            # Find WHERE clause and append condition
            insert_pos = query.upper().find(" WHERE ") + len(" WHERE ")
            tenant_clause = f"tenant_id = '{user.tenant_id}' AND "
            return query[:insert_pos] + tenant_clause + query[insert_pos:]
        else:
            # Insert WHERE clause before RETURN
            if " RETURN " in query.upper():
                insert_pos = query.upper().find(" RETURN ")
                tenant_clause = f" WHERE tenant_id = '{user.tenant_id}'"
                return query[:insert_pos] + tenant_clause + query[insert_pos:]
            else:
                # No RETURN clause found, append at end
                tenant_clause = f" WHERE tenant_id = '{user.tenant_id}'"
                return query + tenant_clause

    def apply_row_level_security(
        self,
        query: str,
        user: UserContext,
    ) -> str:
        """Apply row-level security policies to query.

        Args:
            query: Original query
            user: User security context

        Returns:
            Modified query with RLS filters applied
        """
        rls_filters = []

        # Check each RLS policy
        for policy in self.rls_policies.values():
            filter_clause = policy.get_filter(user)
            if filter_clause:
                rls_filters.append(filter_clause)

        # If no RLS policies apply, return original query
        if not rls_filters:
            return query

        # Combine all RLS filters
        combined_filter = " AND ".join(rls_filters)

        # Apply to query
        if " WHERE " in query.upper():
            insert_pos = query.upper().find(" WHERE ") + len(" WHERE ")
            return query[:insert_pos] + combined_filter + " AND " + query[insert_pos:]
        else:
            if " RETURN " in query.upper():
                insert_pos = query.upper().find(" RETURN ")
                return query[:insert_pos] + f" WHERE {combined_filter}" + query[insert_pos:]
            else:
                return query + f" WHERE {combined_filter}"

    def secure_query(
        self,
        query: str,
        user: UserContext,
        required_permission: Optional[Permission] = None,
    ) -> str:
        """Apply all security controls to a query.

        This method:
        1. Checks permissions
        2. Injects tenant filter
        3. Applies row-level security
        4. Logs the access

        Args:
            query: Original query
            user: User security context
            required_permission: Required permission to execute query

        Returns:
            Secured query with filters injected

        Raises:
            PermissionError: If user lacks required permission
        """
        # Check permission if specified
        if required_permission:
            if not self.check_permission(user, required_permission, query):
                raise PermissionError(
                    f"User {user.user_id} lacks permission {required_permission.value}"
                )

        # Inject tenant filter (fundamental security)
        secured_query = self.inject_tenant_filter(query, user)

        # Apply row-level security
        secured_query = self.apply_row_level_security(secured_query, user)

        # Log access
        if self.audit_logger:
            self.audit_logger.log_query_submitted(
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                query=query,
                source_ip=user.source_ip,
                user_agent=user.user_agent,
            )

        return secured_query

    def add_rls_policy(self, policy: RowLevelSecurityPolicy) -> None:
        """Register a row-level security policy.

        Args:
            policy: The RLS policy to add

        Raises:
            ValueError: If policy name already exists
        """
        if policy.name in self.rls_policies:
            raise ValueError(f"RLS policy '{policy.name}' already exists")

        self.rls_policies[policy.name] = policy

    def remove_rls_policy(self, policy_name: str) -> None:
        """Remove a row-level security policy.

        Args:
            policy_name: Name of policy to remove

        Raises:
            KeyError: If policy doesn't exist
        """
        del self.rls_policies[policy_name]

    def grant_permission(
        self,
        tenant_id: str,
        user_id: str,
        permission: Permission,
    ) -> None:
        """Grant a permission to a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            permission: Permission to grant
        """
        if tenant_id not in self.user_permissions:
            self.user_permissions[tenant_id] = {}

        if user_id not in self.user_permissions[tenant_id]:
            self.user_permissions[tenant_id][user_id] = set()

        self.user_permissions[tenant_id][user_id].add(permission)

    def revoke_permission(
        self,
        tenant_id: str,
        user_id: str,
        permission: Permission,
    ) -> None:
        """Revoke a permission from a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            permission: Permission to revoke
        """
        if tenant_id in self.user_permissions:
            if user_id in self.user_permissions[tenant_id]:
                self.user_permissions[tenant_id][user_id].discard(permission)

    def get_user_permissions(
        self,
        tenant_id: str,
        user_id: str,
    ) -> Set[Permission]:
        """Get all permissions for a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Set of Permission objects
        """
        return self.user_permissions.get(tenant_id, {}).get(user_id, set()).copy()

    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        role: str,
    ) -> None:
        """Assign a role to a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            role: Role to assign
        """
        if tenant_id not in self.user_roles:
            self.user_roles[tenant_id] = {}

        if user_id not in self.user_roles[tenant_id]:
            self.user_roles[tenant_id][user_id] = []

        if role not in self.user_roles[tenant_id][user_id]:
            self.user_roles[tenant_id][user_id].append(role)

    def revoke_role(
        self,
        tenant_id: str,
        user_id: str,
        role: str,
    ) -> None:
        """Revoke a role from a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            role: Role to revoke
        """
        if tenant_id in self.user_roles:
            if user_id in self.user_roles[tenant_id]:
                if role in self.user_roles[tenant_id][user_id]:
                    self.user_roles[tenant_id][user_id].remove(role)

    def get_user_roles(
        self,
        tenant_id: str,
        user_id: str,
    ) -> List[str]:
        """Get all roles for a user.

        Args:
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            List of role names
        """
        return self.user_roles.get(tenant_id, {}).get(user_id, []).copy()

    def define_role(
        self,
        role_name: str,
        permissions: Set[Permission],
    ) -> None:
        """Define a new role with specific permissions.

        Args:
            role_name: Name of the role
            permissions: Set of permissions for this role
        """
        self.role_permissions[role_name] = permissions.copy()

    def get_role_permissions(self, role_name: str) -> Set[Permission]:
        """Get permissions for a role.

        Args:
            role_name: Name of the role

        Returns:
            Set of permissions
        """
        return self.role_permissions.get(role_name, set()).copy()

    def build_user_context(
        self,
        user_id: str,
        tenant_id: str,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserContext:
        """Build a complete user context with permissions.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            source_ip: Source IP address
            user_agent: User agent string

        Returns:
            UserContext with all permissions and roles populated
        """
        # Get user's permissions
        permissions = self.get_user_permissions(tenant_id, user_id)

        # Get user's roles
        roles = self.get_user_roles(tenant_id, user_id)

        # Add permissions from roles
        for role in roles:
            role_perms = self.get_role_permissions(role)
            permissions.update(role_perms)

        return UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=permissions,
            roles=roles,
            source_ip=source_ip,
            user_agent=user_agent,
        )
