"""
Main KQL translator orchestrator.

This module provides the primary interface for translating Cypher query ASTs
to KQL queries. It coordinates the graph match, where clause, and return clause
translators into a cohesive end-to-end translation pipeline.
"""

from typing import Optional
from ..parser.ast_nodes import Query, MatchClause, WhereClause, ReturnClause
from ..models import KQLQuery, TranslationStrategy
from .graph_match import GraphMatchTranslator
from .where_clause import WhereClauseTranslator
from .return_clause import ReturnClauseTranslator


class CypherToKQLTranslator:
    """Orchestrates translation of Cypher queries to KQL.

    This is the main translator class that coordinates the translation of all
    Cypher clauses (MATCH, WHERE, RETURN) into a coherent KQL query string.
    """

    def __init__(self) -> None:
        """Initialize the translator with component translators."""
        self.graph_match_translator = GraphMatchTranslator()
        self.where_translator = WhereClauseTranslator()
        self.return_translator = ReturnClauseTranslator()

    def translate(self, query: Query, confidence: float = 0.95) -> KQLQuery:
        """Translate a Cypher query AST to KQL.

        Args:
            query: A Query AST node containing MATCH, WHERE, and RETURN clauses
            confidence: Confidence score for this translation (0.0-1.0)

        Returns:
            KQLQuery with translated query string, strategy, and metadata

        Raises:
            ValueError: If query structure is invalid or translation fails
            TypeError: If input is not a Query AST node
        """
        if not isinstance(query, Query):
            raise TypeError(f"Expected Query AST node, got {type(query)}")

        if not query.match_clause:
            raise ValueError("Query must have a MATCH clause")

        if not query.return_clause:
            raise ValueError("Query must have a RETURN clause")

        try:
            # Translate match clause (graph pattern)
            match_part = self.translate_match(query.match_clause)

            # Translate where clause if present
            where_part = ""
            if query.where_clause:
                where_part = self.translate_where(query.where_clause)

            # Translate return clause (projection and aggregation)
            return_part = self.translate_return(query.return_clause)

            # Assemble complete KQL query
            kql_query_str = self._assemble_query(match_part, where_part, return_part)

            return KQLQuery(
                query=kql_query_str,
                strategy=TranslationStrategy.FAST_PATH,
                confidence=confidence,
                estimated_execution_time_ms=None,
            )

        except Exception as e:
            raise ValueError(f"Translation failed: {e}") from e

    def translate_match(self, match_clause: MatchClause) -> str:
        """Translate MATCH clause to graph-match syntax.

        Args:
            match_clause: MatchClause AST node

        Returns:
            KQL graph-match string

        Raises:
            ValueError: If match clause is invalid
        """
        if not isinstance(match_clause, MatchClause):
            raise TypeError(f"Expected MatchClause, got {type(match_clause)}")

        return self.graph_match_translator.translate(match_clause)

    def translate_where(self, where_clause: WhereClause) -> str:
        """Translate WHERE clause to KQL filter syntax.

        Args:
            where_clause: WhereClause AST node

        Returns:
            KQL where filter string (e.g., "where n.age > 30 and m.name == 'John'")

        Raises:
            ValueError: If where clause is invalid
        """
        if not isinstance(where_clause, WhereClause):
            raise TypeError(f"Expected WhereClause, got {type(where_clause)}")

        condition_str = self.where_translator.translate(where_clause.conditions)

        if condition_str:
            return f"where {condition_str}"
        return ""

    def translate_return(self, return_clause: ReturnClause) -> str:
        """Translate RETURN clause to KQL projection syntax.

        Args:
            return_clause: ReturnClause AST node

        Returns:
            KQL projection string (e.g., "project n.name, m.age | sort by n.name")

        Raises:
            ValueError: If return clause is invalid
        """
        if not isinstance(return_clause, ReturnClause):
            raise TypeError(f"Expected ReturnClause, got {type(return_clause)}")

        return self.return_translator.translate(return_clause)

    def _assemble_query(self, match: str, where: str, return_: str) -> str:
        """Assemble individual clause translations into complete KQL query.

        Args:
            match: Translated MATCH clause
            where: Translated WHERE clause (may be empty)
            return_: Translated RETURN clause

        Returns:
            Complete KQL query string

        Raises:
            ValueError: If any clause is invalid
        """
        if not match or not return_:
            raise ValueError("Query must have both MATCH and RETURN clauses")

        # Build query: graph-match | where | project
        parts = [match]

        if where:
            parts.append(where)

        parts.append(return_)

        return "\n| ".join(parts)

    def get_translation_summary(self, query: Query) -> dict:
        """Get a summary of translation metadata without full translation.

        Useful for determining translation strategy and estimating resource usage.

        Args:
            query: Query AST node to analyze

        Returns:
            Dictionary with metadata:
            - num_hops: Number of relationship hops
            - has_variable_length_paths: Whether paths have variable length
            - num_conditions: Number of WHERE conditions
            - has_aggregation: Whether RETURN has aggregation functions
            - estimated_complexity: Low/Medium/High

        Raises:
            ValueError: If query structure is invalid
        """
        if not isinstance(query, Query):
            raise TypeError(f"Expected Query AST node, got {type(query)}")

        num_hops = sum(
            len(path.relationships) for path in query.match_clause.paths
        )

        # Check for variable-length paths
        has_var_length = any(
            any(rel.variable for rel in path.relationships)
            for path in query.match_clause.paths
        )

        # Count conditions in WHERE
        num_conditions = self._count_conditions(
            query.where_clause.conditions if query.where_clause else {}
        )

        # Check for aggregations in RETURN
        has_aggregation = self._has_aggregation_functions(query.return_clause)

        # Estimate complexity
        complexity = self._estimate_complexity(
            num_hops, has_var_length, num_conditions, has_aggregation
        )

        return {
            "num_hops": num_hops,
            "has_variable_length_paths": has_var_length,
            "num_conditions": num_conditions,
            "has_aggregation": has_aggregation,
            "estimated_complexity": complexity,
        }

    def _count_conditions(self, conditions: dict) -> int:
        """Recursively count conditions in WHERE clause.

        Args:
            conditions: Conditions dictionary

        Returns:
            Count of condition nodes
        """
        if not conditions:
            return 0

        condition_type = conditions.get("type")

        if condition_type == "logical":
            operands = conditions.get("operands", [])
            return sum(self._count_conditions(op) for op in operands)
        elif condition_type in ("comparison", "function"):
            return 1
        else:
            return 0

    def _has_aggregation_functions(self, return_clause: ReturnClause) -> bool:
        """Check if RETURN clause has aggregation functions.

        Args:
            return_clause: ReturnClause to check

        Returns:
            True if aggregation functions are present
        """
        aggregation_funcs = {"COUNT", "SUM", "AVG", "MIN", "MAX", "COLLECT"}

        for item in return_clause.items:
            if isinstance(item, dict):
                if item.get("type") == "function":
                    func_name = item.get("name", "").upper()
                    if func_name in aggregation_funcs:
                        return True

        return False

    def _estimate_complexity(
        self, num_hops: int, has_var_length: bool, num_conditions: int, has_aggregation: bool
    ) -> str:
        """Estimate query complexity based on characteristics.

        Args:
            num_hops: Number of relationship hops
            has_var_length: Whether there are variable-length paths
            num_conditions: Number of WHERE conditions
            has_aggregation: Whether aggregation is used

        Returns:
            Complexity level: "Low", "Medium", or "High"
        """
        complexity_score = 0

        # Hops contribute to complexity
        complexity_score += min(num_hops * 2, 6)

        # Variable-length paths increase complexity
        if has_var_length:
            complexity_score += 3

        # Conditions add complexity
        complexity_score += min(num_conditions, 4)

        # Aggregations add complexity
        if has_aggregation:
            complexity_score += 2

        if complexity_score >= 8:
            return "High"
        elif complexity_score >= 4:
            return "Medium"
        else:
            return "Low"


def translate(query: Query, confidence: float = 0.95) -> KQLQuery:
    """Convenience function to translate a single Cypher query AST to KQL.

    Args:
        query: Query AST node to translate
        confidence: Confidence score for translation (default 0.95)

    Returns:
        KQLQuery with translated query and metadata

    Raises:
        ValueError: If query is invalid or translation fails
        TypeError: If input is not a Query AST node

    Example:
        >>> from yellowstone.parser.ast_nodes import Query, MatchClause, ReturnClause
        >>> query = Query(match_clause=..., return_clause=...)
        >>> kql = translate(query)
        >>> print(kql.query)
    """
    translator = CypherToKQLTranslator()
    return translator.translate(query, confidence=confidence)
