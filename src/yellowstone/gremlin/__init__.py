"""
Gremlin parser module for Yellowstone.

This module provides a complete Gremlin query parser that converts query strings
into an Abstract Syntax Tree (AST) for further processing and translation.

Main Components:
    - GremlinParser: The main parser class
    - parse_gremlin(): Convenience function for parsing queries
    - AST Nodes: Complete set of step types and traversal containers

Example:
    >>> from yellowstone.gremlin import parse_gremlin
    >>> query_str = "g.V().hasLabel('Person').out('KNOWS').values('name')"
    >>> traversal = parse_gremlin(query_str)
    >>> print(traversal.steps[0])
    V()
"""

from .parser import GremlinParser, parse_gremlin, GremlinParseError, GremlinTokenizer
from .ast import (
    GremlinTraversal,
    Step,
    VertexStep,
    EdgeStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    OrderStep,
    CountStep,
    DedupStep,
    GremlinValue,
    Predicate,
)
from .cypher_bridge import (
    translate_gremlin_to_cypher,
    TranslationError,
    UnsupportedPatternError,
)

__all__ = [
    # Parser classes and functions
    "GremlinParser",
    "parse_gremlin",
    "GremlinParseError",
    "GremlinTokenizer",
    # AST node classes
    "GremlinTraversal",
    "Step",
    "VertexStep",
    "EdgeStep",
    "FilterStep",
    "TraversalStep",
    "ProjectionStep",
    "LimitStep",
    "OrderStep",
    "CountStep",
    "DedupStep",
    "GremlinValue",
    "Predicate",
    # Bridge translation
    "translate_gremlin_to_cypher",
    "TranslationError",
    "UnsupportedPatternError",
]
