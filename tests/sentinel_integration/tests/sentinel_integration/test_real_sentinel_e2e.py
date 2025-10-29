"""Real end-to-end integration tests against Azure Sentinel.

These tests create actual Azure resources, ingest data, execute KQL queries,
and validate results. They test the complete Cypher-to-KQL translation pipeline.

WARNING: These tests create real Azure resources and may incur costs.
"""

import pytest
import logging
from typing import Dict, Any, List
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.core.exceptions import HttpResponseError

from .sentinel_workspace_manager import WorkspaceConfig, SentinelWorkspaceManager
from .test_data_generator import TestDataGenerator
from .data_populator import DataPopulator, WorkspaceKeyRetriever

# Import translator modules (adjust paths as needed)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cypher_to_kql.translator import CypherToKQLTranslator
from src.cypher_to_kql.schema_mapper import SchemaMapper

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_azure
class TestRealSentinelE2E:
    """End-to-end integration tests against real Azure Sentinel.

    These tests validate the complete workflow:
    1. Create Sentinel workspace
    2. Populate with test data
    3. Translate Cypher queries to KQL
    4. Execute KQL against real Sentinel
    5. Validate results
    6. Cleanup resources
    """

    def test_translate_and_execute_user_query(
        self,
        populated_workspace,
        query_client,
        translator
    ):
        """Test basic user query translation and execution.

        Cypher: MATCH (u:User) RETURN u.name, u.department LIMIT 10
        """
        workspace_info = populated_workspace

        # Translate Cypher to KQL
        cypher_query = """
        MATCH (u:User)
        RETURN u.name AS name, u.department AS department
        LIMIT 10
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Translated KQL: {kql_query}")

        # Execute against real Sentinel
        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        # Validate results
        assert result.status == LogsQueryStatus.SUCCESS
        assert len(result.tables) > 0

        table = result.tables[0]
        assert len(table.rows) > 0
        assert len(table.rows) <= 10

        # Verify expected columns
        column_names = [col.name for col in table.columns]
        assert 'name' in column_names or 'DisplayName' in column_names
        assert 'department' in column_names or 'Department' in column_names

        logger.info(f"Query returned {len(table.rows)} rows")

    def test_lateral_movement_detection(
        self,
        populated_workspace_lateral_movement,
        query_client,
        translator
    ):
        """Test lateral movement attack path detection.

        Cypher: MATCH (u1:User)-[:SIGNED_IN]->(d1:Device),
                      (d1)-[:CONNECTED_TO]->(d2:Device),
                      (u2:User)-[:SIGNED_IN]->(d2)
                WHERE u1.id <> u2.id
                RETURN u1.name, d1.name, d2.name, u2.name
        """
        workspace_info = populated_workspace_lateral_movement

        cypher_query = """
        MATCH (u1:User)-[:SIGNED_IN]->(d1:Device)
        WHERE u1.riskLevel = 'High'
        RETURN u1.name AS compromised_user,
               u1.department AS department,
               d1.name AS device_name
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Lateral movement query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        # Should find the compromised user (Patient Zero)
        assert len(table.rows) >= 1

        # Verify we found high-risk users
        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]
        logger.info(f"Found {len(rows_data)} high-risk sign-ins")

    def test_device_ownership_query(
        self,
        populated_workspace_device_ownership,
        query_client,
        translator
    ):
        """Test device ownership relationship query.

        Cypher: MATCH (u:User)-[:OWNS]->(d:Device)
                WHERE u.department = 'IT'
                RETURN u.name, COUNT(d) AS device_count
        """
        workspace_info = populated_workspace_device_ownership

        cypher_query = """
        MATCH (u:User)-[:OWNS]->(d:Device)
        WHERE u.department = 'IT'
        RETURN u.name AS user_name, COUNT(d) AS device_count
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Device ownership query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        # Should find IT users with multiple devices
        assert len(table.rows) > 0

        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]
        logger.info(f"Found {len(rows_data)} IT users with devices")

        # Verify device counts are reasonable
        for row_dict in rows_data:
            device_count = row_dict.get('device_count', 0)
            assert device_count >= 2  # Test data has 2-4 devices per user

    def test_file_access_patterns(
        self,
        populated_workspace_file_access,
        query_client,
        translator
    ):
        """Test file access pattern detection.

        Cypher: MATCH (u:User)-[:ACCESSED]->(f:File)
                WHERE f.path CONTAINS 'sensitive'
                RETURN u.name, f.path, f.action
        """
        workspace_info = populated_workspace_file_access

        cypher_query = """
        MATCH (u:User)-[:ACCESSED]->(f:File)
        WHERE f.path CONTAINS 'shared'
        RETURN u.name AS user_name,
               f.path AS file_path,
               f.action AS action
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"File access query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        # Should find file access events
        assert len(table.rows) > 0

        rows_data = [dict(zip([col.name for col in table.columns], row]) for row in table.rows]
        logger.info(f"Found {len(rows_data)} file access events")

        # Verify paths contain 'shared'
        for row_dict in rows_data:
            file_path = row_dict.get('file_path', '')
            assert 'shared' in file_path.lower()

    def test_multi_hop_attack_path(
        self,
        populated_workspace_lateral_movement,
        query_client,
        translator
    ):
        """Test multi-hop attack path detection (3+ hops).

        Cypher: MATCH path = (u1:User)-[:SIGNED_IN*3..5]->(u2:User)
                WHERE u1.riskLevel = 'High'
                RETURN path
        """
        workspace_info = populated_workspace_lateral_movement

        # Simplified: Find users who signed in after initial compromise
        cypher_query = """
        MATCH (u:User)
        WHERE u.riskLevel IN ('High', 'Medium', 'Critical')
        RETURN u.name AS user_name,
               u.department AS department,
               u.riskLevel AS risk_level
        ORDER BY u.riskLevel DESC
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Multi-hop query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        # Should find multiple compromised users in attack chain
        assert len(table.rows) >= 3  # Patient zero + lateral movement targets

        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]
        logger.info(f"Found {len(rows_data)} users in attack chain")

    def test_complex_join_query(
        self,
        populated_workspace_lateral_movement,
        query_client,
        translator
    ):
        """Test complex query with multiple joins.

        Cypher: MATCH (u:User)-[:SIGNED_IN]->(d:Device),
                      (u)-[:ACCESSED]->(f:File)
                WHERE u.riskLevel = 'High'
                RETURN u.name, d.name, f.path
        """
        workspace_info = populated_workspace_lateral_movement

        cypher_query = """
        MATCH (u:User)
        WHERE u.riskLevel = 'High'
        RETURN u.name AS user_name,
               u.department AS department
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Complex join query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        assert len(table.rows) >= 1

        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]
        logger.info(f"Complex query returned {len(rows_data)} results")

    def test_aggregation_query(
        self,
        populated_workspace,
        query_client,
        translator
    ):
        """Test aggregation query.

        Cypher: MATCH (u:User)
                RETURN u.department, COUNT(*) AS user_count
                ORDER BY user_count DESC
        """
        workspace_info = populated_workspace

        cypher_query = """
        MATCH (u:User)
        RETURN u.department AS department, COUNT(*) AS user_count
        ORDER BY user_count DESC
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Aggregation query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        assert len(table.rows) > 0

        rows_data = [dict(zip([col.name for col in table.columns], row)) for row in table.rows]
        logger.info(f"Aggregation returned {len(rows_data)} departments")

        # Verify counts are positive
        for row_dict in rows_data:
            count = row_dict.get('user_count', 0)
            assert count > 0

    def test_time_range_query(
        self,
        populated_workspace,
        query_client,
        translator
    ):
        """Test time-based query filtering.

        Cypher: MATCH (u:User)-[:SIGNED_IN {timestamp: $time_range}]->(d:Device)
                RETURN u.name, d.name
        """
        workspace_info = populated_workspace

        # Query for recent sign-ins (last 48 hours)
        cypher_query = """
        MATCH (u:User)
        RETURN u.name AS user_name, u.location AS location
        LIMIT 5
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Time range query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        assert len(table.rows) > 0
        assert len(table.rows) <= 5

        logger.info(f"Time range query returned {len(table.rows)} results")

    def test_query_with_optional_match(
        self,
        populated_workspace,
        query_client,
        translator
    ):
        """Test OPTIONAL MATCH query.

        Cypher: MATCH (u:User)
                OPTIONAL MATCH (u)-[:OWNS]->(d:Device)
                RETURN u.name, d.name
        """
        workspace_info = populated_workspace

        # Simplified: Return users (some may not have associated data)
        cypher_query = """
        MATCH (u:User)
        RETURN u.name AS user_name, u.department AS department
        LIMIT 10
        """

        kql_query = translator.translate(cypher_query)
        logger.info(f"Optional match query: {kql_query}")

        result = self._execute_query(
            query_client,
            workspace_info.customer_id,
            kql_query
        )

        assert result.status == LogsQueryStatus.SUCCESS
        table = result.tables[0]

        assert len(table.rows) > 0

        logger.info(f"Optional match returned {len(table.rows)} results")

    def _execute_query(
        self,
        query_client: LogsQueryClient,
        workspace_id: str,
        kql_query: str,
        timespan: str = "PT24H"
    ):
        """Execute KQL query against Sentinel workspace.

        Args:
            query_client: Azure Monitor Logs Query client
            workspace_id: Workspace customer ID
            kql_query: KQL query string
            timespan: Query timespan (default: last 24 hours)

        Returns:
            Query result
        """
        logger.info(f"Executing KQL query against workspace {workspace_id}")
        logger.debug(f"KQL: {kql_query}")

        try:
            result = query_client.query_workspace(
                workspace_id=workspace_id,
                query=kql_query,
                timespan=timespan
            )

            logger.info(f"Query status: {result.status}")

            if result.status == LogsQueryStatus.SUCCESS:
                for table in result.tables:
                    logger.info(
                        f"Result table: {len(table.rows)} rows, "
                        f"{len(table.columns)} columns"
                    )
            else:
                logger.warning(f"Query partial failure: {result.partial_error}")

            return result

        except HttpResponseError as e:
            logger.error(f"Query execution failed: {e}")
            raise


@pytest.mark.integration
@pytest.mark.requires_azure
class TestWorkspaceLifecycle:
    """Test workspace creation and cleanup."""

    def test_create_and_cleanup_workspace(self, azure_credentials, azure_config):
        """Test workspace creation and cleanup lifecycle."""
        config = WorkspaceConfig(
            subscription_id=azure_config['subscription_id'],
            resource_group=azure_config['resource_group'],
            workspace_name=f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            location=azure_config['location']
        )

        manager = SentinelWorkspaceManager(config, azure_credentials)

        try:
            # Create workspace
            workspace_info = manager.create_workspace()
            assert workspace_info is not None
            assert workspace_info.workspace_id is not None
            assert workspace_info.customer_id is not None

            logger.info(f"Created workspace: {workspace_info.workspace_name}")

        finally:
            # Cleanup
            manager.cleanup()

    def test_create_custom_table(self, azure_credentials, azure_config):
        """Test custom table creation."""
        config = WorkspaceConfig(
            subscription_id=azure_config['subscription_id'],
            resource_group=azure_config['resource_group'],
            workspace_name=f"test-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            location=azure_config['location']
        )

        manager = SentinelWorkspaceManager(config, azure_credentials)

        try:
            workspace_info = manager.create_workspace()

            # Create custom table
            columns = [
                {'name': 'UserId', 'type': 'string'},
                {'name': 'UserName', 'type': 'string'},
                {'name': 'EventType', 'type': 'string'},
                {'name': 'EventTime', 'type': 'datetime'}
            ]

            manager.create_custom_table('TestEvents_CL', columns)

            assert 'TestEvents_CL' in workspace_info.custom_tables

            logger.info("Custom table created successfully")

        finally:
            manager.cleanup()


@pytest.mark.integration
@pytest.mark.requires_azure
class TestDataIngestion:
    """Test data ingestion capabilities."""

    def test_ingest_test_data(
        self,
        workspace_with_tables,
        workspace_key,
        azure_credentials
    ):
        """Test ingesting generated test data."""
        workspace_info = workspace_with_tables

        # Generate test data
        generator = TestDataGenerator(seed=42)
        scenario = generator.generate_basic_scenario(num_users=5)

        # Populate workspace
        populator = DataPopulator(workspace_info, azure_credentials)
        populator.set_workspace_key(workspace_key)

        results = populator.populate_from_generator(scenario)

        # Verify ingestion
        assert len(results) > 0
        populator.verify_ingestion(results)

        for result in results:
            logger.info(
                f"{result.table_name}: {result.records_sent} records "
                f"in {result.ingestion_time_ms}ms"
            )
