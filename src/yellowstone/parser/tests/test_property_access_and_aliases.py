"""
Comprehensive tests for property access and alias support in RETURN clauses.

This test suite validates:
    - Simple identifier returns
    - Property access (single and multiple)
    - Alias support for identifiers and properties
    - Combined patterns (identifiers, properties, and aliases)
    - Edge cases and error handling
"""

import pytest
from yellowstone.parser import (
    parse_query,
    Identifier,
    Property,
    AliasedExpression,
)


# ============================================================================
# Basic Property Access Tests
# ============================================================================


class TestPropertyAccess:
    """Test suite for property access in RETURN clauses."""

    def test_single_property_access(self) -> None:
        """Test RETURN with single property access."""
        query = parse_query("MATCH (n) RETURN n.name")
        item = query.return_clause.items[0]

        assert isinstance(item, Property)
        assert item.variable.name == "n"
        assert item.property_name.name == "name"

    def test_multiple_property_access(self) -> None:
        """Test RETURN with multiple property access."""
        query = parse_query("MATCH (n) RETURN n.name, n.age, n.email")
        items = query.return_clause.items

        assert len(items) == 3
        assert all(isinstance(item, Property) for item in items)
        assert items[0].property_name.name == "name"
        assert items[1].property_name.name == "age"
        assert items[2].property_name.name == "email"

    def test_mixed_identifier_and_property(self) -> None:
        """Test RETURN with both identifiers and properties."""
        query = parse_query("MATCH (n) RETURN n, n.name, n.age")
        items = query.return_clause.items

        assert len(items) == 3
        assert isinstance(items[0], Identifier)
        assert isinstance(items[1], Property)
        assert isinstance(items[2], Property)

    def test_multiple_variables_with_properties(self) -> None:
        """Test RETURN with properties from different variables."""
        query = parse_query("MATCH (n)-[r]->(m) RETURN n.name, m.name, r.weight")
        items = query.return_clause.items

        assert len(items) == 3
        assert items[0].variable.name == "n"
        assert items[1].variable.name == "m"
        assert items[2].variable.name == "r"

    def test_property_with_distinct(self) -> None:
        """Test RETURN DISTINCT with property access."""
        query = parse_query("MATCH (n) RETURN DISTINCT n.name")

        assert query.return_clause.distinct is True
        assert isinstance(query.return_clause.items[0], Property)

    def test_property_with_order_by(self) -> None:
        """Test property access with ORDER BY."""
        query = parse_query("MATCH (n) RETURN n.name ORDER BY n.age")

        assert isinstance(query.return_clause.items[0], Property)
        assert query.return_clause.order_by is not None

    def test_property_with_limit(self) -> None:
        """Test property access with LIMIT."""
        query = parse_query("MATCH (n) RETURN n.name LIMIT 10")

        assert isinstance(query.return_clause.items[0], Property)
        assert query.return_clause.limit == 10

    def test_property_with_skip(self) -> None:
        """Test property access with SKIP."""
        query = parse_query("MATCH (n) RETURN n.name SKIP 5")

        assert isinstance(query.return_clause.items[0], Property)
        assert query.return_clause.skip == 5


# ============================================================================
# Alias Tests
# ============================================================================


class TestAliases:
    """Test suite for alias support in RETURN clauses."""

    def test_simple_property_alias(self) -> None:
        """Test property with AS alias."""
        query = parse_query("MATCH (n) RETURN n.name AS userName")
        item = query.return_clause.items[0]

        assert isinstance(item, AliasedExpression)
        assert isinstance(item.expression, Property)
        assert item.expression.property_name.name == "name"
        assert item.alias.name == "userName"

    def test_identifier_alias(self) -> None:
        """Test identifier with AS alias."""
        query = parse_query("MATCH (n) RETURN n AS node")
        item = query.return_clause.items[0]

        assert isinstance(item, AliasedExpression)
        assert isinstance(item.expression, Identifier)
        assert item.expression.name == "n"
        assert item.alias.name == "node"

    def test_multiple_aliases(self) -> None:
        """Test multiple aliased expressions."""
        query = parse_query("MATCH (n) RETURN n.name AS userName, n.age AS userAge")
        items = query.return_clause.items

        assert len(items) == 2
        assert all(isinstance(item, AliasedExpression) for item in items)
        assert items[0].alias.name == "userName"
        assert items[1].alias.name == "userAge"

    def test_mixed_aliased_and_non_aliased(self) -> None:
        """Test mix of aliased and non-aliased expressions."""
        query = parse_query("MATCH (n) RETURN n, n.name AS userName, n.age")
        items = query.return_clause.items

        assert len(items) == 3
        assert isinstance(items[0], Identifier)
        assert isinstance(items[1], AliasedExpression)
        assert isinstance(items[2], Property)

    def test_alias_with_distinct(self) -> None:
        """Test aliased expression with DISTINCT."""
        query = parse_query("MATCH (n) RETURN DISTINCT n.name AS userName")

        assert query.return_clause.distinct is True
        assert isinstance(query.return_clause.items[0], AliasedExpression)

    def test_alias_with_order_by(self) -> None:
        """Test aliased expression with ORDER BY."""
        query = parse_query("MATCH (n) RETURN n.name AS userName ORDER BY n.age")

        assert isinstance(query.return_clause.items[0], AliasedExpression)
        assert query.return_clause.order_by is not None

    def test_alias_with_limit_and_skip(self) -> None:
        """Test aliased expression with LIMIT and SKIP."""
        query = parse_query("MATCH (n) RETURN n.name AS userName LIMIT 10 SKIP 5")

        assert isinstance(query.return_clause.items[0], AliasedExpression)
        assert query.return_clause.limit == 10
        assert query.return_clause.skip == 5


# ============================================================================
# Complex Scenarios
# ============================================================================


class TestComplexScenarios:
    """Test suite for complex property access and alias combinations."""

    def test_relationship_properties_with_aliases(self) -> None:
        """Test relationship properties with aliases."""
        query = parse_query(
            "MATCH (n)-[r:KNOWS]->(m) RETURN n.name AS person, r.since AS friendSince, m.name AS friend"
        )
        items = query.return_clause.items

        assert len(items) == 3
        assert all(isinstance(item, AliasedExpression) for item in items)
        assert items[0].alias.name == "person"
        assert items[1].alias.name == "friendSince"
        assert items[2].alias.name == "friend"

    def test_complete_query_with_all_features(self) -> None:
        """Test complete query with properties, aliases, and modifiers."""
        query = parse_query(
            "MATCH (n:Person)-[r:KNOWS]->(m:Person) "
            "WHERE n.age > 30 "
            "RETURN n.name AS personName, m.name AS friendName, r.weight AS strength "
            "ORDER BY n.age DESC "
            "LIMIT 10 "
            "SKIP 5"
        )

        items = query.return_clause.items
        assert len(items) == 3
        assert all(isinstance(item, AliasedExpression) for item in items)
        assert query.return_clause.order_by is not None
        assert query.return_clause.limit == 10
        assert query.return_clause.skip == 5

    def test_distinct_with_multiple_properties_and_aliases(self) -> None:
        """Test DISTINCT with multiple properties and aliases."""
        query = parse_query(
            "MATCH (n) RETURN DISTINCT n.name AS userName, n.age AS userAge, n.email"
        )

        assert query.return_clause.distinct is True
        assert len(query.return_clause.items) == 3
        assert isinstance(query.return_clause.items[0], AliasedExpression)
        assert isinstance(query.return_clause.items[1], AliasedExpression)
        assert isinstance(query.return_clause.items[2], Property)

    def test_complex_path_with_multiple_properties(self) -> None:
        """Test complex path with properties from all nodes and relationships."""
        query = parse_query(
            "MATCH (n:Person)-[r1:ACTED_IN]->(m:Movie)<-[r2:DIRECTED]-(p:Person) "
            "RETURN n.name, m.title, p.name, r1.role, r2.year"
        )

        items = query.return_clause.items
        assert len(items) == 5
        assert all(isinstance(item, Property) for item in items)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_property_access_on_empty_identifier(self) -> None:
        """Test that property access requires a valid identifier."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n) RETURN .name")

    def test_missing_property_after_dot(self) -> None:
        """Test that dot must be followed by property name."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n) RETURN n.")

    def test_missing_alias_after_as(self) -> None:
        """Test that AS must be followed by alias name."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n) RETURN n.name AS")

    def test_reserved_keyword_as_alias(self) -> None:
        """Test using potential reserved words as aliases (should work)."""
        # Note: These should work as they're in identifier context
        query = parse_query("MATCH (n) RETURN n.name AS name")
        item = query.return_clause.items[0]
        assert isinstance(item, AliasedExpression)
        assert item.alias.name == "name"

    def test_multiple_dots_not_supported(self) -> None:
        """Test that nested property access is not supported."""
        # This should fail because we only support one level of property access
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n) RETURN n.address.street")

    def test_camelcase_property_names(self) -> None:
        """Test property names with camelCase."""
        query = parse_query("MATCH (n) RETURN n.firstName, n.lastName")
        items = query.return_clause.items

        assert items[0].property_name.name == "firstName"
        assert items[1].property_name.name == "lastName"

    def test_underscore_property_names(self) -> None:
        """Test property names with underscores."""
        query = parse_query("MATCH (n) RETURN n.first_name, n.last_name")
        items = query.return_clause.items

        assert items[0].property_name.name == "first_name"
        assert items[1].property_name.name == "last_name"

    def test_numeric_suffixes_in_properties(self) -> None:
        """Test property names with numeric suffixes."""
        query = parse_query("MATCH (n) RETURN n.prop1, n.prop2, n.value123")
        items = query.return_clause.items

        assert len(items) == 3
        assert items[0].property_name.name == "prop1"
        assert items[2].property_name.name == "value123"


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining property access with other features."""

    def test_property_access_in_where_and_return(self) -> None:
        """Test properties used in both WHERE and RETURN."""
        query = parse_query(
            "MATCH (n:Person) WHERE n.age > 30 RETURN n.name, n.age"
        )

        # Check WHERE clause
        assert query.where_clause is not None

        # Check RETURN clause
        items = query.return_clause.items
        assert len(items) == 2
        assert all(isinstance(item, Property) for item in items)

    def test_optional_match_with_properties(self) -> None:
        """Test OPTIONAL MATCH with property returns."""
        query = parse_query(
            "OPTIONAL MATCH (n:Person) RETURN n.name, n.age"
        )

        assert query.match_clause.optional is True
        items = query.return_clause.items
        assert len(items) == 2

    def test_multiple_path_patterns_with_properties(self) -> None:
        """Test multiple paths with property access."""
        query = parse_query(
            "MATCH (n:Person), (m:Movie) RETURN n.name, m.title"
        )

        assert len(query.match_clause.paths) == 2
        items = query.return_clause.items
        assert len(items) == 2
        assert items[0].variable.name == "n"
        assert items[1].variable.name == "m"
