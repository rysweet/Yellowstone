"""
Comprehensive test suite for persistent graph module.

This module contains 40+ tests covering all aspects of persistent graph
management, including graph lifecycle, snapshots, versioning, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock

from yellowstone.persistent_graph import (
    GraphManager,
    GraphBuilder,
    SnapshotManager,
    PersistentGraph,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition,
    GraphStatus,
    GraphSnapshot,
    SnapshotType,
    SnapshotStatus,
)


# Fixtures

@pytest.fixture
def workspace_id():
    """Test workspace ID."""
    return "test-workspace-123"


@pytest.fixture
def simple_schema():
    """Simple graph schema for testing."""
    return GraphSchema(
        nodes=[
            NodeDefinition(
                label='Alert',
                source_table='SecurityAlert',
                id_property='AlertId',
                properties={
                    'AlertId': 'SystemAlertId',
                    'severity': 'AlertSeverity',
                    'timestamp': 'TimeGenerated',
                }
            ),
            NodeDefinition(
                label='User',
                source_table='IdentityInfo',
                id_property='UserId',
                properties={
                    'UserId': 'AccountObjectId',
                    'name': 'AccountDisplayName',
                    'email': 'AccountUPN',
                }
            ),
        ],
        edges=[
            EdgeDefinition(
                type='TRIGGERED_BY',
                from_label='Alert',
                to_label='User',
                join_condition='Alert.UserId == User.UserId',
                strength='high',
            )
        ]
    )


@pytest.fixture
def complex_schema():
    """Complex graph schema for testing."""
    return GraphSchema(
        nodes=[
            NodeDefinition(
                label='Alert',
                source_table='SecurityAlert',
                id_property='AlertId',
                properties={'AlertId': 'SystemAlertId', 'severity': 'AlertSeverity'},
                filters=['AlertSeverity in ("High", "Medium")']
            ),
            NodeDefinition(
                label='User',
                source_table='IdentityInfo',
                id_property='UserId',
                properties={'UserId': 'AccountObjectId', 'name': 'AccountDisplayName'}
            ),
            NodeDefinition(
                label='Device',
                source_table='DeviceInfo',
                id_property='DeviceId',
                properties={'DeviceId': 'DeviceName', 'os': 'OSPlatform'}
            ),
        ],
        edges=[
            EdgeDefinition(
                type='TRIGGERED_BY',
                from_label='Alert',
                to_label='User',
                join_condition='Alert.UserId == User.UserId',
                strength='high',
            ),
            EdgeDefinition(
                type='ORIGINATED_FROM',
                from_label='Alert',
                to_label='Device',
                join_condition='Alert.DeviceId == Device.DeviceId',
                strength='medium',
            ),
        ]
    )


@pytest.fixture
def mock_sentinel_client():
    """Mock Sentinel API client for testing."""
    client = Mock()

    # Mock execute_management_command
    client.execute_management_command.return_value = {
        'status': 'success',
        'command': 'mocked',
        'execution_time_ms': 100,
    }

    # Mock execute_kql
    client.execute_kql.return_value = {
        'status': 'success',
        'columns': ['node_id', 'node_label', 'properties'],
        'rows': [
            ['n1', 'Alert', {'severity': 'high'}],
            ['n2', 'User', {'name': 'alice'}],
        ],
        'row_count': 2,
        'execution_time_ms': 45,
    }

    return client


@pytest.fixture
def graph_manager(workspace_id, mock_sentinel_client):
    """Graph manager instance with mocked Sentinel client."""
    return GraphManager(workspace_id, api_client=mock_sentinel_client)


@pytest.fixture
def snapshot_manager(workspace_id):
    """Snapshot manager instance."""
    return SnapshotManager(workspace_id)


# Model Tests

class TestModels:
    """Tests for data models."""

    def test_node_definition_validation(self):
        """Test node definition validation."""
        # Valid node
        node = NodeDefinition(
            label='Alert',
            source_table='SecurityAlert',
            id_property='AlertId',
            properties={'severity': 'AlertSeverity'}
        )
        assert node.label == 'Alert'

    def test_node_label_must_start_uppercase(self):
        """Test that node labels must start with uppercase."""
        with pytest.raises(ValueError, match="must start with uppercase"):
            NodeDefinition(
                label='alert',
                source_table='SecurityAlert',
                id_property='AlertId',
                properties={}
            )

    def test_node_label_alphanumeric(self):
        """Test that node labels must be alphanumeric."""
        with pytest.raises(ValueError, match="must be alphanumeric"):
            NodeDefinition(
                label='Alert@Type',
                source_table='SecurityAlert',
                id_property='AlertId',
                properties={}
            )

    def test_edge_definition_validation(self):
        """Test edge definition validation."""
        edge = EdgeDefinition(
            type='TRIGGERED_BY',
            from_label='Alert',
            to_label='User',
            join_condition='Alert.UserId == User.UserId',
            strength='high',
        )
        assert edge.type == 'TRIGGERED_BY'
        assert edge.strength == 'high'

    def test_edge_type_must_start_uppercase(self):
        """Test that edge types must start with uppercase."""
        with pytest.raises(ValueError, match="must start with uppercase"):
            EdgeDefinition(
                type='triggered_by',
                from_label='Alert',
                to_label='User',
                join_condition='x == y',
            )

    def test_edge_invalid_strength(self):
        """Test edge with invalid strength."""
        with pytest.raises(ValueError, match="Strength must be"):
            EdgeDefinition(
                type='TRIGGERED_BY',
                from_label='Alert',
                to_label='User',
                join_condition='x == y',
                strength='invalid',
            )

    def test_graph_schema_get_node(self, simple_schema):
        """Test getting node by label."""
        node = simple_schema.get_node('Alert')
        assert node is not None
        assert node.label == 'Alert'

        # Non-existent node
        assert simple_schema.get_node('NonExistent') is None

    def test_graph_schema_get_edge(self, simple_schema):
        """Test getting edge by type."""
        edge = simple_schema.get_edge('TRIGGERED_BY')
        assert edge is not None
        assert edge.type == 'TRIGGERED_BY'

    def test_graph_schema_validate_edges(self, simple_schema):
        """Test edge validation in schema."""
        errors = simple_schema.validate_edges()
        assert len(errors) == 0

    def test_graph_schema_validate_edges_invalid(self):
        """Test edge validation with invalid references."""
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='AlertId',
                    properties={}
                )
            ],
            edges=[
                EdgeDefinition(
                    type='RELATED_TO',
                    from_label='Alert',
                    to_label='NonExistent',
                    join_condition='x == y',
                )
            ]
        )
        errors = schema.validate_edges()
        assert len(errors) > 0
        assert 'NonExistent' in errors[0]

    def test_persistent_graph_name_validation(self, workspace_id, simple_schema):
        """Test persistent graph name validation."""
        # Valid names
        graph = PersistentGraph(
            name='MyGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        assert graph.name == 'MyGraph'

        # Too short
        with pytest.raises(ValueError, match="at least 3 characters"):
            PersistentGraph(
                name='ab',
                workspace_id=workspace_id,
                schema=simple_schema,
            )

        # Must start with letter
        with pytest.raises(ValueError, match="must start with a letter"):
            PersistentGraph(
                name='123Graph',
                workspace_id=workspace_id,
                schema=simple_schema,
            )

    def test_persistent_graph_update_status(self, workspace_id, simple_schema):
        """Test updating graph status."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        old_time = graph.updated_at
        graph.update_status(GraphStatus.ACTIVE)

        assert graph.status == GraphStatus.ACTIVE
        assert graph.updated_at > old_time

    def test_persistent_graph_increment_version(self, workspace_id, simple_schema):
        """Test incrementing graph version."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        assert graph.version == 1
        graph.increment_version()
        assert graph.version == 2

    def test_snapshot_id_validation(self):
        """Test snapshot ID validation."""
        # Valid ID
        snapshot = GraphSnapshot(
            snapshot_id='snap_12345678',
            graph_name='TestGraph',
            graph_version=1,
        )
        assert snapshot.snapshot_id == 'snap_12345678'

        # Too short
        with pytest.raises(ValueError, match="at least 8 characters"):
            GraphSnapshot(
                snapshot_id='short',
                graph_name='TestGraph',
                graph_version=1,
            )

    def test_snapshot_complete(self):
        """Test marking snapshot as complete."""
        snapshot = GraphSnapshot(
            snapshot_id='snap_12345678',
            graph_name='TestGraph',
            graph_version=1,
        )

        assert snapshot.status == SnapshotStatus.CREATING
        snapshot.complete(node_count=1000, edge_count=5000, size_bytes=1024000)

        assert snapshot.status == SnapshotStatus.READY
        assert snapshot.node_count == 1000
        assert snapshot.edge_count == 5000
        assert snapshot.size_bytes == 1024000
        assert snapshot.completed_at is not None

    def test_snapshot_fail(self):
        """Test marking snapshot as failed."""
        snapshot = GraphSnapshot(
            snapshot_id='snap_12345678',
            graph_name='TestGraph',
            graph_version=1,
        )

        snapshot.fail("Connection timeout")

        assert snapshot.status == SnapshotStatus.FAILED
        assert snapshot.error_message == "Connection timeout"
        assert snapshot.completed_at is not None


# GraphBuilder Tests

class TestGraphBuilder:
    """Tests for GraphBuilder."""

    def test_build_create_statement(self, workspace_id, simple_schema):
        """Test building create statement."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        builder = GraphBuilder(graph)
        kql = builder.build_create_statement()

        assert '.create-or-alter persistent-graph TestGraph' in kql
        assert 'SecurityAlert' in kql
        assert 'make-graph' in kql

    def test_build_delete_statement(self, workspace_id, simple_schema):
        """Test building delete statement."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        builder = GraphBuilder(graph)
        kql = builder.build_delete_statement()

        assert '.drop persistent-graph TestGraph' in kql

    def test_build_query_statement(self, workspace_id, simple_schema):
        """Test building query statement."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        builder = GraphBuilder(graph)
        kql = builder.build_query_statement()

        assert "persistent-graph('TestGraph')" in kql

    def test_validate_schema_success(self, workspace_id, simple_schema):
        """Test schema validation success."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()

        assert len(errors) == 0

    def test_validate_schema_no_nodes(self, workspace_id):
        """Test schema validation with no nodes."""
        schema = GraphSchema(nodes=[], edges=[])
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=schema,
        )
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()

        assert len(errors) > 0
        assert any('at least one node' in e for e in errors)

    def test_validate_schema_duplicate_labels(self, workspace_id):
        """Test schema validation with duplicate node labels."""
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='AlertId',
                    properties={}
                ),
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert2',
                    id_property='AlertId',
                    properties={}
                ),
            ]
        )
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=schema,
        )
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()

        assert len(errors) > 0
        assert any('Duplicate node labels' in e for e in errors)

    def test_validate_schema_invalid_edge_reference(self, workspace_id):
        """Test schema validation with invalid edge reference."""
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='AlertId',
                    properties={}
                )
            ],
            edges=[
                EdgeDefinition(
                    type='RELATED_TO',
                    from_label='Alert',
                    to_label='NonExistent',
                    join_condition='x == y',
                )
            ]
        )
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=schema,
        )
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()

        assert len(errors) > 0
        assert any('NonExistent' in e for e in errors)

    def test_estimate_performance(self, workspace_id, simple_schema):
        """Test performance estimation."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )
        builder = GraphBuilder(graph)
        perf = builder.estimate_performance()

        assert perf['node_types'] == 2
        assert perf['edge_types'] == 1
        assert perf['expected_speedup'] >= 10
        assert perf['supports_incremental_updates'] is True

    def test_generate_documentation(self, workspace_id, simple_schema):
        """Test documentation generation."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
            description='A test graph'
        )
        builder = GraphBuilder(graph)
        docs = builder.generate_documentation()

        assert '# Persistent Graph: TestGraph' in docs
        assert 'A test graph' in docs
        assert '## Node Types' in docs
        assert '### Alert' in docs
        assert '## Edge Types' in docs


# SnapshotManager Tests

class TestSnapshotManager:
    """Tests for SnapshotManager."""

    def test_create_full_snapshot(self, snapshot_manager, workspace_id, simple_schema):
        """Test creating a full snapshot."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot = snapshot_manager.create_snapshot(graph)

        assert snapshot.snapshot_id.startswith('snap_')
        assert snapshot.graph_name == 'TestGraph'
        assert snapshot.snapshot_type == SnapshotType.FULL
        assert snapshot.status == SnapshotStatus.READY
        assert snapshot.node_count > 0
        assert snapshot.edge_count > 0

    def test_create_differential_snapshot(self, snapshot_manager, workspace_id, simple_schema):
        """Test creating a differential snapshot."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        # Create base snapshot first
        base = snapshot_manager.create_snapshot(graph)

        # Create differential snapshot
        diff = snapshot_manager.create_snapshot(
            graph,
            snapshot_type=SnapshotType.DIFFERENTIAL,
            base_snapshot_id=base.snapshot_id,
        )

        assert diff.snapshot_type == SnapshotType.DIFFERENTIAL
        assert diff.base_snapshot_id == base.snapshot_id
        assert diff.status == SnapshotStatus.READY

    def test_create_differential_without_base(self, snapshot_manager, workspace_id, simple_schema):
        """Test creating differential snapshot without base fails."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        with pytest.raises(ValueError, match="requires base_snapshot_id"):
            snapshot_manager.create_snapshot(
                graph,
                snapshot_type=SnapshotType.DIFFERENTIAL,
            )

    def test_create_differential_invalid_base(self, snapshot_manager, workspace_id, simple_schema):
        """Test creating differential snapshot with invalid base fails."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        with pytest.raises(ValueError, match="not found"):
            snapshot_manager.create_snapshot(
                graph,
                snapshot_type=SnapshotType.DIFFERENTIAL,
                base_snapshot_id='invalid_id',
            )

    def test_get_snapshot(self, snapshot_manager, workspace_id, simple_schema):
        """Test retrieving snapshot by ID."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        created = snapshot_manager.create_snapshot(graph)
        retrieved = snapshot_manager.get_snapshot(created.snapshot_id)

        assert retrieved is not None
        assert retrieved.snapshot_id == created.snapshot_id

    def test_get_snapshot_not_found(self, snapshot_manager):
        """Test retrieving non-existent snapshot."""
        result = snapshot_manager.get_snapshot('nonexistent')
        assert result is None

    def test_list_snapshots(self, snapshot_manager, workspace_id, simple_schema):
        """Test listing snapshots."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        # Create multiple snapshots
        snapshot_manager.create_snapshot(graph)
        snapshot_manager.create_snapshot(graph)

        snapshots = snapshot_manager.list_snapshots(graph_name='TestGraph')
        assert len(snapshots) == 2

    def test_list_snapshots_filter_by_status(self, snapshot_manager, workspace_id, simple_schema):
        """Test listing snapshots filtered by status."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot_manager.create_snapshot(graph)

        ready_snapshots = snapshot_manager.list_snapshots(status=SnapshotStatus.READY)
        assert len(ready_snapshots) >= 1

    def test_restore_full_snapshot(self, snapshot_manager, workspace_id, simple_schema):
        """Test restoring from full snapshot."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
            version=5,
        )

        snapshot = snapshot_manager.create_snapshot(graph)
        restored = snapshot_manager.restore_snapshot(snapshot.snapshot_id)

        assert restored.name == 'TestGraph'
        assert restored.version == 5
        assert restored.schema.nodes[0].label == 'Alert'

    def test_restore_with_new_name(self, snapshot_manager, workspace_id, simple_schema):
        """Test restoring snapshot with new name."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot = snapshot_manager.create_snapshot(graph)
        restored = snapshot_manager.restore_snapshot(
            snapshot.snapshot_id,
            target_graph_name='RestoredGraph'
        )

        assert restored.name == 'RestoredGraph'

    def test_restore_not_ready(self, snapshot_manager, workspace_id, simple_schema):
        """Test restoring snapshot that's not ready fails."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot = snapshot_manager.create_snapshot(graph)
        snapshot.status = SnapshotStatus.CREATING

        with pytest.raises(ValueError, match="not ready"):
            snapshot_manager.restore_snapshot(snapshot.snapshot_id)

    def test_delete_snapshot(self, snapshot_manager, workspace_id, simple_schema):
        """Test deleting snapshot."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot = snapshot_manager.create_snapshot(graph)
        result = snapshot_manager.delete_snapshot(snapshot.snapshot_id)

        assert result is True
        assert snapshot_manager.get_snapshot(snapshot.snapshot_id) is None

    def test_delete_nonexistent_snapshot(self, snapshot_manager):
        """Test deleting non-existent snapshot."""
        result = snapshot_manager.delete_snapshot('nonexistent')
        assert result is False

    def test_cleanup_expired_snapshots(self, snapshot_manager, workspace_id, simple_schema):
        """Test cleaning up expired snapshots."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        # Create snapshot with short retention
        snapshot = snapshot_manager.create_snapshot(graph, retention_days=1)

        # Simulate expiration
        snapshot.created_at = datetime.utcnow() - timedelta(days=2)

        deleted = snapshot_manager.cleanup_expired_snapshots()
        assert snapshot.snapshot_id in deleted

    def test_compare_snapshots(self, snapshot_manager, workspace_id, simple_schema):
        """Test comparing two snapshots."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snap1 = snapshot_manager.create_snapshot(graph)
        graph.increment_version()
        snap2 = snapshot_manager.create_snapshot(graph)

        diff = snapshot_manager.compare_snapshots(snap1.snapshot_id, snap2.snapshot_id)

        assert diff['version_delta'] == 1
        assert 'node_count_delta' in diff
        assert 'edge_count_delta' in diff

    def test_get_snapshot_chain(self, snapshot_manager, workspace_id, simple_schema):
        """Test getting snapshot chain."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        # Create base snapshot
        base = snapshot_manager.create_snapshot(graph)

        # Create differential snapshot
        diff = snapshot_manager.create_snapshot(
            graph,
            snapshot_type=SnapshotType.DIFFERENTIAL,
            base_snapshot_id=base.snapshot_id,
        )

        chain = snapshot_manager.get_snapshot_chain(diff.snapshot_id)
        assert len(chain) == 2
        assert chain[0].snapshot_id == base.snapshot_id
        assert chain[1].snapshot_id == diff.snapshot_id

    def test_estimate_restore_time(self, snapshot_manager, workspace_id, simple_schema):
        """Test estimating restore time."""
        graph = PersistentGraph(
            name='TestGraph',
            workspace_id=workspace_id,
            schema=simple_schema,
        )

        snapshot = snapshot_manager.create_snapshot(graph)
        estimate = snapshot_manager.estimate_restore_time(snapshot.snapshot_id)

        assert 'estimated_seconds' in estimate
        assert 'snapshot_chain_length' in estimate
        assert estimate['estimated_seconds'] > 0


# GraphManager Tests

class TestGraphManager:
    """Tests for GraphManager."""

    def test_create_graph(self, graph_manager, simple_schema):
        """Test creating a persistent graph."""
        graph = graph_manager.create_graph('TestGraph', simple_schema)

        assert graph.name == 'TestGraph'
        assert graph.status == GraphStatus.ACTIVE
        assert graph.version == 1

    def test_create_graph_with_description(self, graph_manager, simple_schema):
        """Test creating graph with description."""
        graph = graph_manager.create_graph(
            'TestGraph',
            simple_schema,
            description='A test graph'
        )

        assert graph.description == 'A test graph'

    def test_create_graph_duplicate_name(self, graph_manager, simple_schema):
        """Test creating graph with duplicate name fails."""
        graph_manager.create_graph('TestGraph', simple_schema)

        with pytest.raises(ValueError, match="already exists"):
            graph_manager.create_graph('TestGraph', simple_schema)

    def test_create_graph_invalid_schema(self, graph_manager):
        """Test creating graph with invalid schema fails."""
        schema = GraphSchema(nodes=[], edges=[])

        with pytest.raises(ValueError, match="validation failed"):
            graph_manager.create_graph('TestGraph', schema)

    def test_create_graph_with_snapshot(self, graph_manager, simple_schema):
        """Test creating graph with initial snapshot."""
        graph = graph_manager.create_graph(
            'TestGraph',
            simple_schema,
            create_snapshot=True
        )

        assert graph.last_snapshot_id is not None

    def test_get_graph(self, graph_manager, simple_schema):
        """Test retrieving graph by name."""
        created = graph_manager.create_graph('TestGraph', simple_schema)
        retrieved = graph_manager.get_graph('TestGraph')

        assert retrieved is not None
        assert retrieved.name == created.name

    def test_get_graph_not_found(self, graph_manager):
        """Test retrieving non-existent graph."""
        result = graph_manager.get_graph('NonExistent')
        assert result is None

    def test_update_graph(self, graph_manager, simple_schema, complex_schema):
        """Test updating a graph."""
        graph = graph_manager.create_graph('TestGraph', simple_schema)
        assert graph.version == 1

        updated = graph_manager.update_graph(
            'TestGraph',
            complex_schema,
            changes=['Added Device nodes']
        )

        assert updated.version == 2
        assert len(updated.schema.nodes) == 3

    def test_update_graph_not_found(self, graph_manager, simple_schema):
        """Test updating non-existent graph fails."""
        with pytest.raises(ValueError, match="not found"):
            graph_manager.update_graph('NonExistent', simple_schema)

    def test_delete_graph(self, graph_manager, simple_schema):
        """Test deleting a graph."""
        graph_manager.create_graph('TestGraph', simple_schema)
        result = graph_manager.delete_graph('TestGraph')

        assert result is True
        assert graph_manager.get_graph('TestGraph') is None

    def test_delete_graph_not_found(self, graph_manager):
        """Test deleting non-existent graph."""
        result = graph_manager.delete_graph('NonExistent')
        assert result is False

    def test_delete_graph_with_snapshots_without_force(self, graph_manager, simple_schema):
        """Test deleting graph with snapshots without force fails."""
        graph = graph_manager.create_graph('TestGraph', simple_schema, create_snapshot=True)

        with pytest.raises(ValueError, match="has .* snapshots"):
            graph_manager.delete_graph('TestGraph', force=False)

    def test_delete_graph_with_snapshots_with_force(self, graph_manager, simple_schema):
        """Test deleting graph with snapshots with force."""
        graph = graph_manager.create_graph('TestGraph', simple_schema, create_snapshot=True)
        result = graph_manager.delete_graph('TestGraph', force=True)

        assert result is True

    def test_list_graphs(self, graph_manager, simple_schema):
        """Test listing graphs."""
        graph_manager.create_graph('Graph1', simple_schema)
        graph_manager.create_graph('Graph2', simple_schema)

        graphs = graph_manager.list_graphs()
        assert len(graphs) == 2

    def test_list_graphs_filter_by_status(self, graph_manager, simple_schema):
        """Test listing graphs filtered by status."""
        graph_manager.create_graph('Graph1', simple_schema)

        active_graphs = graph_manager.list_graphs(status=GraphStatus.ACTIVE)
        assert len(active_graphs) == 1

    def test_get_version_history(self, graph_manager, simple_schema, complex_schema):
        """Test getting version history."""
        graph_manager.create_graph('TestGraph', simple_schema)
        graph_manager.update_graph('TestGraph', complex_schema, changes=['Added nodes'])

        versions = graph_manager.get_version_history('TestGraph')
        assert len(versions) == 2
        assert versions[0].version == 1
        assert versions[1].version == 2

    def test_rollback_version(self, graph_manager, simple_schema, complex_schema):
        """Test rolling back to previous version."""
        graph_manager.create_graph('TestGraph', simple_schema)
        graph_manager.update_graph('TestGraph', complex_schema)

        # Rollback to version 1
        graph = graph_manager.rollback_version('TestGraph', 1)

        assert graph.version == 3  # New version with old schema
        assert len(graph.schema.nodes) == 2  # Back to simple schema

    def test_rollback_nonexistent_version(self, graph_manager, simple_schema):
        """Test rolling back to non-existent version fails."""
        graph_manager.create_graph('TestGraph', simple_schema)

        with pytest.raises(ValueError, match="not found"):
            graph_manager.rollback_version('TestGraph', 99)

    def test_query_graph(self, graph_manager, simple_schema):
        """Test querying a graph."""
        graph_manager.create_graph('TestGraph', simple_schema)

        results = graph_manager.query_graph(
            'TestGraph',
            "persistent-graph('TestGraph') | graph-match ..."
        )

        assert 'rows' in results
        assert results['row_count'] > 0

    def test_query_inactive_graph(self, graph_manager, simple_schema):
        """Test querying inactive graph fails."""
        graph = graph_manager.create_graph('TestGraph', simple_schema)
        graph.update_status(GraphStatus.DELETING)

        with pytest.raises(ValueError, match="not active"):
            graph_manager.query_graph('TestGraph', "...")

    def test_get_metrics(self, graph_manager, simple_schema):
        """Test getting graph metrics."""
        graph_manager.create_graph('TestGraph', simple_schema)
        metrics = graph_manager.get_metrics('TestGraph')

        assert metrics is not None
        assert metrics.graph_name == 'TestGraph'

    def test_refresh_graph(self, graph_manager, simple_schema):
        """Test refreshing graph data."""
        graph = graph_manager.create_graph('TestGraph', simple_schema)
        old_time = graph.updated_at

        import time
        time.sleep(0.01)  # Ensure time difference

        refreshed = graph_manager.refresh_graph('TestGraph')
        assert refreshed.updated_at > old_time

    def test_get_operation_status(self, graph_manager, simple_schema):
        """Test getting operation status."""
        graph_manager.create_graph('TestGraph', simple_schema)
        ops = graph_manager.list_operations(graph_name='TestGraph')

        assert len(ops) > 0
        op = graph_manager.get_operation_status(ops[0].operation_id)
        assert op is not None
        assert op.status == 'completed'

    def test_list_operations(self, graph_manager, simple_schema, complex_schema):
        """Test listing operations."""
        graph_manager.create_graph('TestGraph', simple_schema)
        graph_manager.update_graph('TestGraph', complex_schema)

        ops = graph_manager.list_operations(graph_name='TestGraph')
        assert len(ops) >= 2  # create and update

    def test_list_operations_filter_by_type(self, graph_manager, simple_schema):
        """Test listing operations filtered by type."""
        graph_manager.create_graph('TestGraph', simple_schema)

        create_ops = graph_manager.list_operations(operation_type='create')
        assert len(create_ops) >= 1
        assert all(op.operation_type == 'create' for op in create_ops)


# Integration Tests

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_lifecycle(self, graph_manager, simple_schema, complex_schema):
        """Test complete graph lifecycle."""
        # Create
        graph = graph_manager.create_graph('LifecycleTest', simple_schema)
        assert graph.status == GraphStatus.ACTIVE

        # Update
        updated = graph_manager.update_graph('LifecycleTest', complex_schema)
        assert updated.version == 2

        # Query
        results = graph_manager.query_graph(
            'LifecycleTest',
            "persistent-graph('LifecycleTest') | take 10"
        )
        assert results is not None

        # Delete
        deleted = graph_manager.delete_graph('LifecycleTest', force=True)
        assert deleted is True

    def test_snapshot_workflow(self, graph_manager, simple_schema):
        """Test snapshot creation and restoration workflow."""
        # Create graph
        graph = graph_manager.create_graph(
            'SnapshotTest',
            simple_schema,
            create_snapshot=True
        )

        # Get snapshot manager
        sm = graph_manager.snapshot_manager

        # List snapshots
        snapshots = sm.list_snapshots(graph_name='SnapshotTest')
        assert len(snapshots) >= 1

        # Restore from snapshot
        restored = sm.restore_snapshot(
            snapshots[0].snapshot_id,
            target_graph_name='RestoredTest'
        )
        assert restored.name == 'RestoredTest'

    def test_version_management(self, graph_manager, simple_schema, complex_schema):
        """Test version management workflow."""
        # Create graph
        graph_manager.create_graph('VersionTest', simple_schema)

        # Make multiple updates
        for i in range(3):
            graph_manager.update_graph(
                'VersionTest',
                complex_schema,
                changes=[f'Update {i+1}']
            )

        # Check version history
        versions = graph_manager.get_version_history('VersionTest')
        assert len(versions) == 4  # Initial + 3 updates

        # Rollback
        graph = graph_manager.rollback_version('VersionTest', 1)
        assert graph.version == 5  # New version with v1 schema
