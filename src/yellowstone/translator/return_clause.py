"""
RETURN clause translator for Cypher to KQL conversion.

Handles translation of RETURN clauses, including:
- Simple variable returns
- Property projections
- Distinct modifier
- Order by clauses
- Limit and skip (offset)
- Aggregation functions
"""

from typing import Any, Dict, List, Optional
from ..parser.ast_nodes import ReturnClause, Identifier, Property


class ReturnClauseTranslator:
    """Translates Cypher RETURN clauses to KQL project and sort syntax."""

    def __init__(self) -> None:
        """Initialize the return clause translator."""
        self.aggregation_functions = {
            "COUNT",
            "SUM",
            "AVG",
            "MIN",
            "MAX",
            "COLLECT",
            "DISTINCT",
        }

    def translate(self, return_clause: ReturnClause) -> str:
        """Translate RETURN clause to KQL project statement.

        Args:
            return_clause: ReturnClause AST node with items, distinct, order_by, limit, skip

        Returns:
            KQL projection string (e.g., "project n, m.name | sort by n.age desc")

        Raises:
            ValueError: If return clause structure is invalid
        """
        if not isinstance(return_clause, ReturnClause):
            raise ValueError(f"Expected ReturnClause, got {type(return_clause)}")

        if not return_clause.items:
            raise ValueError("RETURN clause must have at least one item")

        # Build the project clause
        project_items = []
        for item in return_clause.items:
            project_item = self._translate_return_item(item)
            project_items.append(project_item)

        # Handle DISTINCT
        distinct_modifier = ""
        if return_clause.distinct:
            distinct_modifier = "distinct "

        result = f"{distinct_modifier}project {', '.join(project_items)}"

        # Add sort/order by if specified
        if return_clause.order_by:
            sort_clause = self._translate_order_by(return_clause.order_by)
            result += f" | {sort_clause}"

        # Add limit if specified
        if return_clause.limit is not None:
            if return_clause.limit < 0:
                raise ValueError(f"LIMIT must be non-negative, got {return_clause.limit}")
            result += f" | limit {return_clause.limit}"

        # Add skip (offset) if specified
        if return_clause.skip is not None:
            if return_clause.skip < 0:
                raise ValueError(f"SKIP must be non-negative, got {return_clause.skip}")
            # In KQL, skip is achieved with 'limit' or offset-based pagination
            # We'll use offset semantic if available
            result += f" | offset {return_clause.skip}"

        return result

    def _translate_return_item(self, item: Any) -> str:
        """Translate a single return item.

        Items can be:
        - Identifiers (variables): n, m
        - Properties: n.name, m.age
        - Function calls: COUNT(n), SUM(m.age)
        - Literals: 'constant_value', 42
        - Aliases: n.name as actor_name

        Args:
            item: A return item (could be dict, Identifier, Property, or other)

        Returns:
            KQL projection item string

        Raises:
            ValueError: If item type is unsupported
        """
        # Handle Identifier objects
        if isinstance(item, Identifier):
            return str(item)

        # Handle Property objects
        if isinstance(item, Property):
            return str(item)

        # Handle dictionary items (for more complex structures)
        if isinstance(item, dict):
            item_type = item.get("type")

            if item_type == "identifier":
                return item.get("name", "")

            elif item_type == "property":
                variable = item.get("variable", "")
                prop = item.get("property", "")
                return f"{variable}.{prop}"

            elif item_type == "function":
                return self._translate_function_item(item)

            elif item_type == "literal":
                return self._translate_literal_item(item)

            elif item_type == "alias":
                # Handle aliased expressions: expr as alias_name
                expr = self._translate_return_item(item.get("expression"))
                alias = item.get("alias", "")
                return f"{expr} as {alias}"

            else:
                raise ValueError(f"Unsupported return item type: {item_type}")

        # Handle string items (variable names)
        if isinstance(item, str):
            return item

        # Handle numeric literals
        if isinstance(item, (int, float)):
            return str(item)

        # Handle boolean literals
        if isinstance(item, bool):
            return "true" if item else "false"

        raise ValueError(f"Unsupported return item: {item} (type: {type(item)})")

    def _translate_function_item(self, func_item: Dict[str, Any]) -> str:
        """Translate a function call in a return item.

        Args:
            func_item: Function dict with 'name' and 'arguments'

        Returns:
            KQL function call string

        Raises:
            KeyError: If required fields are missing
        """
        if "name" not in func_item or "arguments" not in func_item:
            raise KeyError("Function item requires 'name' and 'arguments' fields")

        func_name = func_item["name"].upper()
        arguments = func_item["arguments"]

        # Map Cypher aggregation functions to KQL
        function_mapping = {
            "COUNT": "count",
            "SUM": "sum",
            "AVG": "avg",
            "MIN": "min",
            "MAX": "max",
            "COLLECT": "make_set",
            "UPPER": "toupper",
            "LOWER": "tolower",
            "TRIM": "trim",
            "LENGTH": "strlen",
            "SIZE": "array_length",
            "SUBSTRING": "substring",
            "TOSTRING": "tostring",
            "TONUMBER": "tonumber",
        }

        kql_func = function_mapping.get(func_name, func_name.lower())

        # Translate arguments
        if not isinstance(arguments, list):
            raise ValueError("Function arguments must be a list")

        translated_args = [
            self._translate_return_item(arg) if isinstance(arg, (dict, Identifier, Property))
            else str(arg)
            for arg in arguments
        ]

        return f"{kql_func}({', '.join(translated_args)})"

    def _translate_literal_item(self, literal_item: Dict[str, Any]) -> str:
        """Translate a literal value in a return item.

        Args:
            literal_item: Literal dict with 'value' and 'value_type'

        Returns:
            KQL literal representation

        Raises:
            KeyError: If required fields are missing
        """
        if "value" not in literal_item:
            raise KeyError("Literal item requires 'value' field")

        value = literal_item["value"]
        value_type = literal_item.get("value_type", "string")

        if value_type == "string":
            # Escape single quotes
            escaped = str(value).replace("'", "\\'")
            return f"'{escaped}'"
        elif value_type == "number":
            return str(value)
        elif value_type == "boolean":
            return "true" if value else "false"
        elif value_type == "null":
            return "null"
        else:
            raise ValueError(f"Unsupported literal type: {value_type}")

    def _translate_order_by(self, order_by_items: List[Dict[str, Any]]) -> str:
        """Translate order by specification to KQL sort clause.

        Args:
            order_by_items: List of order by specifications, each with 'item' and 'direction'

        Returns:
            KQL sort clause (e.g., "sort by n.age desc, m.name asc")

        Raises:
            ValueError: If order by structure is invalid
        """
        if not isinstance(order_by_items, list):
            raise ValueError("order_by must be a list")

        if not order_by_items:
            return ""

        sort_parts = []
        for order_spec in order_by_items:
            if not isinstance(order_spec, dict):
                raise ValueError("Each order_by item must be a dictionary")

            if "item" not in order_spec:
                raise KeyError("Order by item requires 'item' field")

            item = order_spec["item"]
            direction = order_spec.get("direction", "asc").lower()

            # Validate direction
            if direction not in ("asc", "desc"):
                raise ValueError(f"Invalid sort direction: {direction}")

            # Translate the item
            item_str = self._translate_return_item(item)

            # Add to sort parts
            if direction == "desc":
                sort_parts.append(f"{item_str} desc")
            else:
                sort_parts.append(f"{item_str} asc")

        return f"sort by {', '.join(sort_parts)}"

    def extract_projected_fields(self, return_clause: ReturnClause) -> List[str]:
        """Extract list of fields that will be projected in the return clause.

        Useful for schema inference and result validation.

        Args:
            return_clause: ReturnClause to analyze

        Returns:
            List of field names (e.g., ['n', 'm', 'n.name', 'count'])
        """
        fields = []

        for item in return_clause.items:
            if isinstance(item, Identifier):
                fields.append(str(item))
            elif isinstance(item, Property):
                fields.append(str(item))
            elif isinstance(item, dict):
                if item.get("type") == "identifier":
                    fields.append(item.get("name", ""))
                elif item.get("type") == "property":
                    var = item.get("variable", "")
                    prop = item.get("property", "")
                    fields.append(f"{var}.{prop}")
                elif item.get("type") == "alias":
                    fields.append(item.get("alias", ""))
                elif item.get("type") == "function":
                    fields.append(item.get("name", ""))

        return fields
