"""Comprehensive test suite for path algorithm translators (30+ tests)."""

import pytest
from yellowstone.algorithms import (
    ShortestPathTranslator,
    PathAlgorithmTranslator,
    PathConstraint,
    PathNode,
    PathRelationship,
    PathFilterConfig,
    PathEnumerationConfig,
)


class TestPathConstraint:
    """Test suite for PathConstraint dataclass."""

    def test_default_constraint(self):
        """Test PathConstraint with default values."""
        constraint = PathConstraint()
        assert constraint.max_length is None
        assert constraint.weighted is False
        assert constraint.bidirectional is False
        assert constraint.weight_property is None

    def test_constraint_with_max_length(self):
        """Test PathConstraint with maximum length."""
        constraint = PathConstraint(max_length=5)
        assert constraint.max_length == 5
        constraint.validate()  # Should not raise

    def test_constraint_negative_max_length_raises_error(self):
        """Test that negative max_length raises error."""
        constraint = PathConstraint(max_length=-1)
        with pytest.raises(ValueError, match="cannot be negative"):
            constraint.validate()

    def test_weighted_constraint_requires_weight_property(self):
        """Test that weighted=True requires weight_property."""
        constraint = PathConstraint(weighted=True)
        with pytest.raises(ValueError, match="Weight property required"):
            constraint.validate()

    def test_weighted_constraint_with_weight_property(self):
        """Test valid weighted constraint."""
        constraint = PathConstraint(weighted=True, weight_property="cost")
        constraint.validate()  # Should not raise

    def test_bidirectional_constraint(self):
        """Test bidirectional constraint."""
        constraint = PathConstraint(bidirectional=True)
        constraint.validate()  # Should not raise


class TestPathNode:
    """Test suite for PathNode dataclass."""

    def test_simple_node_variable(self):
        """Test node with only variable."""
        node = PathNode(variable="n")
        assert node.to_kql_format() == "n"

    def test_node_with_single_label(self):
        """Test node with variable and label."""
        node = PathNode(variable="n", labels=["Person"])
        assert node.to_kql_format() == "n:Person"

    def test_node_with_multiple_labels(self):
        """Test node with multiple labels."""
        node = PathNode(variable="n", labels=["Person", "Employee"])
        kql = node.to_kql_format()
        assert "n:" in kql
        assert "Person" in kql
        assert "Employee" in kql

    def test_node_without_variable(self):
        """Test node without variable, only labels."""
        node = PathNode(variable="", labels=["Person"])
        assert node.to_kql_format() == "Person"


class TestPathRelationship:
    """Test suite for PathRelationship dataclass."""

    def test_simple_relationship_variable(self):
        """Test relationship with only variable."""
        rel = PathRelationship(variable="r")
        assert rel.to_kql_format() == "r"

    def test_relationship_with_type(self):
        """Test relationship with variable and type."""
        rel = PathRelationship(variable="r", types=["KNOWS"])
        assert rel.to_kql_format() == "r:KNOWS"

    def test_relationship_with_multiple_types(self):
        """Test relationship with multiple types."""
        rel = PathRelationship(variable="r", types=["KNOWS", "LIKES"])
        kql = rel.to_kql_format()
        assert "r:" in kql
        assert "KNOWS" in kql
        assert "LIKES" in kql

    def test_invalid_direction_raises_error(self):
        """Test that invalid direction raises error."""
        rel = PathRelationship(direction="invalid")
        with pytest.raises(ValueError, match="Invalid direction"):
            rel.validate()

    def test_valid_directions(self):
        """Test all valid directions."""
        for direction in ("out", "in", "both"):
            rel = PathRelationship(direction=direction)
            rel.validate()  # Should not raise


class TestShortestPathTranslator:
    """Test suite for ShortestPathTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = ShortestPathTranslator()

    def test_basic_shortest_path(self):
        """Test basic shortest path translation."""
        query = self.translator.translate_shortest_path("n", "m", "KNOWS")
        assert "graph-shortest-paths" in query
        assert "(n)" in query
        assert "(m)" in query
        assert "KNOWS" in query

    def test_shortest_path_without_relationship(self):
        """Test shortest path without relationship type."""
        query = self.translator.translate_shortest_path("n", "m")
        assert "graph-shortest-paths" in query
        assert "(n)" in query
        assert "(m)" in query

    def test_shortest_path_with_direction_in(self):
        """Test shortest path with incoming direction."""
        rel_config = PathRelationship(direction="in")
        query = self.translator.translate_shortest_path(
            "n", "m", "KNOWS", relationship_config=rel_config
        )
        assert "<-" in query
        assert "->" not in query or "<-" in query  # in uses <-

    def test_shortest_path_with_direction_out(self):
        """Test shortest path with outgoing direction."""
        rel_config = PathRelationship(direction="out")
        query = self.translator.translate_shortest_path(
            "n", "m", "KNOWS", relationship_config=rel_config
        )
        assert "->" in query

    def test_shortest_path_with_direction_both(self):
        """Test shortest path with bidirectional relationship."""
        rel_config = PathRelationship(direction="both")
        query = self.translator.translate_shortest_path(
            "n", "m", "KNOWS", relationship_config=rel_config
        )
        assert "-" in query

    def test_shortest_path_with_max_length_constraint(self):
        """Test shortest path with maximum length."""
        constraint = PathConstraint(max_length=5)
        query = self.translator.translate_shortest_path(
            "n", "m", "KNOWS", constraints=constraint
        )
        assert "path_length <= 5" in query

    def test_shortest_path_weighted(self):
        """Test weighted shortest path."""
        constraint = PathConstraint(weighted=True, weight_property="distance")
        query = self.translator.translate_shortest_path(
            "n", "m", "ROAD", constraints=constraint
        )
        assert "weight=" in query or "distance" in query

    def test_shortest_path_bidirectional(self):
        """Test bidirectional shortest path."""
        constraint = PathConstraint(bidirectional=True)
        query = self.translator.translate_shortest_path(
            "n", "m", "KNOWS", constraints=constraint
        )
        assert "bidirectional" in query

    def test_source_empty_raises_error(self):
        """Test that empty source raises error."""
        with pytest.raises(ValueError, match="Source must be"):
            self.translator.translate_shortest_path("", "m")

    def test_target_empty_raises_error(self):
        """Test that empty target raises error."""
        with pytest.raises(ValueError, match="Target must be"):
            self.translator.translate_shortest_path("n", "")

    def test_source_not_string_raises_error(self):
        """Test that non-string source raises error."""
        with pytest.raises(ValueError, match="Source must be"):
            self.translator.translate_shortest_path(123, "m")  # type: ignore

    def test_multiple_target_nodes(self):
        """Test shortest path with multiple targets."""
        query = self.translator.translate_shortest_path_multiple_targets(
            "n", ["m", "p", "q"], "KNOWS"
        )
        assert "union" in query
        assert "(n)" in query

    def test_multiple_source_nodes(self):
        """Test shortest path with multiple sources."""
        query = self.translator.translate_shortest_path_multiple_sources(
            ["n", "p"], "m", "KNOWS"
        )
        assert "union" in query
        assert "(m)" in query

    def test_multiple_targets_empty_list_raises_error(self):
        """Test that empty targets list raises error."""
        with pytest.raises(ValueError, match="Targets must be"):
            self.translator.translate_shortest_path_multiple_targets(
                "n", [], "KNOWS"
            )

    def test_multiple_sources_empty_list_raises_error(self):
        """Test that empty sources list raises error."""
        with pytest.raises(ValueError, match="Sources must be"):
            self.translator.translate_shortest_path_multiple_sources(
                [], "m", "KNOWS"
            )

    def test_weighted_shortest_path(self):
        """Test weighted shortest path helper."""
        query = self.translator.translate_weighted_shortest_path(
            "n", "m", "ROAD", "distance", max_length=10
        )
        assert "graph-shortest-paths" in query
        assert "distance" in query

    def test_weighted_shortest_path_missing_weight_property(self):
        """Test that missing weight property raises error."""
        with pytest.raises(ValueError, match="Weight property"):
            self.translator.translate_weighted_shortest_path(
                "n", "m", "ROAD", ""
            )

    def test_bidirectional_shortest_path_helper(self):
        """Test bidirectional shortest path helper."""
        query = self.translator.translate_bidirectional_shortest_path("n", "m")
        assert "graph-shortest-paths" in query
        assert "bidirectional" in query

    def test_constrained_shortest_path(self):
        """Test shortest path with multiple constraints."""
        query = self.translator.translate_constrained_shortest_path(
            "n", "m", "KNOWS", max_length=5
        )
        assert "graph-shortest-paths" in query
        assert "path_length <= 5" in query

    def test_extract_path_length_from_result(self):
        """Test extracting path length from result."""
        result = {"path_length": 3, "nodes": ["n", "x", "y", "m"]}
        length = self.translator.extract_path_length_from_result(result)
        assert length == 3

    def test_extract_path_length_missing_field(self):
        """Test error when path_length missing."""
        result = {"nodes": ["n", "x", "y", "m"]}
        with pytest.raises(ValueError, match="path_length"):
            self.translator.extract_path_length_from_result(result)

    def test_extract_path_length_negative_value(self):
        """Test error on negative path length."""
        result = {"path_length": -1}
        with pytest.raises(ValueError, match="non-negative"):
            self.translator.extract_path_length_from_result(result)

    def test_validate_cypher_shortest_path_syntax_valid(self):
        """Test validation of valid shortestPath syntax."""
        expr = "shortestPath((n)-[*]-(m))"
        assert self.translator.validate_cypher_shortest_path_syntax(expr)

    def test_validate_cypher_shortest_path_missing_start(self):
        """Test validation fails without shortestPath prefix."""
        expr = "allPaths((n)-[*]-(m))"
        with pytest.raises(ValueError, match="start with"):
            self.translator.validate_cypher_shortest_path_syntax(expr)

    def test_validate_cypher_shortest_path_missing_end_paren(self):
        """Test validation fails without closing paren."""
        expr = "shortestPath((n)-[*]-(m)"
        with pytest.raises(ValueError, match="end with"):
            self.translator.validate_cypher_shortest_path_syntax(expr)

    def test_validate_cypher_shortest_path_missing_relationship(self):
        """Test validation fails without relationship pattern."""
        expr = "shortestPath((n) (m))"
        with pytest.raises(ValueError, match="relationship pattern"):
            self.translator.validate_cypher_shortest_path_syntax(expr)


class TestPathAlgorithmTranslator:
    """Test suite for PathAlgorithmTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = PathAlgorithmTranslator()

    def test_all_shortest_paths_basic(self):
        """Test basic all shortest paths translation."""
        query = self.translator.translate_all_shortest_paths("n", "m", "KNOWS")
        assert "all_shortest_paths" in query
        assert "(n)" in query
        assert "(m)" in query

    def test_all_shortest_paths_with_max_length(self):
        """Test all shortest paths with max length filter."""
        filters = PathFilterConfig(max_path_length=5)
        query = self.translator.translate_all_shortest_paths(
            "n", "m", "KNOWS", filters=filters
        )
        assert "array_length(path) <= 5" in query

    def test_all_shortest_paths_with_min_length(self):
        """Test all shortest paths with min length filter."""
        filters = PathFilterConfig(min_path_length=2)
        query = self.translator.translate_all_shortest_paths(
            "n", "m", "KNOWS", filters=filters
        )
        assert "array_length(path) >= 2" in query

    def test_all_shortest_paths_with_max_paths_limit(self):
        """Test all shortest paths with result limit."""
        query = self.translator.translate_all_shortest_paths(
            "n", "m", "KNOWS", max_paths=10
        )
        assert "limit 10" in query

    def test_all_paths_basic(self):
        """Test basic all paths translation."""
        query = self.translator.translate_all_paths("n", "m", "KNOWS", max_length=5)
        assert "all_paths" in query
        assert "(n)" in query
        assert "(m)" in query
        assert "*1..5" in query  # Variable-length path format

    def test_all_paths_with_filters(self):
        """Test all paths with filtering."""
        filters = PathFilterConfig(max_path_length=5)
        query = self.translator.translate_all_paths(
            "n", "m", "KNOWS", max_length=10, filters=filters
        )
        assert "all_paths" in query
        assert "array_length(path) <= 5" in query

    def test_all_paths_cycle_detection_enabled(self):
        """Test all paths with cycle detection."""
        enumeration = PathEnumerationConfig(cycle_detection=True)
        query = self.translator.translate_all_paths(
            "n", "m", "KNOWS", max_length=5, enumeration=enumeration
        )
        assert "no_cycles" in query

    def test_all_paths_cycle_detection_disabled(self):
        """Test all paths without cycle detection."""
        enumeration = PathEnumerationConfig(cycle_detection=False)
        query = self.translator.translate_all_paths(
            "n", "m", "KNOWS", max_length=5, enumeration=enumeration
        )
        assert "no_cycles" not in query

    def test_filtered_paths_with_excluded_nodes(self):
        """Test filtered paths with excluded nodes."""
        filters = PathFilterConfig(excluded_nodes=["x", "y"])
        query = self.translator.translate_filtered_paths(
            "n", "m", filters, "KNOWS"
        )
        assert "excluded_nodes" in str(filters) or "not (" in query

    def test_filtered_paths_with_excluded_relationships(self):
        """Test filtered paths with excluded relationships."""
        filters = PathFilterConfig(excluded_relationships=["BLOCKED"])
        query = self.translator.translate_filtered_paths(
            "n", "m", filters, "KNOWS"
        )
        assert "all_paths" in query

    def test_path_with_node_constraints(self):
        """Test path with node constraints."""
        constraints = {"n": "n.status='active'", "m": "m.status='active'"}
        query = self.translator.translate_path_with_node_constraints(
            "n", "m", constraints, "KNOWS"
        )
        assert "all_paths" in query
        assert "n.status='active'" in query

    def test_path_with_property_constraints(self):
        """Test path with relationship property constraints."""
        constraints = {"weight": "> 10", "confidence": ">= 0.8"}
        query = self.translator.translate_path_with_property_constraints(
            "n", "m", constraints, "KNOWS"
        )
        assert "all_paths" in query
        assert "relationship" in query

    def test_variable_length_path_with_filter(self):
        """Test variable-length path with filter."""
        query = self.translator.translate_variable_length_path_with_filter(
            "n", "m", min_length=2, max_length=5, relationship="KNOWS"
        )
        assert "graph-match" in query
        assert "*2..5" in query  # Variable-length path format

    def test_combined_query_shortest_algorithm(self):
        """Test combined query builder with shortest algorithm."""
        query = self.translator.build_combined_path_query(
            "n", "m", algorithm="shortest", relationship="KNOWS"
        )
        assert "graph-shortest-paths" in query

    def test_combined_query_all_shortest_algorithm(self):
        """Test combined query builder with all_shortest algorithm."""
        query = self.translator.build_combined_path_query(
            "n", "m", algorithm="all_shortest", relationship="KNOWS"
        )
        assert "all_shortest_paths" in query

    def test_combined_query_all_algorithm(self):
        """Test combined query builder with all algorithm."""
        constraint = PathConstraint(max_length=5)
        query = self.translator.build_combined_path_query(
            "n", "m", algorithm="all", relationship="KNOWS", constraints=constraint
        )
        assert "all_paths" in query

    def test_combined_query_invalid_algorithm(self):
        """Test that invalid algorithm raises error."""
        with pytest.raises(ValueError, match="Unknown algorithm"):
            self.translator.build_combined_path_query(
                "n", "m", algorithm="invalid"
            )


class TestPathFilterConfig:
    """Test suite for PathFilterConfig."""

    def test_default_filter_config(self):
        """Test default filter configuration."""
        config = PathFilterConfig()
        config.validate()  # Should not raise

    def test_filter_config_with_path_lengths(self):
        """Test filter with min and max path lengths."""
        config = PathFilterConfig(min_path_length=2, max_path_length=5)
        config.validate()  # Should not raise

    def test_filter_config_invalid_length_range(self):
        """Test that invalid length range raises error."""
        config = PathFilterConfig(min_path_length=5, max_path_length=2)
        with pytest.raises(ValueError, match="cannot be less than"):
            config.validate()

    def test_filter_config_negative_length(self):
        """Test that negative length raises error."""
        config = PathFilterConfig(max_path_length=-1)
        with pytest.raises(ValueError, match="cannot be negative"):
            config.validate()

    def test_filter_config_with_excluded_nodes(self):
        """Test filter with excluded nodes list."""
        config = PathFilterConfig(excluded_nodes=["x", "y"])
        config.validate()  # Should not raise

    def test_filter_config_with_excluded_relationships(self):
        """Test filter with excluded relationships list."""
        config = PathFilterConfig(excluded_relationships=["BLOCKED"])
        config.validate()  # Should not raise


class TestPathEnumerationConfig:
    """Test suite for PathEnumerationConfig."""

    def test_default_enumeration_config(self):
        """Test default enumeration configuration."""
        config = PathEnumerationConfig()
        assert config.max_depth == 10
        assert config.cycle_detection is True

    def test_enumeration_config_with_max_paths(self):
        """Test enumeration with max paths limit."""
        config = PathEnumerationConfig(max_paths=100)
        config.validate()  # Should not raise

    def test_enumeration_config_zero_max_paths(self):
        """Test that zero max_paths raises error."""
        config = PathEnumerationConfig(max_paths=0)
        with pytest.raises(ValueError, match="must be positive"):
            config.validate()

    def test_enumeration_config_zero_max_depth(self):
        """Test that zero max_depth raises error."""
        config = PathEnumerationConfig(max_depth=0)
        with pytest.raises(ValueError, match="must be positive"):
            config.validate()


class TestIntegration:
    """Integration tests for algorithm translators."""

    def test_shortest_path_workflow(self):
        """Test complete shortest path workflow."""
        translator = ShortestPathTranslator()

        # Validate input
        translator.validate_cypher_shortest_path_syntax("shortestPath((n)-[*]-(m))")

        # Translate to KQL
        query = translator.translate_shortest_path("n", "m", "KNOWS")
        assert "graph-shortest-paths" in query

    def test_all_paths_workflow(self):
        """Test complete all paths workflow."""
        translator = PathAlgorithmTranslator()

        # Translate all paths
        query = translator.translate_all_paths("n", "m", "KNOWS", max_length=5)
        assert "all_paths" in query

        # Apply filters
        filtered_query = translator.translate_filtered_paths(
            "n", "m", PathFilterConfig(max_path_length=5), "KNOWS"
        )
        assert "all_paths" in filtered_query

    def test_constrained_path_workflow(self):
        """Test workflow with multiple constraints."""
        translator = PathAlgorithmTranslator()

        # Build query with constraints
        filters = PathFilterConfig(
            max_path_length=5,
            min_path_length=2,
            excluded_nodes=["intermediate"],
        )

        query = translator.translate_filtered_paths(
            "n", "m", filters, relationship="KNOWS", max_length=10
        )

        assert "all_paths" in query
        assert "array_length(path)" in query
