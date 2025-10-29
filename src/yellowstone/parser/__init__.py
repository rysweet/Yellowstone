"""
Cypher parser module for Yellowstone.

This module provides a complete Cypher query parser that converts query strings
into an Abstract Syntax Tree (AST) for further processing and translation.

Main Components:
    - CypherParser: The main parser class using recursive descent
    - parse_query(): Convenience function for parsing queries
    - AST Nodes: Complete set of node types (Query, MatchClause, etc.)
    - Visitor: Pattern for traversing and transforming the AST

Example:
    >>> from yellowstone.parser import parse_query
    >>> query_str = "MATCH (n:Person {name: 'John'}) RETURN n.age"
    >>> ast = parse_query(query_str)
    >>> print(ast.match_clause.paths[0].nodes[0].labels[0].name)
    'Person'
"""

from .parser import CypherParser, parse_query, Lexer
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
from .visitor import (
    Visitor,
    DefaultVisitor,
    CollectingVisitor,
    ValidationVisitor,
    DotVisitor,
)

__all__ = [
    # Parser classes
    "CypherParser",
    "parse_query",
    "Lexer",
    # AST node classes
    "Query",
    "MatchClause",
    "WhereClause",
    "ReturnClause",
    "PathExpression",
    "NodePattern",
    "RelationshipPattern",
    "Property",
    "Identifier",
    "Literal",
    # Visitor classes
    "Visitor",
    "DefaultVisitor",
    "CollectingVisitor",
    "ValidationVisitor",
    "DotVisitor",
]
