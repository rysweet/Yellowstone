"""
Tests for Gremlin-to-Cypher Bridge

Tests verify that Gremlin traversals are correctly translated to Cypher query ASTs.
Focus is on contract fulfillment - inputs/outputs match specifications.
"""

import pytest
from yellowstone.gremlin.ast_nodes import (
    GremlinTraversal,
    VertexStep,
    EdgeStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    OrderStep,
)

from yellowstone.gremlin.cypher_bridge import (
    translate_gremlin_to_cypher,
    TranslationError,
    UnsupportedPatternError,
)

from yellowstone.parser.ast_nodes import (
    Query,
    MatchClause,
    WhereClause,
    ReturnClause,
    Identifier,
    NodePattern,
    RelationshipPattern,
    Property,
)


class TestBasicTranslations:
    """Test simple, single-step translations."""

    def test_simple_vertex_query(self):
        """Test: g.V().hasLabel('User') -> MATCH (v:User) RETURN v"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify it's a Query
        assert isinstance(query, Query)

        # Verify MATCH clause
        assert query.match_clause is not None
        assert len(query.match_clause.paths) == 1
        path = query.match_clause.paths[0]
        assert len(path.nodes) == 1
        assert len(path.relationships) == 0

        node = path.nodes[0]
        assert node.variable.name == 'v0'
        assert len(node.labels) == 1
        assert node.labels[0].name == 'User'

        # Verify no WHERE clause
        assert query.where_clause is None

        # Verify RETURN clause
        assert query.return_clause is not None
        assert len(query.return_clause.items) == 1
        assert isinstance(query.return_clause.items[0], Identifier)
        assert query.return_clause.items[0].name == 'v0'

    def test_vertex_without_label(self):
        """Test: g.V() -> MATCH (v) RETURN v"""
        traversal = GremlinTraversal(steps=[
            VertexStep()
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify node has no labels
        node = query.match_clause.paths[0].nodes[0]
        assert len(node.labels) == 0
        assert node.variable.name == 'v0'

        # Still returns the variable
        assert isinstance(query.return_clause.items[0], Identifier)
        assert query.return_clause.items[0].name == 'v0'


class TestFilterTranslations:
    """Test filter step translations."""

    def test_has_filter_single_property(self):
        """Test: g.V().hasLabel('User').has('age', 30) -> MATCH (v:User) WHERE v.age = 30 RETURN v"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            FilterStep(predicate='has', args=['age', 30])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify MATCH has label
        node = query.match_clause.paths[0].nodes[0]
        assert node.labels[0].name == 'User'

        # Verify WHERE clause exists
        assert query.where_clause is not None
        conditions = query.where_clause.conditions

        assert conditions['type'] == 'comparison'
        assert conditions['operator'] == '='
        assert conditions['left']['variable'] == 'v0'
        assert conditions['left']['property'] == 'age'
        assert conditions['right']['value'] == 30
        assert conditions['right']['value_type'] == 'number'

    def test_has_filter_string_value(self):
        """Test: g.V().hasLabel('User').has('name', 'John')"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            FilterStep(predicate='has', args=['name', 'John'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        conditions = query.where_clause.conditions
        assert conditions['right']['value'] == 'John'
        assert conditions['right']['value_type'] == 'string'

    def test_has_filter_boolean_value(self):
        """Test: g.V().has('active', True)"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='has', args=['active', True])
        ])

        query = translate_gremlin_to_cypher(traversal)

        conditions = query.where_clause.conditions
        assert conditions['right']['value'] is True
        assert conditions['right']['value_type'] == 'boolean'

    def test_multiple_has_filters(self):
        """Test: g.V().has('age', 30).has('name', 'John') -> Multiple conditions with AND"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='has', args=['age', 30]),
            FilterStep(predicate='has', args=['name', 'John'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify WHERE clause combines with AND
        conditions = query.where_clause.conditions
        assert conditions['type'] == 'logical'
        assert conditions['operator'] == 'AND'
        assert len(conditions['operands']) == 2

        # Check both conditions present
        operands = conditions['operands']
        assert operands[0]['left']['property'] == 'age'
        assert operands[0]['right']['value'] == 30
        assert operands[1]['left']['property'] == 'name'
        assert operands[1]['right']['value'] == 'John'


class TestTraversalTranslations:
    """Test traversal step translations."""

    def test_simple_out_traversal(self):
        """Test: g.V().hasLabel('User').out('OWNS') -> MATCH (v0:User)-[:OWNS]->(v1) RETURN v1"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            TraversalStep(direction='out', edge_label='OWNS')
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify path structure
        path = query.match_clause.paths[0]
        assert len(path.nodes) == 2
        assert len(path.relationships) == 1

        # Verify source node
        assert path.nodes[0].variable.name == 'v0'
        assert path.nodes[0].labels[0].name == 'User'

        # Verify relationship
        rel = path.relationships[0]
        assert rel.relationship_type.name == 'OWNS'
        assert rel.directed is True
        assert rel.direction == 'out'

        # Verify target node
        assert path.nodes[1].variable.name == 'v1'

        # Verify return is target node
        assert query.return_clause.items[0].name == 'v1'

    def test_in_traversal(self):
        """Test: g.V().hasLabel('Item').in('OWNS') -> incoming relationship"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['Item']),
            TraversalStep(direction='in', edge_label='OWNS')
        ])

        query = translate_gremlin_to_cypher(traversal)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == 'in'
        assert rel.directed is True

    def test_both_traversal(self):
        """Test: g.V().both('KNOWS') -> undirected relationship"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            TraversalStep(direction='both', edge_label='KNOWS')
        ])

        query = translate_gremlin_to_cypher(traversal)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == 'both'
        assert rel.directed is False

    def test_traversal_without_edge_label(self):
        """Test: g.V().out() -> relationship without type"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            TraversalStep(direction='out', edge_label=None)
        ])

        query = translate_gremlin_to_cypher(traversal)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.relationship_type is None

    def test_chained_traversals(self):
        """Test: g.V().out('OWNS').out('HAS_PART') -> (v0)-[:OWNS]->(v1)-[:HAS_PART]->(v2)"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            TraversalStep(direction='out', edge_label='OWNS'),
            TraversalStep(direction='out', edge_label='HAS_PART')
        ])

        query = translate_gremlin_to_cypher(traversal)

        path = query.match_clause.paths[0]
        assert len(path.nodes) == 3
        assert len(path.relationships) == 2

        # Verify chain
        assert path.nodes[0].variable.name == 'v0'
        assert path.relationships[0].relationship_type.name == 'OWNS'
        assert path.nodes[1].variable.name == 'v1'
        assert path.relationships[1].relationship_type.name == 'HAS_PART'
        assert path.nodes[2].variable.name == 'v2'

        # Returns final node
        assert query.return_clause.items[0].name == 'v2'


class TestProjectionTranslations:
    """Test projection step translations."""

    def test_values_single_property(self):
        """Test: g.V().hasLabel('User').values('name') -> RETURN v.name"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            ProjectionStep(type='values', properties=['name'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify return is property access
        assert len(query.return_clause.items) == 1
        item = query.return_clause.items[0]
        assert isinstance(item, Property)
        assert item.variable.name == 'v0'
        assert item.property_name.name == 'name'

    def test_values_multiple_properties(self):
        """Test: g.V().values('name', 'age') -> RETURN v.name, v.age"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            ProjectionStep(type='values', properties=['name', 'age'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify multiple return items
        assert len(query.return_clause.items) == 2

        item1 = query.return_clause.items[0]
        assert isinstance(item1, Property)
        assert item1.property_name.name == 'name'

        item2 = query.return_clause.items[1]
        assert isinstance(item2, Property)
        assert item2.property_name.name == 'age'


class TestModifiers:
    """Test limit and order modifiers."""

    def test_limit(self):
        """Test: g.V().limit(10) -> RETURN v LIMIT 10"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            LimitStep(count=10)
        ])

        query = translate_gremlin_to_cypher(traversal)

        assert query.return_clause.limit == 10

    def test_order_ascending(self):
        """Test: g.V().order().by('name') -> ORDER BY v.name ASC"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            OrderStep(property='name', ascending=True)
        ])

        query = translate_gremlin_to_cypher(traversal)

        assert query.return_clause.order_by is not None
        assert len(query.return_clause.order_by) == 1
        order_spec = query.return_clause.order_by[0]
        assert order_spec['expression']['property'] == 'name'
        assert order_spec['direction'] == 'ASC'

    def test_order_descending(self):
        """Test: g.V().order().by('age', desc) -> ORDER BY v.age DESC"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            OrderStep(property='age', ascending=False)
        ])

        query = translate_gremlin_to_cypher(traversal)

        order_spec = query.return_clause.order_by[0]
        assert order_spec['direction'] == 'DESC'

    def test_combined_modifiers(self):
        """Test: g.V().order().by('name').limit(5) -> ORDER BY ... LIMIT ..."""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            OrderStep(property='name', ascending=True),
            LimitStep(count=5)
        ])

        query = translate_gremlin_to_cypher(traversal)

        assert query.return_clause.order_by is not None
        assert query.return_clause.limit == 5


class TestComplexQueries:
    """Test complex combined patterns."""

    def test_traversal_with_filters(self):
        """Test: g.V().hasLabel('User').has('age', 30).out('OWNS').values('name')"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            FilterStep(predicate='has', args=['age', 30]),
            TraversalStep(direction='out', edge_label='OWNS'),
            ProjectionStep(type='values', properties=['name'])
        ])

        query = translate_gremlin_to_cypher(traversal)

        # Verify MATCH pattern
        path = query.match_clause.paths[0]
        assert len(path.nodes) == 2
        assert path.nodes[0].labels[0].name == 'User'
        assert path.relationships[0].relationship_type.name == 'OWNS'

        # Verify WHERE clause
        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions['left']['variable'] == 'v0'
        assert conditions['left']['property'] == 'age'
        assert conditions['right']['value'] == 30

        # Verify RETURN projection
        item = query.return_clause.items[0]
        assert isinstance(item, Property)
        assert item.variable.name == 'v1'  # Target node
        assert item.property_name.name == 'name'

    def test_full_featured_query(self):
        """Test query with all features: filters, traversal, projection, order, limit"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User']),
            FilterStep(predicate='has', args=['active', True]),
            TraversalStep(direction='out', edge_label='OWNS'),
            ProjectionStep(type='values', properties=['name']),
            OrderStep(property='name', ascending=True),
            LimitStep(count=10)
        ])

        query = translate_gremlin_to_cypher(traversal)

        # All components should be present
        assert query.match_clause is not None
        assert query.where_clause is not None
        assert query.return_clause is not None
        assert query.return_clause.order_by is not None
        assert query.return_clause.limit == 10


class TestErrorHandling:
    """Test error conditions and validation."""

    def test_empty_traversal(self):
        """Test that empty traversal raises error"""
        traversal = GremlinTraversal(steps=[])

        with pytest.raises(TranslationError, match="Empty traversal"):
            translate_gremlin_to_cypher(traversal)

    def test_edge_starting_point_unsupported(self):
        """Test that E() starting point raises error"""
        traversal = GremlinTraversal(steps=[
            EdgeStep()
        ])

        with pytest.raises(UnsupportedPatternError, match="Edge starting point E\\(\\)"):
            translate_gremlin_to_cypher(traversal)

    def test_invalid_starting_step(self):
        """Test that non-V/E starting step raises error"""
        traversal = GremlinTraversal(steps=[
            FilterStep(predicate='hasLabel', args=['User'])
        ])

        with pytest.raises(TranslationError, match="must start with V\\(\\) or E\\(\\)"):
            translate_gremlin_to_cypher(traversal)

    def test_unsupported_filter_predicate(self):
        """Test that unsupported filter predicate raises error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='where', args=[])
        ])

        with pytest.raises(UnsupportedPatternError, match="Filter predicate 'where'"):
            translate_gremlin_to_cypher(traversal)

    def test_unsupported_traversal_direction(self):
        """Test that unsupported traversal direction raises error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            TraversalStep(direction='outE', edge_label='KNOWS')
        ])

        with pytest.raises(UnsupportedPatternError, match="Traversal direction 'outE'"):
            translate_gremlin_to_cypher(traversal)

    def test_unsupported_projection_type(self):
        """Test that unsupported projection type raises error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            ProjectionStep(type='project', properties=['name'])
        ])

        with pytest.raises(UnsupportedPatternError, match="Projection type 'project'"):
            translate_gremlin_to_cypher(traversal)

    def test_multiple_projections_unsupported(self):
        """Test that multiple projection steps raise error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            ProjectionStep(type='values', properties=['name']),
            ProjectionStep(type='values', properties=['age'])
        ])

        with pytest.raises(UnsupportedPatternError, match="Multiple projection steps"):
            translate_gremlin_to_cypher(traversal)

    def test_multiple_limits_unsupported(self):
        """Test that multiple limit steps raise error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            LimitStep(count=10),
            LimitStep(count=5)
        ])

        with pytest.raises(UnsupportedPatternError, match="Multiple limit steps"):
            translate_gremlin_to_cypher(traversal)

    def test_hasLabel_wrong_arg_count(self):
        """Test that hasLabel with wrong number of args raises error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='hasLabel', args=['User', 'Admin'])
        ])

        with pytest.raises(TranslationError, match="hasLabel requires exactly 1 argument"):
            translate_gremlin_to_cypher(traversal)

    def test_has_wrong_arg_count(self):
        """Test that has with wrong number of args raises error"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='has', args=['name'])
        ])

        with pytest.raises(TranslationError, match="has requires exactly 2 arguments"):
            translate_gremlin_to_cypher(traversal)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_vertex_with_ids_raises_warning(self):
        """Test V(id) - IDs are preserved but may not affect query"""
        # For now, IDs are ignored in translation (MVP)
        traversal = GremlinTraversal(steps=[
            VertexStep(ids=[1, 2, 3])
        ])

        # Should succeed - IDs are just ignored for now
        query = translate_gremlin_to_cypher(traversal)
        assert query is not None

    def test_null_value_in_has(self):
        """Test has() with null value"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='has', args=['name', None])
        ])

        query = translate_gremlin_to_cypher(traversal)

        conditions = query.where_clause.conditions
        assert conditions['right']['value'] is None
        assert conditions['right']['value_type'] == 'null'

    def test_float_value_in_has(self):
        """Test has() with float value"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            FilterStep(predicate='has', args=['rating', 4.5])
        ])

        query = translate_gremlin_to_cypher(traversal)

        conditions = query.where_clause.conditions
        assert conditions['right']['value'] == 4.5
        assert conditions['right']['value_type'] == 'number'

    def test_zero_limit(self):
        """Test limit(0) - edge case"""
        traversal = GremlinTraversal(steps=[
            VertexStep(),
            LimitStep(count=0)
        ])

        query = translate_gremlin_to_cypher(traversal)
        assert query.return_clause.limit == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
