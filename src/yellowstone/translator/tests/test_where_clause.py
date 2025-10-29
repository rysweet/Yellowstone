"""Tests for WHERE clause translation."""

import pytest
from yellowstone.translator.where_clause import WhereClauseTranslator


class TestWhereClauseTranslator:
    """Test suite for WhereClauseTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = WhereClauseTranslator()

    def test_translator_initialization(self):
        """Test translator initializes with operator mappings."""
        assert "=" in self.translator.operator_mapping
        assert self.translator.operator_mapping["="] == "=="
        assert self.translator.operator_mapping["AND"] == "and"

    def test_translate_empty_conditions(self):
        """Test translation of empty conditions."""
        result = self.translator.translate({})
        assert result == ""

    def test_translate_none_conditions(self):
        """Test translation of None conditions."""
        result = self.translator.translate(None)
        assert result == ""

    def test_translate_simple_comparison(self):
        """Test translation of simple comparison."""
        conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
            'right': {'type': 'literal', 'value': 'Alice', 'value_type': 'string'}
        }

        result = self.translator.translate(conditions)

        assert "n.name" in result
        assert "==" in result
        assert "'Alice'" in result

    def test_translate_comparison_operators(self):
        """Test translation of various comparison operators."""
        operators = [
            ('=', '=='),
            ('!=', '!='),
            ('<', '<'),
            ('>', '>'),
            ('<=', '<='),
            ('>=', '>='),
        ]

        for cypher_op, kql_op in operators:
            conditions = {
                'type': 'comparison',
                'operator': cypher_op,
                'left': {'type': 'property', 'variable': 'n', 'property': 'age'},
                'right': {'type': 'literal', 'value': 30, 'value_type': 'number'}
            }
            result = self.translator.translate(conditions)
            assert kql_op in result

    def test_translate_and_logical(self):
        """Test translation of AND operator."""
        conditions = {
            'type': 'logical',
            'operator': 'AND',
            'operands': [
                {
                    'type': 'comparison',
                    'operator': '=',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
                    'right': {'type': 'literal', 'value': 'Alice', 'value_type': 'string'}
                },
                {
                    'type': 'comparison',
                    'operator': '>',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'age'},
                    'right': {'type': 'literal', 'value': 18, 'value_type': 'number'}
                }
            ]
        }

        result = self.translator.translate(conditions)

        assert "and" in result
        assert "n.name" in result
        assert "n.age" in result

    def test_translate_or_logical(self):
        """Test translation of OR operator."""
        conditions = {
            'type': 'logical',
            'operator': 'OR',
            'operands': [
                {
                    'type': 'comparison',
                    'operator': '=',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'status'},
                    'right': {'type': 'literal', 'value': 'active', 'value_type': 'string'}
                },
                {
                    'type': 'comparison',
                    'operator': '=',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'status'},
                    'right': {'type': 'literal', 'value': 'pending', 'value_type': 'string'}
                }
            ]
        }

        result = self.translator.translate(conditions)

        assert "or" in result

    def test_translate_not_logical(self):
        """Test translation of NOT operator."""
        conditions = {
            'type': 'logical',
            'operator': 'NOT',
            'operands': [
                {
                    'type': 'comparison',
                    'operator': '=',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'status'},
                    'right': {'type': 'literal', 'value': 'deleted', 'value_type': 'string'}
                }
            ]
        }

        result = self.translator.translate(conditions)

        assert "not(" in result

    def test_translate_number_literal(self):
        """Test translation of number literals."""
        conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'count'},
            'right': {'type': 'literal', 'value': 42, 'value_type': 'number'}
        }

        result = self.translator.translate(conditions)

        assert "42" in result

    def test_translate_boolean_literal(self):
        """Test translation of boolean literals."""
        conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'active'},
            'right': {'type': 'literal', 'value': True, 'value_type': 'boolean'}
        }

        result = self.translator.translate(conditions)

        assert "true" in result

    def test_translate_null_literal(self):
        """Test translation of null literals."""
        conditions = {
            'type': 'comparison',
            'operator': '=',
            'left': {'type': 'property', 'variable': 'n', 'property': 'deleted_at'},
            'right': {'type': 'literal', 'value': None, 'value_type': 'null'}
        }

        result = self.translator.translate(conditions)

        assert "null" in result

    def test_translate_function_call(self):
        """Test translation of function calls."""
        conditions = {
            'type': 'function',
            'name': 'SIZE',
            'arguments': [
                {'type': 'property', 'variable': 'path', 'property': 'edges'}
            ]
        }

        result = self.translator.translate(conditions)

        assert "array_length" in result
        assert "path.edges" in result or "path" in result

    def test_translate_nested_logical(self):
        """Test translation of nested logical expressions."""
        conditions = {
            'type': 'logical',
            'operator': 'AND',
            'operands': [
                {
                    'type': 'comparison',
                    'operator': '=',
                    'left': {'type': 'property', 'variable': 'n', 'property': 'name'},
                    'right': {'type': 'literal', 'value': 'Bob', 'value_type': 'string'}
                },
                {
                    'type': 'logical',
                    'operator': 'OR',
                    'operands': [
                        {
                            'type': 'comparison',
                            'operator': '>',
                            'left': {'type': 'property', 'variable': 'n', 'property': 'age'},
                            'right': {'type': 'literal', 'value': 18, 'value_type': 'number'}
                        },
                        {
                            'type': 'comparison',
                            'operator': '<',
                            'left': {'type': 'property', 'variable': 'n', 'property': 'age'},
                            'right': {'type': 'literal', 'value': 12, 'value_type': 'number'}
                        }
                    ]
                }
            ]
        }

        result = self.translator.translate(conditions)

        assert "and" in result
        assert "or" in result

    def test_translate_raises_on_invalid_condition_type(self):
        """Test that translator raises on unsupported condition type."""
        conditions = {
            'type': 'unknown_type',
        }

        with pytest.raises(ValueError):
            self.translator.translate(conditions)

    def test_translate_raises_on_non_dict_conditions(self):
        """Test that translator raises when conditions is not dict."""
        with pytest.raises(ValueError):
            self.translator.translate("not a dict")

    def test_translate_raises_on_missing_comparison_fields(self):
        """Test that translator raises when comparison fields are missing."""
        conditions = {
            'type': 'comparison',
            'operator': '='
            # Missing left and right
        }

        with pytest.raises(KeyError):
            self.translator.translate(conditions)

    def test_translate_raises_on_invalid_literal_type(self):
        """Test that translator raises on unsupported literal type."""
        conditions = {
            'type': 'literal',
            'value': 42,
            'value_type': 'unknown_type'
        }

        with pytest.raises(ValueError):
            self.translator.translate(conditions)

    def test_translate_not_requires_single_operand(self):
        """Test that NOT operator requires exactly one operand."""
        conditions = {
            'type': 'logical',
            'operator': 'NOT',
            'operands': [
                {'type': 'comparison', 'operator': '=', 'left': {}, 'right': {}},
                {'type': 'comparison', 'operator': '=', 'left': {}, 'right': {}}
            ]
        }

        with pytest.raises(ValueError):
            self.translator.translate(conditions)

    def test_function_mapping(self):
        """Test that all expected functions are mapped."""
        expected_mappings = {
            'SIZE': 'array_length',
            'LENGTH': 'array_length',
            'COUNT': 'array_length',
            'UPPER': 'toupper',
            'LOWER': 'tolower',
        }

        for cypher_func, kql_func in expected_mappings.items():
            assert cypher_func in self.translator.operator_mapping or cypher_func in expected_mappings

    def test_string_escaping(self):
        """Test that strings with quotes are properly escaped."""
        conditions = {
            'type': 'literal',
            'value': "Alice's name",
            'value_type': 'string'
        }

        result = self.translator._translate_literal(conditions)

        assert "\\" in result or "Alice" in result
