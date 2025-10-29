"""
Visitor pattern implementation for AST traversal and transformation.

This module provides the base classes for implementing the Visitor design
pattern for traversing and transforming Cypher AST nodes. Subclasses can
override visit methods to implement specific transformations or analyses.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from .ast_nodes import (
    Query,
    MatchClause,
    WhereClause,
    ReturnClause,
    PathExpression,
    NodePattern,
    RelationshipPattern,
    Property,
    Identifier,
    Literal,
)

# Type variable for visitor return values
T = TypeVar("T")


class Visitor(ABC, Generic[T]):
    """Abstract base class for AST visitors.

    Implements the Visitor design pattern for traversing and transforming
    AST nodes. Subclasses should override visit_* methods to implement
    specific behavior.

    Type parameter T represents the return type of visit methods.

    Example:
        >>> class PrintingVisitor(Visitor[None]):
        ...     def visit_query(self, node: Query) -> None:
        ...         print(f"Query with {len(node.match_clause.paths)} paths")
        ...         node.match_clause.accept(self)
    """

    @abstractmethod
    def visit_query(self, node: Query) -> T:
        """Visit a Query node.

        Args:
            node: The Query AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_match_clause(self, node: MatchClause) -> T:
        """Visit a MatchClause node.

        Args:
            node: The MatchClause AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_where_clause(self, node: WhereClause) -> T:
        """Visit a WhereClause node.

        Args:
            node: The WhereClause AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_return_clause(self, node: ReturnClause) -> T:
        """Visit a ReturnClause node.

        Args:
            node: The ReturnClause AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_path_expression(self, node: PathExpression) -> T:
        """Visit a PathExpression node.

        Args:
            node: The PathExpression AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_node_pattern(self, node: NodePattern) -> T:
        """Visit a NodePattern node.

        Args:
            node: The NodePattern AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_relationship_pattern(self, node: RelationshipPattern) -> T:
        """Visit a RelationshipPattern node.

        Args:
            node: The RelationshipPattern AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_property(self, node: Property) -> T:
        """Visit a Property node.

        Args:
            node: The Property AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_identifier(self, node: Identifier) -> T:
        """Visit an Identifier node.

        Args:
            node: The Identifier AST node

        Returns:
            Result of type T
        """
        pass

    @abstractmethod
    def visit_literal(self, node: Literal) -> T:
        """Visit a Literal node.

        Args:
            node: The Literal AST node

        Returns:
            Result of type T
        """
        pass


class DefaultVisitor(Visitor[None]):
    """Default visitor implementation that does nothing.

    Useful as a base class for visitors that only need to override
    specific visit methods.

    Example:
        >>> class CountingVisitor(DefaultVisitor):
        ...     def __init__(self):
        ...         self.identifier_count = 0
        ...
        ...     def visit_identifier(self, node: Identifier) -> None:
        ...         self.identifier_count += 1
    """

    def visit_query(self, node: Query) -> None:
        """Default query visit: traverse children."""
        node.match_clause.accept(self)
        if node.where_clause:
            node.where_clause.accept(self)
        node.return_clause.accept(self)

    def visit_match_clause(self, node: MatchClause) -> None:
        """Default match clause visit: traverse paths."""
        for path in node.paths:
            path.accept(self)

    def visit_where_clause(self, node: WhereClause) -> None:
        """Default where clause visit: do nothing."""
        pass

    def visit_return_clause(self, node: ReturnClause) -> None:
        """Default return clause visit: traverse items."""
        for item in node.items:
            if isinstance(item, (Identifier, Property, Literal)):
                item.accept(self)

    def visit_path_expression(self, node: PathExpression) -> None:
        """Default path expression visit: traverse nodes and relationships."""
        for node_pattern in node.nodes:
            node_pattern.accept(self)
        for rel_pattern in node.relationships:
            rel_pattern.accept(self)

    def visit_node_pattern(self, node: NodePattern) -> None:
        """Default node pattern visit: traverse labels."""
        if node.variable:
            node.variable.accept(self)
        for label in node.labels:
            label.accept(self)

    def visit_relationship_pattern(self, node: RelationshipPattern) -> None:
        """Default relationship pattern visit: traverse variable and type."""
        if node.variable:
            node.variable.accept(self)
        if node.relationship_type:
            node.relationship_type.accept(self)

    def visit_property(self, node: Property) -> None:
        """Default property visit: traverse variable and property name."""
        node.variable.accept(self)
        node.property_name.accept(self)

    def visit_identifier(self, node: Identifier) -> None:
        """Default identifier visit: do nothing."""
        pass

    def visit_literal(self, node: Literal) -> None:
        """Default literal visit: do nothing."""
        pass


# ============================================================================
# Concrete Visitor Implementations
# ============================================================================


class CollectingVisitor(DefaultVisitor):
    """Visitor that collects all identifiers and literals in a query.

    Attributes:
        identifiers: List of all Identifier nodes found
        literals: List of all Literal nodes found
    """

    def __init__(self) -> None:
        """Initialize the collecting visitor."""
        super().__init__()
        self.identifiers: list[Identifier] = []
        self.literals: list[Literal] = []

    def visit_identifier(self, node: Identifier) -> None:
        """Collect identifier."""
        self.identifiers.append(node)

    def visit_literal(self, node: Literal) -> None:
        """Collect literal."""
        self.literals.append(node)


class ValidationVisitor(DefaultVisitor):
    """Visitor that validates query structure and semantics.

    Attributes:
        errors: List of validation error messages
        warnings: List of validation warning messages
    """

    def __init__(self) -> None:
        """Initialize the validation visitor."""
        super().__init__()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.defined_variables: set[str] = set()

    def visit_query(self, node: Query) -> None:
        """Validate query structure."""
        # Reset defined variables for this query
        self.defined_variables.clear()

        # Validate match clause
        node.match_clause.accept(self)

        # Validate where clause
        if node.where_clause:
            node.where_clause.accept(self)

        # Validate return clause
        node.return_clause.accept(self)

    def visit_node_pattern(self, node: NodePattern) -> None:
        """Validate node pattern."""
        if node.variable:
            var_name = node.variable.name
            self.defined_variables.add(var_name)

    def visit_relationship_pattern(self, node: RelationshipPattern) -> None:
        """Validate relationship pattern."""
        if node.variable:
            var_name = node.variable.name
            self.defined_variables.add(var_name)

    def visit_return_clause(self, node: ReturnClause) -> None:
        """Validate return clause references defined variables."""
        for item in node.items:
            if isinstance(item, Identifier):
                if item.name not in self.defined_variables:
                    self.warnings.append(
                        f"RETURN clause references undefined variable: '{item.name}'"
                    )
            elif isinstance(item, Property):
                if item.variable.name not in self.defined_variables:
                    self.errors.append(
                        f"RETURN clause references undefined variable: '{item.variable.name}'"
                    )


class DotVisitor(DefaultVisitor):
    """Visitor that generates GraphViz DOT representation of the AST.

    Used to visualize the query structure for debugging and analysis.

    Attributes:
        nodes: List of DOT node definitions
        edges: List of DOT edge definitions
    """

    def __init__(self) -> None:
        """Initialize the DOT visitor."""
        super().__init__()
        self.nodes: list[str] = []
        self.edges: list[str] = []
        self._counter = 0

    def _next_id(self) -> str:
        """Generate next unique node ID.

        Returns:
            Unique node identifier
        """
        self._counter += 1
        return f"node_{self._counter}"

    def generate_dot(self, query: Query) -> str:
        """Generate complete DOT graph representation.

        Args:
            query: The Query to visualize

        Returns:
            DOT format string
        """
        self.nodes.clear()
        self.edges.clear()
        self._counter = 0

        query.accept(self)

        dot_lines = ["digraph CypherAST {"]
        dot_lines.extend(self.nodes)
        dot_lines.extend(self.edges)
        dot_lines.append("}")

        return "\n".join(dot_lines)

    def visit_query(self, node: Query) -> None:
        """Visit query and generate DOT nodes."""
        query_id = self._next_id()
        self.nodes.append(f'  {query_id} [label="Query"]')

        match_id = self._next_id()
        self.nodes.append(f'  {match_id} [label="MATCH"]')
        self.edges.append(f"  {query_id} -> {match_id}")

        node.match_clause.accept(self)

        if node.where_clause:
            where_id = self._next_id()
            self.nodes.append(f'  {where_id} [label="WHERE"]')
            self.edges.append(f"  {query_id} -> {where_id}")
            node.where_clause.accept(self)

        return_id = self._next_id()
        self.nodes.append(f'  {return_id} [label="RETURN"]')
        self.edges.append(f"  {query_id} -> {return_id}")
        node.return_clause.accept(self)

    def visit_identifier(self, node: Identifier) -> None:
        """Visit identifier and generate DOT node."""
        ident_id = self._next_id()
        self.nodes.append(f'  {ident_id} [label="Identifier: {node.name}"]')

    def visit_literal(self, node: Literal) -> None:
        """Visit literal and generate DOT node."""
        lit_id = self._next_id()
        label = f"Literal: {node.value} ({node.value_type})"
        self.nodes.append(f'  {lit_id} [label="{label}"]')


# ============================================================================
# Extend AST Nodes with Visitor Support
# ============================================================================

# Note: These methods are added to the AST node classes to support
# the visitor pattern. They enable traversal by calling accept(visitor)
# on any AST node.


def add_visitor_methods() -> None:
    """Add visitor support methods to all AST node classes.

    This function adds the accept() method to all AST node classes,
    enabling them to work with the Visitor pattern.
    """

    def make_accept(visit_method_name: str):
        """Create an accept method for a specific visit method.

        Args:
            visit_method_name: The name of the visitor method to call

        Returns:
            An accept method implementation
        """

        def accept(self: Any, visitor: Visitor[T]) -> T:
            """Accept a visitor.

            Args:
                visitor: The visitor to accept

            Returns:
                Result from visitor method
            """
            return getattr(visitor, visit_method_name)(self)

        return accept

    # Add accept methods to each node class
    Query.accept = make_accept("visit_query")  # type: ignore
    MatchClause.accept = make_accept("visit_match_clause")  # type: ignore
    WhereClause.accept = make_accept("visit_where_clause")  # type: ignore
    ReturnClause.accept = make_accept("visit_return_clause")  # type: ignore
    PathExpression.accept = make_accept("visit_path_expression")  # type: ignore
    NodePattern.accept = make_accept("visit_node_pattern")  # type: ignore
    RelationshipPattern.accept = make_accept("visit_relationship_pattern")  # type: ignore
    Property.accept = make_accept("visit_property")  # type: ignore
    Identifier.accept = make_accept("visit_identifier")  # type: ignore
    Literal.accept = make_accept("visit_literal")  # type: ignore


# Initialize visitor support
add_visitor_methods()
