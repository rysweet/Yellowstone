"""
Abstract Syntax Tree (AST) node definitions for Cypher queries.

This module defines the complete set of AST nodes used to represent parsed
Cypher query structures. All nodes are Pydantic BaseModel subclasses for
validation, serialization, and type safety.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Literal and Identifier Nodes
# ============================================================================


class Identifier(BaseModel):
    """Represents a named identifier in a Cypher query.

    Examples:
        - Variable names: 'n', 'actor', 'film'
        - Label references: 'Person', 'Movie'
        - Property names: 'name', 'birthYear'

    Attributes:
        name: The identifier string
    """

    name: str = Field(description="The identifier name")

    def __str__(self) -> str:
        """Return string representation."""
        return self.name


class Literal(BaseModel):
    """Represents a literal value in a Cypher query.

    Supports strings, numbers, booleans, and null values.

    Attributes:
        value: The literal value
        value_type: The type of the literal ('string', 'number', 'boolean', 'null')

    Example:
        >>> Literal(value='John', value_type='string')
        Literal(value='John', value_type='string')
        >>> Literal(value=42, value_type='number')
        Literal(value=42, value_type='number')
    """

    value: Any = Field(description="The literal value")
    value_type: str = Field(
        description="Type of the literal: 'string', 'number', 'boolean', or 'null'"
    )

    def __str__(self) -> str:
        """Return string representation."""
        if self.value_type == "string":
            return f"'{self.value}'"
        return str(self.value)


# ============================================================================
# Property and Expression Nodes
# ============================================================================


class Property(BaseModel):
    """Represents a property access expression.

    Used to access node or relationship properties.

    Attributes:
        variable: The variable being accessed (e.g., 'n')
        property_name: The property name (e.g., 'name', 'age')

    Example:
        >>> Property(variable=Identifier('n'), property_name=Identifier('name'))
    """

    variable: Identifier = Field(description="Variable or entity being accessed")
    property_name: Identifier = Field(description="The property name")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.variable}.{self.property_name}"


class AliasedExpression(BaseModel):
    """Represents an aliased expression (e.g., n.name AS userName).

    Used in RETURN clauses to give expressions custom names.

    Attributes:
        expression: The expression being aliased (Identifier, Property, etc.)
        alias: The alias name

    Example:
        >>> AliasedExpression(
        ...     expression=Property(variable=Identifier('n'), property_name=Identifier('name')),
        ...     alias=Identifier('userName')
        ... )
    """

    expression: Any = Field(description="The expression being aliased")
    alias: Identifier = Field(description="The alias name")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.expression} AS {self.alias}"


class RelationshipPattern(BaseModel):
    """Represents a relationship pattern in a Cypher query.

    Attributes:
        variable: Optional variable name for the relationship (e.g., 'r')
        relationship_type: Optional relationship type (e.g., 'KNOWS', 'ACTED_IN')
        directed: Whether the relationship is directed (True for ->, False for --)
        direction: 'out' for outgoing, 'in' for incoming, 'both' for undirected

    Example:
        >>> RelationshipPattern(
        ...     variable=Identifier('r'),
        ...     relationship_type=Identifier('KNOWS'),
        ...     directed=True,
        ...     direction='out'
        ... )
    """

    variable: Optional[Identifier] = Field(
        default=None, description="Optional relationship variable"
    )
    relationship_type: Optional[Identifier] = Field(
        default=None, description="Optional relationship type"
    )
    directed: bool = Field(default=True, description="Whether relationship is directed")
    direction: str = Field(
        default="out",
        description="Direction: 'out' (->), 'in' (<-), or 'both' (--)",
    )

    def __str__(self) -> str:
        """Return string representation."""
        rel_part = ""
        if self.variable or self.relationship_type:
            rel_part = "["
            if self.variable:
                rel_part += str(self.variable)
            if self.relationship_type:
                rel_part += f":{self.relationship_type}"
            rel_part += "]"

        if self.direction == "in":
            return f"<-{rel_part}-"
        elif self.direction == "both":
            return f"-{rel_part}-"
        else:  # out
            return f"-{rel_part}->"


class NodePattern(BaseModel):
    """Represents a node pattern in a Cypher query.

    Attributes:
        variable: Optional variable name (e.g., 'n', 'actor')
        labels: List of label names (e.g., ['Person', 'Actor'])
        properties: Optional dictionary of property constraints

    Example:
        >>> NodePattern(
        ...     variable=Identifier('n'),
        ...     labels=[Identifier('Person')],
        ...     properties={'name': Literal(value='John', value_type='string')}
        ... )
    """

    variable: Optional[Identifier] = Field(
        default=None, description="Optional node variable"
    )
    labels: list[Identifier] = Field(default_factory=list, description="Node labels")
    properties: Optional[dict[str, Any]] = Field(
        default=None, description="Optional property constraints"
    )

    def __str__(self) -> str:
        """Return string representation."""
        result = "("
        if self.variable:
            result += str(self.variable)
        if self.labels:
            labels_str = ":".join(str(label) for label in self.labels)
            result += f":{labels_str}"
        result += ")"
        return result


class PathExpression(BaseModel):
    """Represents a path pattern in a Cypher query.

    A path consists of alternating nodes and relationships.

    Attributes:
        nodes: List of node patterns
        relationships: List of relationship patterns between nodes

    Example:
        >>> PathExpression(
        ...     nodes=[
        ...         NodePattern(variable=Identifier('n'), labels=[Identifier('Person')]),
        ...         NodePattern(variable=Identifier('m'), labels=[Identifier('Person')])
        ...     ],
        ...     relationships=[
        ...         RelationshipPattern(
        ...             relationship_type=Identifier('KNOWS'),
        ...             direction='out'
        ...         )
        ...     ]
        ... )
    """

    nodes: list[NodePattern] = Field(description="Node patterns in the path")
    relationships: list[RelationshipPattern] = Field(
        description="Relationship patterns between nodes"
    )

    def validate_structure(self) -> bool:
        """Validate that the path structure is valid.

        Returns:
            True if valid (n nodes require n-1 relationships)

        Raises:
            ValueError: If structure is invalid
        """
        if len(self.nodes) != len(self.relationships) + 1:
            raise ValueError(
                f"Invalid path structure: {len(self.nodes)} nodes "
                f"requires {len(self.nodes) - 1} relationships, "
                f"got {len(self.relationships)}"
            )
        return True


# ============================================================================
# Clause Nodes
# ============================================================================


class MatchClause(BaseModel):
    """Represents a MATCH clause in a Cypher query.

    Attributes:
        paths: List of path expressions to match
        optional: Whether this is an OPTIONAL MATCH

    Example:
        >>> MatchClause(
        ...     paths=[PathExpression(nodes=[...], relationships=[...])],
        ...     optional=False
        ... )
    """

    paths: list[PathExpression] = Field(description="Path patterns to match")
    optional: bool = Field(
        default=False, description="Whether this is an OPTIONAL MATCH"
    )


class WhereClause(BaseModel):
    """Represents a WHERE clause in a Cypher query.

    Attributes:
        conditions: The predicate expressions as a dictionary

    Example:
        >>> WhereClause(
        ...     conditions={
        ...         'type': 'comparison',
        ...         'operator': '=',
        ...         'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
        ...         'right': {'type': 'literal', 'value': 'John', 'value_type': 'string'}
        ...     }
        ... )
    """

    conditions: dict[str, Any] = Field(
        description="Predicate expressions (nested dictionary)"
    )


class ReturnClause(BaseModel):
    """Represents a RETURN clause in a Cypher query.

    Attributes:
        items: List of items to return (identifiers, properties, or expressions)
        distinct: Whether to use DISTINCT
        order_by: Optional list of ordering specifications
        limit: Optional limit value
        skip: Optional skip value

    Example:
        >>> ReturnClause(
        ...     items=[Identifier('n'), Property(Identifier('n'), Identifier('name'))],
        ...     distinct=False,
        ...     limit=10
        ... )
    """

    items: list[Any] = Field(description="Items to return")
    distinct: bool = Field(default=False, description="Whether to use DISTINCT")
    order_by: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Ordering specifications"
    )
    limit: Optional[int] = Field(default=None, description="LIMIT clause value")
    skip: Optional[int] = Field(default=None, description="SKIP clause value")


# ============================================================================
# Query Node
# ============================================================================


class Query(BaseModel):
    """Represents a complete Cypher query.

    This is the root AST node for any parsed Cypher query.

    Attributes:
        match_clause: The MATCH clause (required for basic queries)
        where_clause: Optional WHERE clause
        return_clause: The RETURN clause

    Example:
        >>> Query(
        ...     match_clause=MatchClause(paths=[...]),
        ...     where_clause=WhereClause(conditions={}),
        ...     return_clause=ReturnClause(items=[Identifier('n')])
        ... )
    """

    match_clause: MatchClause = Field(description="MATCH clause")
    where_clause: Optional[WhereClause] = Field(
        default=None, description="Optional WHERE clause"
    )
    return_clause: ReturnClause = Field(description="RETURN clause")

    def __str__(self) -> str:
        """Return string representation of the query."""
        parts = [f"MATCH {self.match_clause}"]
        if self.where_clause:
            parts.append(f"WHERE {self.where_clause}")
        parts.append(f"RETURN {self.return_clause}")
        return "\n".join(parts)
