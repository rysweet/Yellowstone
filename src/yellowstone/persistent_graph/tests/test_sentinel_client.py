"""
Integration tests for real Azure Sentinel API client.

These tests can run against a real Sentinel workspace when proper
credentials are configured via environment variables.

Environment variables:
    SENTINEL_WORKSPACE_ID: Azure Log Analytics workspace ID
    AZURE_CLIENT_ID: Service principal client ID (optional)
    AZURE_CLIENT_SECRET: Service principal secret (optional)
    AZURE_TENANT_ID: Azure tenant ID (optional)

If service principal variables are not set, DefaultAzureCredential will be used.
"""

import os
import pytest
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.core.exceptions import HttpResponseError, ServiceRequestError

from ..sentinel_client import (
    SentinelClient,
    SentinelConfig,
    SentinelAPIError,
    AuthenticationError,
    QueryExecutionError,
    WorkspaceNotFoundError,
)


# Configuration for integration tests
WORKSPACE_ID = os.getenv('SENTINEL_WORKSPACE_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
TENANT_ID = os.getenv('AZURE_TENANT_ID')

# Skip integration tests if workspace ID not configured
pytestmark = pytest.mark.skipif(
    not WORKSPACE_ID,
    reason="SENTINEL_WORKSPACE_ID environment variable not set"
)


@pytest.fixture
def mock_credential():
    """Create a mock Azure credential."""
    return Mock(spec=DefaultAzureCredential)


@pytest.fixture
def mock_logs_client():
    """Create a mock LogsQueryClient."""
    return Mock(spec=LogsQueryClient)


@pytest.fixture
def sentinel_client(mock_credential):
    """Create a SentinelClient with mocked dependencies for unit tests."""
    with patch('yellowstone.persistent_graph.sentinel_client.LogsQueryClient') as mock_client_class:
        mock_client = Mock(spec=LogsQueryClient)
        mock_client_class.return_value = mock_client

        client = SentinelClient(
            workspace_id='test-workspace-id',
            credential=mock_credential
        )
        client._client = mock_client
        return client


def get_real_credential():
    """Get real Azure credential for integration tests."""
    if CLIENT_ID and CLIENT_SECRET and TENANT_ID:
        return ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
    else:
        return DefaultAzureCredential()


class TestSentinelClientInitialization:
    """Test SentinelClient initialization and validation."""

    def test_init_requires_workspace_id(self, mock_credential):
        """Test that workspace_id is required."""
        with pytest.raises(ValueError, match="workspace_id is required"):
            SentinelClient(workspace_id='', credential=mock_credential)

        with pytest.raises(ValueError, match="workspace_id is required"):
            SentinelClient(workspace_id='   ', credential=mock_credential)

    def test_init_with_explicit_credential(self, mock_credential):
        """Test initialization with explicit credential."""
        with patch('yellowstone.persistent_graph.sentinel_client.LogsQueryClient'):
            client = SentinelClient(
                workspace_id='test-workspace',
                credential=mock_credential
            )
            assert client.workspace_id == 'test-workspace'
            assert client.credential == mock_credential

    def test_init_with_default_credential(self):
        """Test initialization with DefaultAzureCredential."""
        with patch('yellowstone.persistent_graph.sentinel_client.DefaultAzureCredential') as mock_default_cred:
            with patch('yellowstone.persistent_graph.sentinel_client.LogsQueryClient'):
                mock_default_cred.return_value = Mock()
                client = SentinelClient(workspace_id='test-workspace')
                assert client.workspace_id == 'test-workspace'
                mock_default_cred.assert_called_once()

    def test_init_with_retry_config(self, mock_credential):
        """Test initialization with custom retry configuration."""
        with patch('yellowstone.persistent_graph.sentinel_client.LogsQueryClient'):
            client = SentinelClient(
                workspace_id='test-workspace',
                credential=mock_credential,
                max_retries=5,
                retry_delay_seconds=2.0,
                timeout_seconds=600
            )
            assert client.max_retries == 5
            assert client.retry_delay_seconds == 2.0
            assert client.timeout_seconds == 600


class TestExecuteKQL:
    """Test KQL query execution."""

    def test_execute_kql_success(self, sentinel_client):
        """Test successful KQL query execution."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_table = Mock()
        mock_table.name = 'PrimaryResult'
        mock_table.columns = [
            Mock(name='TimeGenerated', type='datetime'),
            Mock(name='AlertName', type='string'),
        ]
        mock_table.rows = [
            ['2024-01-01T00:00:00Z', 'Test Alert 1'],
            ['2024-01-01T01:00:00Z', 'Test Alert 2'],
        ]
        mock_response.tables = [mock_table]

        sentinel_client._client.query_workspace.return_value = mock_response

        # Execute query
        result = sentinel_client.execute_kql("SecurityAlert | take 2")

        # Verify results
        assert result['status'] == 'success'
        assert result['row_count'] == 2
        assert len(result['rows']) == 2
        assert result['columns'] == ['TimeGenerated', 'AlertName']
        assert 'execution_time_ms' in result

    def test_execute_kql_empty_result(self, sentinel_client):
        """Test KQL query with no results."""
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_response.tables = []

        sentinel_client._client.query_workspace.return_value = mock_response

        result = sentinel_client.execute_kql("SecurityAlert | where 1==0")

        assert result['status'] == 'success'
        assert result['row_count'] == 0
        assert len(result['rows']) == 0

    def test_execute_kql_partial_success(self, sentinel_client):
        """Test KQL query with partial success."""
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.PARTIAL
        mock_response.partial_error = Mock()
        mock_response.partial_error.__str__ = lambda x: "Partial query failure"

        # Partial data
        mock_partial_data = Mock()
        mock_table = Mock()
        mock_table.columns = [Mock(name='col1', type='string')]
        mock_table.rows = [['value1']]
        mock_partial_data.tables = [mock_table]
        mock_response.partial_data = mock_partial_data

        sentinel_client._client.query_workspace.return_value = mock_response

        result = sentinel_client.execute_kql("some query")

        assert result['status'] == 'partial'
        assert 'error' in result
        assert result['row_count'] == 1

    def test_execute_kql_validation(self, sentinel_client):
        """Test query validation."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            sentinel_client.execute_kql("")

        with pytest.raises(ValueError, match="Query cannot be empty"):
            sentinel_client.execute_kql("   ")

    def test_execute_kql_authentication_error(self, sentinel_client):
        """Test handling of authentication errors."""
        sentinel_client._client.query_workspace.side_effect = HttpResponseError(
            message="Unauthorized",
            response=Mock(status_code=401)
        )

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            sentinel_client.execute_kql("test query")

    def test_execute_kql_workspace_not_found(self, sentinel_client):
        """Test handling of workspace not found errors."""
        sentinel_client._client.query_workspace.side_effect = HttpResponseError(
            message="Not Found",
            response=Mock(status_code=404)
        )

        with pytest.raises(WorkspaceNotFoundError, match="not found"):
            sentinel_client.execute_kql("test query")

    def test_execute_kql_retry_on_transient_error(self, sentinel_client):
        """Test retry logic for transient errors."""
        sentinel_client.max_retries = 3
        sentinel_client.retry_delay_seconds = 0.01  # Fast retry for testing

        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_response.tables = []

        sentinel_client._client.query_workspace.side_effect = [
            ServiceRequestError("Network error"),
            ServiceRequestError("Network error"),
            mock_response,
        ]

        result = sentinel_client.execute_kql("test query")
        assert result['status'] == 'success'
        assert sentinel_client._client.query_workspace.call_count == 3

    def test_execute_kql_retry_exhausted(self, sentinel_client):
        """Test behavior when retries are exhausted."""
        sentinel_client.max_retries = 2
        sentinel_client.retry_delay_seconds = 0.01

        sentinel_client._client.query_workspace.side_effect = ServiceRequestError("Network error")

        with pytest.raises(QueryExecutionError, match="after 2 attempts"):
            sentinel_client.execute_kql("test query")

        assert sentinel_client._client.query_workspace.call_count == 2


class TestManagementCommands:
    """Test KQL management command execution."""

    def test_execute_management_command_success(self, sentinel_client):
        """Test successful management command execution."""
        result = sentinel_client.execute_management_command(
            ".create table TestTable (id: string, value: int)"
        )

        assert result['status'] == 'success'
        assert 'command' in result
        assert 'execution_time_ms' in result

    def test_execute_management_command_validation(self, sentinel_client):
        """Test management command validation."""
        with pytest.raises(ValueError, match="cannot be empty"):
            sentinel_client.execute_management_command("")

        with pytest.raises(ValueError, match="must start with"):
            sentinel_client.execute_management_command("not a command")

        with pytest.raises(ValueError, match="Unsupported management command"):
            sentinel_client.execute_management_command(".invalid command")

    def test_execute_management_command_supported_prefixes(self, sentinel_client):
        """Test all supported management command prefixes."""
        commands = [
            ".create table Test (id: string)",
            ".alter table Test",
            ".drop table Test",
            ".set table Test",
            ".create-or-alter table Test (id: string)",
        ]

        for cmd in commands:
            result = sentinel_client.execute_management_command(cmd)
            assert result['status'] == 'success'


class TestQueryLogs:
    """Test log querying functionality."""

    def test_query_logs_success(self, sentinel_client):
        """Test successful log query."""
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_table = Mock()
        mock_table.name = 'Result'
        mock_table.columns = [Mock(name='col1', type='string')]
        mock_table.rows = [['value1'], ['value2']]
        mock_response.tables = [mock_table]

        sentinel_client._client.query_workspace.return_value = mock_response

        result = sentinel_client.query_logs("SecurityAlert | take 2")

        assert result['status'] == 'success'
        assert result['row_count'] == 2

    def test_query_logs_with_timespan(self, sentinel_client):
        """Test log query with custom timespan."""
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_response.tables = []

        sentinel_client._client.query_workspace.return_value = mock_response

        result = sentinel_client.query_logs(
            "SecurityAlert",
            timespan=timedelta(hours=12)
        )

        assert result['status'] == 'success'
        sentinel_client._client.query_workspace.assert_called_once()
        call_args = sentinel_client._client.query_workspace.call_args
        assert call_args[1]['timespan'] == timedelta(hours=12)

    def test_query_logs_validation(self, sentinel_client):
        """Test query validation for query_logs."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            sentinel_client.query_logs("")


class TestConnectionValidation:
    """Test connection validation functionality."""

    def test_validate_connection_success(self, sentinel_client):
        """Test successful connection validation."""
        mock_response = Mock()
        mock_response.status = LogsQueryStatus.SUCCESS
        mock_response.tables = []

        sentinel_client._client.query_workspace.return_value = mock_response

        result = sentinel_client.validate_connection()
        assert result is True

    def test_validate_connection_auth_failure(self, sentinel_client):
        """Test connection validation with auth failure."""
        sentinel_client._client.query_workspace.side_effect = HttpResponseError(
            message="Unauthorized",
            response=Mock(status_code=401)
        )

        with pytest.raises(AuthenticationError):
            sentinel_client.validate_connection()

    def test_validate_connection_workspace_not_found(self, sentinel_client):
        """Test connection validation with workspace not found."""
        sentinel_client._client.query_workspace.side_effect = HttpResponseError(
            message="Not Found",
            response=Mock(status_code=404)
        )

        with pytest.raises(WorkspaceNotFoundError):
            sentinel_client.validate_connection()


class TestWorkspaceInfo:
    """Test workspace information retrieval."""

    def test_get_workspace_info(self, sentinel_client):
        """Test getting workspace information."""
        info = sentinel_client.get_workspace_info()

        assert info['workspace_id'] == 'test-workspace-id'
        assert 'max_retries' in info
        assert 'retry_delay_seconds' in info
        assert 'timeout_seconds' in info


class TestClientCleanup:
    """Test client cleanup."""

    def test_close(self, sentinel_client):
        """Test client close."""
        sentinel_client.close()
        sentinel_client._client.close.assert_called_once()


# Integration tests - only run when workspace is configured
@pytest.mark.integration
class TestRealSentinelIntegration:
    """Integration tests against real Azure Sentinel workspace."""

    @pytest.fixture
    def real_client(self):
        """Create a real SentinelClient for integration tests."""
        if not WORKSPACE_ID:
            pytest.skip("SENTINEL_WORKSPACE_ID not configured")

        credential = get_real_credential()
        return SentinelClient(workspace_id=WORKSPACE_ID, credential=credential)

    def test_real_connection_validation(self, real_client):
        """Test connection to real workspace."""
        result = real_client.validate_connection()
        assert result is True

    def test_real_simple_query(self, real_client):
        """Test simple query against real workspace."""
        result = real_client.execute_kql(
            "print test='hello', value=42",
            timespan=timedelta(minutes=1)
        )

        assert result['status'] in ('success', 'partial')
        assert 'row_count' in result

    def test_real_security_alert_query(self, real_client):
        """Test querying SecurityAlert table."""
        result = real_client.execute_kql(
            "SecurityAlert | take 5",
            timespan=timedelta(days=7)
        )

        assert result['status'] in ('success', 'partial')
        # May have 0 rows if no alerts in timespan
        assert result['row_count'] >= 0

    def test_real_workspace_info(self, real_client):
        """Test getting real workspace info."""
        info = real_client.get_workspace_info()
        assert info['workspace_id'] == WORKSPACE_ID
