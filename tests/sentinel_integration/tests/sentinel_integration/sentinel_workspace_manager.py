"""Real Azure Sentinel workspace manager for integration testing.

This module manages the lifecycle of Azure Log Analytics workspaces with
Sentinel enabled, including creation, configuration, and cleanup.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.mgmt.loganalytics import LogAnalyticsManagementClient
from azure.mgmt.securityinsights import SecurityInsights
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from azure.mgmt.loganalytics.models import (
    Workspace,
    WorkspaceSku,
    Table,
    Column,
    ColumnTypeEnum,
    TablePlanEnum
)

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceConfig:
    """Configuration for a Sentinel test workspace."""

    subscription_id: str
    resource_group: str
    workspace_name: str
    location: str = "eastus"
    sku: str = "PerGB2018"
    retention_in_days: int = 30

    def __post_init__(self):
        """Validate configuration."""
        if not self.subscription_id:
            raise ValueError("subscription_id is required")
        if not self.resource_group:
            raise ValueError("resource_group is required")
        if not self.workspace_name:
            raise ValueError("workspace_name is required")


@dataclass
class WorkspaceInfo:
    """Information about a created workspace."""

    workspace_id: str
    workspace_name: str
    resource_group: str
    location: str
    customer_id: str
    created_at: datetime
    custom_tables: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'workspace_id': self.workspace_id,
            'workspace_name': self.workspace_name,
            'resource_group': self.resource_group,
            'location': self.location,
            'customer_id': self.customer_id,
            'created_at': self.created_at.isoformat(),
            'custom_tables': self.custom_tables,
        }


class SentinelWorkspaceManager:
    """Manages Azure Sentinel workspaces for integration testing.

    This class handles the complete lifecycle of test Sentinel workspaces:
    - Creating Log Analytics workspaces
    - Enabling Sentinel (Microsoft.SecurityInsights)
    - Creating custom tables for test data
    - Cleaning up resources

    Example:
        >>> config = WorkspaceConfig(
        ...     subscription_id="sub-123",
        ...     resource_group="rg-test",
        ...     workspace_name="test-sentinel-workspace"
        ... )
        >>> manager = SentinelWorkspaceManager(config)
        >>> workspace = await manager.create_workspace()
        >>> try:
        ...     # Run tests
        ...     pass
        ... finally:
        ...     await manager.cleanup()
    """

    def __init__(
        self,
        config: WorkspaceConfig,
        credential: Optional[DefaultAzureCredential] = None
    ):
        """Initialize workspace manager.

        Args:
            config: Workspace configuration
            credential: Azure credential (uses DefaultAzureCredential if None)
        """
        self.config = config
        self.credential = credential or DefaultAzureCredential()

        # Initialize Azure clients
        self.log_analytics_client = LogAnalyticsManagementClient(
            credential=self.credential,
            subscription_id=config.subscription_id
        )
        self.sentinel_client = SecurityInsights(
            credential=self.credential,
            subscription_id=config.subscription_id
        )
        self.resource_client = ResourceManagementClient(
            credential=self.credential,
            subscription_id=config.subscription_id
        )

        self.workspace_info: Optional[WorkspaceInfo] = None
        self._cleanup_attempted = False

    def ensure_resource_group(self) -> None:
        """Ensure the resource group exists, create if needed."""
        logger.info(f"Ensuring resource group '{self.config.resource_group}' exists")

        try:
            self.resource_client.resource_groups.get(self.config.resource_group)
            logger.info(f"Resource group '{self.config.resource_group}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating resource group '{self.config.resource_group}'")
            self.resource_client.resource_groups.create_or_update(
                self.config.resource_group,
                {'location': self.config.location}
            )
            logger.info(f"Resource group '{self.config.resource_group}' created")

    def create_workspace(self) -> WorkspaceInfo:
        """Create a Log Analytics workspace with Sentinel enabled.

        Returns:
            WorkspaceInfo with details about the created workspace

        Raises:
            HttpResponseError: If workspace creation fails
        """
        logger.info(f"Creating Log Analytics workspace '{self.config.workspace_name}'")

        # Ensure resource group exists
        self.ensure_resource_group()

        # Create workspace
        workspace_params = Workspace(
            location=self.config.location,
            sku=WorkspaceSku(name=self.config.sku),
            retention_in_days=self.config.retention_in_days,
            tags={
                'purpose': 'yellowstone-integration-testing',
                'created_by': 'sentinel_workspace_manager',
                'created_at': datetime.utcnow().isoformat()
            }
        )

        try:
            # Start workspace creation (async operation)
            create_operation = self.log_analytics_client.workspaces.begin_create_or_update(
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace_name,
                parameters=workspace_params
            )

            logger.info("Waiting for workspace creation to complete...")
            workspace = create_operation.result()  # Wait for completion
            logger.info(f"Workspace '{self.config.workspace_name}' created successfully")

            # Get workspace details
            customer_id = workspace.customer_id
            workspace_id = workspace.id

            # Wait for workspace to be fully provisioned
            self._wait_for_workspace_ready(customer_id)

            # Enable Sentinel
            self._enable_sentinel()

            # Store workspace info
            self.workspace_info = WorkspaceInfo(
                workspace_id=workspace_id,
                workspace_name=self.config.workspace_name,
                resource_group=self.config.resource_group,
                location=self.config.location,
                customer_id=customer_id,
                created_at=datetime.utcnow(),
                custom_tables=[]
            )

            logger.info(f"Workspace ready. Customer ID: {customer_id}")
            return self.workspace_info

        except HttpResponseError as e:
            logger.error(f"Failed to create workspace: {e.message}")
            raise

    def _wait_for_workspace_ready(self, customer_id: str, timeout: int = 300) -> None:
        """Wait for workspace to be fully provisioned.

        Args:
            customer_id: Workspace customer ID
            timeout: Maximum wait time in seconds
        """
        logger.info("Waiting for workspace to become ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                workspace = self.log_analytics_client.workspaces.get(
                    resource_group_name=self.config.resource_group,
                    workspace_name=self.config.workspace_name
                )

                if workspace.provisioning_state == "Succeeded":
                    logger.info("Workspace is ready")
                    return

                logger.debug(f"Workspace state: {workspace.provisioning_state}")
                time.sleep(5)

            except Exception as e:
                logger.debug(f"Waiting for workspace: {e}")
                time.sleep(5)

        raise TimeoutError(f"Workspace did not become ready within {timeout} seconds")

    def _enable_sentinel(self) -> None:
        """Enable Azure Sentinel on the workspace."""
        logger.info("Enabling Azure Sentinel...")

        try:
            # Check if Sentinel is already enabled
            try:
                self.sentinel_client.sentinel_onboarding_states.get(
                    resource_group_name=self.config.resource_group,
                    workspace_name=self.config.workspace_name,
                    sentinel_onboarding_state_name="default"
                )
                logger.info("Sentinel already enabled")
                return
            except ResourceNotFoundError:
                pass

            # Enable Sentinel by creating onboarding state
            self.sentinel_client.sentinel_onboarding_states.create(
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace_name,
                sentinel_onboarding_state_name="default",
                sentinel_onboarding_state_parameter={}
            )

            logger.info("Azure Sentinel enabled successfully")

        except Exception as e:
            logger.warning(f"Could not enable Sentinel: {e}")
            # Continue anyway - workspace is still usable for KQL queries

    def create_custom_table(
        self,
        table_name: str,
        columns: List[Dict[str, str]],
        retention_in_days: Optional[int] = None
    ) -> None:
        """Create a custom table in the workspace.

        Args:
            table_name: Name of the table (must end with '_CL')
            columns: List of column definitions [{'name': 'col', 'type': 'string'}, ...]
            retention_in_days: Data retention period (inherits workspace default if None)

        Raises:
            ValueError: If table name is invalid
            HttpResponseError: If table creation fails
        """
        if not table_name.endswith('_CL'):
            raise ValueError("Custom table names must end with '_CL'")

        logger.info(f"Creating custom table '{table_name}'")

        # Convert column definitions
        table_columns = []
        for col in columns:
            col_type = self._map_column_type(col['type'])
            table_columns.append(
                Column(
                    name=col['name'],
                    type=col_type
                )
            )

        # Add TimeGenerated if not present
        if not any(c.name == 'TimeGenerated' for c in table_columns):
            table_columns.insert(0, Column(
                name='TimeGenerated',
                type=ColumnTypeEnum.DATE_TIME
            ))

        # Create table
        table_params = Table(
            retention_in_days=retention_in_days or self.config.retention_in_days,
            plan=TablePlanEnum.ANALYTICS,
            schema={
                'name': table_name,
                'columns': table_columns
            }
        )

        try:
            create_operation = self.log_analytics_client.tables.begin_create_or_update(
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace_name,
                table_name=table_name,
                parameters=table_params
            )

            create_operation.result()  # Wait for completion
            logger.info(f"Custom table '{table_name}' created successfully")

            if self.workspace_info:
                self.workspace_info.custom_tables.append(table_name)

        except HttpResponseError as e:
            logger.error(f"Failed to create table '{table_name}': {e.message}")
            raise

    def _map_column_type(self, type_str: str) -> ColumnTypeEnum:
        """Map string type to ColumnTypeEnum."""
        type_mapping = {
            'string': ColumnTypeEnum.STRING,
            'int': ColumnTypeEnum.INT,
            'long': ColumnTypeEnum.LONG,
            'real': ColumnTypeEnum.REAL,
            'boolean': ColumnTypeEnum.BOOLEAN,
            'datetime': ColumnTypeEnum.DATE_TIME,
            'dynamic': ColumnTypeEnum.DYNAMIC,
            'guid': ColumnTypeEnum.GUID
        }

        return type_mapping.get(type_str.lower(), ColumnTypeEnum.STRING)

    def get_workspace(self) -> Optional[WorkspaceInfo]:
        """Get current workspace info.

        Returns:
            WorkspaceInfo if workspace exists, None otherwise
        """
        if self.workspace_info:
            return self.workspace_info

        # Try to fetch existing workspace
        try:
            workspace = self.log_analytics_client.workspaces.get(
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace_name
            )

            self.workspace_info = WorkspaceInfo(
                workspace_id=workspace.id,
                workspace_name=self.config.workspace_name,
                resource_group=self.config.resource_group,
                location=workspace.location,
                customer_id=workspace.customer_id,
                created_at=datetime.utcnow(),
                custom_tables=[]
            )

            return self.workspace_info

        except ResourceNotFoundError:
            return None

    def cleanup(self, force: bool = False) -> None:
        """Delete the workspace and all associated resources.

        Args:
            force: If True, delete even if cleanup was already attempted

        Raises:
            HttpResponseError: If deletion fails
        """
        if self._cleanup_attempted and not force:
            logger.info("Cleanup already attempted, skipping")
            return

        self._cleanup_attempted = True

        logger.info(f"Cleaning up workspace '{self.config.workspace_name}'")

        try:
            # Delete workspace (this also deletes all tables and data)
            delete_operation = self.log_analytics_client.workspaces.begin_delete(
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace_name,
                force=True  # Permanent deletion
            )

            logger.info("Waiting for workspace deletion...")
            delete_operation.result()  # Wait for completion
            logger.info(f"Workspace '{self.config.workspace_name}' deleted successfully")

            self.workspace_info = None

        except ResourceNotFoundError:
            logger.info(f"Workspace '{self.config.workspace_name}' not found (already deleted)")
        except HttpResponseError as e:
            logger.error(f"Failed to delete workspace: {e.message}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        return False
