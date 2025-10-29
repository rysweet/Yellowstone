"""
Integration tests for the complete Cypher-to-KQL translation pipeline.

Tests end-to-end translation from Cypher queries to KQL using all components:
- Parser
- Schema mapper
- Component translators (graph_match, where_clause, return_clause)
- Main translator orchestration
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from yellowstone import CypherTranslator, TranslationError
from yellowstone.models import CypherQuery, KQLQuery, TranslationContext, TranslationStrategy


@pytest.fixture
def translator():
    """Create a translator instance with default schema."""
    return CypherTranslator(enable_ai=False)


@pytest.fixture
def context():
    """Create a translation context for testing."""
    return TranslationContext(
        user_id="test_user",
        tenant_id="test_tenant",
        permissions=["read"],
        enable_ai_translation=False
    )


class TestBasicTranslation:
    """Test basic Cypher query translation."""

    def test_simple_node_query(self, translator, context):
        """Test translation of simple node pattern."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n")

        result = translator.translate(cypher, context)

        assert isinstance(result, KQLQuery)
        assert "graph-match" in result.query.lower()
        assert "(n:User)" in result.query
        assert "project n" in result.query
        assert result.strategy == TranslationStrategy.FAST_PATH
        assert result.confidence > 0.9

    def test_node_with_property_filter(self, translator, context):
        """Test node pattern with property constraints."""
        cypher = CypherQuery(query="MATCH (n:User {name: 'John'}) RETURN n")

        result = translator.translate(cypher, context)

        assert "graph-match" in result.query.lower()
        assert "(n:User" in result.query
        assert "name: 'John'" in result.query
        assert "project n" in result.query

    def test_relationship_query(self, translator, context):
        """Test translation of node-relationship-node pattern."""
        cypher = CypherQuery(query="MATCH (n:User)-[r:KNOWS]->(m:User) RETURN n, m")

        result = translator.translate(cypher, context)

        assert "graph-match" in result.query.lower()
        assert "(n:User)" in result.query
        assert "-[r:KNOWS]->" in result.query
        assert "(m:User)" in result.query
        assert "project n, m" in result.query

    def test_bidirectional_relationship(self, translator, context):
        """Test translation of undirected relationship."""
        cypher = CypherQuery(query="MATCH (n:User)-[r:KNOWS]-(m:User) RETURN n, m")

        result = translator.translate(cypher, context)

        assert "(n:User)" in result.query
        assert "-[r:KNOWS]-" in result.query
        assert "(m:User)" in result.query

    def test_incoming_relationship(self, translator, context):
        """Test translation of incoming relationship."""
        cypher = CypherQuery(query="MATCH (n:User)<-[r:FOLLOWS]-(m:User) RETURN n, m")

        result = translator.translate(cypher, context)

        assert "(n:User)" in result.query
        assert "<-[r:FOLLOWS]-" in result.query
        assert "(m:User)" in result.query


class TestWhereClauseTranslation:
    """Test WHERE clause translation."""

    def test_simple_where_equals(self, translator, context):
        """Test WHERE clause with equality comparison."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.name = 'Alice' RETURN n")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.name == 'Alice'" in result.query

    def test_where_greater_than(self, translator, context):
        """Test WHERE clause with > operator."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.age > 30 RETURN n")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.age > 30" in result.query

    def test_where_less_than_equals(self, translator, context):
        """Test WHERE clause with <= operator."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.age <= 25 RETURN n.name")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.age <= 25" in result.query

    def test_where_and_condition(self, translator, context):
        """Test WHERE clause with AND logical operator."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.age > 18 AND n.age < 65 RETURN n")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.age > 18" in result.query
        assert "and" in result.query.lower()
        assert "n.age < 65" in result.query

    def test_where_or_condition(self, translator, context):
        """Test WHERE clause with OR logical operator."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.role = 'admin' OR n.role = 'superuser' RETURN n")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.role == 'admin'" in result.query
        assert "or" in result.query.lower()
        assert "n.role == 'superuser'" in result.query

    def test_where_not_equals(self, translator, context):
        """Test WHERE clause with != operator."""
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.status != 'inactive' RETURN n")

        result = translator.translate(cypher, context)

        assert "where" in result.query.lower()
        assert "n.status != 'inactive'" in result.query


class TestReturnClauseTranslation:
    """Test RETURN clause translation."""

    def test_return_multiple_variables(self, translator, context):
        """Test RETURN with multiple variables."""
        cypher = CypherQuery(query="MATCH (n:User)-[r:KNOWS]->(m:User) RETURN n, r, m")

        result = translator.translate(cypher, context)

        assert "project n, r, m" in result.query

    def test_return_property(self, translator, context):
        """Test RETURN with property projection."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n.name")

        result = translator.translate(cypher, context)

        assert "project n.name" in result.query

    def test_return_multiple_properties(self, translator, context):
        """Test RETURN with multiple properties."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n.name, n.email, n.age")

        result = translator.translate(cypher, context)

        assert "project n.name, n.email, n.age" in result.query

    def test_return_distinct(self, translator, context):
        """Test RETURN DISTINCT."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN DISTINCT n.role")

        result = translator.translate(cypher, context)

        assert "distinct project n.role" in result.query

    def test_return_limit(self, translator, context):
        """Test RETURN with LIMIT."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n LIMIT 10")

        result = translator.translate(cypher, context)

        assert "limit 10" in result.query

    def test_return_skip(self, translator, context):
        """Test RETURN with SKIP (offset)."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n SKIP 5")

        result = translator.translate(cypher, context)

        assert "offset 5" in result.query

    def test_return_order_by_asc(self, translator, context):
        """Test RETURN with ORDER BY ascending."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n ORDER BY n.name")

        result = translator.translate(cypher, context)

        assert "sort by" in result.query.lower()
        assert "n.name" in result.query

    def test_return_order_by_desc(self, translator, context):
        """Test RETURN with ORDER BY descending."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n ORDER BY n.age DESC")

        result = translator.translate(cypher, context)

        assert "sort by" in result.query.lower()
        assert "n.age desc" in result.query


class TestComplexQueries:
    """Test complex query patterns."""

    def test_multi_hop_path(self, translator, context):
        """Test translation of multi-hop path pattern."""
        cypher = CypherQuery(
            query="MATCH (a:User)-[r1:KNOWS]->(b:User)-[r2:KNOWS]->(c:User) RETURN a, c"
        )

        result = translator.translate(cypher, context)

        assert "(a:User)" in result.query
        assert "-[r1:KNOWS]->" in result.query
        assert "(b:User)" in result.query
        assert "-[r2:KNOWS]->" in result.query
        assert "(c:User)" in result.query
        assert "project a, c" in result.query

    def test_query_with_all_clauses(self, translator, context):
        """Test query with MATCH, WHERE, RETURN, ORDER BY, LIMIT."""
        cypher = CypherQuery(
            query="MATCH (n:User)-[r:CREATED]->(p:Post) "
                  "WHERE n.verified = TRUE AND p.published = TRUE "
                  "RETURN n.name, p.title "
                  "ORDER BY p.created DESC "
                  "LIMIT 20"
        )

        result = translator.translate(cypher, context)

        # Check all components are present
        assert "graph-match" in result.query.lower()
        assert "(n:User)" in result.query
        assert "-[r:CREATED]->" in result.query
        assert "(p:Post)" in result.query
        assert "where" in result.query.lower()
        assert "n.verified" in result.query
        assert "p.published" in result.query
        assert "project n.name, p.title" in result.query
        assert "sort by" in result.query.lower()
        assert "p.created desc" in result.query
        assert "limit 20" in result.query

    def test_multiple_paths(self, translator, context):
        """Test translation with multiple comma-separated paths."""
        cypher = CypherQuery(
            query="MATCH (n:User)-[r:KNOWS]->(m:User), (n)-[r2:LIKES]->(p:Post) RETURN n, m, p"
        )

        result = translator.translate(cypher, context)

        assert "(n:User)" in result.query
        assert "-[r:KNOWS]->" in result.query
        assert "(m:User)" in result.query
        assert "(n)-[r2:LIKES]->" in result.query
        assert "(p:Post)" in result.query


class TestErrorHandling:
    """Test error handling in translation."""

    def test_invalid_cypher_syntax(self, translator, context):
        """Test that invalid Cypher raises TranslationError."""
        cypher = CypherQuery(query="MATCH n:User RETURN n")  # Missing parentheses

        with pytest.raises(TranslationError):
            translator.translate(cypher, context)

    def test_empty_query(self, translator, context):
        """Test that empty query raises TranslationError."""
        cypher = CypherQuery(query="")

        with pytest.raises(TranslationError):
            translator.translate(cypher, context)

    def test_malformed_where_clause(self, translator, context):
        """Test error handling for malformed WHERE clause."""
        # Missing right side of comparison
        cypher = CypherQuery(query="MATCH (n:User) WHERE n.name = RETURN n")

        with pytest.raises(TranslationError):
            translator.translate(cypher, context)


class TestValidation:
    """Test KQL query validation."""

    def test_validate_valid_query(self, translator, context):
        """Test that valid KQL passes validation."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n")
        result = translator.translate(cypher, context)

        # Validation should pass (called internally during translate)
        assert translator.validate(result) is True

    def test_validate_balanced_parentheses(self, translator):
        """Test validation checks for balanced parentheses."""
        invalid_kql = KQLQuery(
            query="graph-match (n:User RETURN n",  # Missing closing paren
            strategy=TranslationStrategy.FAST_PATH,
            confidence=0.95
        )

        assert translator.validate(invalid_kql) is False

    def test_validate_balanced_brackets(self, translator):
        """Test validation checks for balanced brackets."""
        invalid_kql = KQLQuery(
            query="graph-match (n:User)-[r:KNOWS->(m:User)",  # Missing closing bracket
            strategy=TranslationStrategy.FAST_PATH,
            confidence=0.95
        )

        assert translator.validate(invalid_kql) is False

    def test_validate_empty_query(self, translator):
        """Test validation rejects empty queries."""
        invalid_kql = KQLQuery(
            query="",
            strategy=TranslationStrategy.FAST_PATH,
            confidence=0.95
        )

        assert translator.validate(invalid_kql) is False


class TestStrategyClassification:
    """Test query complexity classification."""

    def test_fast_path_simple_query(self, translator, context):
        """Test that simple queries use fast path."""
        cypher = CypherQuery(query="MATCH (n:User) RETURN n")
        result = translator.translate(cypher, context)

        assert result.strategy == TranslationStrategy.FAST_PATH

    def test_fast_path_two_hop_query(self, translator, context):
        """Test that two-hop queries still use fast path."""
        cypher = CypherQuery(
            query="MATCH (a:User)-[r1:KNOWS]->(b:User)-[r2:KNOWS]->(c:User) RETURN a, c"
        )
        result = translator.translate(cypher, context)

        assert result.strategy == TranslationStrategy.FAST_PATH

    def test_confidence_scores(self, translator, context):
        """Test that confidence scores are reasonable."""
        simple_cypher = CypherQuery(query="MATCH (n:User) RETURN n")
        result = translator.translate(simple_cypher, context)

        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence >= 0.9  # Simple queries should have high confidence


class TestEndToEndScenarios:
    """Test realistic end-to-end scenarios."""

    def test_find_user_friends(self, translator, context):
        """Test: Find all friends of a specific user."""
        cypher = CypherQuery(
            query="MATCH (me:User {username: 'alice'})-[r:FRIENDS]->(friend:User) "
                  "RETURN friend.username, friend.name"
        )

        result = translator.translate(cypher, context)

        assert "graph-match" in result.query.lower()
        assert "(me:User" in result.query
        assert "username: 'alice'" in result.query
        assert "-[r:FRIENDS]->" in result.query
        assert "(friend:User)" in result.query
        assert "project friend.username, friend.name" in result.query

    def test_find_active_users_with_posts(self, translator, context):
        """Test: Find active users who have created posts."""
        cypher = CypherQuery(
            query="MATCH (u:User)-[r:CREATED]->(p:Post) "
                  "WHERE u.status = 'active' AND p.views > 100 "
                  "RETURN u.username, p.title, p.views "
                  "ORDER BY p.views DESC "
                  "LIMIT 10"
        )

        result = translator.translate(cypher, context)

        assert "(u:User)" in result.query
        assert "-[r:CREATED]->" in result.query
        assert "(p:Post)" in result.query
        assert "where" in result.query.lower()
        assert "u.status == 'active'" in result.query
        assert "p.views > 100" in result.query
        assert "project u.username, p.title, p.views" in result.query
        assert "sort by" in result.query.lower()
        assert "p.views desc" in result.query
        assert "limit 10" in result.query

    def test_find_shared_connections(self, translator, context):
        """Test: Find users who share connections."""
        cypher = CypherQuery(
            query="MATCH (a:User)-[r1:KNOWS]->(mutual:User)<-[r2:KNOWS]-(b:User) "
                  "WHERE a.id = 'user123' "
                  "RETURN b.name, mutual.name"
        )

        result = translator.translate(cypher, context)

        assert "(a:User)" in result.query
        assert "-[r1:KNOWS]->" in result.query
        assert "(mutual:User)" in result.query
        assert "<-[r2:KNOWS]-" in result.query
        assert "(b:User)" in result.query
        assert "where" in result.query.lower()
        assert "a.id == 'user123'" in result.query
        assert "project b.name, mutual.name" in result.query
