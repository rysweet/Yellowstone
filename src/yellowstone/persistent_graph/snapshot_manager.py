"""
Graph snapshot management for persistent graphs.

This module handles creating, managing, and restoring snapshots of persistent graphs,
including full and differential snapshots with versioning support.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from .models import (
    GraphSnapshot,
    SnapshotStatus,
    SnapshotType,
    PersistentGraph,
    GraphVersion,
)


class SnapshotManager:
    """Manager for graph snapshots."""

    def __init__(self, workspace_id: str):
        """
        Initialize snapshot manager.

        Args:
            workspace_id: Sentinel workspace ID
        """
        self.workspace_id = workspace_id
        self._snapshots: Dict[str, GraphSnapshot] = {}
        self._snapshot_data: Dict[str, Dict[str, Any]] = {}

    def create_snapshot(
        self,
        graph: PersistentGraph,
        snapshot_type: SnapshotType = SnapshotType.FULL,
        base_snapshot_id: Optional[str] = None,
        retention_days: int = 90,
    ) -> GraphSnapshot:
        """
        Create a snapshot of the persistent graph.

        Args:
            graph: Persistent graph to snapshot
            snapshot_type: Type of snapshot (full or differential)
            base_snapshot_id: Base snapshot for differential snapshots
            retention_days: How long to retain the snapshot

        Returns:
            GraphSnapshot object

        Raises:
            ValueError: If differential snapshot requested without base
            ValueError: If base snapshot not found

        Example:
            >>> manager = SnapshotManager(workspace_id)
            >>> snapshot = manager.create_snapshot(graph)
            >>> print(snapshot.snapshot_id)
            'snap_8f4a2b1c'
        """
        # Validate differential snapshot requirements
        if snapshot_type == SnapshotType.DIFFERENTIAL:
            if not base_snapshot_id:
                raise ValueError("Differential snapshot requires base_snapshot_id")
            if base_snapshot_id not in self._snapshots:
                raise ValueError(f"Base snapshot '{base_snapshot_id}' not found")

        # Generate snapshot ID
        snapshot_id = self._generate_snapshot_id(graph.name)

        # Create snapshot object
        snapshot = GraphSnapshot(
            snapshot_id=snapshot_id,
            graph_name=graph.name,
            graph_version=graph.version,
            snapshot_type=snapshot_type,
            status=SnapshotStatus.CREATING,
            base_snapshot_id=base_snapshot_id,
            retention_days=retention_days,
            metadata={
                'workspace_id': self.workspace_id,
                'schema_version': graph.schema.version,
                'node_types': [node.label for node in graph.schema.nodes],
                'edge_types': [edge.type for edge in graph.schema.edges],
            }
        )

        # Store snapshot
        self._snapshots[snapshot_id] = snapshot

        # Simulate snapshot creation (in production, this would call Sentinel API)
        self._capture_snapshot_data(graph, snapshot, base_snapshot_id)

        return snapshot

    def _generate_snapshot_id(self, graph_name: str) -> str:
        """
        Generate unique snapshot ID.

        Args:
            graph_name: Name of the graph

        Returns:
            Unique snapshot identifier
        """
        timestamp = datetime.utcnow().isoformat()
        data = f"{graph_name}:{timestamp}:{uuid4()}"
        hash_hex = hashlib.sha256(data.encode()).hexdigest()[:8]
        return f"snap_{hash_hex}"

    def _capture_snapshot_data(
        self,
        graph: PersistentGraph,
        snapshot: GraphSnapshot,
        base_snapshot_id: Optional[str] = None,
    ) -> None:
        """
        Capture graph data for snapshot (mocked implementation).

        Args:
            graph: Graph to snapshot
            snapshot: Snapshot object to populate
            base_snapshot_id: Base snapshot for differential snapshots
        """
        # Mock: simulate capturing graph data
        if snapshot.snapshot_type == SnapshotType.FULL:
            # Full snapshot captures all data
            node_count = len(graph.schema.nodes) * 1000  # Simulate 1000 nodes per type
            edge_count = len(graph.schema.edges) * 5000  # Simulate 5000 edges per type

            snapshot_data = {
                'schema': graph.schema.model_dump(),
                'graph_metadata': {
                    'name': graph.name,
                    'version': graph.version,
                    'created_at': graph.created_at.isoformat(),
                },
                'statistics': {
                    'node_count': node_count,
                    'edge_count': edge_count,
                }
            }
        else:
            # Differential snapshot only captures changes since base
            base_data = self._snapshot_data.get(base_snapshot_id, {})
            base_stats = base_data.get('statistics', {})

            # Simulate differential changes (10% of base)
            node_count = int(base_stats.get('node_count', 0) * 0.1)
            edge_count = int(base_stats.get('edge_count', 0) * 0.1)

            snapshot_data = {
                'base_snapshot_id': base_snapshot_id,
                'changes': {
                    'schema_diff': {},  # Schema changes
                    'added_nodes': node_count,
                    'added_edges': edge_count,
                },
                'statistics': {
                    'node_count': node_count,
                    'edge_count': edge_count,
                }
            }

        # Calculate size
        size_bytes = len(json.dumps(snapshot_data).encode('utf-8'))

        # Store snapshot data
        self._snapshot_data[snapshot.snapshot_id] = snapshot_data

        # Mark snapshot as complete
        snapshot.complete(
            node_count=snapshot_data['statistics']['node_count'],
            edge_count=snapshot_data['statistics']['edge_count'],
            size_bytes=size_bytes
        )

    def get_snapshot(self, snapshot_id: str) -> Optional[GraphSnapshot]:
        """
        Retrieve snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            GraphSnapshot or None if not found

        Example:
            >>> snapshot = manager.get_snapshot('snap_8f4a2b1c')
            >>> if snapshot:
            ...     print(snapshot.status)
            'ready'
        """
        return self._snapshots.get(snapshot_id)

    def list_snapshots(
        self,
        graph_name: Optional[str] = None,
        status: Optional[SnapshotStatus] = None,
    ) -> List[GraphSnapshot]:
        """
        List snapshots with optional filtering.

        Args:
            graph_name: Filter by graph name
            status: Filter by snapshot status

        Returns:
            List of matching snapshots

        Example:
            >>> snapshots = manager.list_snapshots(graph_name='MyGraph')
            >>> for snap in snapshots:
            ...     print(snap.snapshot_id, snap.created_at)
        """
        snapshots = list(self._snapshots.values())

        if graph_name:
            snapshots = [s for s in snapshots if s.graph_name == graph_name]

        if status:
            snapshots = [s for s in snapshots if s.status == status]

        # Sort by creation time (newest first)
        snapshots.sort(key=lambda s: s.created_at, reverse=True)

        return snapshots

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_graph_name: Optional[str] = None,
    ) -> PersistentGraph:
        """
        Restore a graph from a snapshot.

        Args:
            snapshot_id: Snapshot to restore from
            target_graph_name: Optional new name for restored graph

        Returns:
            Restored PersistentGraph

        Raises:
            ValueError: If snapshot not found or not ready
            ValueError: If differential snapshot with missing base

        Example:
            >>> graph = manager.restore_snapshot('snap_8f4a2b1c')
            >>> print(graph.name, graph.version)
            'MyGraph', 5
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        if snapshot.status != SnapshotStatus.READY:
            raise ValueError(f"Snapshot '{snapshot_id}' is not ready (status: {snapshot.status})")

        # Mark snapshot as restoring
        snapshot.status = SnapshotStatus.RESTORING

        try:
            # Get snapshot data
            snapshot_data = self._snapshot_data[snapshot_id]

            # Restore based on snapshot type
            if snapshot.snapshot_type == SnapshotType.FULL:
                graph = self._restore_full_snapshot(snapshot_data, target_graph_name)
            else:
                graph = self._restore_differential_snapshot(
                    snapshot,
                    snapshot_data,
                    target_graph_name
                )

            # Mark snapshot as ready again
            snapshot.status = SnapshotStatus.READY

            return graph

        except Exception as e:
            snapshot.fail(f"Restore failed: {str(e)}")
            raise

    def _restore_full_snapshot(
        self,
        snapshot_data: Dict[str, Any],
        target_graph_name: Optional[str] = None,
    ) -> PersistentGraph:
        """
        Restore from a full snapshot.

        Args:
            snapshot_data: Snapshot data
            target_graph_name: Optional new graph name

        Returns:
            Restored graph
        """
        from .models import GraphSchema

        schema_data = snapshot_data['schema']
        graph_meta = snapshot_data['graph_metadata']

        # Reconstruct schema
        schema = GraphSchema(**schema_data)

        # Create graph object
        graph = PersistentGraph(
            name=target_graph_name or graph_meta['name'],
            workspace_id=self.workspace_id,
            schema=schema,
            version=graph_meta['version'],
            created_at=datetime.fromisoformat(graph_meta['created_at']),
        )

        # Set statistics
        stats = snapshot_data['statistics']
        graph.estimated_node_count = stats['node_count']
        graph.estimated_edge_count = stats['edge_count']

        return graph

    def _restore_differential_snapshot(
        self,
        snapshot: GraphSnapshot,
        snapshot_data: Dict[str, Any],
        target_graph_name: Optional[str] = None,
    ) -> PersistentGraph:
        """
        Restore from a differential snapshot.

        Args:
            snapshot: Snapshot object
            snapshot_data: Snapshot data
            target_graph_name: Optional new graph name

        Returns:
            Restored graph

        Raises:
            ValueError: If base snapshot not available
        """
        # Get base snapshot
        base_id = snapshot.base_snapshot_id
        if not base_id or base_id not in self._snapshots:
            raise ValueError(f"Base snapshot '{base_id}' not available")

        # Restore from base first
        base_graph = self.restore_snapshot(base_id)

        # Apply differential changes
        changes = snapshot_data.get('changes', {})

        # Update statistics
        base_graph.estimated_node_count = (
            (base_graph.estimated_node_count or 0) + changes.get('added_nodes', 0)
        )
        base_graph.estimated_edge_count = (
            (base_graph.estimated_edge_count or 0) + changes.get('added_edges', 0)
        )

        # Set new name if provided
        if target_graph_name:
            base_graph.name = target_graph_name

        return base_graph

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.

        Args:
            snapshot_id: Snapshot to delete

        Returns:
            True if deleted, False if not found

        Example:
            >>> manager.delete_snapshot('snap_8f4a2b1c')
            True
        """
        if snapshot_id not in self._snapshots:
            return False

        snapshot = self._snapshots[snapshot_id]
        snapshot.status = SnapshotStatus.DELETED

        # Remove snapshot data
        self._snapshot_data.pop(snapshot_id, None)
        self._snapshots.pop(snapshot_id)

        return True

    def cleanup_expired_snapshots(self) -> List[str]:
        """
        Delete snapshots past their retention period.

        Returns:
            List of deleted snapshot IDs

        Example:
            >>> deleted = manager.cleanup_expired_snapshots()
            >>> print(f"Deleted {len(deleted)} expired snapshots")
        """
        deleted = []
        now = datetime.utcnow()

        for snapshot_id, snapshot in list(self._snapshots.items()):
            expiry_date = snapshot.created_at + timedelta(days=snapshot.retention_days)

            if now > expiry_date:
                self.delete_snapshot(snapshot_id)
                deleted.append(snapshot_id)

        return deleted

    def compare_snapshots(
        self,
        snapshot_id_1: str,
        snapshot_id_2: str,
    ) -> Dict[str, Any]:
        """
        Compare two snapshots and return differences.

        Args:
            snapshot_id_1: First snapshot ID
            snapshot_id_2: Second snapshot ID

        Returns:
            Dictionary with comparison results

        Raises:
            ValueError: If either snapshot not found

        Example:
            >>> diff = manager.compare_snapshots('snap_abc123', 'snap_def456')
            >>> print(diff['node_count_delta'])
            500
        """
        snap1 = self._snapshots.get(snapshot_id_1)
        snap2 = self._snapshots.get(snapshot_id_2)

        if not snap1:
            raise ValueError(f"Snapshot '{snapshot_id_1}' not found")
        if not snap2:
            raise ValueError(f"Snapshot '{snapshot_id_2}' not found")

        # Compare metrics
        node_delta = (snap2.node_count or 0) - (snap1.node_count or 0)
        edge_delta = (snap2.edge_count or 0) - (snap1.edge_count or 0)
        size_delta = (snap2.size_bytes or 0) - (snap1.size_bytes or 0)

        # Compare metadata
        meta1 = snap1.metadata.get('node_types', [])
        meta2 = snap2.metadata.get('node_types', [])
        added_node_types = set(meta2) - set(meta1)
        removed_node_types = set(meta1) - set(meta2)

        return {
            'snapshot_1': {
                'id': snapshot_id_1,
                'created_at': snap1.created_at,
                'version': snap1.graph_version,
            },
            'snapshot_2': {
                'id': snapshot_id_2,
                'created_at': snap2.created_at,
                'version': snap2.graph_version,
            },
            'node_count_delta': node_delta,
            'edge_count_delta': edge_delta,
            'size_delta_bytes': size_delta,
            'version_delta': snap2.graph_version - snap1.graph_version,
            'added_node_types': list(added_node_types),
            'removed_node_types': list(removed_node_types),
            'time_delta': (snap2.created_at - snap1.created_at).total_seconds(),
        }

    def get_snapshot_chain(self, snapshot_id: str) -> List[GraphSnapshot]:
        """
        Get the chain of snapshots from base to target.

        Args:
            snapshot_id: Target snapshot ID

        Returns:
            List of snapshots in dependency order (base first)

        Raises:
            ValueError: If snapshot not found

        Example:
            >>> chain = manager.get_snapshot_chain('snap_xyz789')
            >>> for snap in chain:
            ...     print(snap.snapshot_id, snap.snapshot_type)
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        chain = [snapshot]

        # Follow base snapshot chain for differential snapshots
        current = snapshot
        while current.base_snapshot_id:
            base = self._snapshots.get(current.base_snapshot_id)
            if not base:
                break
            chain.insert(0, base)
            current = base

        return chain

    def estimate_restore_time(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Estimate time required to restore from snapshot.

        Args:
            snapshot_id: Snapshot to estimate

        Returns:
            Dictionary with time estimates

        Example:
            >>> estimate = manager.estimate_restore_time('snap_123')
            >>> print(f"Estimated time: {estimate['estimated_seconds']}s")
        """
        chain = self.get_snapshot_chain(snapshot_id)

        # Estimate based on data size and snapshot count
        total_size = sum(s.size_bytes or 0 for s in chain)
        snapshot_count = len(chain)

        # Mock estimation: 10MB/sec, plus overhead per snapshot
        estimated_seconds = (total_size / (10 * 1024 * 1024)) + (snapshot_count * 2)

        return {
            'snapshot_id': snapshot_id,
            'snapshot_chain_length': snapshot_count,
            'total_data_size_bytes': total_size,
            'estimated_seconds': max(1, int(estimated_seconds)),
            'estimated_minutes': max(1, int(estimated_seconds / 60)),
        }
