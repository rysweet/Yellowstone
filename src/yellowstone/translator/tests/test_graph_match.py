"""Tests for graph MATCH clause translation."""

import pytest
from yellowstone.parser.ast_nodes import (
    MatchClause, PathExpression, NodePattern, RelationshipPattern, Identifier
)
from yellowstone.translator.graph_match import GraphMatchTranslator


class TestGraphMatchTranslator:
    """Test suite for GraphMatchTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = GraphMatchTranslator()

    def test_translator_initialization(self):
        """Test translator initializes with path translator."""
        assert self.translator.path_translator is not None

    def test_translate_single_node(self):
        """Test translation of single node pattern."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "graph-match" in result
        assert "(n)" in result

    def test_translate_node_with_label(self):
        """Test translation of node with label."""
        node = NodePattern(
            variable=Identifier(name='n'),
            labels=[Identifier(name='Person')]
        )
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "n:Person" in result

    def test_translate_node_with_multiple_labels(self):
        """Test translation of node with multiple labels."""
        node = NodePattern(
            variable=Identifier(name='n'),
            labels=[Identifier(name='Person'), Identifier(name='Actor')]
        )
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "Person" in result
        assert "Actor" in result

    def test_translate_simple_relationship(self):
        """Test translation of simple node-relationship-node pattern."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(variable=Identifier(name='r'))
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "-[r]->" in result

    def test_translate_relationship_with_type(self):
        """Test translation of relationship with type."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(
            variable=Identifier(name='r'),
            relationship_type=Identifier(name='KNOWS')
        )
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "-[r:KNOWS]->" in result

    def test_translate_relationship_incoming(self):
        """Test translation of incoming relationship."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(direction='in')
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "<-[" in result

    def test_translate_relationship_undirected(self):
        """Test translation of undirected relationship."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(direction='both')
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "-[" in result and "]-" in result
        assert "->" not in result  # Should not have arrow

    def test_translate_multi_hop_path(self):
        """Test translation of multi-hop path."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        node_p = NodePattern(variable=Identifier(name='p'))

        rel1 = RelationshipPattern(variable=Identifier(name='r1'))
        rel2 = RelationshipPattern(variable=Identifier(name='r2'))

        path = PathExpression(nodes=[node_n, node_m, node_p], relationships=[rel1, rel2])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "graph-match" in result
        assert "(n)" in result
        assert "(m)" in result
        assert "(p)" in result

    def test_translate_optional_match(self):
        """Test translation of OPTIONAL MATCH."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path], optional=True)

        result = self.translator.translate(match)

        assert "optional" in result

    def test_translate_multiple_paths(self):
        """Test translation with multiple disjoint paths."""
        path1 = PathExpression(
            nodes=[NodePattern(variable=Identifier(name='n'))],
            relationships=[]
        )
        path2 = PathExpression(
            nodes=[NodePattern(variable=Identifier(name='m'))],
            relationships=[]
        )
        match = MatchClause(paths=[path1, path2])

        result = self.translator.translate(match)

        assert "(n)" in result
        assert "(m)" in result
        assert "," in result  # Paths should be comma-separated

    def test_translate_raises_on_invalid_match_type(self):
        """Test that translator raises on non-MatchClause input."""
        with pytest.raises(ValueError):
            self.translator.translate("not a match clause")

    def test_translate_raises_on_no_paths(self):
        """Test that translator raises when MATCH has no paths."""
        match = MatchClause(paths=[])

        with pytest.raises(ValueError):
            self.translator.translate(match)

    def test_extract_variable_names(self):
        """Test extraction of variable names from MATCH clause."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(variable=Identifier(name='r'))
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        variables = self.translator.extract_variable_names(match)

        assert 'n' in variables
        assert 'm' in variables
        assert 'r' in variables

    def test_extract_return_candidates(self):
        """Test extraction of available labels for return clause."""
        node_n = NodePattern(
            variable=Identifier(name='n'),
            labels=[Identifier(name='Person')]
        )
        node_m = NodePattern(
            variable=Identifier(name='m'),
            labels=[Identifier(name='Movie')]
        )
        rel = RelationshipPattern()
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        candidates = self.translator.extract_return_candidates(match)

        assert 'n' in candidates
        assert 'Person' in candidates['n']
        assert 'm' in candidates
        assert 'Movie' in candidates['m']

    def test_extract_return_candidates_multiple_labels(self):
        """Test extraction with nodes having multiple labels."""
        node = NodePattern(
            variable=Identifier(name='n'),
            labels=[Identifier(name='Person'), Identifier(name='Actor')]
        )
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        candidates = self.translator.extract_return_candidates(match)

        assert len(candidates['n']) == 2
        assert 'Person' in candidates['n']
        assert 'Actor' in candidates['n']

    def test_format_properties_with_string(self):
        """Test property formatting with string value."""
        result = self.translator._format_properties({'name': 'John'})

        assert 'name' in result
        assert 'John' in result

    def test_format_properties_with_number(self):
        """Test property formatting with numeric value."""
        result = self.translator._format_properties({'age': 30})

        assert 'age' in result
        assert '30' in result

    def test_format_properties_with_boolean(self):
        """Test property formatting with boolean value."""
        result = self.translator._format_properties({'active': True})

        assert 'active' in result
        assert 'true' in result

    def test_format_properties_with_null(self):
        """Test property formatting with null value."""
        result = self.translator._format_properties({'deleted': None})

        assert 'deleted' in result
        assert 'null' in result

    def test_format_properties_empty(self):
        """Test property formatting with empty dict."""
        result = self.translator._format_properties({})

        assert result == ""

    def test_translate_node_pattern_without_variable(self):
        """Test translation of node pattern without variable."""
        node = NodePattern(labels=[Identifier(name='Person')])
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "Person" in result

    def test_translate_node_pattern_without_labels(self):
        """Test translation of node pattern without labels."""
        node = NodePattern(variable=Identifier(name='n'))
        path = PathExpression(nodes=[node], relationships=[])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "(n)" in result

    def test_translate_relationship_without_type(self):
        """Test translation of relationship without type."""
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))
        rel = RelationshipPattern(variable=Identifier(name='r'))
        path = PathExpression(nodes=[node_n, node_m], relationships=[rel])
        match = MatchClause(paths=[path])

        result = self.translator.translate(match)

        assert "-[r]->" in result

    def test_invalid_path_structure_raises(self):
        """Test that invalid path structure raises ValueError."""
        # Create path with mismatched nodes and relationships
        node_n = NodePattern(variable=Identifier(name='n'))
        node_m = NodePattern(variable=Identifier(name='m'))

        rel1 = RelationshipPattern()
        rel2 = RelationshipPattern()

        path = PathExpression(nodes=[node_n, node_m], relationships=[rel1, rel2])
        match = MatchClause(paths=[path])

        with pytest.raises(ValueError):
            self.translator.translate(match)
