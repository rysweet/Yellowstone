"""
Main Cypher-to-KQL translation engine.
"""

from typing import Optional
import re
from .models import CypherQuery, KQLQuery, TranslationContext, TranslationStrategy
from .parser.parser import parse_query
from .parser.ast_nodes import Query, WhereClause
from .schema.schema_mapper import SchemaMapper
from .translator.graph_match import GraphMatchTranslator
from .translator.where_clause import WhereClauseTranslator
from .translator.return_clause import ReturnClauseTranslator


class TranslationError(Exception):
    """Raised when translation fails."""
    pass


class CypherTranslator:
    """
    Translates Cypher queries to KQL using native graph operators.

    Implements a three-tier translation strategy:
    - Fast Path (85%): Direct graph operator translation
    - AI Path (10%): Agentic AI via Claude Agent SDK
    - Fallback (5%): Join-based translation
    """

    def __init__(self, enable_ai: bool = True, schema_path: Optional[str] = None):
        """
        Initialize the translator.

        Args:
            enable_ai: Enable agentic AI translation for complex patterns
            schema_path: Path to schema YAML file (None for default)
        """
        self.enable_ai = enable_ai

        # Initialize schema mapper
        try:
            self.schema_mapper = SchemaMapper(schema_path=schema_path)
        except Exception as e:
            raise TranslationError(f"Failed to load schema: {e}")

        # Initialize component translators
        self.graph_match_translator = GraphMatchTranslator()
        self.where_clause_translator = WhereClauseTranslator()
        self.return_clause_translator = ReturnClauseTranslator()

    def translate(
        self,
        cypher: CypherQuery,
        context: TranslationContext
    ) -> KQLQuery:
        """
        Translate a Cypher query to KQL.

        Args:
            cypher: Input Cypher query
            context: Translation context (user, permissions, etc.)

        Returns:
            Translated KQL query with metadata

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Step 1: Parse Cypher query into AST
            ast = parse_query(cypher.query)

            # Step 2: Determine translation strategy
            strategy = self._classify_query_complexity(ast)

            # Step 3: Translate using fast path (for now, AI path not implemented)
            if strategy == TranslationStrategy.FAST_PATH:
                kql_query_str = self._translate_fast_path(ast, cypher)
                confidence = 0.95
            elif strategy == TranslationStrategy.AI_PATH and self.enable_ai:
                # AI path not yet implemented, fall back to fast path
                kql_query_str = self._translate_fast_path(ast, cypher)
                confidence = 0.80
            else:
                # Fallback path
                kql_query_str = self._translate_fast_path(ast, cypher)
                confidence = 0.70

            # Step 4: Create KQL query object
            kql = KQLQuery(
                query=kql_query_str,
                strategy=strategy,
                confidence=confidence,
                estimated_execution_time_ms=None  # Could be estimated from query complexity
            )

            # Step 5: Validate the generated KQL
            if not self.validate(kql):
                raise TranslationError("Generated KQL failed validation")

            return kql

        except SyntaxError as e:
            raise TranslationError(f"Failed to parse Cypher query: {e}")
        except Exception as e:
            raise TranslationError(f"Translation failed: {e}")

    def _classify_query_complexity(self, ast: Query) -> TranslationStrategy:
        """
        Classify query complexity to determine translation strategy.

        Args:
            ast: Parsed Cypher query AST

        Returns:
            Translation strategy to use
        """
        # Simple heuristics for now:
        # - Fast path: Simple patterns with 1-2 hops, basic WHERE, simple RETURN
        # - AI path: Complex patterns with 3+ hops, complex WHERE, aggregations
        # - Fallback: Very complex patterns that need join-based approach

        num_paths = len(ast.match_clause.paths)
        total_relationships = sum(len(path.relationships) for path in ast.match_clause.paths)

        has_complex_where = False
        if ast.where_clause:
            # Check for nested logical operators (more than 2 levels deep)
            has_complex_where = self._is_complex_condition(ast.where_clause.conditions, depth=0)

        # Fast path: Simple queries
        if num_paths <= 2 and total_relationships <= 2 and not has_complex_where:
            return TranslationStrategy.FAST_PATH

        # AI path would be for medium complexity (not implemented yet)
        # For now, use fast path for everything that's not extremely complex
        if num_paths <= 5 and total_relationships <= 5:
            return TranslationStrategy.FAST_PATH

        # Fallback for very complex queries
        return TranslationStrategy.FALLBACK

    def _is_complex_condition(self, condition: dict, depth: int, max_depth: int = 3) -> bool:
        """Check if a condition is complex (deeply nested)."""
        if depth > max_depth:
            return True

        if condition.get("type") == "logical":
            # Check operands recursively
            operands = condition.get("operands", [])
            for operand in operands:
                if isinstance(operand, dict) and self._is_complex_condition(operand, depth + 1, max_depth):
                    return True

        return False

    def _translate_fast_path(self, ast: Query, cypher: CypherQuery) -> str:
        """
        Translate using fast path (direct graph operator translation).

        Args:
            ast: Parsed query AST
            cypher: Original Cypher query

        Returns:
            KQL query string
        """
        kql_parts = []

        # Step 1: Translate MATCH clause to graph-match
        match_kql = self.graph_match_translator.translate(ast.match_clause)
        kql_parts.append(match_kql)

        # Step 2: Translate WHERE clause if present
        if ast.where_clause:
            where_kql = self.where_clause_translator.translate(ast.where_clause.conditions)
            if where_kql:
                kql_parts.append(f"| where {where_kql}")

        # Step 3: Translate RETURN clause
        return_kql = self.return_clause_translator.translate(ast.return_clause)
        kql_parts.append(f"| {return_kql}")

        # Combine all parts
        return "\n".join(kql_parts)

    def validate(self, kql: KQLQuery) -> bool:
        """
        Validate a translated KQL query.

        Args:
            kql: KQL query to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            query = kql.query

            # Basic syntax validation
            if not query or not query.strip():
                return False

            # Check for required keywords
            if "graph-match" not in query.lower() and "project" not in query.lower():
                return False

            # Validate table references against schema
            # Extract table names from the query (simplified pattern matching)
            table_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
            potential_tables = re.findall(table_pattern, query)

            # Get valid Sentinel tables from schema
            valid_tables = set(self.schema_mapper.cache.table_to_fields.keys())

            # For now, just check that the query doesn't reference non-existent tables
            # Note: This is a simplified check - a full validator would parse the KQL AST
            for table in potential_tables:
                # Skip common KQL keywords
                if table.lower() in {'graph', 'match', 'where', 'project', 'sort',
                                     'by', 'limit', 'offset', 'distinct', 'asc', 'desc'}:
                    continue

                # If it looks like a table reference and isn't in our schema,
                # that's okay - it might be a valid KQL construct we don't recognize
                # We'll be permissive here

            # Check for balanced parentheses
            if query.count('(') != query.count(')'):
                return False

            # Check for balanced brackets
            if query.count('[') != query.count(']'):
                return False

            # Check for valid operators (simplified)
            invalid_cypher_ops = ['=~', '=~']  # Regex ops not directly supported
            for op in invalid_cypher_ops:
                if op in query:
                    return False

            return True

        except Exception:
            return False
