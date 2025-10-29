"""
Comprehensive tests for the Cypher parser.

Tests cover:
    - Lexer tokenization
    - Node pattern parsing
    - Relationship parsing
    - Path expressions
    - WHERE clause parsing
    - RETURN clause parsing
    - Complete query parsing
    - Error handling
"""

import pytest
from yellowstone.parser import (
    parse_query,
    CypherParser,
    Lexer,
    Query,
    Identifier,
    Literal,
    PathExpression,
    NodePattern,
    RelationshipPattern,
)


# ============================================================================
# Lexer Tests
# ============================================================================


class TestLexer:
    """Test suite for Lexer tokenization."""

    def test_keyword_tokenization(self) -> None:
        """Test that keywords are recognized."""
        lexer = Lexer("MATCH WHERE RETURN")
        assert len(lexer.tokens) == 3
        assert lexer.tokens[0].type == "KEYWORD"
        assert lexer.tokens[0].value == "MATCH"

    def test_identifier_tokenization(self) -> None:
        """Test that identifiers are recognized."""
        lexer = Lexer("n Person name")
        assert len(lexer.tokens) == 3
        assert all(token.type == "IDENTIFIER" for token in lexer.tokens)

    def test_operator_tokenization(self) -> None:
        """Test that operators are recognized."""
        lexer = Lexer("= <> != < > <= >=")
        types = [token.type for token in lexer.tokens]
        assert "EQUALS" in types
        assert "NOT_EQUALS" in types
        assert "LT" in types
        assert "GT" in types

    def test_arrow_tokenization(self) -> None:
        """Test that arrows are recognized."""
        lexer = Lexer("-> <- --")
        assert len(lexer.tokens) == 3
        assert lexer.tokens[0].type == "ARROW_OUT"
        assert lexer.tokens[1].type == "ARROW_IN"
        assert lexer.tokens[2].type == "DASH"

    def test_string_literals(self) -> None:
        """Test that string literals are recognized."""
        lexer = Lexer("'John' \"Jane\"")
        assert len(lexer.tokens) == 2
        assert lexer.tokens[0].type == "STRING"
        assert lexer.tokens[0].value == "'John'"

    def test_number_literals(self) -> None:
        """Test that numbers are recognized."""
        lexer = Lexer("42 3.14 0")
        assert len(lexer.tokens) == 3
        assert lexer.tokens[0].type == "NUMBER"
        assert lexer.tokens[1].type == "NUMBER"
        assert lexer.tokens[2].type == "NUMBER"

    def test_delimiter_tokenization(self) -> None:
        """Test that delimiters are recognized."""
        lexer = Lexer("( ) [ ] { } : . , ;")
        types = [token.type for token in lexer.tokens]
        assert "LPAREN" in types
        assert "RPAREN" in types
        assert "LBRACKET" in types
        assert "RBRACKET" in types
        assert "LBRACE" in types
        assert "RBRACE" in types
        assert "COLON" in types
        assert "DOT" in types

    def test_invalid_token(self) -> None:
        """Test that invalid tokens raise SyntaxError."""
        with pytest.raises(SyntaxError):
            Lexer("@invalid#token$")


# ============================================================================
# Node Pattern Tests
# ============================================================================


class TestNodePatterns:
    """Test suite for node pattern parsing."""

    def test_simple_node(self) -> None:
        """Test parsing simple node (n)."""
        query_str = "MATCH (n) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert node.variable is not None
        assert node.variable.name == "n"
        assert len(node.labels) == 0

    def test_node_with_label(self) -> None:
        """Test parsing node with single label."""
        query_str = "MATCH (n:Person) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert len(node.labels) == 1
        assert node.labels[0].name == "Person"

    def test_node_with_multiple_labels(self) -> None:
        """Test parsing node with multiple labels."""
        query_str = "MATCH (n:Person:Actor) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert len(node.labels) == 2
        assert node.labels[0].name == "Person"
        assert node.labels[1].name == "Actor"

    def test_node_with_string_property(self) -> None:
        """Test parsing node with string property."""
        query_str = "MATCH (n:Person {name: 'John'}) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert "name" in node.properties
        prop = node.properties["name"]
        assert isinstance(prop, Literal)
        assert prop.value == "John"

    def test_node_with_number_property(self) -> None:
        """Test parsing node with number property."""
        query_str = "MATCH (n:Person {age: 30}) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert "age" in node.properties
        prop = node.properties["age"]
        assert isinstance(prop, Literal)
        assert prop.value == 30

    def test_node_without_variable(self) -> None:
        """Test parsing node without variable."""
        query_str = "MATCH (:Person) RETURN 1"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert node.variable is None
        assert len(node.labels) == 1

    def test_node_with_multiple_properties(self) -> None:
        """Test parsing node with multiple properties."""
        query_str = "MATCH (n {name: 'John', age: 30}) RETURN n"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert len(node.properties) == 2
        assert "name" in node.properties
        assert "age" in node.properties


# ============================================================================
# Relationship Pattern Tests
# ============================================================================


class TestRelationshipPatterns:
    """Test suite for relationship pattern parsing."""

    def test_simple_relationship_outgoing(self) -> None:
        """Test parsing simple outgoing relationship."""
        query_str = "MATCH (n)-[r]->(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == "out"
        assert rel.directed is True

    def test_simple_relationship_incoming(self) -> None:
        """Test parsing incoming relationship."""
        query_str = "MATCH (n)<-[r]-(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == "in"
        assert rel.directed is True

    def test_undirected_relationship(self) -> None:
        """Test parsing undirected relationship."""
        query_str = "MATCH (n)-[r]-(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == "both"
        assert rel.directed is False

    def test_relationship_with_type(self) -> None:
        """Test parsing relationship with type."""
        query_str = "MATCH (n)-[r:KNOWS]->(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.relationship_type is not None
        assert rel.relationship_type.name == "KNOWS"

    def test_relationship_without_variable(self) -> None:
        """Test parsing relationship without variable."""
        query_str = "MATCH (n)-[:KNOWS]->(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.variable is None
        assert rel.relationship_type.name == "KNOWS"

    def test_relationship_shorthand(self) -> None:
        """Test parsing relationship shorthand."""
        query_str = "MATCH (n)-->(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.direction == "out"


# ============================================================================
# Path Expression Tests
# ============================================================================


class TestPathExpressions:
    """Test suite for path expression parsing."""

    def test_simple_path(self) -> None:
        """Test parsing simple two-node path."""
        query_str = "MATCH (n:Person)-[r:KNOWS]->(m:Person) RETURN n, m"
        query = parse_query(query_str)

        path = query.match_clause.paths[0]
        assert len(path.nodes) == 2
        assert len(path.relationships) == 1

    def test_longer_path(self) -> None:
        """Test parsing longer path."""
        query_str = "MATCH (n)-[r1]->(m)-[r2]->(p) RETURN n, m, p"
        query = parse_query(query_str)

        path = query.match_clause.paths[0]
        assert len(path.nodes) == 3
        assert len(path.relationships) == 2

    def test_path_validation(self) -> None:
        """Test that invalid paths raise errors."""
        path = PathExpression(
            nodes=[NodePattern(variable=Identifier(name="n"))],
            relationships=[RelationshipPattern(direction="out")],
        )
        with pytest.raises(ValueError):
            path.validate_structure()


# ============================================================================
# WHERE Clause Tests
# ============================================================================


class TestWhereClauses:
    """Test suite for WHERE clause parsing."""

    def test_simple_equality(self) -> None:
        """Test parsing simple equality comparison."""
        query_str = "MATCH (n) WHERE n.name = 'John' RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["type"] == "comparison"
        assert conditions["operator"] == "="

    def test_string_property_comparison(self) -> None:
        """Test WHERE with string property comparison."""
        query_str = "MATCH (n:Person) WHERE n.name = 'John' RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["left"]["type"] == "property"
        assert conditions["left"]["property"] == "name"

    def test_numeric_comparison(self) -> None:
        """Test WHERE with numeric comparison."""
        query_str = "MATCH (n) WHERE n.age > 30 RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["operator"] == ">"

    def test_not_equals_comparison(self) -> None:
        """Test WHERE with not equals comparison."""
        query_str = "MATCH (n) WHERE n.status <> 'inactive' RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["operator"] == "<>"

    def test_and_operator(self) -> None:
        """Test WHERE with AND operator."""
        query_str = "MATCH (n) WHERE n.age > 30 AND n.name = 'John' RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["type"] == "logical"
        assert conditions["operator"] == "AND"

    def test_or_operator(self) -> None:
        """Test WHERE with OR operator."""
        query_str = "MATCH (n) WHERE n.status = 'active' OR n.status = 'pending' RETURN n"
        query = parse_query(query_str)

        assert query.where_clause is not None
        conditions = query.where_clause.conditions
        assert conditions["type"] == "logical"
        assert conditions["operator"] == "OR"


# ============================================================================
# RETURN Clause Tests
# ============================================================================


class TestReturnClauses:
    """Test suite for RETURN clause parsing."""

    def test_simple_return(self) -> None:
        """Test simple RETURN single item."""
        query_str = "MATCH (n) RETURN n"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert len(return_clause.items) == 1
        assert isinstance(return_clause.items[0], Identifier)
        assert return_clause.items[0].name == "n"

    def test_return_multiple_items(self) -> None:
        """Test RETURN multiple items."""
        query_str = "MATCH (n) RETURN n, n.name, n.age"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert len(return_clause.items) == 3

    def test_return_property(self) -> None:
        """Test RETURN property."""
        query_str = "MATCH (n) RETURN n.name"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert len(return_clause.items) == 1
        item = return_clause.items[0]
        assert item.variable.name == "n"
        assert item.property_name.name == "name"

    def test_return_distinct(self) -> None:
        """Test RETURN DISTINCT."""
        query_str = "MATCH (n) RETURN DISTINCT n.name"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert return_clause.distinct is True

    def test_return_limit(self) -> None:
        """Test RETURN with LIMIT."""
        query_str = "MATCH (n) RETURN n LIMIT 10"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert return_clause.limit == 10

    def test_return_skip(self) -> None:
        """Test RETURN with SKIP."""
        query_str = "MATCH (n) RETURN n SKIP 5"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert return_clause.skip == 5

    def test_return_order_by(self) -> None:
        """Test RETURN with ORDER BY."""
        query_str = "MATCH (n) RETURN n ORDER BY n.name"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert return_clause.order_by is not None
        assert len(return_clause.order_by) == 1
        assert return_clause.order_by[0]["direction"] == "ASC"

    def test_return_order_by_desc(self) -> None:
        """Test RETURN with ORDER BY DESC."""
        query_str = "MATCH (n) RETURN n ORDER BY n.age DESC"
        query = parse_query(query_str)

        return_clause = query.return_clause
        assert return_clause.order_by is not None
        assert return_clause.order_by[0]["direction"] == "DESC"


# ============================================================================
# Complex Query Tests
# ============================================================================


class TestComplexQueries:
    """Test suite for complex query parsing."""

    def test_complete_query(self) -> None:
        """Test parsing complete query with all clauses."""
        query_str = (
            "MATCH (n:Person)-[r:KNOWS]->(m:Person) "
            "WHERE n.age > 30 AND m.age < 50 "
            "RETURN n.name, m.name ORDER BY n.name LIMIT 10"
        )
        query = parse_query(query_str)

        assert isinstance(query, Query)
        assert query.match_clause is not None
        assert query.where_clause is not None
        assert query.return_clause is not None

    def test_multiple_paths(self) -> None:
        """Test parsing MATCH with multiple paths."""
        query_str = "MATCH (n:Person), (m:Movie) RETURN n, m"
        query = parse_query(query_str)

        assert len(query.match_clause.paths) == 2

    def test_optional_match(self) -> None:
        """Test parsing OPTIONAL MATCH."""
        query_str = "OPTIONAL MATCH (n:Person) RETURN n"
        query = parse_query(query_str)

        assert query.match_clause.optional is True

    def test_complex_path(self) -> None:
        """Test parsing complex path expression."""
        query_str = "MATCH (n:Person)-[r1:ACTED_IN]->(m:Movie)<-[r2:DIRECTED]-(p:Person) RETURN n, m, p"
        query = parse_query(query_str)

        path = query.match_clause.paths[0]
        assert len(path.nodes) == 3
        assert len(path.relationships) == 2
        assert path.relationships[0].direction == "out"
        assert path.relationships[1].direction == "in"


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test suite for error handling."""

    def test_invalid_syntax(self) -> None:
        """Test that invalid syntax raises SyntaxError."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n RETURN n")  # Missing closing paren

    def test_missing_return(self) -> None:
        """Test that missing RETURN raises error."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n:Person)")

    def test_invalid_token(self) -> None:
        """Test that invalid tokens raise error."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n@Person) RETURN n")

    def test_unexpected_token_at_end(self) -> None:
        """Test that unexpected tokens at end raise error."""
        with pytest.raises(SyntaxError):
            parse_query("MATCH (n) RETURN n EXTRA")


# ============================================================================
# Edge Cases and Integration
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases."""

    def test_empty_node(self) -> None:
        """Test parsing empty node ()."""
        query_str = "MATCH () RETURN 1"
        query = parse_query(query_str)

        node = query.match_clause.paths[0].nodes[0]
        assert node.variable is None
        assert len(node.labels) == 0

    def test_relationship_without_brackets(self) -> None:
        """Test parsing relationship shorthand without brackets."""
        query_str = "MATCH (n)-->(m) RETURN n, m"
        query = parse_query(query_str)

        rel = query.match_clause.paths[0].relationships[0]
        assert rel.variable is None
        assert rel.relationship_type is None
