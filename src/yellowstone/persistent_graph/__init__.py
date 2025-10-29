"""
Persistent Graph Module for Yellowstone.

This module provides comprehensive support for Microsoft Sentinel persistent graphs,
including graph lifecycle management, schema building, and snapshot functionality.

Example:
    >>> from yellowstone.persistent_graph import GraphManager, GraphSchema, NodeDefinition
    >>>
    >>> # Define graph schema
    >>> schema = GraphSchema(
    ...     nodes=[
    ...         NodeDefinition(
    ...             label='Alert',
    ...             source_table='SecurityAlert',
    ...             id_property='AlertId',
    ...             properties={'severity': 'AlertSeverity'}
    ...         )
    ...     ]
    ... )
    >>>
    >>> # Create persistent graph
    >>> manager = GraphManager(workspace_id='ws-12345')
    >>> graph = manager.create_graph('ThreatGraph', schema)
    >>> print(graph.status)
    'active'
"""

# Core management classes
from .graph_manager import GraphManager, MockSentinelAPI
from .graph_builder import GraphBuilder
from .snapshot_manager import SnapshotManager

# Data models
from .models import (
    # Graph models
    PersistentGraph,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition,
    GraphVersion,
    GraphMetrics,
    GraphOperation,

    # Snapshot models
    GraphSnapshot,
    SnapshotType,
    SnapshotStatus,

    # Status enums
    GraphStatus,
)

__all__ = [
    # Core classes
    'GraphManager',
    'GraphBuilder',
    'SnapshotManager',
    'MockSentinelAPI',

    # Graph models
    'PersistentGraph',
    'GraphSchema',
    'NodeDefinition',
    'EdgeDefinition',
    'GraphVersion',
    'GraphMetrics',
    'GraphOperation',

    # Snapshot models
    'GraphSnapshot',
    'SnapshotType',
    'SnapshotStatus',

    # Status enums
    'GraphStatus',
]

__version__ = '0.1.0'
