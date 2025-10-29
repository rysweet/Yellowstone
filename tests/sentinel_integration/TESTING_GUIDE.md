# Azure Sentinel Integration Testing Guide

Quick reference for developers working with real Sentinel integration tests.

## Quick Start

```bash
# 1. Setup
cd tests/sentinel_integration
cp .env.template .env
# Edit .env with your Azure details

# 2. Authenticate
az login

# 3. Run tests (interactive)
./run_integration_tests.sh

# 4. Or run directly
export RUN_INTEGRATION_TESTS="true"
source .env
pytest tests/sentinel_integration/ -v
```

## Test Categories

### Unit-Level Integration Tests

Test individual components:

```bash
# Test workspace management only
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestWorkspaceLifecycle -v

# Test data ingestion only
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestDataIngestion -v
```

### Full E2E Tests

Test complete translation and execution:

```bash
# All E2E tests
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestRealSentinelE2E -v

# Specific scenario
pytest tests/sentinel_integration/test_real_sentinel_e2e.py::TestRealSentinelE2E::test_lateral_movement_detection -v
```

## Fixtures Cheat Sheet

### Azure Configuration
- `azure_credentials` - DefaultAzureCredential instance
- `azure_config` - Dict with subscription_id, resource_group, location
- `workspace_key` - Workspace shared key for data ingestion

### Workspace Lifecycle
- `workspace_manager` - SentinelWorkspaceManager (session-scoped)
- `workspace_info` - Empty workspace (session-scoped)
- `workspace_with_tables` - Workspace with custom tables created

### Populated Workspaces
- `populated_workspace` - Basic scenario (10 users)
- `populated_workspace_lateral_movement` - Attack scenario
- `populated_workspace_device_ownership` - Multi-device scenario
- `populated_workspace_file_access` - File access scenario

### Query & Translation
- `query_client` - LogsQueryClient for KQL execution
- `schema_mapper` - SchemaMapper with test schema
- `translator` - CypherToKQLTranslator

### Data Generation
- `test_data_generator` - TestDataGenerator with seed=42

## Writing New Tests

### Pattern 1: Simple Query Test

```python
@pytest.mark.integration
@pytest.mark.requires_azure
def test_my_query(populated_workspace, query_client, translator):
    """Test a specific Cypher query pattern."""
    workspace_info = populated_workspace

    cypher = "MATCH (u:User) WHERE u.department = 'IT' RETURN u.name"
    kql = translator.translate(cypher)

    result = query_client.query_workspace(
        workspace_id=workspace_info.customer_id,
        query=kql,
        timespan="PT24H"
    )

    assert result.status == LogsQueryStatus.SUCCESS
    assert len(result.tables[0].rows) > 0
```

### Pattern 2: Custom Scenario Test

```python
@pytest.mark.integration
@pytest.mark.requires_azure
def test_custom_scenario(
    workspace_with_tables,
    workspace_key,
    azure_credentials,
    test_data_generator,
    query_client,
    translator
):
    """Test with custom generated data."""
    # Generate custom data
    identities = [
        test_data_generator.create_identity("User1", "IT", "Engineer"),
        test_data_generator.create_identity("User2", "Finance", "Analyst")
    ]

    # Populate workspace
    populator = DataPopulator(workspace_with_tables, azure_credentials)
    populator.set_workspace_key(workspace_key)

    result = populator.ingest_data(
        'IdentityInfo_CL',
        [identity.to_dict() for identity in identities]
    )
    assert result.success

    # Wait for data
    populator.wait_for_data_available('IdentityInfo_CL')

    # Run query
    cypher = "MATCH (u:User) RETURN u.name"
    kql = translator.translate(cypher)

    query_result = query_client.query_workspace(
        workspace_id=workspace_with_tables.customer_id,
        query=kql,
        timespan="PT24H"
    )

    assert len(query_result.tables[0].rows) == 2
```

## Common Test Scenarios

### Test: User Investigation

```python
def test_user_investigation(populated_workspace, query_client, translator):
    """Find all actions by a specific user."""
    cypher = """
    MATCH (u:User {name: 'Alice Johnson'})
    OPTIONAL MATCH (u)-[:SIGNED_IN]->(d:Device)
    OPTIONAL MATCH (u)-[:ACCESSED]->(f:File)
    RETURN u.name, d.name, f.path
    """
    # ... execute and validate
```

### Test: Anomaly Detection

```python
def test_failed_login_detection(populated_workspace, query_client, translator):
    """Detect failed login attempts."""
    cypher = """
    MATCH (u:User)-[s:SIGNED_IN]->(d:Device)
    WHERE s.result = 'Failure'
    RETURN u.name, COUNT(s) AS failed_attempts
    ORDER BY failed_attempts DESC
    """
    # ... execute and validate
```

### Test: Relationship Query

```python
def test_device_ownership(populated_workspace_device_ownership, query_client, translator):
    """Query device ownership relationships."""
    cypher = """
    MATCH (u:User)-[:OWNS]->(d:Device)
    WHERE u.department = 'IT'
    RETURN u.name, COUNT(d) AS device_count
    HAVING device_count > 1
    """
    # ... execute and validate
```

## Data Generator Usage

### Create Single Entities

```python
generator = TestDataGenerator(seed=42)

# Create user
user = generator.create_identity(
    name="John Doe",
    department="IT",
    job_title="Security Engineer",
    risk_level="Low"
)

# Create device
device = generator.create_device(
    device_name="LAPTOP-JOHN",
    owner_user_id=user.user_id,
    device_type="Laptop"
)

# Create sign-in event
signin = generator.create_sign_in_event(
    user_id=user.user_id,
    user_principal_name=user.user_principal_name,
    device_id=device.device_id,
    result="Success",
    risk_level="Low"
)
```

### Use Pre-Built Scenarios

```python
# Basic scenario: Users, devices, sign-ins
basic = generator.generate_basic_scenario(num_users=10)
# Returns: {'identities': [...], 'devices': [...], 'sign_in_events': [...]}

# Attack scenario: Lateral movement pattern
attack = generator.generate_lateral_movement_scenario()
# Returns: Full attack chain with compromised accounts

# Multi-device scenario
devices = generator.generate_device_ownership_scenario()
# Returns: Users with 2-4 devices each

# File access scenario
files = generator.generate_file_access_pattern_scenario()
# Returns: Users accessing sensitive files
```

## Custom Table Schemas

When creating custom tables, use this pattern:

```python
columns = [
    {'name': 'UserId', 'type': 'string'},
    {'name': 'UserName', 'type': 'string'},
    {'name': 'EventType', 'type': 'string'},
    {'name': 'EventTime', 'type': 'datetime'},
    {'name': 'RiskScore', 'type': 'real'},
    {'name': 'IsAnomaly', 'type': 'boolean'},
    {'name': 'Metadata', 'type': 'dynamic'}
]

workspace_manager.create_custom_table('MyEvents_CL', columns)
```

Supported types:
- `string` - Text
- `int` - 32-bit integer
- `long` - 64-bit integer
- `real` - Floating point
- `boolean` - True/False
- `datetime` - Timestamp
- `dynamic` - JSON/nested data
- `guid` - UUID

## Debugging Tips

### Enable Verbose Logging

```bash
pytest tests/sentinel_integration/ -v -s --log-cli-level=DEBUG
```

### Test Single Fixture

```python
def test_fixture_debug(workspace_with_tables):
    """Debug fixture setup."""
    print(f"Workspace: {workspace_with_tables.workspace_name}")
    print(f"Tables: {workspace_with_tables.custom_tables}")
    assert workspace_with_tables.customer_id is not None
```

### Inspect Query Results

```python
def test_inspect_results(populated_workspace, query_client, translator):
    """Inspect actual query results."""
    cypher = "MATCH (u:User) RETURN u LIMIT 1"
    kql = translator.translate(cypher)

    result = query_client.query_workspace(
        workspace_id=populated_workspace.customer_id,
        query=kql,
        timespan="PT24H"
    )

    table = result.tables[0]

    # Print schema
    print("Columns:", [col.name for col in table.columns])

    # Print first row
    if table.rows:
        row_dict = dict(zip([col.name for col in table.columns], table.rows[0]))
        print("First row:", row_dict)
```

### Check Data Ingestion

```python
def test_verify_ingestion(workspace_with_tables, workspace_key, azure_credentials):
    """Verify data was ingested correctly."""
    generator = TestDataGenerator()
    identity = generator.create_identity("Test User", "IT", "Engineer")

    populator = DataPopulator(workspace_with_tables, azure_credentials)
    populator.set_workspace_key(workspace_key)

    result = populator.ingest_data('IdentityInfo_CL', [identity.to_dict()])

    print(f"Success: {result.success}")
    print(f"Records sent: {result.records_sent}")
    print(f"Time: {result.ingestion_time_ms}ms")

    if not result.success:
        print(f"Error: {result.error_message}")
```

## Performance Considerations

### Minimize Data Volume

```python
# Good: Small dataset for testing logic
scenario = generator.generate_basic_scenario(num_users=5)

# Avoid: Large dataset unless testing scale
scenario = generator.generate_basic_scenario(num_users=1000)
```

### Reuse Workspaces

```python
# Use session-scoped fixtures to share workspace across tests
@pytest.fixture(scope="session")
def my_shared_workspace(workspace_with_tables):
    # Workspace is created once and reused
    return workspace_with_tables
```

### Batch Operations

```python
# Good: Bulk ingest
populator.bulk_ingest({
    'IdentityInfo_CL': identity_records,
    'DeviceInfo_CL': device_records
})

# Avoid: Individual ingests
for record in records:
    populator.ingest_data('Table_CL', [record])  # Slow!
```

## Cost Monitoring

### Estimate Test Costs

```python
# Each test scenario ingests approximately:
# - Basic scenario (10 users): ~1 KB
# - Lateral movement: ~5 KB
# - Device ownership: ~3 KB
# - File access: ~2 KB

# At ~$2-4/GB ingested:
# - Single test: ~$0.01
# - Full suite: ~$0.10-0.50
# - With workspace retention (30 days): Add ~$0.10-0.30/GB
```

### Check Azure Costs

```bash
# View costs in Azure Portal
az consumption usage list \
  --start-date 2025-10-01 \
  --end-date 2025-10-29 \
  --query "[?contains(instanceName, 'yellowstone')].{Name:instanceName, Cost:pretaxCost}"

# Set budget alert
az consumption budget create \
  --budget-name "integration-tests" \
  --amount 10 \
  --time-grain Monthly \
  --start-date 2025-10-01
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Sentinel Integration Tests

on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly
  workflow_dispatch:      # Manual only

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
        run: pip install -r requirements.txt

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run Tests
        env:
          AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
          AZURE_LOCATION: eastus
          RUN_INTEGRATION_TESTS: true
        run: pytest tests/sentinel_integration/ -v -m integration
```

## Troubleshooting Checklist

- [ ] Azure CLI authenticated (`az account show`)
- [ ] Correct subscription selected
- [ ] Environment variables set (`.env` loaded)
- [ ] `RUN_INTEGRATION_TESTS=true` set
- [ ] Azure permissions sufficient (Contributor + Log Analytics Contributor)
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Workspace name unique (if creating new)
- [ ] Region has capacity for Log Analytics workspaces
- [ ] Network connectivity to Azure (no firewall blocks)
- [ ] Workspace key retrieved correctly (for ingestion)

## Best Practices

1. **Always use fixtures** - Don't create workspaces manually in tests
2. **Seed generators** - Use `TestDataGenerator(seed=42)` for reproducibility
3. **Wait for ingestion** - Call `wait_for_data_available()` before querying
4. **Check result status** - Always verify `result.status == LogsQueryStatus.SUCCESS`
5. **Clean up** - Fixtures handle this, but be aware of cleanup order
6. **Minimize costs** - Run integration tests sparingly, use small datasets
7. **Isolate tests** - Use function-scoped populated workspace fixtures
8. **Document scenarios** - Add clear docstrings explaining what each test validates

## References

- [Main README](./README.md) - Comprehensive setup guide
- [Azure Log Analytics API](https://learn.microsoft.com/en-us/rest/api/loganalytics/)
- [KQL Reference](https://learn.microsoft.com/en-us/azure/data-explorer/kusto/query/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
