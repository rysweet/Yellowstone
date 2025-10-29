"""Tests for RETURN clause translation."""

import pytest
from yellowstone.parser.ast_nodes import ReturnClause, Identifier, Property
from yellowstone.translator.return_clause import ReturnClauseTranslator


class TestReturnClauseTranslator:
    """Test suite for ReturnClauseTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = ReturnClauseTranslator()

    def test_translator_initialization(self):
        """Test translator initializes with aggregation function set."""
        assert len(self.translator.aggregation_functions) > 0
        assert "COUNT" in self.translator.aggregation_functions

    def test_translate_simple_identifier(self):
        """Test translation of simple variable returns."""
        return_clause = ReturnClause(items=[Identifier(name='n')])

        result = self.translator.translate(return_clause)

        assert "project" in result
        assert "n" in result

    def test_translate_multiple_identifiers(self):
        """Test translation with multiple variables."""
        return_clause = ReturnClause(
            items=[Identifier(name='n'), Identifier(name='m')]
        )

        result = self.translator.translate(return_clause)

        assert "project" in result
        assert "n" in result
        assert "m" in result

    def test_translate_property(self):
        """Test translation of property access."""
        prop = Property(variable=Identifier(name='n'), property_name=Identifier(name='name'))
        return_clause = ReturnClause(items=[prop])

        result = self.translator.translate(return_clause)

        assert "project" in result
        assert "n.name" in result

    def test_translate_distinct(self):
        """Test translation with DISTINCT modifier."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            distinct=True
        )

        result = self.translator.translate(return_clause)

        assert "distinct" in result

    def test_translate_limit(self):
        """Test translation with LIMIT clause."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            limit=10
        )

        result = self.translator.translate(return_clause)

        assert "limit 10" in result

    def test_translate_skip(self):
        """Test translation with SKIP clause."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            skip=5
        )

        result = self.translator.translate(return_clause)

        assert "offset 5" in result

    def test_translate_order_by_asc(self):
        """Test translation with ORDER BY ascending."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            order_by=[
                {
                    'item': {'type': 'property', 'variable': 'n', 'property': 'name'},
                    'direction': 'asc'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "sort by" in result
        assert "asc" in result

    def test_translate_order_by_desc(self):
        """Test translation with ORDER BY descending."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            order_by=[
                {
                    'item': {'type': 'identifier', 'name': 'n'},
                    'direction': 'desc'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "sort by" in result
        assert "desc" in result

    def test_translate_order_by_multiple_fields(self):
        """Test translation with multiple ORDER BY fields."""
        return_clause = ReturnClause(
            items=[Identifier(name='n'), Identifier(name='m')],
            order_by=[
                {
                    'item': {'type': 'identifier', 'name': 'n'},
                    'direction': 'asc'
                },
                {
                    'item': {'type': 'identifier', 'name': 'm'},
                    'direction': 'desc'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "sort by" in result

    def test_translate_function_count(self):
        """Test translation of COUNT aggregation function."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'function',
                    'name': 'COUNT',
                    'arguments': [{'type': 'identifier', 'name': 'm'}]
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "count(" in result

    def test_translate_function_sum(self):
        """Test translation of SUM aggregation function."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'function',
                    'name': 'SUM',
                    'arguments': [
                        {'type': 'property', 'variable': 'r', 'property': 'weight'}
                    ]
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "sum(" in result

    def test_translate_function_with_alias(self):
        """Test translation of function with alias."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'alias',
                    'expression': {
                        'type': 'function',
                        'name': 'COUNT',
                        'arguments': [{'type': 'identifier', 'name': 'm'}]
                    },
                    'alias': 'total'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "as total" in result

    def test_translate_literal_string(self):
        """Test translation of string literals."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'literal',
                    'value': 'constant',
                    'value_type': 'string'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "'constant'" in result

    def test_translate_literal_number(self):
        """Test translation of number literals."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'literal',
                    'value': 42,
                    'value_type': 'number'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "42" in result

    def test_translate_literal_boolean(self):
        """Test translation of boolean literals."""
        return_clause = ReturnClause(
            items=[
                {
                    'type': 'literal',
                    'value': True,
                    'value_type': 'boolean'
                }
            ]
        )

        result = self.translator.translate(return_clause)

        assert "true" in result

    def test_translate_raises_on_invalid_return_type(self):
        """Test that translator raises on non-ReturnClause input."""
        with pytest.raises(ValueError):
            self.translator.translate("not a return clause")

    def test_translate_raises_on_no_items(self):
        """Test that translator raises when RETURN has no items."""
        return_clause = ReturnClause(items=[])

        with pytest.raises(ValueError):
            self.translator.translate(return_clause)

    def test_translate_raises_on_invalid_limit(self):
        """Test that translator raises on negative limit."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            limit=-1
        )

        with pytest.raises(ValueError):
            self.translator.translate(return_clause)

    def test_translate_raises_on_invalid_skip(self):
        """Test that translator raises on negative skip."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            skip=-1
        )

        with pytest.raises(ValueError):
            self.translator.translate(return_clause)

    def test_translate_raises_on_invalid_sort_direction(self):
        """Test that translator raises on invalid sort direction."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            order_by=[
                {
                    'item': {'type': 'identifier', 'name': 'n'},
                    'direction': 'invalid'
                }
            ]
        )

        with pytest.raises(ValueError):
            self.translator.translate(return_clause)

    def test_function_mapping(self):
        """Test that aggregation functions are properly mapped."""
        mappings = {
            'COUNT': 'count',
            'SUM': 'sum',
            'AVG': 'avg',
            'MIN': 'min',
            'MAX': 'max',
        }

        for cypher_func, kql_func in mappings.items():
            assert cypher_func in self.translator.aggregation_functions

    def test_extract_projected_fields(self):
        """Test extraction of projected field names."""
        return_clause = ReturnClause(
            items=[
                Identifier(name='n'),
                Property(variable=Identifier(name='m'), property_name=Identifier(name='name'))
            ]
        )

        fields = self.translator.extract_projected_fields(return_clause)

        assert 'n' in fields
        assert 'm.name' in fields

    def test_translate_return_item_with_dict_identifier(self):
        """Test translating return item as dictionary identifier."""
        item = {'type': 'identifier', 'name': 'x'}
        result = self.translator._translate_return_item(item)

        assert result == 'x'

    def test_translate_return_item_with_dict_property(self):
        """Test translating return item as dictionary property."""
        item = {'type': 'property', 'variable': 'n', 'property': 'age'}
        result = self.translator._translate_return_item(item)

        assert 'n.age' in result

    def test_translate_return_item_with_string(self):
        """Test translating return item as string."""
        result = self.translator._translate_return_item('n')

        assert result == 'n'

    def test_translate_return_item_with_number(self):
        """Test translating return item as number."""
        result = self.translator._translate_return_item(42)

        assert result == '42'

    def test_translate_return_item_with_boolean(self):
        """Test translating return item as boolean."""
        result = self.translator._translate_return_item(True)

        assert result == 'True'  # Python str(True) returns 'True'

    def test_translate_return_item_raises_on_unsupported(self):
        """Test that translator raises on unsupported item type."""
        with pytest.raises(ValueError):
            self.translator._translate_return_item(['unsupported', 'list'])

    def test_translate_return_item_raises_on_unknown_dict_type(self):
        """Test that translator raises on unknown dictionary type."""
        item = {'type': 'unknown_type'}

        with pytest.raises(ValueError):
            self.translator._translate_return_item(item)

    def test_translate_all_aggregation_functions(self):
        """Test translation of all supported aggregation functions."""
        functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']

        for func in functions:
            return_clause = ReturnClause(
                items=[
                    {
                        'type': 'function',
                        'name': func,
                        'arguments': [{'type': 'identifier', 'name': 'x'}]
                    }
                ]
            )
            result = self.translator.translate(return_clause)
            assert 'project' in result

    def test_limit_and_skip_together(self):
        """Test translation with both LIMIT and SKIP."""
        return_clause = ReturnClause(
            items=[Identifier(name='n')],
            limit=10,
            skip=5
        )

        result = self.translator.translate(return_clause)

        assert "limit 10" in result
        assert "offset 5" in result

    def test_all_clauses_together(self):
        """Test translation with all optional clauses."""
        return_clause = ReturnClause(
            items=[Identifier(name='n'), Identifier(name='m')],
            distinct=True,
            order_by=[
                {'item': {'type': 'identifier', 'name': 'n'}, 'direction': 'asc'}
            ],
            limit=20,
            skip=10
        )

        result = self.translator.translate(return_clause)

        assert "distinct" in result
        assert "sort by" in result
        assert "limit 20" in result
        assert "offset 10" in result
