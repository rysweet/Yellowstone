"""
Persistent graph lifecycle management.

This module manages the complete lifecycle of persistent graphs in Microsoft Sentinel,
including creation, updates, versioning, and integration with workspace management.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from .models import (
    PersistentGraph,
    GraphSchema,
    GraphStatus,
    GraphVersion,
    GraphOperation,
    GraphMetrics,
)
from .graph_builder import GraphBuilder
from .snapshot_manager import SnapshotManager, SnapshotType


class GraphManager:
    """Manager for persistent graph lifecycle operations."""

    def __init__(self, workspace_id: str, api_client: Optional[Any] = None):
        """
        Initialize graph manager.

        Args:
            workspace_id: Microsoft Sentinel workspace ID
            api_client: Optional Azure API client (mocked if not provided)

        Example:
            >>> manager = GraphManager(workspace_id='ws-12345')
            >>> graph = manager.create_graph('SecurityGraph', schema)
        """
        self.workspace_id = workspace_id
        self.api_client = api_client or MockSentinelAPI()
        self.snapshot_manager = SnapshotManager(workspace_id)

        # In-memory storage (in production, this would be persistent)
        self._graphs: Dict[str, PersistentGraph] = {}
        self._versions: Dict[str, List[GraphVersion]] = {}
        self._operations: Dict[str, GraphOperation] = {}
        self._metrics: Dict[str, GraphMetrics] = {}

    def create_graph(
        self,
        name: str,
        schema: GraphSchema,
        description: Optional[str] = None,
        create_snapshot: bool = True,
    ) -> PersistentGraph:
        """
        Create a new persistent graph.

        Args:
            name: Unique graph name
            schema: Graph schema definition
            description: Optional description
            create_snapshot: Whether to create initial snapshot

        Returns:
            Created PersistentGraph

        Raises:
            ValueError: If graph name already exists
            ValueError: If schema validation fails

        Example:
            >>> schema = GraphSchema(nodes=[...], edges=[...])
            >>> graph = manager.create_graph('ThreatGraph', schema)
            >>> print(graph.status)
            'active'
        """
        # Check if graph already exists
        if name in self._graphs:
            raise ValueError(f"Graph '{name}' already exists")

        # Create graph object
        graph = PersistentGraph(
            name=name,
            workspace_id=self.workspace_id,
            schema=schema,
            description=description,
            status=GraphStatus.CREATING,
        )

        # Validate schema
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()
        if errors:
            raise ValueError(f"Schema validation failed: {', '.join(errors)}")

        # Create operation record
        operation = self._create_operation(
            graph_name=name,
            operation_type='create',
        )

        try:
            # Build KQL statement
            kql = builder.build_create_statement()

            # Execute via API (mocked)
            self.api_client.execute_management_command(kql)

            # Store graph
            self._graphs[name] = graph
            graph.update_status(GraphStatus.ACTIVE)

            # Create initial version
            version = GraphVersion(
                graph_name=name,
                version=1,
                schema=schema,
                changes=['Initial graph creation'],
            )
            self._versions[name] = [version]

            # Create initial snapshot if requested
            if create_snapshot:
                snapshot = self.snapshot_manager.create_snapshot(graph)
                graph.last_snapshot_id = snapshot.snapshot_id

            # Complete operation
            self._complete_operation(operation.operation_id)

            # Initialize metrics
            self._initialize_metrics(graph)

            return graph

        except Exception as e:
            graph.update_status(GraphStatus.FAILED)
            self._fail_operation(operation.operation_id, str(e))
            raise

    def get_graph(self, name: str) -> Optional[PersistentGraph]:
        """
        Retrieve a persistent graph by name.

        Args:
            name: Graph name

        Returns:
            PersistentGraph or None if not found

        Example:
            >>> graph = manager.get_graph('ThreatGraph')
            >>> if graph:
            ...     print(graph.version)
        """
        return self._graphs.get(name)

    def update_graph(
        self,
        name: str,
        schema: GraphSchema,
        changes: Optional[List[str]] = None,
        create_snapshot: bool = True,
    ) -> PersistentGraph:
        """
        Update an existing persistent graph with new schema.

        Args:
            name: Graph name
            schema: New graph schema
            changes: Description of changes
            create_snapshot: Whether to create snapshot before update

        Returns:
            Updated PersistentGraph

        Raises:
            ValueError: If graph not found
            ValueError: If schema validation fails

        Example:
            >>> new_schema = GraphSchema(nodes=[...], edges=[...])
            >>> graph = manager.update_graph(
            ...     'ThreatGraph',
            ...     new_schema,
            ...     changes=['Added Device nodes']
            ... )
        """
        graph = self._graphs.get(name)
        if not graph:
            raise ValueError(f"Graph '{name}' not found")

        # Create snapshot before update if requested
        if create_snapshot:
            self.snapshot_manager.create_snapshot(graph)

        # Update graph
        old_version = graph.version
        graph.schema = schema
        graph.increment_version()
        graph.update_status(GraphStatus.UPDATING)

        # Validate new schema
        builder = GraphBuilder(graph)
        errors = builder.validate_schema()
        if errors:
            # Rollback
            graph.version = old_version
            graph.update_status(GraphStatus.ACTIVE)
            raise ValueError(f"Schema validation failed: {', '.join(errors)}")

        # Create operation record
        operation = self._create_operation(
            graph_name=name,
            operation_type='update',
            metadata={'changes': changes or []}
        )

        try:
            # Build update statement
            kql = builder.build_update_statement(changes)

            # Execute via API (mocked)
            self.api_client.execute_management_command(kql)

            # Update status
            graph.update_status(GraphStatus.ACTIVE)

            # Create version record
            version = GraphVersion(
                graph_name=name,
                version=graph.version,
                schema=schema,
                changes=changes or ['Schema update'],
            )
            self._versions[name].append(version)

            # Complete operation
            self._complete_operation(operation.operation_id)

            return graph

        except Exception as e:
            graph.update_status(GraphStatus.FAILED)
            self._fail_operation(operation.operation_id, str(e))
            raise

    def delete_graph(self, name: str, force: bool = False) -> bool:
        """
        Delete a persistent graph.

        Args:
            name: Graph name
            force: Force deletion even if snapshots exist

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If snapshots exist and force=False

        Example:
            >>> manager.delete_graph('OldGraph', force=True)
            True
        """
        graph = self._graphs.get(name)
        if not graph:
            return False

        # Check for snapshots
        snapshots = self.snapshot_manager.list_snapshots(graph_name=name)
        if snapshots and not force:
            raise ValueError(
                f"Graph '{name}' has {len(snapshots)} snapshots. "
                "Use force=True to delete anyway."
            )

        # Create operation record
        operation = self._create_operation(
            graph_name=name,
            operation_type='delete',
        )

        try:
            # Build delete statement
            builder = GraphBuilder(graph)
            kql = builder.build_delete_statement()

            # Execute via API (mocked)
            self.api_client.execute_management_command(kql)

            # Update status
            graph.update_status(GraphStatus.DELETED)

            # Delete associated snapshots if force
            if force:
                for snapshot in snapshots:
                    self.snapshot_manager.delete_snapshot(snapshot.snapshot_id)

            # Remove from storage
            self._graphs.pop(name)
            self._versions.pop(name, None)
            self._metrics.pop(name, None)

            # Complete operation
            self._complete_operation(operation.operation_id)

            return True

        except Exception as e:
            graph.update_status(GraphStatus.FAILED)
            self._fail_operation(operation.operation_id, str(e))
            raise

    def list_graphs(
        self,
        status: Optional[GraphStatus] = None,
    ) -> List[PersistentGraph]:
        """
        List all persistent graphs with optional filtering.

        Args:
            status: Optional status filter

        Returns:
            List of PersistentGraph objects

        Example:
            >>> graphs = manager.list_graphs(status=GraphStatus.ACTIVE)
            >>> for graph in graphs:
            ...     print(graph.name, graph.version)
        """
        graphs = list(self._graphs.values())

        if status:
            graphs = [g for g in graphs if g.status == status]

        # Sort by creation time
        graphs.sort(key=lambda g: g.created_at, reverse=True)

        return graphs

    def get_version_history(self, graph_name: str) -> List[GraphVersion]:
        """
        Get version history for a graph.

        Args:
            graph_name: Graph name

        Returns:
            List of GraphVersion objects

        Example:
            >>> versions = manager.get_version_history('ThreatGraph')
            >>> for v in versions:
            ...     print(f"v{v.version}: {v.changes}")
        """
        return self._versions.get(graph_name, [])

    def rollback_version(
        self,
        graph_name: str,
        target_version: int,
    ) -> PersistentGraph:
        """
        Rollback graph to a previous version.

        Args:
            graph_name: Graph name
            target_version: Version number to rollback to

        Returns:
            Updated PersistentGraph

        Raises:
            ValueError: If graph or version not found

        Example:
            >>> graph = manager.rollback_version('ThreatGraph', 3)
            >>> print(graph.version)
            4  # New version with schema from v3
        """
        graph = self._graphs.get(graph_name)
        if not graph:
            raise ValueError(f"Graph '{graph_name}' not found")

        versions = self._versions.get(graph_name, [])
        target = next((v for v in versions if v.version == target_version), None)

        if not target:
            raise ValueError(
                f"Version {target_version} not found for graph '{graph_name}'"
            )

        # Update graph with old schema
        return self.update_graph(
            graph_name,
            target.schema,
            changes=[f'Rollback to version {target_version}'],
            create_snapshot=True,
        )

    def query_graph(
        self,
        graph_name: str,
        kql_query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a query against a persistent graph.

        Args:
            graph_name: Graph name
            kql_query: KQL query to execute
            parameters: Optional query parameters

        Returns:
            Query results

        Raises:
            ValueError: If graph not found or not active

        Example:
            >>> results = manager.query_graph(
            ...     'ThreatGraph',
            ...     "persistent-graph('ThreatGraph') | graph-match ..."
            ... )
        """
        graph = self._graphs.get(graph_name)
        if not graph:
            raise ValueError(f"Graph '{graph_name}' not found")

        if graph.status != GraphStatus.ACTIVE:
            raise ValueError(
                f"Graph '{graph_name}' is not active (status: {graph.status})"
            )

        # Execute query via API (mocked)
        start_time = datetime.utcnow()
        results = self.api_client.execute_query(kql_query, parameters)
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Update metrics
        self._update_query_metrics(graph_name, execution_time)

        return results

    def get_metrics(self, graph_name: str) -> Optional[GraphMetrics]:
        """
        Get performance metrics for a graph.

        Args:
            graph_name: Graph name

        Returns:
            GraphMetrics or None if not found

        Example:
            >>> metrics = manager.get_metrics('ThreatGraph')
            >>> print(f"Speedup: {metrics.speedup_factor}x")
        """
        return self._metrics.get(graph_name)

    def refresh_graph(self, graph_name: str) -> PersistentGraph:
        """
        Refresh graph data from source tables.

        Args:
            graph_name: Graph name

        Returns:
            Updated PersistentGraph

        Raises:
            ValueError: If graph not found

        Example:
            >>> graph = manager.refresh_graph('ThreatGraph')
            >>> print(f"Refreshed at {graph.updated_at}")
        """
        graph = self._graphs.get(graph_name)
        if not graph:
            raise ValueError(f"Graph '{graph_name}' not found")

        # Create operation record
        operation = self._create_operation(
            graph_name=graph_name,
            operation_type='update',
            metadata={'refresh': True}
        )

        try:
            # Build refresh command (same as update for persistent graphs)
            builder = GraphBuilder(graph)
            kql = builder.build_create_statement()

            # Execute via API (mocked)
            self.api_client.execute_management_command(kql)

            # Update timestamp
            graph.updated_at = datetime.utcnow()

            # Complete operation
            self._complete_operation(operation.operation_id)

            return graph

        except Exception as e:
            self._fail_operation(operation.operation_id, str(e))
            raise

    def _create_operation(
        self,
        graph_name: str,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphOperation:
        """Create and track an operation."""
        operation_id = f"op_{uuid4().hex[:12]}"

        operation = GraphOperation(
            operation_id=operation_id,
            graph_name=graph_name,
            operation_type=operation_type,
            status='running',
            metadata=metadata or {},
        )

        self._operations[operation_id] = operation
        return operation

    def _complete_operation(self, operation_id: str) -> None:
        """Mark operation as completed."""
        operation = self._operations.get(operation_id)
        if operation:
            operation.status = 'completed'
            operation.completed_at = datetime.utcnow()

    def _fail_operation(self, operation_id: str, error: str) -> None:
        """Mark operation as failed."""
        operation = self._operations.get(operation_id)
        if operation:
            operation.status = 'failed'
            operation.completed_at = datetime.utcnow()
            operation.error_message = error

    def _initialize_metrics(self, graph: PersistentGraph) -> None:
        """Initialize metrics for a new graph."""
        metrics = GraphMetrics(
            graph_name=graph.name,
            node_count=graph.estimated_node_count or 0,
            edge_count=graph.estimated_edge_count or 0,
        )
        self._metrics[graph.name] = metrics

    def _update_query_metrics(self, graph_name: str, execution_time_ms: float) -> None:
        """Update query metrics for a graph."""
        metrics = self._metrics.get(graph_name)
        if not metrics:
            return

        # Update query count
        metrics.query_count += 1

        # Update average query time
        old_avg = metrics.avg_query_time_ms
        metrics.avg_query_time_ms = (
            (old_avg * (metrics.query_count - 1) + execution_time_ms)
            / metrics.query_count
        )

        # Estimate speedup (mock: persistent graphs are ~25x faster)
        metrics.speedup_factor = 25.0

        metrics.timestamp = datetime.utcnow()

    def get_operation_status(self, operation_id: str) -> Optional[GraphOperation]:
        """
        Get status of a graph operation.

        Args:
            operation_id: Operation identifier

        Returns:
            GraphOperation or None if not found

        Example:
            >>> op = manager.get_operation_status('op_abc123')
            >>> print(op.status)
        """
        return self._operations.get(operation_id)

    def list_operations(
        self,
        graph_name: Optional[str] = None,
        operation_type: Optional[str] = None,
    ) -> List[GraphOperation]:
        """
        List graph operations with optional filtering.

        Args:
            graph_name: Filter by graph name
            operation_type: Filter by operation type

        Returns:
            List of GraphOperation objects

        Example:
            >>> ops = manager.list_operations(graph_name='ThreatGraph')
            >>> for op in ops:
            ...     print(op.operation_type, op.status)
        """
        operations = list(self._operations.values())

        if graph_name:
            operations = [op for op in operations if op.graph_name == graph_name]

        if operation_type:
            operations = [op for op in operations if op.operation_type == operation_type]

        # Sort by start time (newest first)
        operations.sort(key=lambda op: op.started_at, reverse=True)

        return operations


class MockSentinelAPI:
    """Mock Sentinel API for testing without Azure connection."""

    def execute_management_command(self, kql: str) -> Dict[str, Any]:
        """
        Mock execution of management command.

        Args:
            kql: KQL command to execute

        Returns:
            Mock response
        """
        # Simulate API call
        return {
            'status': 'success',
            'command': kql[:100],
            'execution_time_ms': 150,
        }

    def execute_query(
        self,
        kql: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Mock execution of query.

        Args:
            kql: KQL query to execute
            parameters: Query parameters

        Returns:
            Mock results
        """
        # Simulate query execution
        return {
            'columns': ['node_id', 'node_label', 'properties'],
            'rows': [
                ['n1', 'Alert', {'severity': 'high'}],
                ['n2', 'User', {'name': 'alice'}],
            ],
            'row_count': 2,
            'execution_time_ms': 45,
        }
