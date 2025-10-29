"""
Pydantic models for persistent graph management.

This module defines data models for persistent graphs in Microsoft Sentinel,
including graph definitions, snapshots, and version management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class GraphStatus(str, Enum):
    """Status of a persistent graph."""
    CREATING = "creating"
    ACTIVE = "active"
    UPDATING = "updating"
    DELETING = "deleting"
    FAILED = "failed"
    DELETED = "deleted"


class SnapshotStatus(str, Enum):
    """Status of a graph snapshot."""
    CREATING = "creating"
    READY = "ready"
    RESTORING = "restoring"
    FAILED = "failed"
    DELETED = "deleted"


class NodeDefinition(BaseModel):
    """Definition of a node type in the persistent graph."""
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="Node label/type")
    source_table: str = Field(..., description="Sentinel source table")
    properties: Dict[str, str] = Field(
        default_factory=dict,
        description="Property mappings: graph_property -> table_column"
    )
    id_property: str = Field(..., description="Property to use as node ID")
    filters: Optional[List[str]] = Field(
        None,
        description="KQL filter expressions to apply"
    )

    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate node label format."""
        if not v or not v[0].isupper():
            raise ValueError("Node label must start with uppercase letter")
        if not v.replace('_', '').isalnum():
            raise ValueError("Node label must be alphanumeric with underscores")
        return v


class EdgeDefinition(BaseModel):
    """Definition of an edge type in the persistent graph."""
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="Edge type/relationship name")
    from_label: str = Field(..., description="Source node label")
    to_label: str = Field(..., description="Target node label")
    join_condition: str = Field(..., description="KQL join condition")
    properties: Dict[str, str] = Field(
        default_factory=dict,
        description="Edge property mappings"
    )
    strength: str = Field(
        default="medium",
        description="Join strength: high, medium, low"
    )

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate edge type format."""
        if not v or not v[0].isupper():
            raise ValueError("Edge type must start with uppercase letter")
        if not v.replace('_', '').isalnum():
            raise ValueError("Edge type must be alphanumeric with underscores")
        return v

    @field_validator('strength')
    @classmethod
    def validate_strength(cls, v: str) -> str:
        """Validate strength value."""
        if v not in {'high', 'medium', 'low'}:
            raise ValueError(f"Strength must be high, medium, or low, got {v}")
        return v


class GraphSchema(BaseModel):
    """Schema definition for a persistent graph."""
    model_config = ConfigDict(extra="forbid")

    nodes: List[NodeDefinition] = Field(
        default_factory=list,
        description="Node type definitions"
    )
    edges: List[EdgeDefinition] = Field(
        default_factory=list,
        description="Edge type definitions"
    )
    version: str = Field(
        default="1.0.0",
        description="Schema version"
    )

    def get_node(self, label: str) -> Optional[NodeDefinition]:
        """Get node definition by label."""
        for node in self.nodes:
            if node.label == label:
                return node
        return None

    def get_edge(self, edge_type: str) -> Optional[EdgeDefinition]:
        """Get edge definition by type."""
        for edge in self.edges:
            if edge.type == edge_type:
                return edge
        return None

    def validate_edges(self) -> List[str]:
        """Validate that all edge references exist in nodes."""
        errors = []
        node_labels = {node.label for node in self.nodes}

        for edge in self.edges:
            if edge.from_label not in node_labels:
                errors.append(
                    f"Edge '{edge.type}' references unknown from_label '{edge.from_label}'"
                )
            if edge.to_label not in node_labels:
                errors.append(
                    f"Edge '{edge.type}' references unknown to_label '{edge.to_label}'"
                )

        return errors


class PersistentGraph(BaseModel):
    """Persistent graph definition and metadata."""
    model_config = ConfigDict(extra="allow", protected_namespaces=(), arbitrary_types_allowed=True)

    name: str = Field(..., description="Unique graph name")
    workspace_id: str = Field(..., description="Sentinel workspace ID")
    schema: GraphSchema = Field(..., description="Graph schema definition")
    status: GraphStatus = Field(
        default=GraphStatus.CREATING,
        description="Current graph status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    version: int = Field(
        default=1,
        description="Graph version number"
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    estimated_node_count: Optional[int] = Field(
        None,
        description="Estimated number of nodes"
    )
    estimated_edge_count: Optional[int] = Field(
        None,
        description="Estimated number of edges"
    )
    last_snapshot_id: Optional[str] = Field(
        None,
        description="ID of the most recent snapshot"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate graph name format."""
        if not v or len(v) < 3:
            raise ValueError("Graph name must be at least 3 characters")
        if not v[0].isalpha():
            raise ValueError("Graph name must start with a letter")
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Graph name must be alphanumeric with hyphens/underscores")
        return v

    def update_status(self, status: GraphStatus) -> None:
        """Update graph status and timestamp."""
        self.status = status
        self.updated_at = datetime.utcnow()

    def increment_version(self) -> None:
        """Increment graph version."""
        self.version += 1
        self.updated_at = datetime.utcnow()


class GraphVersion(BaseModel):
    """Version history entry for a persistent graph."""
    model_config = ConfigDict(extra="forbid", protected_namespaces=(), arbitrary_types_allowed=True)

    graph_name: str = Field(..., description="Graph name")
    version: int = Field(..., description="Version number")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Version creation timestamp"
    )
    schema: GraphSchema = Field(..., description="Schema at this version")
    changes: List[str] = Field(
        default_factory=list,
        description="List of changes in this version"
    )
    created_by: Optional[str] = Field(
        None,
        description="User who created this version"
    )
    snapshot_id: Optional[str] = Field(
        None,
        description="Associated snapshot ID"
    )


class SnapshotType(str, Enum):
    """Type of snapshot."""
    FULL = "full"
    DIFFERENTIAL = "differential"


class GraphSnapshot(BaseModel):
    """Point-in-time snapshot of a persistent graph."""
    model_config = ConfigDict(extra="allow")

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    graph_name: str = Field(..., description="Graph name")
    graph_version: int = Field(..., description="Graph version at snapshot time")
    snapshot_type: SnapshotType = Field(
        default=SnapshotType.FULL,
        description="Type of snapshot"
    )
    status: SnapshotStatus = Field(
        default=SnapshotStatus.CREATING,
        description="Snapshot status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot creation timestamp"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Snapshot completion timestamp"
    )
    base_snapshot_id: Optional[str] = Field(
        None,
        description="Base snapshot for differential snapshots"
    )
    node_count: Optional[int] = Field(
        None,
        description="Number of nodes in snapshot"
    )
    edge_count: Optional[int] = Field(
        None,
        description="Number of edges in snapshot"
    )
    size_bytes: Optional[int] = Field(
        None,
        description="Snapshot size in bytes"
    )
    retention_days: int = Field(
        default=90,
        description="Snapshot retention period"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional snapshot metadata"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if snapshot failed"
    )

    @field_validator('snapshot_id')
    @classmethod
    def validate_snapshot_id(cls, v: str) -> str:
        """Validate snapshot ID format."""
        if not v or len(v) < 8:
            raise ValueError("Snapshot ID must be at least 8 characters")
        return v

    def complete(self, node_count: int, edge_count: int, size_bytes: int) -> None:
        """Mark snapshot as complete."""
        self.status = SnapshotStatus.READY
        self.completed_at = datetime.utcnow()
        self.node_count = node_count
        self.edge_count = edge_count
        self.size_bytes = size_bytes

    def fail(self, error_message: str) -> None:
        """Mark snapshot as failed."""
        self.status = SnapshotStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()


class GraphMetrics(BaseModel):
    """Performance metrics for a persistent graph."""
    model_config = ConfigDict(extra="forbid")

    graph_name: str = Field(..., description="Graph name")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp"
    )
    query_count: int = Field(default=0, description="Number of queries executed")
    avg_query_time_ms: float = Field(
        default=0.0,
        description="Average query execution time"
    )
    node_count: int = Field(default=0, description="Current node count")
    edge_count: int = Field(default=0, description="Current edge count")
    storage_size_mb: float = Field(default=0.0, description="Storage size in MB")
    cache_hit_rate: float = Field(
        default=0.0,
        description="Cache hit rate (0.0-1.0)"
    )
    speedup_factor: float = Field(
        default=1.0,
        description="Performance speedup vs. non-persistent queries"
    )


class GraphOperation(BaseModel):
    """Record of a graph operation."""
    model_config = ConfigDict(extra="forbid")

    operation_id: str = Field(..., description="Unique operation identifier")
    graph_name: str = Field(..., description="Target graph name")
    operation_type: str = Field(
        ...,
        description="Operation type: create, update, delete, snapshot, restore"
    )
    status: str = Field(
        default="pending",
        description="Operation status: pending, running, completed, failed"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Operation start time"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Operation completion time"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation metadata"
    )

    @field_validator('operation_type')
    @classmethod
    def validate_operation_type(cls, v: str) -> str:
        """Validate operation type."""
        valid_types = {'create', 'update', 'delete', 'snapshot', 'restore'}
        if v not in valid_types:
            raise ValueError(f"Operation type must be one of {valid_types}, got {v}")
        return v
