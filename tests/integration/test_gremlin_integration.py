"""Integration tests for Gremlin-to-KQL translation."""
import pytest
from yellowstone.models import CypherQuery, TranslationContext
from yellowstone.main_translator import CypherTranslator


@pytest.fixture
def translator():
    return CypherTranslator(enable_ai=False)


@pytest.fixture
def context():
    return TranslationContext(user_id="test", tenant_id="test", permissions=[])


class TestGremlinBasic:
    """Test basic Gremlin queries."""

    def test_simple_vertex_query(self, translator, context):
        """Test g.V().hasLabel('User')"""
        gremlin = CypherQuery(query="g.V().hasLabel('User')")
        result = translator.translate(gremlin, context)
        
        assert "make-graph" in result.query.lower()
        assert "graph-match" in result.query
        assert "(v0:User)" in result.query

    def test_vertex_with_property_filter(self, translator, context):
        """Test g.V().hasLabel('User').has('age', 30)"""
        gremlin = CypherQuery(query="g.V().hasLabel('User').has('age',30)")
        result = translator.translate(gremlin, context)
        
        assert "graph-match" in result.query
        assert "where v0.age == 30" in result.query

    def test_vertex_with_traversal(self, translator, context):
        """Test g.V().hasLabel('User').out('OWNS')"""
        gremlin = CypherQuery(query="g.V().hasLabel('User').out('OWNS')")
        result = translator.translate(gremlin, context)
        
        assert "graph-match" in result.query
        assert "-[OWNS]->" in result.query

    def test_full_query_with_projection(self, translator, context):
        """Test complete Gremlin query with projection"""
        gremlin = CypherQuery(query="g.V().hasLabel('User').has('age',30).out('OWNS').values('name')")
        result = translator.translate(gremlin, context)
        
        assert "make-graph" in result.query.lower()
        assert "graph-match" in result.query
        assert "where v0.age == 30" in result.query
        assert "project v1.name" in result.query


class TestGremlinTraversals:
    """Test Gremlin traversal patterns."""

    def test_out_traversal(self, translator, context):
        """Test out() edge traversal"""
        gremlin = CypherQuery(query="g.V().out('CREATED')")
        result = translator.translate(gremlin, context)
        assert "-[CREATED]->" in result.query

    def test_in_traversal(self, translator, context):
        """Test in() edge traversal"""
        gremlin = CypherQuery(query="g.V().in('CREATED')")
        result = translator.translate(gremlin, context)
        assert "<-[CREATED]-" in result.query

    def test_both_traversal(self, translator, context):
        """Test both() undirected edge"""
        gremlin = CypherQuery(query="g.V().both('KNOWS')")
        result = translator.translate(gremlin, context)
        assert "-[KNOWS]-" in result.query
