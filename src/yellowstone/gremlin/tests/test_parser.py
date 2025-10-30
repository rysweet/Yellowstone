"""
Tests for Gremlin parser.

These tests verify that the parser correctly handles all supported
Gremlin query patterns and converts them into the appropriate AST.
"""

import pytest
from yellowstone.gremlin import (
    parse_gremlin,
    GremlinParser,
    GremlinParseError,
    GremlinTraversal,
    VertexStep,
    EdgeStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    CountStep,
    DedupStep,
    GremlinValue,
    Predicate,
)


class TestBasicParsing:
    """Test basic parsing functionality."""

    def test_parse_simple_vertex_step(self):
        """Test parsing g.V()"""
        traversal = parse_gremlin("g.V()")
        assert len(traversal.steps) == 1
        assert isinstance(traversal.steps[0], VertexStep)
        assert traversal.steps[0].vertex_id is None

    def test_parse_vertex_step_with_id(self):
        """Test parsing g.V('123')"""
        traversal = parse_gremlin("g.V('123')")
        assert len(traversal.steps) == 1
        assert isinstance(traversal.steps[0], VertexStep)
        assert traversal.steps[0].vertex_id == "123"

    def test_parse_vertex_step_with_numeric_id(self):
        """Test parsing g.V(123)"""
        traversal = parse_gremlin("g.V(123)")
        assert len(traversal.steps) == 1
        assert isinstance(traversal.steps[0], VertexStep)
        assert traversal.steps[0].vertex_id == "123"

    def test_parse_edge_step(self):
        """Test parsing g.E()"""
        traversal = parse_gremlin("g.E()")
        assert len(traversal.steps) == 1
        assert isinstance(traversal.steps[0], EdgeStep)
        assert traversal.steps[0].edge_id is None

    def test_empty_query_raises_error(self):
        """Test that empty query raises error"""
        with pytest.raises(GremlinParseError):
            parse_gremlin("")

    def test_query_without_g_raises_error(self):
        """Test that query not starting with 'g' raises error"""
        with pytest.raises(GremlinParseError, match="must start with 'g'"):
            parse_gremlin("V().hasLabel('Person')")


class TestFilterSteps:
    """Test filter step parsing."""

    def test_parse_has_label(self):
        """Test parsing g.V().hasLabel('Person')"""
        traversal = parse_gremlin("g.V().hasLabel('Person')")
        assert len(traversal.steps) == 2
        assert isinstance(traversal.steps[1], FilterStep)
        assert traversal.steps[1].filter_type == "hasLabel"
        assert traversal.steps[1].value.value == "Person"
        assert traversal.steps[1].value.value_type == "string"

    def test_parse_has_with_property_and_value(self):
        """Test parsing g.V().has('name','marko')"""
        traversal = parse_gremlin("g.V().has('name','marko')")
        assert len(traversal.steps) == 2
        filter_step = traversal.steps[1]
        assert isinstance(filter_step, FilterStep)
        assert filter_step.filter_type == "has"
        assert filter_step.property_name == "name"
        assert filter_step.value.value == "marko"

    def test_parse_has_with_numeric_value(self):
        """Test parsing g.V().has('age', 30)"""
        traversal = parse_gremlin("g.V().has('age', 30)")
        filter_step = traversal.steps[1]
        assert filter_step.property_name == "age"
        assert filter_step.value.value == 30
        assert filter_step.value.value_type == "number"

    def test_parse_has_with_predicate_gt(self):
        """Test parsing g.V().has('age', gt(30))"""
        traversal = parse_gremlin("g.V().has('age', gt(30))")
        filter_step = traversal.steps[1]
        assert isinstance(filter_step, FilterStep)
        assert filter_step.property_name == "age"
        assert filter_step.predicate is not None
        assert filter_step.predicate.operator == "gt"
        assert filter_step.predicate.value.value == 30

    def test_parse_has_with_predicate_lt(self):
        """Test parsing g.V().has('age', lt(50))"""
        traversal = parse_gremlin("g.V().has('age', lt(50))")
        filter_step = traversal.steps[1]
        assert filter_step.predicate.operator == "lt"
        assert filter_step.predicate.value.value == 50

    def test_parse_has_id(self):
        """Test parsing g.V().hasId('123')"""
        traversal = parse_gremlin("g.V().hasId('123')")
        filter_step = traversal.steps[1]
        assert filter_step.filter_type == "hasId"
        assert filter_step.value.value == "123"

    def test_parse_has_key(self):
        """Test parsing g.V().hasKey('name')"""
        traversal = parse_gremlin("g.V().hasKey('name')")
        filter_step = traversal.steps[1]
        assert filter_step.filter_type == "hasKey"
        assert filter_step.value.value == "name"

    def test_parse_has_value(self):
        """Test parsing g.V().hasValue('John')"""
        traversal = parse_gremlin("g.V().hasValue('John')")
        filter_step = traversal.steps[1]
        assert filter_step.filter_type == "hasValue"
        assert filter_step.value.value == "John"


class TestTraversalSteps:
    """Test traversal step parsing."""

    def test_parse_out(self):
        """Test parsing g.V().out()"""
        traversal = parse_gremlin("g.V().out()")
        traversal_step = traversal.steps[1]
        assert isinstance(traversal_step, TraversalStep)
        assert traversal_step.direction == "out"
        assert traversal_step.traversal_type == "vertex"
        assert traversal_step.edge_label is None

    def test_parse_out_with_label(self):
        """Test parsing g.V().out('KNOWS')"""
        traversal = parse_gremlin("g.V().out('KNOWS')")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "out"
        assert traversal_step.edge_label == "KNOWS"

    def test_parse_in(self):
        """Test parsing g.V().in('CREATED')"""
        traversal = parse_gremlin("g.V().in('CREATED')")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "in"
        assert traversal_step.edge_label == "CREATED"

    def test_parse_both(self):
        """Test parsing g.V().both('KNOWS')"""
        traversal = parse_gremlin("g.V().both('KNOWS')")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "both"
        assert traversal_step.edge_label == "KNOWS"

    def test_parse_out_e(self):
        """Test parsing g.V().outE('KNOWS')"""
        traversal = parse_gremlin("g.V().outE('KNOWS')")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "out"
        assert traversal_step.traversal_type == "edge"
        assert traversal_step.edge_label == "KNOWS"

    def test_parse_in_e(self):
        """Test parsing g.V().inE()"""
        traversal = parse_gremlin("g.V().inE()")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "in"
        assert traversal_step.traversal_type == "edge"

    def test_parse_both_e(self):
        """Test parsing g.V().bothE()"""
        traversal = parse_gremlin("g.V().bothE()")
        traversal_step = traversal.steps[1]
        assert traversal_step.direction == "both"
        assert traversal_step.traversal_type == "edge"


class TestProjectionSteps:
    """Test projection step parsing."""

    def test_parse_values_with_property(self):
        """Test parsing g.V().values('name')"""
        traversal = parse_gremlin("g.V().values('name')")
        projection_step = traversal.steps[1]
        assert isinstance(projection_step, ProjectionStep)
        assert projection_step.projection_type == "values"
        assert projection_step.property_names == ["name"]

    def test_parse_values_with_multiple_properties(self):
        """Test parsing g.V().values('name', 'age')"""
        traversal = parse_gremlin("g.V().values('name', 'age')")
        projection_step = traversal.steps[1]
        assert projection_step.property_names == ["name", "age"]

    def test_parse_values_without_properties(self):
        """Test parsing g.V().values()"""
        traversal = parse_gremlin("g.V().values()")
        projection_step = traversal.steps[1]
        assert projection_step.projection_type == "values"
        assert projection_step.property_names == []

    def test_parse_value_map(self):
        """Test parsing g.V().valueMap()"""
        traversal = parse_gremlin("g.V().valueMap()")
        projection_step = traversal.steps[1]
        assert projection_step.projection_type == "valueMap"

    def test_parse_properties(self):
        """Test parsing g.V().properties('name')"""
        traversal = parse_gremlin("g.V().properties('name')")
        projection_step = traversal.steps[1]
        assert projection_step.projection_type == "properties"
        assert projection_step.property_names == ["name"]

    def test_parse_element_map(self):
        """Test parsing g.V().elementMap()"""
        traversal = parse_gremlin("g.V().elementMap()")
        projection_step = traversal.steps[1]
        assert projection_step.projection_type == "elementMap"


class TestModifierSteps:
    """Test modifier steps (limit, order, count, dedup)."""

    def test_parse_limit(self):
        """Test parsing g.V().limit(10)"""
        traversal = parse_gremlin("g.V().limit(10)")
        limit_step = traversal.steps[1]
        assert isinstance(limit_step, LimitStep)
        assert limit_step.count == 10

    def test_parse_count(self):
        """Test parsing g.V().count()"""
        traversal = parse_gremlin("g.V().count()")
        count_step = traversal.steps[1]
        assert isinstance(count_step, CountStep)

    def test_parse_dedup(self):
        """Test parsing g.V().dedup()"""
        traversal = parse_gremlin("g.V().dedup()")
        dedup_step = traversal.steps[1]
        assert isinstance(dedup_step, DedupStep)

    def test_parse_order(self):
        """Test parsing g.V().order()"""
        traversal = parse_gremlin("g.V().order()")
        order_step = traversal.steps[1]
        assert order_step.step_type == "order"


class TestComplexQueries:
    """Test complex multi-step queries."""

    def test_parse_person_query(self):
        """Test parsing g.V().hasLabel('Person').out('KNOWS').values('name')"""
        query = "g.V().hasLabel('Person').out('KNOWS').values('name')"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 4
        assert isinstance(traversal.steps[0], VertexStep)
        assert isinstance(traversal.steps[1], FilterStep)
        assert isinstance(traversal.steps[2], TraversalStep)
        assert isinstance(traversal.steps[3], ProjectionStep)

        assert traversal.steps[1].value.value == "Person"
        assert traversal.steps[2].edge_label == "KNOWS"
        assert traversal.steps[3].property_names == ["name"]

    def test_parse_query_with_predicates(self):
        """Test parsing g.V().hasLabel('Person').has('age',gt(30)).out('created').values('name')"""
        query = "g.V().hasLabel('Person').has('age',gt(30)).out('created').values('name')"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 5
        assert isinstance(traversal.steps[2], FilterStep)
        assert traversal.steps[2].predicate.operator == "gt"
        assert traversal.steps[2].predicate.value.value == 30

    def test_parse_query_with_limit(self):
        """Test parsing g.V().hasLabel('Person').limit(5).values('name')"""
        query = "g.V().hasLabel('Person').limit(5).values('name')"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 4
        assert isinstance(traversal.steps[2], LimitStep)
        assert traversal.steps[2].count == 5

    def test_parse_edge_traversal_query(self):
        """Test parsing g.V().outE('KNOWS').inV().values('name')"""
        query = "g.V().outE('KNOWS').inV().values('name')"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 4
        assert traversal.steps[1].traversal_type == "edge"
        assert traversal.steps[2].direction == "in"
        assert traversal.steps[2].traversal_type == "vertex"

    def test_parse_query_with_count(self):
        """Test parsing g.V().hasLabel('Person').out('KNOWS').count()"""
        query = "g.V().hasLabel('Person').out('KNOWS').count()"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 4
        assert isinstance(traversal.steps[3], CountStep)

    def test_parse_deduped_query(self):
        """Test parsing g.V().out('knows').dedup().values('name')"""
        query = "g.V().out('knows').dedup().values('name')"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 4
        assert isinstance(traversal.steps[2], DedupStep)


class TestQuoteHandling:
    """Test proper handling of different quote types."""

    def test_parse_double_quotes(self):
        """Test parsing with double quotes"""
        traversal = parse_gremlin('g.V().hasLabel("Person")')
        assert traversal.steps[1].value.value == "Person"

    def test_parse_mixed_quotes(self):
        """Test parsing with mixed quote types"""
        traversal = parse_gremlin('g.V().hasLabel("Person").has(\'name\',"John")')
        assert traversal.steps[1].value.value == "Person"
        assert traversal.steps[2].property_name == "name"
        assert traversal.steps[2].value.value == "John"


class TestWhitespace:
    """Test handling of whitespace in queries."""

    def test_parse_with_extra_whitespace(self):
        """Test parsing with extra whitespace"""
        query = "g.V()  .  hasLabel( 'Person' )  .  values( 'name' )"
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 3
        assert traversal.steps[1].value.value == "Person"
        assert traversal.steps[2].property_names == ["name"]

    def test_parse_with_newlines(self):
        """Test parsing with newlines"""
        query = """g.V()
        .hasLabel('Person')
        .values('name')"""
        traversal = parse_gremlin(query)

        assert len(traversal.steps) == 3


class TestErrorHandling:
    """Test error handling for invalid queries."""

    def test_invalid_method_raises_error(self):
        """Test that invalid method name raises error"""
        with pytest.raises(GremlinParseError, match="Unknown Gremlin step"):
            parse_gremlin("g.V().invalidMethod()")

    def test_has_label_without_args_raises_error(self):
        """Test that hasLabel without args raises error"""
        with pytest.raises(GremlinParseError, match="requires a label argument"):
            parse_gremlin("g.V().hasLabel()")

    def test_limit_without_args_raises_error(self):
        """Test that limit without args raises error"""
        with pytest.raises(GremlinParseError, match="requires a count argument"):
            parse_gremlin("g.V().limit()")

    def test_unclosed_string_raises_error(self):
        """Test that unclosed string raises error"""
        with pytest.raises(GremlinParseError, match="Unterminated string"):
            parse_gremlin("g.V().hasLabel('Person)")


class TestStringRepresentation:
    """Test string representation of AST nodes."""

    def test_traversal_str(self):
        """Test string representation of complete traversal"""
        traversal = parse_gremlin("g.V().hasLabel('Person').values('name')")
        result = str(traversal)
        assert "g." in result
        assert "V()" in result
        assert "hasLabel" in result
        assert "values" in result

    def test_vertex_step_str(self):
        """Test string representation of VertexStep"""
        traversal = parse_gremlin("g.V()")
        assert str(traversal.steps[0]) == "V()"

    def test_vertex_step_with_id_str(self):
        """Test string representation of VertexStep with ID"""
        traversal = parse_gremlin("g.V('123')")
        assert str(traversal.steps[0]) == "V('123')"
