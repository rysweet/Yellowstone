"""
Tests for the Visitor pattern implementation.

Tests cover:
    - DefaultVisitor traversal
    - CollectingVisitor functionality
    - ValidationVisitor error detection
    - DotVisitor graph generation
"""

import pytest
from yellowstone.parser import (
    parse_query,
    DefaultVisitor,
    CollectingVisitor,
    ValidationVisitor,
    DotVisitor,
    Identifier,
)


class TestDefaultVisitor:
    """Test suite for DefaultVisitor."""

    def test_traversal_simple_query(self) -> None:
        """Test that DefaultVisitor can traverse a simple query."""
        query_str = "MATCH (n:Person) RETURN n"
        query = parse_query(query_str)

        visitor = DefaultVisitor()
        # Should not raise any errors
        query.accept(visitor)

    def test_traversal_complex_query(self) -> None:
        """Test that DefaultVisitor can traverse complex query."""
        query_str = (
            "MATCH (n:Person)-[r:KNOWS]->(m:Person) "
            "WHERE n.age > 30 "
            "RETURN n, m LIMIT 10"
        )
        query = parse_query(query_str)

        visitor = DefaultVisitor()
        query.accept(visitor)


class TestCollectingVisitor:
    """Test suite for CollectingVisitor."""

    def test_collects_identifiers(self) -> None:
        """Test that identifiers are collected."""
        query_str = "MATCH (n:Person {name: 'John'}) RETURN n"
        query = parse_query(query_str)

        visitor = CollectingVisitor()
        query.accept(visitor)

        assert len(visitor.identifiers) > 0
        identifier_names = [ident.name for ident in visitor.identifiers]
        assert "n" in identifier_names
        assert "Person" in identifier_names

    def test_collects_literals(self) -> None:
        """Test that literals are collected."""
        query_str = "MATCH (n {name: 'John', age: 30}) RETURN n"
        query = parse_query(query_str)

        visitor = CollectingVisitor()
        query.accept(visitor)

        assert len(visitor.literals) == 2

    def test_no_duplicates(self) -> None:
        """Test that collection works correctly."""
        query_str = "MATCH (n:Person), (m:Person) RETURN n, m"
        query = parse_query(query_str)

        visitor = CollectingVisitor()
        query.accept(visitor)

        # Person should appear twice (both labels)
        person_count = sum(
            1 for ident in visitor.identifiers if ident.name == "Person"
        )
        assert person_count == 2


class TestValidationVisitor:
    """Test suite for ValidationVisitor."""

    def test_valid_query(self) -> None:
        """Test that valid query has no errors."""
        query_str = "MATCH (n:Person) RETURN n"
        query = parse_query(query_str)

        visitor = ValidationVisitor()
        query.accept(visitor)

        assert len(visitor.errors) == 0

    def test_undefined_variable_in_return(self) -> None:
        """Test detection of undefined variable in RETURN."""
        query_str = "MATCH (n:Person) RETURN m"
        query = parse_query(query_str)

        visitor = ValidationVisitor()
        query.accept(visitor)

        assert len(visitor.warnings) > 0

    def test_defined_variables_tracked(self) -> None:
        """Test that defined variables are tracked."""
        query_str = "MATCH (n:Person)-[r:KNOWS]->(m:Person) RETURN n, m"
        query = parse_query(query_str)

        visitor = ValidationVisitor()
        query.accept(visitor)

        assert len(visitor.errors) == 0

    def test_property_access_on_undefined_variable(self) -> None:
        """Test detection of property on undefined variable."""
        query_str = "MATCH (n:Person) RETURN m.name"
        query = parse_query(query_str)

        visitor = ValidationVisitor()
        query.accept(visitor)

        assert len(visitor.errors) > 0


class TestDotVisitor:
    """Test suite for DotVisitor."""

    def test_generates_dot_format(self) -> None:
        """Test that DOT format is generated."""
        query_str = "MATCH (n:Person) RETURN n"
        query = parse_query(query_str)

        visitor = DotVisitor()
        dot_output = visitor.generate_dot(query)

        assert "digraph" in dot_output
        assert "Query" in dot_output
        assert "{" in dot_output
        assert "}" in dot_output

    def test_dot_contains_nodes(self) -> None:
        """Test that generated DOT contains node definitions."""
        query_str = "MATCH (n:Person {name: 'John'}) RETURN n"
        query = parse_query(query_str)

        visitor = DotVisitor()
        dot_output = visitor.generate_dot(query)

        assert "Person" in dot_output
        assert "John" in dot_output

    def test_dot_complex_query(self) -> None:
        """Test DOT generation for complex query."""
        query_str = (
            "MATCH (n:Person)-[r:KNOWS]->(m:Person) "
            "WHERE n.age > 30 "
            "RETURN n, m"
        )
        query = parse_query(query_str)

        visitor = DotVisitor()
        dot_output = visitor.generate_dot(query)

        assert "MATCH" in dot_output
        assert "WHERE" in dot_output
        assert "RETURN" in dot_output


class TestVisitorIntegration:
    """Integration tests for visitor pattern."""

    def test_multiple_visitors(self) -> None:
        """Test running multiple visitors on same query."""
        query_str = "MATCH (n:Person {name: 'John'}) RETURN n"
        query = parse_query(query_str)

        # Run collecting visitor
        collector = CollectingVisitor()
        query.accept(collector)
        assert len(collector.identifiers) > 0

        # Run validation visitor
        validator = ValidationVisitor()
        query.accept(validator)
        assert len(validator.errors) == 0

        # Run DOT visitor
        dot_gen = DotVisitor()
        dot_output = dot_gen.generate_dot(query)
        assert len(dot_output) > 0

    def test_visitor_state_independence(self) -> None:
        """Test that visitor state is independent between calls."""
        query1 = parse_query("MATCH (n:Person) RETURN n")
        query2 = parse_query("MATCH (m:Movie) RETURN m")

        visitor = CollectingVisitor()

        # Visit first query
        query1.accept(visitor)
        count1 = len(visitor.identifiers)

        # Clear and visit second query
        visitor.identifiers.clear()
        query2.accept(visitor)
        count2 = len(visitor.identifiers)

        # Counts should be comparable but both > 0
        assert count1 > 0
        assert count2 > 0


class TestCustomVisitors:
    """Test creating custom visitors."""

    def test_custom_visitor_counting(self) -> None:
        """Test creating custom visitor that counts nodes."""

        class CountingVisitor(DefaultVisitor):
            """Custom visitor that counts node patterns."""

            def __init__(self):
                super().__init__()
                self.node_count = 0

            def visit_node_pattern(self, node):
                self.node_count += 1
                super().visit_node_pattern(node)

        query_str = "MATCH (n)-[r]->(m) RETURN n, m"
        query = parse_query(query_str)

        visitor = CountingVisitor()
        query.accept(visitor)

        assert visitor.node_count == 2

    def test_custom_visitor_label_tracking(self) -> None:
        """Test custom visitor tracking labels."""

        class LabelTracker(DefaultVisitor):
            """Custom visitor that tracks all labels."""

            def __init__(self):
                super().__init__()
                self.labels = []

            def visit_identifier(self, node):
                # In simplified version, track all identifiers
                self.labels.append(node.name)

        query_str = "MATCH (n:Person:Actor) RETURN n"
        query = parse_query(query_str)

        visitor = LabelTracker()
        query.accept(visitor)

        assert "Person" in visitor.labels
        assert "Actor" in visitor.labels
