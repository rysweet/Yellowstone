"""
WHERE clause translator for Cypher to KQL conversion.

Handles translation of WHERE clause conditions, including:
- Comparison operators (= becomes ==)
- Logical operators (AND becomes 'and', OR becomes 'or')
- Property access and literals
- Complex nested expressions
"""

from typing import Any, Dict
from ..parser.ast_nodes import Identifier, Literal, Property


class WhereClauseTranslator:
    """Translates Cypher WHERE clauses to KQL where conditions."""

    def __init__(self) -> None:
        """Initialize the WHERE clause translator."""
        self.operator_mapping = {
            "=": "==",
            "!=": "!=",
            "<": "<",
            ">": ">",
            "<=": "<=",
            ">=": ">=",
            "AND": "and",
            "OR": "or",
            "NOT": "not",
            "IN": "in",
            "CONTAINS": "contains",
            "STARTS_WITH": "startswith",
            "ENDS_WITH": "endswith",
        }

    def translate(self, conditions: Dict[str, Any]) -> str:
        """Translate WHERE clause conditions to KQL filter expression.

        Args:
            conditions: The conditions dictionary from WhereClause AST node.
                       Nested dictionary structure representing predicate tree.

        Returns:
            KQL where condition string (e.g., "n.name == 'John' and m.age > 30")

        Raises:
            ValueError: If conditions structure is invalid or unsupported
            KeyError: If required condition fields are missing
        """
        if not conditions:
            return ""

        if not isinstance(conditions, dict):
            raise ValueError(f"Conditions must be dictionary, got {type(conditions)}")

        return self._translate_condition(conditions)

    def _translate_condition(self, condition: Dict[str, Any]) -> str:
        """Recursively translate a condition node.

        Args:
            condition: A condition dictionary with 'type' field

        Returns:
            KQL expression string

        Raises:
            ValueError: If condition type is unsupported
        """
        condition_type = condition.get("type")

        if condition_type == "comparison":
            return self._translate_comparison(condition)
        elif condition_type == "logical":
            return self._translate_logical(condition)
        elif condition_type == "property":
            return self._translate_property(condition)
        elif condition_type == "literal":
            return self._translate_literal(condition)
        elif condition_type == "identifier":
            return self._translate_identifier(condition)
        elif condition_type == "function":
            return self._translate_function(condition)
        else:
            raise ValueError(f"Unsupported condition type: {condition_type}")

    def _translate_comparison(self, condition: Dict[str, Any]) -> str:
        """Translate comparison expression (e.g., n.name = 'John').

        Args:
            condition: Comparison condition with 'operator', 'left', 'right'

        Returns:
            KQL comparison expression (e.g., "n.name == 'John'")

        Raises:
            KeyError: If required fields are missing
        """
        if "operator" not in condition or "left" not in condition or "right" not in condition:
            raise KeyError("Comparison condition requires 'operator', 'left', 'right' fields")

        operator = condition["operator"].upper()
        kql_operator = self.operator_mapping.get(operator, operator)

        left = self._translate_condition(condition["left"])
        right = self._translate_condition(condition["right"])

        return f"{left} {kql_operator} {right}"

    def _translate_logical(self, condition: Dict[str, Any]) -> str:
        """Translate logical expression (AND, OR, NOT).

        Args:
            condition: Logical condition with 'operator' and either 'operands' (list)
                      or 'left'/'right' (binary format)

        Returns:
            KQL logical expression (e.g., "n.name == 'John' and m.age > 30")

        Raises:
            KeyError: If required fields are missing
        """
        if "operator" not in condition:
            raise KeyError("Logical condition requires 'operator' field")

        operator = condition["operator"].upper()
        kql_operator = self.operator_mapping.get(operator, operator.lower())

        # Handle both formats: operands list or left/right binary
        operands = []
        if "operands" in condition:
            operands = condition["operands"]
            if not isinstance(operands, list) or len(operands) == 0:
                raise ValueError("Logical condition operands must be non-empty list")
        elif "left" in condition and "right" in condition:
            # Binary format from parser (left, right)
            operands = [condition["left"], condition["right"]]
        else:
            raise KeyError("Logical condition requires either 'operands' or 'left'/'right' fields")

        # Handle NOT specially (unary operator)
        if operator == "NOT":
            if len(operands) != 1:
                raise ValueError("NOT operator requires exactly one operand")
            operand = self._translate_condition(operands[0])
            return f"not({operand})"

        # Handle AND, OR (binary or multi-way operators)
        translated_operands = [
            self._translate_condition(operand) for operand in operands
        ]
        return f" {kql_operator} ".join(translated_operands)

    def _translate_property(self, condition: Dict[str, Any]) -> str:
        """Translate property access (e.g., n.name).

        Args:
            condition: Property condition with 'variable' and 'property' fields

        Returns:
            KQL property reference (e.g., "n.name")

        Raises:
            KeyError: If required fields are missing
        """
        if "variable" not in condition or "property" not in condition:
            raise KeyError("Property condition requires 'variable' and 'property' fields")

        variable = condition["variable"]
        prop = condition["property"]

        return f"{variable}.{prop}"

    def _translate_literal(self, condition: Dict[str, Any]) -> str:
        """Translate literal value.

        Args:
            condition: Literal condition with 'value' and 'value_type' fields

        Returns:
            KQL literal representation (strings quoted, numbers unquoted)

        Raises:
            KeyError: If required fields are missing
        """
        if "value" not in condition:
            raise KeyError("Literal condition requires 'value' field")

        value = condition["value"]
        value_type = condition.get("value_type", "string")

        if value_type == "string":
            # Escape single quotes in string values
            escaped_value = str(value).replace("'", "\\'")
            return f"'{escaped_value}'"
        elif value_type == "number":
            return str(value)
        elif value_type == "boolean":
            return "true" if value else "false"
        elif value_type == "null":
            return "null"
        else:
            raise ValueError(f"Unsupported literal type: {value_type}")

    def _translate_identifier(self, condition: Dict[str, Any]) -> str:
        """Translate identifier.

        Args:
            condition: Identifier condition with 'name' field

        Returns:
            Identifier name as-is

        Raises:
            KeyError: If required fields are missing
        """
        if "name" not in condition:
            raise KeyError("Identifier condition requires 'name' field")

        return condition["name"]

    def _translate_function(self, condition: Dict[str, Any]) -> str:
        """Translate function call (e.g., size(path), length(path)).

        Args:
            condition: Function condition with 'name' and 'arguments' fields

        Returns:
            KQL function call (e.g., "array_length(path)")

        Raises:
            KeyError: If required fields are missing
            ValueError: If function is unsupported
        """
        if "name" not in condition or "arguments" not in condition:
            raise KeyError("Function condition requires 'name' and 'arguments' fields")

        func_name = condition["name"].upper()
        arguments = condition["arguments"]

        # Map Cypher functions to KQL functions
        function_mapping = {
            "SIZE": "array_length",
            "LENGTH": "array_length",
            "COUNT": "array_length",
            "UPPER": "toupper",
            "LOWER": "tolower",
            "TRIM": "trim",
            "SUBSTRING": "substring",
            "TOSTRING": "tostring",
            "TONUMBER": "tonumber",
        }

        kql_func = function_mapping.get(func_name, func_name.lower())

        # Translate each argument
        translated_args = [
            self._translate_condition(arg) if isinstance(arg, dict) else str(arg)
            for arg in arguments
        ]

        return f"{kql_func}({', '.join(translated_args)})"
