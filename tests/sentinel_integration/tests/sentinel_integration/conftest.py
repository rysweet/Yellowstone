"""Pytest fixtures for Azure Sentinel integration tests.

This module provides fixtures for workspace lifecycle management, test data
generation, and Azure client configuration.
"""

import os
import pytest
import logging
from typing import Dict, Any, Generator
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from azure.core.exceptions import ClientAuthenticationError

from .sentinel_workspace_manager import (
    WorkspaceConfig,
    SentinelWorkspaceManager,
    WorkspaceInfo
)
from .test_data_generator import TestDataGenerator
from .data_populator import DataPopulator, WorkspaceKeyRetriever

# Import translator modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cypher_to_kql.translator import CypherToKQLTranslator
from src.cypher_to_kql.schema_mapper import SchemaMapper

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring Azure resources"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (may take minutes to complete)"
    )
    config.addinivalue_line(
        "markers",
        "requires_azure: mark test as requiring Azure credentials and configuration"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if Azure credentials not available."""
    skip_integration = pytest.mark.skip(
        reason="Azure credentials not available or integration tests disabled"
    )

    # Check for Azure credentials
    has_credentials = False
    try:
        # Try to get credentials
        credential = DefaultAzureCredential()
        # Attempt a simple operation to verify credentials work
        has_credentials = True
    except Exception as e:
        logger.warning(f"Azure credentials not available: {e}")

    # Check for required environment variables
    required_vars = [
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_RESOURCE_GROUP',
        'AZURE_LOCATION'
    ]
    has_config = all(os.environ.get(var) for var in required_vars)

    # Check if integration tests are explicitly enabled
    run_integration = os.environ.get('RUN_INTEGRATION_TESTS', '').lower() == 'true'

    if not run_integration:
        logger.info("Integration tests disabled (set RUN_INTEGRATION_TESTS=true to enable)")

    skip_tests = not (has_credentials and has_config and run_integration)

    for item in items:
        if "requires_azure" in item.keywords and skip_tests:
            item.add_marker(skip_integration)


# Configuration fixtures

@pytest.fixture(scope="session")
def azure_credentials() -> DefaultAzureCredential:
    """Provide Azure credentials.

    Uses DefaultAzureCredential which attempts multiple authentication methods:
    - Environment variables
    - Managed identity
    - Azure CLI
    - Visual Studio Code
    - Azure PowerShell

    Returns:
        DefaultAzureCredential instance

    Raises:
        ClientAuthenticationError: If no authentication method succeeds
    """
    try:
        credential = DefaultAzureCredential()
        logger.info("Azure credentials acquired successfully")
        return credential
    except Exception as e:
        logger.error(f"Failed to acquire Azure credentials: {e}")
        pytest.skip(f"Azure credentials not available: {e}")


@pytest.fixture(scope="session")
def azure_config() -> Dict[str, str]:
    """Provide Azure configuration from environment variables.

    Required environment variables:
    - AZURE_SUBSCRIPTION_ID: Azure subscription ID
    - AZURE_RESOURCE_GROUP: Resource group for test resources
    - AZURE_LOCATION: Azure region (e.g., 'eastus')

    Optional:
    - AZURE_WORKSPACE_NAME: Workspace name (generated if not provided)

    Returns:
        Configuration dictionary

    Raises:
        pytest.skip: If required variables are not set
    """
    required_vars = {
        'subscription_id': 'AZURE_SUBSCRIPTION_ID',
        'resource_group': 'AZURE_RESOURCE_GROUP',
        'location': 'AZURE_LOCATION'
    }

    config = {}
    missing = []

    for key, env_var in required_vars.items():
        value = os.environ.get(env_var)
        if value:
            config[key] = value
        else:
            missing.append(env_var)

    if missing:
        pytest.skip(f"Required environment variables not set: {', '.join(missing)}")

    # Optional workspace name
    config['workspace_name'] = os.environ.get(
        'AZURE_WORKSPACE_NAME',
        f"yellowstone-test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    )

    logger.info(f"Azure config: {config}")
    return config


@pytest.fixture(scope="session")
def workspace_key(azure_credentials, azure_config) -> str:
    """Retrieve workspace shared key.

    Requires an existing workspace or will skip if key cannot be retrieved.

    Returns:
        Workspace shared key
    """
    try:
        retriever = WorkspaceKeyRetriever(azure_credentials)
        key = retriever.get_workspace_key(
            subscription_id=azure_config['subscription_id'],
            resource_group=azure_config['resource_group'],
            workspace_name=azure_config['workspace_name']
        )
        logger.info("Workspace key retrieved successfully")
        return key
    except Exception as e:
        logger.warning(f"Could not retrieve workspace key: {e}")
        pytest.skip(f"Workspace key not available: {e}")


# Workspace lifecycle fixtures

@pytest.fixture(scope="session")
def workspace_manager(
    azure_credentials,
    azure_config
) -> Generator[SentinelWorkspaceManager, None, None]:
    """Create workspace manager for session.

    Yields:
        SentinelWorkspaceManager instance

    Cleanup:
        Automatically cleans up workspace after session
    """
    config = WorkspaceConfig(
        subscription_id=azure_config['subscription_id'],
        resource_group=azure_config['resource_group'],
        workspace_name=azure_config['workspace_name'],
        location=azure_config['location']
    )

    manager = SentinelWorkspaceManager(config, azure_credentials)

    yield manager

    # Cleanup
    logger.info("Cleaning up workspace after session")
    try:
        manager.cleanup()
        logger.info("Workspace cleanup complete")
    except Exception as e:
        logger.error(f"Error during workspace cleanup: {e}")


@pytest.fixture(scope="session")
def workspace_info(workspace_manager) -> WorkspaceInfo:
    """Create and configure workspace for session.

    Returns:
        WorkspaceInfo for the created workspace
    """
    logger.info("Creating workspace for test session")
    workspace = workspace_manager.create_workspace()
    logger.info(f"Workspace created: {workspace.workspace_name}")
    return workspace


@pytest.fixture(scope="session")
def workspace_with_tables(workspace_manager) -> WorkspaceInfo:
    """Create workspace with custom tables defined.

    Returns:
        WorkspaceInfo with custom tables created
    """
    workspace = workspace_manager.create_workspace()

    # Define custom tables
    tables = {
        'IdentityInfo_CL': [
            {'name': 'UserId', 'type': 'string'},
            {'name': 'UserPrincipalName', 'type': 'string'},
            {'name': 'DisplayName', 'type': 'string'},
            {'name': 'Department', 'type': 'string'},
            {'name': 'JobTitle', 'type': 'string'},
            {'name': 'Location', 'type': 'string'},
            {'name': 'RiskLevel', 'type': 'string'}
        ],
        'DeviceInfo_CL': [
            {'name': 'DeviceId', 'type': 'string'},
            {'name': 'DeviceName', 'type': 'string'},
            {'name': 'DeviceType', 'type': 'string'},
            {'name': 'OSPlatform', 'type': 'string'},
            {'name': 'OSVersion', 'type': 'string'},
            {'name': 'OwnerUserId', 'type': 'string'},
            {'name': 'Location', 'type': 'string'},
            {'name': 'LastSeen', 'type': 'datetime'}
        ],
        'SignInEvents_CL': [
            {'name': 'EventId', 'type': 'string'},
            {'name': 'UserId', 'type': 'string'},
            {'name': 'UserPrincipalName', 'type': 'string'},
            {'name': 'DeviceId', 'type': 'string'},
            {'name': 'IPAddress', 'type': 'string'},
            {'name': 'Location', 'type': 'string'},
            {'name': 'AppName', 'type': 'string'},
            {'name': 'Result', 'type': 'string'},
            {'name': 'RiskLevel', 'type': 'string'},
            {'name': 'FailureReason', 'type': 'string'}
        ],
        'FileAccessEvents_CL': [
            {'name': 'EventId', 'type': 'string'},
            {'name': 'UserId', 'type': 'string'},
            {'name': 'DeviceId', 'type': 'string'},
            {'name': 'FilePath', 'type': 'string'},
            {'name': 'FileName', 'type': 'string'},
            {'name': 'Action', 'type': 'string'},
            {'name': 'FileHash', 'type': 'string'}
        ],
        'NetworkEvents_CL': [
            {'name': 'EventId', 'type': 'string'},
            {'name': 'DeviceId', 'type': 'string'},
            {'name': 'SourceIP', 'type': 'string'},
            {'name': 'DestinationIP', 'type': 'string'},
            {'name': 'DestinationPort', 'type': 'int'},
            {'name': 'Protocol', 'type': 'string'},
            {'name': 'BytesSent', 'type': 'long'},
            {'name': 'BytesReceived', 'type': 'long'}
        ]
    }

    # Create tables
    for table_name, columns in tables.items():
        logger.info(f"Creating table: {table_name}")
        workspace_manager.create_custom_table(table_name, columns)

    logger.info(f"Created {len(tables)} custom tables")
    return workspace


# Data population fixtures

@pytest.fixture(scope="function")
def test_data_generator() -> TestDataGenerator:
    """Provide test data generator.

    Returns:
        TestDataGenerator with fixed seed for reproducibility
    """
    return TestDataGenerator(seed=42)


@pytest.fixture(scope="function")
def populated_workspace(
    workspace_with_tables,
    workspace_key,
    azure_credentials,
    test_data_generator
) -> WorkspaceInfo:
    """Provide workspace populated with basic test data.

    Returns:
        WorkspaceInfo with data populated
    """
    workspace = workspace_with_tables

    # Generate basic scenario
    scenario = test_data_generator.generate_basic_scenario(num_users=10)

    # Populate workspace
    populator = DataPopulator(workspace, azure_credentials)
    populator.set_workspace_key(workspace_key)

    results = populator.populate_from_generator(scenario)
    populator.verify_ingestion(results)

    logger.info(f"Populated workspace with basic scenario")

    # Wait for data to become available
    populator.wait_for_data_available('IdentityInfo_CL', timeout=120)

    return workspace


@pytest.fixture(scope="function")
def populated_workspace_lateral_movement(
    workspace_with_tables,
    workspace_key,
    azure_credentials,
    test_data_generator
) -> WorkspaceInfo:
    """Provide workspace with lateral movement scenario data.

    Returns:
        WorkspaceInfo with lateral movement data
    """
    workspace = workspace_with_tables

    scenario = test_data_generator.generate_lateral_movement_scenario()

    populator = DataPopulator(workspace, azure_credentials)
    populator.set_workspace_key(workspace_key)

    results = populator.populate_from_generator(scenario)
    populator.verify_ingestion(results)

    logger.info("Populated workspace with lateral movement scenario")

    populator.wait_for_data_available('IdentityInfo_CL', timeout=120)

    return workspace


@pytest.fixture(scope="function")
def populated_workspace_device_ownership(
    workspace_with_tables,
    workspace_key,
    azure_credentials,
    test_data_generator
) -> WorkspaceInfo:
    """Provide workspace with device ownership scenario data.

    Returns:
        WorkspaceInfo with device ownership data
    """
    workspace = workspace_with_tables

    scenario = test_data_generator.generate_device_ownership_scenario()

    populator = DataPopulator(workspace, azure_credentials)
    populator.set_workspace_key(workspace_key)

    results = populator.populate_from_generator(scenario)
    populator.verify_ingestion(results)

    logger.info("Populated workspace with device ownership scenario")

    populator.wait_for_data_available('DeviceInfo_CL', timeout=120)

    return workspace


@pytest.fixture(scope="function")
def populated_workspace_file_access(
    workspace_with_tables,
    workspace_key,
    azure_credentials,
    test_data_generator
) -> WorkspaceInfo:
    """Provide workspace with file access pattern data.

    Returns:
        WorkspaceInfo with file access data
    """
    workspace = workspace_with_tables

    scenario = test_data_generator.generate_file_access_pattern_scenario()

    populator = DataPopulator(workspace, azure_credentials)
    populator.set_workspace_key(workspace_key)

    results = populator.populate_from_generator(scenario)
    populator.verify_ingestion(results)

    logger.info("Populated workspace with file access scenario")

    populator.wait_for_data_available('FileAccessEvents_CL', timeout=120)

    return workspace


# Query client fixtures

@pytest.fixture(scope="session")
def query_client(azure_credentials) -> LogsQueryClient:
    """Provide Azure Monitor Logs Query client.

    Returns:
        LogsQueryClient for executing KQL queries
    """
    client = LogsQueryClient(azure_credentials)
    logger.info("Query client created")
    return client


# Translation fixtures

@pytest.fixture(scope="session")
def schema_mapper() -> SchemaMapper:
    """Provide schema mapper for Cypher-to-KQL translation.

    Returns:
        SchemaMapper configured for Sentinel schema
    """
    mapper = SchemaMapper()

    # Register custom table mappings
    mapper.register_node_table('User', 'IdentityInfo_CL', {
        'id': 'UserId',
        'name': 'DisplayName',
        'email': 'UserPrincipalName',
        'department': 'Department',
        'title': 'JobTitle',
        'location': 'Location',
        'riskLevel': 'RiskLevel'
    })

    mapper.register_node_table('Device', 'DeviceInfo_CL', {
        'id': 'DeviceId',
        'name': 'DeviceName',
        'type': 'DeviceType',
        'os': 'OSPlatform',
        'osVersion': 'OSVersion',
        'owner': 'OwnerUserId',
        'location': 'Location'
    })

    mapper.register_edge_table('SIGNED_IN', 'SignInEvents_CL', {
        'from': 'UserId',
        'to': 'DeviceId',
        'timestamp': 'TimeGenerated',
        'result': 'Result',
        'riskLevel': 'RiskLevel'
    })

    mapper.register_edge_table('ACCESSED', 'FileAccessEvents_CL', {
        'from': 'UserId',
        'to': 'FilePath',
        'action': 'Action',
        'timestamp': 'TimeGenerated'
    })

    mapper.register_edge_table('OWNS', 'DeviceInfo_CL', {
        'from': 'OwnerUserId',
        'to': 'DeviceId'
    })

    logger.info("Schema mapper configured")
    return mapper


@pytest.fixture(scope="session")
def translator(schema_mapper) -> CypherToKQLTranslator:
    """Provide Cypher-to-KQL translator.

    Returns:
        CypherToKQLTranslator configured with schema mapper
    """
    translator = CypherToKQLTranslator(schema_mapper)
    logger.info("Translator created")
    return translator


# Utility fixtures

@pytest.fixture(scope="session")
def integration_test_config() -> Dict[str, Any]:
    """Provide integration test configuration.

    Returns:
        Configuration dictionary with test settings
    """
    return {
        'default_timeout': 300,  # 5 minutes
        'query_timeout': 60,  # 1 minute
        'ingestion_wait_time': 120,  # 2 minutes
        'batch_size': 100,
        'max_retries': 3
    }
