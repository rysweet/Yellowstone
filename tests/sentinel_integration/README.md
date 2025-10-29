# Azure Sentinel Integration Tests

Real end-to-end integration tests for Yellowstone's Cypher-to-KQL translation engine using actual Azure Sentinel workspaces.

## ⚠️ IMPORTANT: Cost Warning

**These tests create real Azure resources and WILL incur costs.**

Approximate costs (as of 2025):
- **Log Analytics Workspace**: $2-5/GB ingested + $0.10-0.30/GB retention
- **Azure Sentinel**: $2-4/GB ingested
- **Test data volume**: ~1-10 MB per test run
- **Estimated cost per full test run**: $0.10 - $1.00

**Best practices to minimize costs:**
1. Run integration tests sparingly (not on every commit)
2. Use a dedicated test subscription if possible
3. Clean up resources immediately after tests (fixtures handle this)
4. Monitor your Azure billing dashboard
5. Set budget alerts in Azure Cost Management

## Prerequisites

### 1. Azure Account Setup

You need an Azure subscription with permissions to:
- Create and delete Log Analytics workspaces
- Enable Azure Sentinel
- Create custom tables
- Ingest data via HTTP Data Collector API
- Execute KQL queries

Recommended roles:
- `Contributor` on the resource group
- `Log Analytics Contributor`
- `Microsoft Sentinel Contributor`

### 2. Authentication

These tests use `DefaultAzureCredential` which tries multiple authentication methods in order:

1. **Environment Variables** (recommended for CI/CD):
   ```bash
   export AZURE_TENANT_ID="your-tenant-id"
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   ```

2. **Azure CLI** (recommended for local development):
   ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

3. **Managed Identity** (for Azure-hosted runners)

4. **Visual Studio Code** / **Azure PowerShell**

### 3. Python Dependencies

Install required Azure SDKs:

```bash
pip install -r requirements.txt
```

Required packages:
- `azure-identity` - Authentication
- `azure-mgmt-loganalytics>=13.0.0` - Workspace management
- `azure-mgmt-securityinsights>=1.0.0` - Sentinel management
- `azure-mgmt-resource>=23.0.0` - Resource group management
- `azure-monitor-ingestion>=1.0.0` - Data ingestion
- `azure-monitor-query>=1.0.0` - KQL query execution
- `pytest>=7.0.0` - Test framework

## Configuration

### Environment Variables

Set these environment variables before running tests:

```bash
# Required
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_RESOURCE_GROUP="yellowstone-integration-tests"
export AZURE_LOCATION="eastus"  # or your preferred region

# Optional
export AZURE_WORKSPACE_NAME="yellowstone-test-$(date +%Y%m%d%H%M%S)"
export RUN_INTEGRATION_TESTS="true"  # Must be set to enable tests
```

### Setup Script

Use the provided setup script:

```bash
# Copy template
cp .env.template .env

# Edit with your values
nano .env

# Load environment
source .env

# Enable integration tests
export RUN_INTEGRATION_TESTS="true"
```

## Running Tests

### Run All Integration Tests

```bash
# Enable integration tests
export RUN_INTEGRATION_TESTS="true"

# Run with verbose output
pytest tests/sentinel_integration/ -v -s --log-cli-level=INFO

# Run specific test class
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestRealSentinelE2E -v

# Run specific test
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestRealSentinelE2E::test_translate_and_execute_user_query -v
```

### Run with Markers

```bash
# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "integration and not slow"

# Run only tests requiring Azure
pytest -m requires_azure
```

### Skip Integration Tests

By default, integration tests are skipped unless explicitly enabled:

```bash
# These will skip (default behavior)
pytest tests/sentinel_integration/

# Enable with environment variable
export RUN_INTEGRATION_TESTS="true"
pytest tests/sentinel_integration/
```

## Test Architecture

### Test Structure

```
tests/sentinel_integration/
├── __init__.py                      # Package initialization
├── conftest.py                      # Pytest fixtures
├── sentinel_workspace_manager.py   # Workspace lifecycle management
├── test_data_generator.py          # Test data generation
├── data_populator.py               # Data ingestion
├── test_real_sentinel_e2e.py       # End-to-end tests
└── README.md                        # This file
```

### Key Components

#### 1. SentinelWorkspaceManager

Manages workspace lifecycle:
- Creates Log Analytics workspace
- Enables Azure Sentinel
- Creates custom tables
- Handles cleanup

```python
from sentinel_workspace_manager import WorkspaceConfig, SentinelWorkspaceManager

config = WorkspaceConfig(
    subscription_id="your-sub",
    resource_group="test-rg",
    workspace_name="test-workspace"
)

with SentinelWorkspaceManager(config) as manager:
    workspace = manager.create_workspace()
    # Run tests
    # Cleanup happens automatically
```

#### 2. TestDataGenerator

Generates realistic security scenarios:
- User identities
- Devices
- Sign-in events
- File access events
- Network connections
- Attack patterns (lateral movement, etc.)

```python
from test_data_generator import TestDataGenerator

generator = TestDataGenerator(seed=42)

# Basic scenario
basic = generator.generate_basic_scenario(num_users=10)

# Attack scenario
lateral_movement = generator.generate_lateral_movement_scenario()
```

#### 3. DataPopulator

Ingests test data into Sentinel:
- Uses HTTP Data Collector API
- Batch ingestion support
- Verification and error handling

```python
from data_populator import DataPopulator

populator = DataPopulator(workspace_info)
populator.set_workspace_key(workspace_key)

results = populator.populate_from_generator(scenario_data)
populator.verify_ingestion(results)
```

#### 4. Pytest Fixtures

Provide test infrastructure:
- `azure_credentials` - Azure authentication
- `workspace_info` - Created workspace
- `populated_workspace` - Workspace with data
- `query_client` - KQL query execution
- `translator` - Cypher-to-KQL translator

## Test Scenarios

### 1. Basic User Query

Tests simple node matching and property projection:

```cypher
MATCH (u:User)
RETURN u.name, u.department
LIMIT 10
```

### 2. Lateral Movement Detection

Tests complex attack path detection:

```cypher
MATCH (u1:User)-[:SIGNED_IN]->(d1:Device)
WHERE u1.riskLevel = 'High'
RETURN u1.name, d1.name
```

### 3. Device Ownership

Tests relationship queries:

```cypher
MATCH (u:User)-[:OWNS]->(d:Device)
WHERE u.department = 'IT'
RETURN u.name, COUNT(d) AS device_count
```

### 4. File Access Patterns

Tests property filtering:

```cypher
MATCH (u:User)-[:ACCESSED]->(f:File)
WHERE f.path CONTAINS 'sensitive'
RETURN u.name, f.path, f.action
```

### 5. Multi-Hop Attack Paths

Tests path queries:

```cypher
MATCH path = (u1:User)-[:SIGNED_IN*3..5]->(u2:User)
WHERE u1.riskLevel = 'High'
RETURN path
```

## Troubleshooting

### Authentication Errors

**Problem**: `ClientAuthenticationError: Authentication failed`

**Solutions**:
1. Verify Azure CLI login: `az account show`
2. Check environment variables are set correctly
3. Verify service principal has correct permissions
4. Try re-authenticating: `az login`

### Workspace Creation Fails

**Problem**: `HttpResponseError: Workspace creation failed`

**Solutions**:
1. Check resource group exists or will be created
2. Verify subscription has available quota
3. Try different region if capacity issues
4. Check for naming conflicts (workspace names must be unique)

### Data Ingestion Fails

**Problem**: `HttpResponseError: Ingestion failed: 403`

**Solutions**:
1. Verify workspace key is correct
2. Check firewall rules aren't blocking requests
3. Ensure custom tables are created before ingestion
4. Verify data format matches table schema

### Query Execution Timeout

**Problem**: `QueryTimeout: Query exceeded timeout`

**Solutions**:
1. Reduce query complexity
2. Add time range filters
3. Increase query timeout in fixture
4. Check workspace performance tier

### Data Not Available

**Problem**: Query returns no results after ingestion

**Solutions**:
1. Wait longer for ingestion latency (1-5 minutes typical)
2. Check table names are correct (`_CL` suffix)
3. Verify data was actually ingested (check `IngestionResult`)
4. Query timespan includes ingestion time

### Cleanup Fails

**Problem**: Resources not deleted after tests

**Solutions**:
1. Manually delete workspace in Azure Portal
2. Check for locks on resource group
3. Verify credentials have delete permissions
4. Run cleanup explicitly: `workspace_manager.cleanup(force=True)`

## Cost Optimization Tips

### 1. Use Existing Workspace

Reuse a workspace across test runs instead of creating new ones:

```bash
# Set existing workspace name
export AZURE_WORKSPACE_NAME="my-persistent-test-workspace"
export REUSE_WORKSPACE="true"
```

### 2. Limit Test Data Volume

Generate smaller datasets:

```python
# Instead of
scenario = generator.generate_basic_scenario(num_users=100)

# Use
scenario = generator.generate_basic_scenario(num_users=10)
```

### 3. Use Basic Pricing Tier

Set retention to minimum:

```python
config = WorkspaceConfig(
    subscription_id=subscription_id,
    resource_group=resource_group,
    workspace_name=workspace_name,
    retention_in_days=7  # Minimum retention
)
```

### 4. Delete Resources Promptly

Ensure cleanup runs even on test failure:

```python
@pytest.fixture
def workspace(workspace_manager):
    workspace = workspace_manager.create_workspace()
    yield workspace
    workspace_manager.cleanup()  # Always runs
```

### 5. Run Selectively

Don't run all tests every time:

```bash
# Run only fast tests locally
pytest -m "integration and not slow"

# Run full suite only in CI
pytest -m integration
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2am
  workflow_dispatch:      # Manual trigger only

jobs:
  integration:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run Integration Tests
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
          AZURE_LOCATION: eastus
          RUN_INTEGRATION_TESTS: true
        run: |
          pytest tests/sentinel_integration/ -v --junitxml=results.xml

      - name: Upload Results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: results.xml
```

### Azure DevOps Pipeline Example

```yaml
trigger: none  # Manual only

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: azure-integration-tests  # Variable group with secrets

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: pip install -r requirements.txt
    displayName: 'Install dependencies'

  - task: AzureCLI@2
    inputs:
      azureSubscription: 'Azure-Sentinel-Testing'
      scriptType: 'bash'
      scriptLocation: 'inlineScript'
      inlineScript: |
        export RUN_INTEGRATION_TESTS=true
        pytest tests/sentinel_integration/ -v
    displayName: 'Run Integration Tests'
```

## Best Practices

1. **Authentication**: Use managed identities in CI/CD, Azure CLI locally
2. **Isolation**: Use dedicated test subscription or resource group
3. **Cleanup**: Always use fixtures to ensure cleanup happens
4. **Monitoring**: Set up billing alerts for unexpected costs
5. **Frequency**: Run integration tests weekly or on-demand, not per-commit
6. **Documentation**: Keep this README updated with any configuration changes
7. **Secrets**: Never commit credentials; use environment variables or secret management

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Azure Monitor logs in Azure Portal
3. Enable verbose logging: `--log-cli-level=DEBUG`
4. Check pytest output for detailed error messages

## References

- [Azure Log Analytics REST API](https://learn.microsoft.com/en-us/rest/api/loganalytics/)
- [Azure Sentinel Documentation](https://learn.microsoft.com/en-us/azure/sentinel/)
- [Azure Monitor Query SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme)
- [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
- [KQL Language Reference](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/)
