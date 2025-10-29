"""
Tests for the Cypher translator.
"""

import pytest
from yellowstone import CypherTranslator, CypherQuery, TranslationContext


def test_translator_initialization():
    """Test translator can be initialized."""
    translator = CypherTranslator()
    assert translator is not None


def test_simple_match_translation():
    """Test simple MATCH pattern translation."""
    translator = CypherTranslator()
    cypher = CypherQuery("MATCH (u:User) RETURN u")
    context = TranslationContext(
        user_id="test_user",
        tenant_id="test_tenant",
        permissions=["read:users"]
    )

    # TODO: Implement test when translation is ready
    with pytest.raises(NotImplementedError):
        kql = translator.translate(cypher, context)


def test_variable_length_path_translation():
    """Test variable-length path translation."""
    translator = CypherTranslator()
    cypher = CypherQuery(
        "MATCH path = (a)-[*1..3]->(b) WHERE a.id = 'start' RETURN path"
    )
    context = TranslationContext(
        user_id="test_user",
        tenant_id="test_tenant",
        permissions=["read:all"]
    )

    # TODO: Implement test when translation is ready
    with pytest.raises(NotImplementedError):
        kql = translator.translate(cypher, context)
