# Azure Sentinel Integration

This document describes the real Azure Sentinel integration in Yellowstone's persistent graph module.

## Overview

The `SentinelClient` class provides production-ready integration with Azure Sentinel using the official `azure-monitor-query` SDK. It replaces the previous mock implementation with real API calls, authentication, error handling, and retry logic.

## Features

- **Real Azure SDK Integration**: Uses `azure-monitor-query.LogsQueryClient`
- **Flexible Authentication**: Supports `DefaultAzureCredential` and explicit credentials
- **Comprehensive Error Handling**: Authentication, network, workspace, and query errors
- **Automatic Retry Logic**: Exponential backoff for transient failures
- **Production Ready**: Full validation, timeouts, and error recovery

## Authentication

### DefaultAzureCredential (Recommended)

The simplest approach is to use `DefaultAzureCredential`, which automatically tries multiple authentication methods:

```python
from azure.identity import DefaultAzureCredential
from yellowstone.persistent_graph import SentinelClient

credential = DefaultAzureCredential()
client = SentinelClient(
    workspace_id='your-workspace-id',
    credential=credential
)
```

`DefaultAzureCredential` tries these methods in order:
1. Environment variables (service principal)
2. Managed Identity
3. Visual Studio Code
4. Azure CLI
5. Azure PowerShell
6. Interactive browser

### Service Principal

For production environments, use a service principal:

```python
from azure.identity import ClientSecretCredential
from yellowstone.persistent_graph import SentinelClient

credential = ClientSecretCredential(
    tenant_id='your-tenant-id',
    client_id='your-client-id',
    client_secret='your-client-secret'
)

client = SentinelClient(
    workspace_id='your-workspace-id',
    credential=credential
)
```

### Managed Identity

For Azure resources (VMs, App Service, Functions):

```python
from azure.identity import ManagedIdentityCredential
from yellowstone.persistent_graph import SentinelClient

credential = ManagedIdentityCredential()
client = SentinelClient(
    workspace_id='your-workspace-id',
    credential=credential
)
```

## Required Permissions

The service principal or managed identity needs the following RBAC roles on the workspace:

- **Log Analytics Reader**: Read access to execute queries
- **Log Analytics Contributor**: Write access for management commands (graph creation/modification)

To assign permissions:

```bash
# Read-only access
az role assignment create \
  --assignee <service-principal-id> \
  --role "Log Analytics Reader" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>

# Read-write access (for graph management)
az role assignment create \
  --assignee <service-principal-id> \
  --role "Log Analytics Contributor" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>
```

## Configuration

### Environment Variables

Set these environment variables for `DefaultAzureCredential`:

```bash
# Service Principal
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"

# Workspace
export SENTINEL_WORKSPACE_ID="your-workspace-id"
```

### Retry Configuration

Configure retry behavior for transient failures:

```python
client = SentinelClient(
    workspace_id='your-workspace-id',
    credential=credential,
    max_retries=5,              # Maximum retry attempts (default: 3)
    retry_delay_seconds=2.0,    # Initial delay (exponential backoff)
    timeout_seconds=600         # Query timeout (default: 300)
)
```

## Usage Examples

### Basic Connection

```python
from azure.identity import DefaultAzureCredential
from yellowstone.persistent_graph import (
    SentinelClient,
    AuthenticationError,
    WorkspaceNotFoundError
)

try:
    credential = DefaultAzureCredential()
    client = SentinelClient(
        workspace_id='your-workspace-id',
        credential=credential
    )

    # Validate connection
    if client.validate_connection():
        print("Connected successfully!")

except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except WorkspaceNotFoundError as e:
    print(f"Workspace not found: {e}")
```

### Execute KQL Query

```python
from datetime import timedelta

# Simple query
result = client.execute_kql(
    "SecurityAlert | take 10",
    timespan=timedelta(hours=24)
)

print(f"Status: {result['status']}")
print(f"Rows: {result['row_count']}")
print(f"Execution time: {result['execution_time_ms']} ms")

for row in result['rows']:
    print(row)
```

### Query with Parameters

```python
# Parameterized query
query = """
SecurityAlert
| where TimeGenerated > ago(7d)
| where AlertSeverity == @severity
| summarize Count=count()
"""

result = client.execute_kql(
    query,
    timespan=timedelta(days=7),
    parameters={'severity': 'High'}
)
```

### Management Commands

```python
# Create custom table (management command)
command = """
.create-or-alter table MyGraph (
    NodeId: string,
    Label: string,
    Properties: dynamic,
    Timestamp: datetime
)
"""

result = client.execute_management_command(command)
print(f"Command status: {result['status']}")
```

### Query Logs Across Workspaces

```python
# Cross-workspace query
result = client.query_logs(
    query="union SecurityAlert, SecurityIncident | take 100",
    timespan=timedelta(days=1),
    additional_workspaces=['workspace-id-2', 'workspace-id-3']
)
```

## Using with GraphManager

The `GraphManager` now uses real Sentinel integration by default:

```python
from azure.identity import DefaultAzureCredential
from yellowstone.persistent_graph import (
    GraphManager,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition
)

# Create manager with real Sentinel integration
credential = DefaultAzureCredential()
manager = GraphManager(
    workspace_id='your-workspace-id',
    credential=credential
)

# Define graph schema
schema = GraphSchema(
    nodes=[
        NodeDefinition(
            label='Alert',
            source_table='SecurityAlert',
            id_property='SystemAlertId',
            properties={
                'AlertId': 'SystemAlertId',
                'severity': 'AlertSeverity',
            }
        )
    ],
    edges=[]
)

# Create persistent graph (executes real KQL commands)
graph = manager.create_graph('SecurityGraph', schema)
print(f"Graph created: {graph.name} (status: {graph.status})")

# Query the graph (executes real KQL queries)
results = manager.query_graph(
    'SecurityGraph',
    "persistent-graph('SecurityGraph') | graph-match (a:Alert) | take 10"
)
print(f"Query returned {results['row_count']} rows")
```

## Error Handling

The client provides specific exceptions for different error scenarios:

```python
from yellowstone.persistent_graph import (
    SentinelClient,
    SentinelAPIError,
    AuthenticationError,
    QueryExecutionError,
    WorkspaceNotFoundError
)

try:
    client = SentinelClient(workspace_id='ws-id')
    result = client.execute_kql("SecurityAlert | take 10")

except AuthenticationError as e:
    # Handle authentication failures
    print(f"Auth error: {e}")
    # Check credentials, permissions, token expiry

except WorkspaceNotFoundError as e:
    # Handle workspace access issues
    print(f"Workspace error: {e}")
    # Verify workspace ID, check RBAC permissions

except QueryExecutionError as e:
    # Handle query execution failures
    print(f"Query error: {e}")
    # Check query syntax, table names, timespan

except SentinelAPIError as e:
    # Handle other Sentinel API errors
    print(f"API error: {e}")

except ValueError as e:
    # Handle validation errors
    print(f"Validation error: {e}")
    # Check input parameters
```

## Testing

### Unit Tests

Unit tests use mocked Azure SDK components:

```python
pytest src/yellowstone/persistent_graph/tests/test_sentinel_client.py
```

### Integration Tests

Integration tests run against a real Sentinel workspace (requires configuration):

```bash
# Set environment variables
export SENTINEL_WORKSPACE_ID="your-workspace-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"

# Run integration tests
pytest src/yellowstone/persistent_graph/tests/test_sentinel_client.py -m integration
```

### Example Script

Run the complete example script:

```bash
# Set credentials
export SENTINEL_WORKSPACE_ID="your-workspace-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"

# Run examples
python src/yellowstone/persistent_graph/examples/real_sentinel_example.py
```

## Performance

### Query Performance

- Default timeout: 300 seconds
- Configurable via `timeout_seconds` parameter
- Automatic retry with exponential backoff
- Parallel query support via additional_workspaces

### Retry Logic

- Default: 3 retries with exponential backoff
- Initial delay: 1 second
- Backoff multiplier: 2x per retry
- Retries on: Network errors, transient service errors
- No retry on: Authentication errors, validation errors

### Connection Pooling

The `LogsQueryClient` maintains an internal connection pool for optimal performance. Reuse the same `SentinelClient` instance across multiple queries.

## Best Practices

### 1. Reuse Client Instances

```python
# Good: Reuse client
client = SentinelClient(workspace_id='ws-id')
for query in queries:
    result = client.execute_kql(query)

# Bad: Create new client each time
for query in queries:
    client = SentinelClient(workspace_id='ws-id')
    result = client.execute_kql(query)
```

### 2. Use Appropriate Timespans

```python
# Good: Narrow timespan for specific queries
result = client.execute_kql(
    "SecurityAlert | where TimeGenerated > ago(1h)",
    timespan=timedelta(hours=1)
)

# Bad: Overly broad timespan
result = client.execute_kql(
    "SecurityAlert | where TimeGenerated > ago(1h)",
    timespan=timedelta(days=365)
)
```

### 3. Handle Partial Results

```python
result = client.execute_kql(query)

if result['status'] == 'success':
    # All data retrieved successfully
    process_data(result['rows'])
elif result['status'] == 'partial':
    # Partial data with errors
    print(f"Warning: {result['error']}")
    process_data(result['rows'])  # Process partial data
else:
    # Query failed
    handle_error(result)
```

### 4. Clean Up Resources

```python
try:
    client = SentinelClient(workspace_id='ws-id')
    # Use client...
finally:
    client.close()  # Clean up resources
```

### 5. Use Managed Identity in Azure

```python
# Best practice for Azure resources
from azure.identity import ManagedIdentityCredential

credential = ManagedIdentityCredential()
client = SentinelClient(
    workspace_id='ws-id',
    credential=credential
)
```

## Troubleshooting

### Authentication Failures

**Error**: `AuthenticationError: Authentication failed`

**Solutions**:
- Verify credentials are correct
- Check environment variables are set
- Ensure service principal has not expired
- Verify tenant ID is correct

### Workspace Not Found

**Error**: `WorkspaceNotFoundError: Workspace not found`

**Solutions**:
- Verify workspace ID is correct (not workspace name)
- Check RBAC permissions on the workspace
- Ensure workspace exists and is not deleted
- Verify subscription access

### Query Execution Failures

**Error**: `QueryExecutionError: Query execution failed`

**Solutions**:
- Check KQL syntax
- Verify table names exist in workspace
- Ensure timespan is appropriate
- Check query timeout settings
- Review workspace ingestion logs

### Network Errors

**Error**: `QueryExecutionError: Network error after N attempts`

**Solutions**:
- Check network connectivity
- Verify firewall rules
- Increase retry count
- Increase retry delay
- Check Azure service health

## API Reference

### SentinelClient

```python
class SentinelClient:
    def __init__(
        self,
        workspace_id: str,
        credential: Optional[Any] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        timeout_seconds: int = 300,
    )

    def execute_kql(
        self,
        query: str,
        timespan: Optional[timedelta] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]

    def execute_management_command(
        self,
        command: str
    ) -> Dict[str, Any]

    def query_logs(
        self,
        query: str,
        timespan: Optional[timedelta] = None,
        additional_workspaces: Optional[List[str]] = None,
    ) -> Dict[str, Any]

    def validate_connection(self) -> bool

    def get_workspace_info(self) -> Dict[str, Any]

    def close(self) -> None
```

### Exceptions

```python
class SentinelAPIError(Exception)
class AuthenticationError(SentinelAPIError)
class QueryExecutionError(SentinelAPIError)
class WorkspaceNotFoundError(SentinelAPIError)
```

## Migration from Mock

If you were using the old `MockSentinelAPI`:

### Before (Mock)

```python
from yellowstone.persistent_graph import GraphManager, MockSentinelAPI

# Old way with mock
mock_api = MockSentinelAPI()
manager = GraphManager(workspace_id='ws-id', api_client=mock_api)
```

### After (Real)

```python
from azure.identity import DefaultAzureCredential
from yellowstone.persistent_graph import GraphManager

# New way with real integration
credential = DefaultAzureCredential()
manager = GraphManager(
    workspace_id='your-real-workspace-id',
    credential=credential
)
```

### For Testing Only

If you need a mock for testing:

```python
from unittest.mock import Mock

mock_client = Mock()
mock_client.execute_management_command.return_value = {'status': 'success'}
mock_client.execute_kql.return_value = {'status': 'success', 'rows': []}

manager = GraphManager(workspace_id='test', api_client=mock_client)
```

## Support

For issues or questions:
- Check the [examples](examples/real_sentinel_example.py)
- Review [integration tests](tests/test_sentinel_client.py)
- See [Azure Monitor Query SDK docs](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme)
- Consult [Azure Identity SDK docs](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
