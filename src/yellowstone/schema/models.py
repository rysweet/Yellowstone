"""
Pydantic models for schema validation and type safety.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PropertyMapping(BaseModel):
    """Mapping of a Cypher property to a Sentinel field."""
    sentinel_field: str = Field(..., description="Target Sentinel table field name")
    type: str = Field(..., description="Data type (string, int, datetime, bool, float)")
    required: bool = Field(default=False, description="Whether field is required")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate that type is one of the supported types."""
        valid_types = {'string', 'int', 'datetime', 'bool', 'float', 'array', 'object'}
        if v not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}, got {v}")
        return v


class NodeMapping(BaseModel):
    """Mapping of a Cypher node label to a Sentinel table."""
    sentinel_table: str = Field(..., description="Target Sentinel table name")
    properties: Dict[str, PropertyMapping] = Field(
        default_factory=dict,
        description="Property mappings from Cypher to Sentinel"
    )


class JoinCondition(BaseModel):
    """Join condition between two Sentinel tables."""
    left_table: Optional[str] = Field(None, description="Left table in join")
    right_table: Optional[str] = Field(None, description="Right table in join")
    join_condition: Optional[str] = Field(None, description="Join SQL condition")


class EdgeProperty(BaseModel):
    """Property definition for an edge/relationship."""
    type: str = Field(..., description="Data type")
    required: bool = Field(default=False, description="Whether property is required")


class EdgeMapping(BaseModel):
    """Mapping of a Cypher relationship to Sentinel join rules."""
    description: str = Field(..., description="Human-readable description")
    from_label: Optional[str] = Field(None, description="Source node label in Cypher")
    to_label: Optional[str] = Field(None, description="Target node label in Cypher")
    sentinel_join: JoinCondition = Field(..., description="Join condition in Sentinel")
    strength: str = Field(
        default="medium",
        description="Join strength/reliability (high, medium, low)"
    )
    properties: Dict[str, EdgeProperty] = Field(
        default_factory=dict,
        description="Edge properties"
    )

    @field_validator('strength')
    @classmethod
    def validate_strength(cls, v):
        """Validate strength value."""
        valid_strengths = {'high', 'medium', 'low'}
        if v not in valid_strengths:
            raise ValueError(f"Strength must be one of {valid_strengths}, got {v}")
        return v


class TableMetadata(BaseModel):
    """Metadata about a Sentinel table."""
    description: str = Field(..., description="Table description")
    retention_days: int = Field(..., description="Data retention period in days")
    fields: List[str] = Field(default_factory=list, description="Available fields")


class SchemaMapping(BaseModel):
    """Complete schema mapping from Cypher to Sentinel."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields in loaded YAML

    version: str = Field(..., description="Schema version")
    description: str = Field(..., description="Schema description")
    nodes: Dict[str, NodeMapping] = Field(
        default_factory=dict,
        description="Node label mappings"
    )
    edges: Dict[str, EdgeMapping] = Field(
        default_factory=dict,
        description="Edge/relationship mappings"
    )
    tables: Dict[str, TableMetadata] = Field(
        default_factory=dict,
        description="Sentinel table metadata"
    )


class SchemaValidationResult(BaseModel):
    """Result of schema validation."""
    is_valid: bool = Field(..., description="Whether schema is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    node_count: int = Field(..., description="Number of node types")
    edge_count: int = Field(..., description="Number of edge types")
    table_count: int = Field(..., description="Number of tables")


class LabelMappingCache(BaseModel):
    """In-memory cache for label to table mappings."""
    label_to_table: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from Cypher label to Sentinel table"
    )
    table_to_fields: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping from table to available fields"
    )
    relationship_to_join: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping from relationship type to join condition"
    )
