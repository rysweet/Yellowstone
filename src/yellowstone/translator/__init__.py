"""
KQL Translator module for Yellowstone.

This module translates Cypher query AST structures into KQL (Kusto Query Language)
queries. The translator handles MATCH, WHERE, and RETURN clauses with support for
variable-length paths and complex expressions.
"""

from .translator import translate, CypherToKQLTranslator

__all__ = ["translate", "CypherToKQLTranslator"]
