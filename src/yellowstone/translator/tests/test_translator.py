"""Tests for the main translator orchestrator."""

import pytest
from yellowstone.parser.ast_nodes import (
    Query, MatchClause, WhereClause, ReturnClause, PathExpression,
    NodePattern, RelationshipPattern, Identifier, Property, Literal
)
from yellowstone.translator import CypherToKQLTranslator, translate
from yellowstone.models import TranslationStrategy, KQLQuery


class TestCypherToKQLTranslator:
    """Test suite for CypherToKQLTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = CypherToKQLTranslator()

    def test_translator_initialization(self):
        """Test translator initializes with component translators."""
        assert self.translator.graph_match_translator is not None
        assert self.translator.where_translator is not None
        assert self.translator.return_translator is not None

    def test_translate_simple_query(self):
        """Test translation of a simple Cypher query."""
        # Build simple query: MATCH (n)-[r]->(m) RETURN n, m
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(variable=Identifier(name='r'))
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])
        return_clause = ReturnClause(items=[Identifier(name='n'), Identifier(name='m')])

        query = Query(match_clause=match, return_clause=return_clause)
        result = self.translator.translate(query)

        assert isinstance(result, KQLQuery)
        assert result.strategy == TranslationStrategy.FAST_PATH
        assert 0.0 <= result.confidence <= 1.0
        assert "graph-match" in result.query
        assert "project" in result.query

    def test_translate_with_where_clause(self):
        """Test translation including WHERE clause."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern()
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        where_conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
            'right': {'type': 'literal', 'value': 'Alice', 'value_type': 'string'}
        }
        where = WhereClause(conditions=where_conditions)

        return_clause = ReturnClause(items=[Identifier(name='n')])
        query = Query(match_clause=match, where_clause=where, return_clause=return_clause)

        result = self.translator.translate(query)

        assert "where" in result.query
        assert "==" in result.query
        assert "'Alice'" in result.query

    def test_translate_raises_on_invalid_query_type(self):
        """Test that translate raises on non-Query input."""
        with pytest.raises(TypeError):
            self.translator.translate("not a query")

    def test_translate_raises_on_missing_match(self):
        """Test that translate raises when MATCH clause is missing."""
        from pydantic import ValidationError
        return_clause = ReturnClause(items=[Identifier(name='n')])

        with pytest.raises(ValidationError):
            query = Query(match_clause=None, return_clause=return_clause)

    def test_translate_raises_on_missing_return(self):
        """Test that translate raises when RETURN clause is missing."""
        from pydantic import ValidationError
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        with pytest.raises(ValidationError):
            query = Query(match_clause=match, return_clause=None)

    def test_translate_match_clause(self):
        """Test translating just the MATCH clause."""
        node_n = NodePattern(variable=Identifier(name='n'), labels=[Identifier(name='Person')])
        node_m = NodePattern(variable=Identifier(name='m'), labels=[Identifier(name='Movie')])
        rel = RelationshipPattern(relationship_type=Identifier(name='ACTED_IN'))
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate_match(match)

        assert "graph-match" in result
        assert "Person" in result
        assert "Movie" in result
        assert "ACTED_IN" in result

    def test_translate_where_clause(self):
        """Test translating just the WHERE clause."""
        conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
            'right': {'type': 'literal', 'value': 'Bob', 'value_type': 'string'}
        }
        where = WhereClause(conditions=conditions)

        result = self.translator.translate_where(where)

        assert "where" in result
        assert "n.name" in result
        assert "==" in result
        assert "'Bob'" in result

    def test_translate_where_raises_on_none(self):
        """Test that translate_where raises on None input."""
        with pytest.raises(TypeError):
            self.translator.translate_where(None)

    def test_translate_return_clause(self):
        """Test translating just the RETURN clause."""
        return_clause = ReturnClause(
            items=[Identifier(name='n'), Property(variable=Identifier(name='m'), property_name=Identifier(name='name'))],
            limit=10
        )

        result = self.translator.translate_return(return_clause)

        assert "project" in result
        assert "limit 10" in result

    def test_translate_return_raises_on_wrong_type(self):
        """Test that translate_return raises on non-ReturnClause input."""
        with pytest.raises(TypeError):
            self.translator.translate_return("not a return clause")

    def test_get_translation_summary(self):
        """Test getting translation metadata without full translation."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        node_p = NodePattern(variable=Identifier(name='p'))

        rel1 = RelationshipPattern()
        rel2 = RelationshipPattern()
        path = PathExpression(nodes=[node_n, node_m, node_p], relationships=[rel1, rel2])
        match = MatchClause(paths=[path])

        conditions = {
            'type': 'logical',
            'operator': 'AND',
            'operands': [
                {'type': 'comparison', 'operator': '=', 'left': {}, 'right': {}},
                {'type': 'comparison', 'operator': '>', 'left': {}, 'right': {}}
            ]
        }
        where = WhereClause(conditions=conditions)
        return_clause = ReturnClause(items=[Identifier(name='n')])

        query = Query(match_clause=match, where_clause=where, return_clause=return_clause)
        summary = self.translator.get_translation_summary(query)

        assert summary["num_hops"] == 2
        assert summary["has_variable_length_paths"] is False
        assert summary["num_conditions"] == 2
        assert summary["has_aggregation"] is False
        assert summary["estimated_complexity"] in ("Low", "Medium", "High")

    def test_get_translation_summary_with_aggregation(self):
        """Test summary with aggregation functions."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        agg_func = {
            'type': 'function',
            'name': 'COUNT',
            'arguments': [{'type': 'identifier', 'name': 'n'}]
        }
        return_clause = ReturnClause(items=[agg_func])

        query = Query(match_clause=match, return_clause=return_clause)
        summary = self.translator.get_translation_summary(query)

        assert summary["has_aggregation"] is True

    def test_assemble_query_requires_match_and_return(self):
        """Test that query assembly requires both match and return."""
        with pytest.raises(ValueError):
            self.translator._assemble_query("", "", "")

    def test_assemble_query_with_all_clauses(self):
        """Test assembling query with all three clause types."""
        match = "graph-match (n)-[r]->(m)"
        where = "where n.age > 30"
        return_ = "project n.name"

        result = self.translator._assemble_query(match, where, return_)

        assert match in result
        assert where in result
        assert return_ in result
        assert "| " in result


class TestTranslateFunction:
    """Test the convenience translate() function."""

    def test_translate_function_basic(self):
        """Test the module-level translate function."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])
        return_clause = ReturnClause(items=[Identifier(name='n')])
        query = Query(match_clause=match, return_clause=return_clause)

        result = translate(query)

        assert isinstance(result, KQLQuery)
        assert result.strategy == TranslationStrategy.FAST_PATH

    def test_translate_function_with_confidence(self):
        """Test translate function with custom confidence."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])
        return_clause = ReturnClause(items=[Identifier(name='n')])
        query = Query(match_clause=match, return_clause=return_clause)

        result = translate(query, confidence=0.85)

        assert result.confidence == 0.85

    def test_translate_function_raises_on_invalid_input(self):
        """Test that translate function raises on invalid input."""
        with pytest.raises((TypeError, ValueError)):
            translate("invalid query")


class TestTranslationEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = CypherToKQLTranslator()

    def test_optional_match(self):
        """Test translation of OPTIONAL MATCH."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path], optional=True)
        return_clause = ReturnClause(items=[Identifier(name='n')])
        query = Query(match_clause=match, return_clause=return_clause)

        result = self.translator.translate(query)

        assert "optional" in result.query

    def test_distinct_return(self):
        """Test translation with DISTINCT modifier."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])
        return_clause = ReturnClause(items=[Identifier(name='n')], distinct=True)
        query = Query(match_clause=match, return_clause=return_clause)

        result = self.translator.translate(query)

        assert "distinct" in result.query

    def test_multiple_paths_in_match(self):
        """Test MATCH with multiple disjoint paths."""
        node1 = NodePattern(variable=Identifier(name='n'))
        path1 = PathExpression(nodes=[node1], relationships=[])

        node2 = NodePattern(variable=Identifier(name='m'))
        path2 = PathExpression(nodes=[node2], relationships=[])

        match = MatchClause(paths=[path1, path2])
        return_clause = ReturnClause(items=[Identifier(name='n'), Identifier(name='m')])
        query = Query(match_clause=match, return_clause=return_clause)

        result = self.translator.translate(query)

        assert "graph-match" in result.query
