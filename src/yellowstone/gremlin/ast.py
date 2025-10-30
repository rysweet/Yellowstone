"""
Abstract Syntax Tree (AST) node definitions for Gremlin queries.

This module defines the complete set of AST nodes used to represent parsed
Gremlin traversal structures. All nodes are Pydantic BaseModel subclasses for
validation, serialization, and type safety.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Base Step Node
# ============================================================================


class Step(BaseModel):
    """Base class for all Gremlin traversal steps.

    Every Gremlin step in a traversal chain extends this base class.
    """

    step_type: str = Field(description="The type of step (e.g., 'vertex', 'filter', 'traversal')")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.step_type}()"


# ============================================================================
# Literal and Value Nodes
# ============================================================================


class GremlinValue(BaseModel):
    """Represents a value in a Gremlin query.

    Supports strings, numbers, booleans, and predicates.

    Attributes:
        value: The actual value
        value_type: The type of value ('string', 'number', 'boolean', 'predicate')

    Example:
        >>> GremlinValue(value='marko', value_type='string')
        GremlinValue(value='marko', value_type='string')
        >>> GremlinValue(value=30, value_type='number')
        GremlinValue(value=30, value_type='number')
    """

    value: Any = Field(description="The actual value")
    value_type: str = Field(
        description="Type of value: 'string', 'number', 'boolean', 'predicate'"
    )

    def __str__(self) -> str:
        """Return string representation."""
        if self.value_type == "string":
            return f"'{self.value}'"
        return str(self.value)


class Predicate(BaseModel):
    """Represents a Gremlin predicate like gt(30), eq('value'), etc.

    Attributes:
        operator: The predicate operator (e.g., 'gt', 'lt', 'eq', 'neq')
        value: The comparison value

    Example:
        >>> Predicate(operator='gt', value=GremlinValue(value=30, value_type='number'))
    """

    operator: str = Field(description="Predicate operator (gt, lt, eq, neq, gte, lte)")
    value: GremlinValue = Field(description="Value to compare against")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.operator}({self.value})"


# ============================================================================
# Step Implementations
# ============================================================================


class VertexStep(Step):
    """Represents g.V() or g.V(id) step.

    Attributes:
        vertex_id: Optional vertex ID to start from

    Example:
        >>> VertexStep()  # g.V()
        >>> VertexStep(vertex_id='123')  # g.V('123')
    """

    step_type: str = Field(default="vertex")
    vertex_id: Optional[str] = Field(default=None, description="Optional vertex ID")

    def __str__(self) -> str:
        """Return string representation."""
        if self.vertex_id:
            return f"V('{self.vertex_id}')"
        return "V()"


class EdgeStep(Step):
    """Represents g.E() or g.E(id) step.

    Attributes:
        edge_id: Optional edge ID to start from

    Example:
        >>> EdgeStep()  # g.E()
        >>> EdgeStep(edge_id='456')  # g.E('456')
    """

    step_type: str = Field(default="edge")
    edge_id: Optional[str] = Field(default=None, description="Optional edge ID")

    def __str__(self) -> str:
        """Return string representation."""
        if self.edge_id:
            return f"E('{self.edge_id}')"
        return "E()"


class FilterStep(Step):
    """Represents filtering steps like hasLabel(), has(), hasId().

    Attributes:
        filter_type: Type of filter ('hasLabel', 'has', 'hasId', 'hasKey', 'hasValue')
        property_name: Optional property name for has() filters
        value: Optional value to filter by
        predicate: Optional predicate for complex filtering

    Examples:
        >>> FilterStep(filter_type='hasLabel', value=GremlinValue(value='Person', value_type='string'))
        >>> FilterStep(filter_type='has', property_name='age', predicate=Predicate(operator='gt', value=...))
    """

    step_type: str = Field(default="filter")
    filter_type: str = Field(description="Type of filter (hasLabel, has, hasId, etc.)")
    property_name: Optional[str] = Field(default=None, description="Property name for has() filters")
    value: Optional[GremlinValue] = Field(default=None, description="Value to filter by")
    predicate: Optional[Predicate] = Field(default=None, description="Predicate for complex filtering")

    def __str__(self) -> str:
        """Return string representation."""
        if self.filter_type == "hasLabel":
            return f"hasLabel({self.value})"
        elif self.filter_type == "has" and self.predicate:
            return f"has('{self.property_name}', {self.predicate})"
        elif self.filter_type == "has" and self.value:
            return f"has('{self.property_name}', {self.value})"
        return f"{self.filter_type}()"


class TraversalStep(Step):
    """Represents traversal steps like out(), in(), both(), outE(), inE().

    Attributes:
        direction: Direction of traversal ('out', 'in', 'both')
        traversal_type: Type of traversal ('vertex', 'edge')
        edge_label: Optional edge label to filter by

    Examples:
        >>> TraversalStep(direction='out', traversal_type='vertex')  # out()
        >>> TraversalStep(direction='out', traversal_type='vertex', edge_label='KNOWS')  # out('KNOWS')
        >>> TraversalStep(direction='out', traversal_type='edge', edge_label='CREATED')  # outE('CREATED')
    """

    step_type: str = Field(default="traversal")
    direction: str = Field(description="Direction: 'out', 'in', or 'both'")
    traversal_type: str = Field(description="Type: 'vertex' or 'edge'")
    edge_label: Optional[str] = Field(default=None, description="Optional edge label")

    def __str__(self) -> str:
        """Return string representation."""
        suffix = "E" if self.traversal_type == "edge" else ""
        label_str = f"'{self.edge_label}'" if self.edge_label else ""
        return f"{self.direction}{suffix}({label_str})"


class ProjectionStep(Step):
    """Represents projection steps like values(), valueMap(), properties().

    Attributes:
        projection_type: Type of projection ('values', 'valueMap', 'properties', 'elementMap')
        property_names: Optional list of property names to project

    Examples:
        >>> ProjectionStep(projection_type='values', property_names=['name'])  # values('name')
        >>> ProjectionStep(projection_type='valueMap')  # valueMap()
    """

    step_type: str = Field(default="projection")
    projection_type: str = Field(description="Type: 'values', 'valueMap', 'properties', 'elementMap'")
    property_names: list[str] = Field(default_factory=list, description="Property names to project")

    def __str__(self) -> str:
        """Return string representation."""
        if self.property_names:
            props_str = ", ".join(f"'{p}'" for p in self.property_names)
            return f"{self.projection_type}({props_str})"
        return f"{self.projection_type}()"


class LimitStep(Step):
    """Represents limit() step.

    Attributes:
        count: Number of results to limit to

    Example:
        >>> LimitStep(count=10)  # limit(10)
    """

    step_type: str = Field(default="limit")
    count: int = Field(description="Number of results to limit")

    def __str__(self) -> str:
        """Return string representation."""
        return f"limit({self.count})"


class OrderStep(Step):
    """Represents order() step.

    Attributes:
        order_by: Optional property to order by
        order: Order direction ('asc' or 'desc')

    Example:
        >>> OrderStep(order_by='name', order='asc')  # order().by('name', asc)
    """

    step_type: str = Field(default="order")
    order_by: Optional[str] = Field(default=None, description="Property to order by")
    order: str = Field(default="asc", description="Order direction: 'asc' or 'desc'")

    def __str__(self) -> str:
        """Return string representation."""
        if self.order_by:
            return f"order().by('{self.order_by}', {self.order})"
        return "order()"


class CountStep(Step):
    """Represents count() step.

    Example:
        >>> CountStep()  # count()
    """

    step_type: str = Field(default="count")

    def __str__(self) -> str:
        """Return string representation."""
        return "count()"


class DedupStep(Step):
    """Represents dedup() step for removing duplicates.

    Example:
        >>> DedupStep()  # dedup()
    """

    step_type: str = Field(default="dedup")

    def __str__(self) -> str:
        """Return string representation."""
        return "dedup()"


# ============================================================================
# Traversal Container
# ============================================================================


class GremlinTraversal(BaseModel):
    """Represents a complete Gremlin traversal query.

    This is the root AST node for any parsed Gremlin query.

    Attributes:
        steps: List of traversal steps in order

    Example:
        >>> GremlinTraversal(steps=[
        ...     VertexStep(),
        ...     FilterStep(filter_type='hasLabel', value=GremlinValue(value='Person', value_type='string')),
        ...     ProjectionStep(projection_type='values', property_names=['name'])
        ... ])
    """

    steps: list[Step] = Field(description="Ordered list of traversal steps")

    def __str__(self) -> str:
        """Return string representation of the traversal."""
        steps_str = ".".join(str(step) for step in self.steps)
        return f"g.{steps_str}"
