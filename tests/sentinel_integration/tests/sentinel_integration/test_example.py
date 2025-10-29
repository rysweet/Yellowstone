"""Example integration tests demonstrating the testing infrastructure.

This file shows how to write new integration tests using the provided fixtures
and utilities. Use these examples as templates for your own tests.

To run these examples:
    pytest tests/sentinel_integration/test_example.py -v
"""

import pytest
from azure.monitor.query import LogsQueryStatus


@pytest.mark.integration
@pytest.mark.requires_azure
class TestExampleBasicQueries:
    """Example tests for basic Cypher query patterns."""

    def test_simple_node_match(self, populated_workspace, query_client, translator):
        """Example: Match all users and return their properties.

        This demonstrates:
        - Basic MATCH clause
        - Property projection
        - LIMIT clause
        """
        cypher_query = """
        MATCH (u:User)
        RETURN u.name AS name, u.department AS department
        LIMIT 5
        """

        # Translate to KQL
        kql_query = translator.translate(cypher_query)
        print(f"\nTranslated KQL:\n{kql_query}")

        # Execute against Sentinel
        result = query_client.query_workspace(
            workspace_id=populated_workspace.customer_id,
            query=kql_query,
            timespan="PT24H"
        )

        # Validate results
        assert result.status == LogsQueryStatus.SUCCESS
        assert len(result.tables) > 0

        table = result.tables[0]
        assert len(table.rows) > 0
        assert len(table.rows) <= 5

        # Print results for inspection
        print(f"\nResults: {len(table.rows)} rows")
        for row in table.rows:
            print(f"  {dict(zip([col.name for col in table.columns], row))}")

    def test_node_with_filter(self, populated_workspace, query_client, translator):
        """Example: Filter nodes by property value.

        This demonstrates:
        - WHERE clause
        - Property filtering
        - Equality comparisons
        """
        cypher_query = """
        MATCH (u:User)
        WHERE u.department = 'IT'
        RETURN u.name AS name, u.jobTitle AS title
        """

        kql_query = translator.translate(cypher_query)
        result = query_client.query_workspace(
            workspace_id=populated_workspace.customer_id,
            query=kql_query,
            timespan="PT24H"
        )

        assert result.status == LogsQueryStatus.SUCCESS

        # All returned users should be from IT department
        table = result.tables[0]
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]

        print(f"\nFound {len(rows_data)} IT users")
        for row_dict in rows_data:
            print(f"  {row_dict}")

    def test_aggregation_query(self, populated_workspace, query_client, translator):
        """Example: Aggregate data with COUNT.

        This demonstrates:
        - COUNT aggregation
        - GROUP BY (implicit via RETURN)
        - ORDER BY
        """
        cypher_query = """
        MATCH (u:User)
        RETURN u.department AS department, COUNT(*) AS user_count
        ORDER BY user_count DESC
        """

        kql_query = translator.translate(cypher_query)
        result = query_client.query_workspace(
            workspace_id=populated_workspace.customer_id,
            query=kql_query,
            timespan="PT24H"
        )

        assert result.status == LogsQueryStatus.SUCCESS

        table = result.tables[0]
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]

        print("\nUser count by department:")
        for row_dict in rows_data:
            dept = row_dict.get('department', 'Unknown')
            count = row_dict.get('user_count', 0)
            print(f"  {dept}: {count} users")

        # Verify all counts are positive
        for row_dict in rows_data:
            assert row_dict.get('user_count', 0) > 0


@pytest.mark.integration
@pytest.mark.requires_azure
class TestExampleCustomData:
    """Example tests using custom generated data."""

    def test_with_custom_scenario(
        self,
        workspace_with_tables,
        workspace_key,
        azure_credentials,
        test_data_generator,
        query_client,
        translator
    ):
        """Example: Generate and query custom test data.

        This demonstrates:
        - Custom data generation
        - Data ingestion
        - Querying custom data
        """
        # Generate custom identities
        identities = [
            test_data_generator.create_identity(
                name="Alice Developer",
                department="Engineering",
                job_title="Senior Software Engineer",
                risk_level="Low"
            ),
            test_data_generator.create_identity(
                name="Bob Analyst",
                department="Security",
                job_title="Security Analyst",
                risk_level="Medium"
            ),
            test_data_generator.create_identity(
                name="Charlie Admin",
                department="IT",
                job_title="System Administrator",
                risk_level="High"
            )
        ]

        # Ingest data
        from .data_populator import DataPopulator

        populator = DataPopulator(workspace_with_tables, azure_credentials)
        populator.set_workspace_key(workspace_key)

        result = populator.ingest_data(
            'IdentityInfo_CL',
            [identity.to_dict() for identity in identities]
        )

        assert result.success
        print(f"\nIngested {result.records_sent} identities in {result.ingestion_time_ms}ms")

        # Wait for data to be available
        populator.wait_for_data_available('IdentityInfo_CL')

        # Query the data
        cypher_query = """
        MATCH (u:User)
        WHERE u.riskLevel IN ['High', 'Medium']
        RETURN u.name AS name, u.riskLevel AS risk
        ORDER BY u.riskLevel DESC
        """

        kql_query = translator.translate(cypher_query)
        query_result = query_client.query_workspace(
            workspace_id=workspace_with_tables.customer_id,
            query=kql_query,
            timespan="PT24H"
        )

        assert query_result.status == LogsQueryStatus.SUCCESS

        table = query_result.tables[0]
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]

        print("\nHigh/Medium risk users:")
        for row_dict in rows_data:
            print(f"  {row_dict}")

        # Should find at least Charlie (High) and Bob (Medium)
        assert len(rows_data) >= 2


@pytest.mark.integration
@pytest.mark.requires_azure
@pytest.mark.slow
class TestExampleComplexScenarios:
    """Example tests for complex multi-table scenarios."""

    def test_lateral_movement_scenario(
        self,
        populated_workspace_lateral_movement,
        query_client,
        translator
    ):
        """Example: Query lateral movement attack scenario.

        This demonstrates:
        - Pre-populated complex scenario
        - Multi-property filtering
        - Risk-based queries
        """
        workspace_info = populated_workspace_lateral_movement

        # Find high-risk users
        cypher_query = """
        MATCH (u:User)
        WHERE u.riskLevel = 'High'
        RETURN u.name AS user_name,
               u.department AS department,
               u.riskLevel AS risk
        """

        kql_query = translator.translate(cypher_query)
        result = query_client.query_workspace(
            workspace_id=workspace_info.customer_id,
            query=kql_query,
            timespan="PT48H"  # Wider timespan for attack scenario
        )

        assert result.status == LogsQueryStatus.SUCCESS

        table = result.tables[0]
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]

        print("\nCompromised users detected:")
        for row_dict in rows_data:
            print(f"  {row_dict}")

        # Should find at least the initial compromised user (Patient Zero)
        assert len(rows_data) >= 1

    def test_device_ownership_scenario(
        self,
        populated_workspace_device_ownership,
        query_client,
        translator
    ):
        """Example: Query device ownership relationships.

        This demonstrates:
        - Relationship queries
        - Aggregation with relationships
        - HAVING-like filters
        """
        workspace_info = populated_workspace_device_ownership

        # Find users with multiple devices
        cypher_query = """
        MATCH (u:User)-[:OWNS]->(d:Device)
        WHERE u.department = 'IT'
        RETURN u.name AS user_name, COUNT(d) AS device_count
        """

        kql_query = translator.translate(cypher_query)
        result = query_client.query_workspace(
            workspace_id=workspace_info.customer_id,
            query=kql_query,
            timespan="PT24H"
        )

        assert result.status == LogsQueryStatus.SUCCESS

        table = result.tables[0]
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]

        print("\nIT users with multiple devices:")
        for row_dict in rows_data:
            user = row_dict.get('user_name', 'Unknown')
            count = row_dict.get('device_count', 0)
            print(f"  {user}: {count} devices")

        # All users in this scenario should have 2+ devices
        for row_dict in rows_data:
            assert row_dict.get('device_count', 0) >= 2


@pytest.mark.integration
@pytest.mark.requires_azure
class TestExampleWorkspaceManagement:
    """Example tests for workspace and table management."""

    def test_workspace_lifecycle(self, azure_credentials, azure_config):
        """Example: Create and cleanup workspace manually.

        This demonstrates:
        - Manual workspace creation
        - Context manager usage
        - Automatic cleanup
        """
        from .sentinel_workspace_manager import WorkspaceConfig, SentinelWorkspaceManager
        from datetime import datetime

        config = WorkspaceConfig(
            subscription_id=azure_config['subscription_id'],
            resource_group=azure_config['resource_group'],
            workspace_name=f"example-test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            location=azure_config['location']
        )

        # Use context manager for automatic cleanup
        with SentinelWorkspaceManager(config, azure_credentials) as manager:
            workspace_info = manager.create_workspace()

            print(f"\nCreated workspace:")
            print(f"  Name: {workspace_info.workspace_name}")
            print(f"  Customer ID: {workspace_info.customer_id}")
            print(f"  Location: {workspace_info.location}")

            assert workspace_info.workspace_id is not None
            assert workspace_info.customer_id is not None

        # Workspace is automatically cleaned up when exiting context

    def test_custom_table_creation(self, workspace_manager):
        """Example: Create custom table schema.

        This demonstrates:
        - Custom table definition
        - Column type mapping
        - Table creation
        """
        workspace_info = workspace_manager.create_workspace()

        # Define custom table schema
        columns = [
            {'name': 'EventId', 'type': 'string'},
            {'name': 'UserId', 'type': 'string'},
            {'name': 'ActionType', 'type': 'string'},
            {'name': 'Timestamp', 'type': 'datetime'},
            {'name': 'RiskScore', 'type': 'real'},
            {'name': 'IsBlocked', 'type': 'boolean'},
            {'name': 'Metadata', 'type': 'dynamic'}
        ]

        # Create table
        workspace_manager.create_custom_table('CustomSecurityEvents_CL', columns)

        print(f"\nCreated custom table: CustomSecurityEvents_CL")
        print(f"Workspace tables: {workspace_info.custom_tables}")

        assert 'CustomSecurityEvents_CL' in workspace_info.custom_tables


@pytest.mark.integration
@pytest.mark.requires_azure
class TestExampleDataGeneration:
    """Example tests for test data generation."""

    def test_generate_scenario_data(self, test_data_generator):
        """Example: Generate different types of test scenarios.

        This demonstrates:
        - Different scenario types
        - Data volume control
        - Scenario structure
        """
        # Generate basic scenario
        basic = test_data_generator.generate_basic_scenario(num_users=5)
        print(f"\nBasic scenario:")
        print(f"  Users: {len(basic['identities'])}")
        print(f"  Devices: {len(basic['devices'])}")
        print(f"  Sign-ins: {len(basic['sign_in_events'])}")

        assert len(basic['identities']) == 5
        assert len(basic['devices']) == 5
        assert len(basic['sign_in_events']) > 0

        # Generate attack scenario
        attack = test_data_generator.generate_lateral_movement_scenario()
        print(f"\nLateral movement scenario:")
        print(f"  Users: {len(attack['identities'])}")
        print(f"  Devices: {len(attack['devices'])}")
        print(f"  Sign-ins: {len(attack['sign_in_events'])}")
        print(f"  File access: {len(attack['file_access_events'])}")
        print(f"  Network events: {len(attack['network_events'])}")

        assert len(attack['identities']) >= 4  # Patient zero + targets
        assert len(attack['sign_in_events']) > 0
        assert len(attack['network_events']) > 0

    def test_create_individual_entities(self, test_data_generator):
        """Example: Create individual test entities.

        This demonstrates:
        - Creating specific users
        - Creating devices
        - Creating events
        - Linking entities
        """
        # Create a user
        user = test_data_generator.create_identity(
            name="Test Engineer",
            department="Engineering",
            job_title="Software Engineer",
            risk_level="Low"
        )

        print(f"\nCreated user:")
        print(f"  ID: {user.user_id}")
        print(f"  Name: {user.display_name}")
        print(f"  Email: {user.user_principal_name}")

        # Create a device for the user
        device = test_data_generator.create_device(
            device_name="LAPTOP-TEST",
            owner_user_id=user.user_id,
            device_type="Laptop"
        )

        print(f"\nCreated device:")
        print(f"  ID: {device.device_id}")
        print(f"  Name: {device.device_name}")
        print(f"  Owner: {device.owner_user_id}")

        # Create sign-in event
        signin = test_data_generator.create_sign_in_event(
            user_id=user.user_id,
            user_principal_name=user.user_principal_name,
            device_id=device.device_id,
            result="Success",
            risk_level="Low"
        )

        print(f"\nCreated sign-in:")
        print(f"  Event ID: {signin.event_id}")
        print(f"  Result: {signin.result}")
        print(f"  Location: {signin.location}")

        # Verify relationships
        assert device.owner_user_id == user.user_id
        assert signin.user_id == user.user_id
        assert signin.device_id == device.device_id


# Skip marker for CI/CD (these are examples)
pytestmark = pytest.mark.skip(reason="Example tests - not meant to run in CI")
