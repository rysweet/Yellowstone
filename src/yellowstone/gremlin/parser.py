"""
Gremlin query parser for Yellowstone.

This module provides a Gremlin query parser that converts query strings
into an Abstract Syntax Tree (AST) for further processing and translation.

The parser uses a simple tokenization approach followed by method chain parsing.

Example:
    >>> from yellowstone.gremlin import parse_gremlin
    >>> query_str = "g.V().hasLabel('Person').out('KNOWS').values('name')"
    >>> traversal = parse_gremlin(query_str)
    >>> print(traversal.steps[0])
    V()
"""

import re
from typing import Any, Optional
from .ast import (
    GremlinTraversal,
    Step,
    VertexStep,
    EdgeStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    OrderStep,
    CountStep,
    DedupStep,
    GremlinValue,
    Predicate,
)


class GremlinParseError(Exception):
    """Exception raised when Gremlin query parsing fails."""

    pass


class GremlinTokenizer:
    """Tokenizes Gremlin query strings into parseable tokens.

    Splits the query into method names and arguments while handling:
    - Quoted strings (single and double quotes)
    - Numeric values
    - Parentheses
    - Method chaining (dots)
    """

    def __init__(self, query: str):
        """Initialize tokenizer with query string.

        Args:
            query: Gremlin query string to tokenize
        """
        self.query = query.strip()
        self.position = 0
        self.length = len(self.query)

    def tokenize(self) -> list[dict[str, Any]]:
        """Tokenize the query into method calls.

        Returns:
            List of token dictionaries with 'method' and 'args' keys

        Example:
            >>> tokenizer = GremlinTokenizer("g.V().hasLabel('Person')")
            >>> tokenizer.tokenize()
            [{'method': 'g', 'args': []}, {'method': 'V', 'args': []},
             {'method': 'hasLabel', 'args': ['Person']}]
        """
        tokens = []

        while self.position < self.length:
            self._skip_whitespace()

            if self.position >= self.length:
                break

            # Skip dots
            if self.query[self.position] == ".":
                self.position += 1
                continue

            # Read method name
            method_name = self._read_identifier()
            if not method_name:
                raise GremlinParseError(
                    f"Expected method name at position {self.position}"
                )

            # Check for opening parenthesis
            self._skip_whitespace()
            args = []
            if self.position < self.length and self.query[self.position] == "(":
                args = self._read_arguments()

            tokens.append({"method": method_name, "args": args})

        return tokens

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.position < self.length and self.query[self.position].isspace():
            self.position += 1

    def _read_identifier(self) -> str:
        """Read an identifier (method name or variable).

        Returns:
            The identifier string
        """
        start = self.position
        while self.position < self.length:
            char = self.query[self.position]
            if char.isalnum() or char == "_":
                self.position += 1
            else:
                break
        return self.query[start : self.position]

    def _read_arguments(self) -> list[Any]:
        """Read arguments from parentheses.

        Returns:
            List of argument values (strings, numbers, or nested method calls)
        """
        if self.query[self.position] != "(":
            raise GremlinParseError(
                f"Expected '(' at position {self.position}, got '{self.query[self.position]}'"
            )

        self.position += 1  # Skip opening parenthesis
        args = []

        while self.position < self.length:
            self._skip_whitespace()

            if self.query[self.position] == ")":
                self.position += 1  # Skip closing parenthesis
                break

            # Read argument value
            arg = self._read_argument_value()
            args.append(arg)

            self._skip_whitespace()

            # Check for comma or closing parenthesis
            if self.position < self.length:
                if self.query[self.position] == ",":
                    self.position += 1  # Skip comma
                elif self.query[self.position] == ")":
                    continue
                else:
                    # Could be a nested method call
                    if self.query[self.position] == "(":
                        continue

        return args

    def _read_argument_value(self) -> Any:
        """Read a single argument value.

        Returns:
            The argument value (string, number, or dict for predicates)
        """
        self._skip_whitespace()

        if self.position >= self.length:
            raise GremlinParseError("Unexpected end of input while reading argument")

        char = self.query[self.position]

        # String literal
        if char in ("'", '"'):
            return self._read_string(char)

        # Number literal
        if char.isdigit() or char == "-":
            return self._read_number()

        # Predicate or nested method (like gt(30))
        if char.isalpha():
            method_name = self._read_identifier()
            if self.position < self.length and self.query[self.position] == "(":
                nested_args = self._read_arguments()
                # Return as predicate dict
                return {"predicate": method_name, "args": nested_args}
            # Boolean literals
            if method_name.lower() == "true":
                return True
            if method_name.lower() == "false":
                return False
            return method_name

        raise GremlinParseError(
            f"Unexpected character '{char}' at position {self.position}"
        )

    def _read_string(self, quote_char: str) -> str:
        """Read a quoted string.

        Args:
            quote_char: The quote character (' or ")

        Returns:
            The string value without quotes
        """
        self.position += 1  # Skip opening quote
        start = self.position

        while self.position < self.length:
            if self.query[self.position] == quote_char:
                value = self.query[start : self.position]
                self.position += 1  # Skip closing quote
                return value
            if self.query[self.position] == "\\" and self.position + 1 < self.length:
                self.position += 2  # Skip escaped character
            else:
                self.position += 1

        raise GremlinParseError(f"Unterminated string starting at position {start - 1}")

    def _read_number(self) -> int | float:
        """Read a numeric value.

        Returns:
            Integer or float value
        """
        start = self.position
        has_dot = False

        if self.query[self.position] == "-":
            self.position += 1

        while self.position < self.length:
            char = self.query[self.position]
            if char.isdigit():
                self.position += 1
            elif char == "." and not has_dot:
                has_dot = True
                self.position += 1
            else:
                break

        number_str = self.query[start : self.position]
        return float(number_str) if has_dot else int(number_str)


class GremlinParser:
    """Parser that converts tokenized Gremlin queries into AST.

    This parser handles common Gremlin traversal patterns and creates
    appropriate Step objects for each method in the chain.
    """

    def __init__(self):
        """Initialize the parser."""
        pass

    def parse(self, query: str) -> GremlinTraversal:
        """Parse a Gremlin query string into a GremlinTraversal AST.

        Args:
            query: Gremlin query string (e.g., "g.V().hasLabel('Person')")

        Returns:
            GremlinTraversal AST object

        Raises:
            GremlinParseError: If the query syntax is invalid

        Example:
            >>> parser = GremlinParser()
            >>> traversal = parser.parse("g.V().hasLabel('Person').values('name')")
            >>> len(traversal.steps)
            3
        """
        # Tokenize the query
        tokenizer = GremlinTokenizer(query)
        tokens = tokenizer.tokenize()

        if not tokens:
            raise GremlinParseError("Empty query")

        # First token should be 'g' (graph traversal source)
        if tokens[0]["method"] != "g":
            raise GremlinParseError(
                f"Query must start with 'g', got '{tokens[0]['method']}'"
            )

        # Parse remaining tokens into steps
        steps = []
        for token in tokens[1:]:
            step = self._parse_step(token)
            if step:
                steps.append(step)

        if not steps:
            raise GremlinParseError("Query must have at least one step after 'g'")

        return GremlinTraversal(steps=steps)

    def _parse_step(self, token: dict[str, Any]) -> Optional[Step]:
        """Parse a single token into a Step object.

        Args:
            token: Token dictionary with 'method' and 'args'

        Returns:
            Step object or None if method is unknown

        Raises:
            GremlinParseError: If step arguments are invalid
        """
        method = token["method"]
        args = token["args"]

        # Vertex step: V()
        if method == "V":
            vertex_id = args[0] if args else None
            if vertex_id is not None and not isinstance(vertex_id, (str, int)):
                raise GremlinParseError(f"V() expects string or int ID, got {type(vertex_id)}")
            return VertexStep(vertex_id=str(vertex_id) if vertex_id is not None else None)

        # Edge step: E()
        if method == "E":
            edge_id = args[0] if args else None
            if edge_id is not None and not isinstance(edge_id, (str, int)):
                raise GremlinParseError(f"E() expects string or int ID, got {type(edge_id)}")
            return EdgeStep(edge_id=str(edge_id) if edge_id is not None else None)

        # Filter steps
        if method == "hasLabel":
            if not args:
                raise GremlinParseError("hasLabel() requires a label argument")
            return FilterStep(
                filter_type="hasLabel",
                value=self._parse_value(args[0]),
            )

        if method == "has":
            if not args:
                raise GremlinParseError("has() requires at least one argument")
            if len(args) == 1:
                # has('propertyName') - property exists check
                return FilterStep(filter_type="has", property_name=str(args[0]))
            elif len(args) == 2:
                # has('propertyName', value) or has('propertyName', predicate)
                property_name = str(args[0])
                value_or_predicate = args[1]

                if isinstance(value_or_predicate, dict) and "predicate" in value_or_predicate:
                    # Predicate case: has('age', gt(30))
                    predicate = self._parse_predicate(value_or_predicate)
                    return FilterStep(
                        filter_type="has",
                        property_name=property_name,
                        predicate=predicate,
                    )
                else:
                    # Value case: has('name', 'marko')
                    return FilterStep(
                        filter_type="has",
                        property_name=property_name,
                        value=self._parse_value(value_or_predicate),
                    )
            else:
                raise GremlinParseError(f"has() accepts 1-2 arguments, got {len(args)}")

        if method == "hasId":
            if not args:
                raise GremlinParseError("hasId() requires an ID argument")
            return FilterStep(
                filter_type="hasId",
                value=self._parse_value(args[0]),
            )

        if method == "hasKey":
            if not args:
                raise GremlinParseError("hasKey() requires a key argument")
            return FilterStep(
                filter_type="hasKey",
                value=self._parse_value(args[0]),
            )

        if method == "hasValue":
            if not args:
                raise GremlinParseError("hasValue() requires a value argument")
            return FilterStep(
                filter_type="hasValue",
                value=self._parse_value(args[0]),
            )

        # Traversal steps
        if method in ("out", "in", "both"):
            edge_label = args[0] if args else None
            if edge_label is not None and not isinstance(edge_label, str):
                raise GremlinParseError(f"{method}() expects string edge label, got {type(edge_label)}")
            return TraversalStep(
                direction=method,
                traversal_type="vertex",
                edge_label=edge_label,
            )

        if method in ("outE", "inE", "bothE"):
            direction = method[:-1]  # Remove 'E' suffix
            edge_label = args[0] if args else None
            if edge_label is not None and not isinstance(edge_label, str):
                raise GremlinParseError(f"{method}() expects string edge label, got {type(edge_label)}")
            return TraversalStep(
                direction=direction,
                traversal_type="edge",
                edge_label=edge_label,
            )

        if method in ("outV", "inV", "bothV", "otherV"):
            # These convert edges to vertices
            direction_map = {"outV": "out", "inV": "in", "bothV": "both", "otherV": "other"}
            return TraversalStep(
                direction=direction_map[method],
                traversal_type="vertex",
            )

        # Projection steps
        if method in ("values", "valueMap", "properties", "elementMap"):
            property_names = [str(arg) for arg in args if isinstance(arg, str)]
            return ProjectionStep(
                projection_type=method,
                property_names=property_names,
            )

        # Limit step
        if method == "limit":
            if not args:
                raise GremlinParseError("limit() requires a count argument")
            if not isinstance(args[0], int):
                raise GremlinParseError(f"limit() expects integer, got {type(args[0])}")
            return LimitStep(count=args[0])

        # Order step
        if method == "order":
            # Basic order() with no arguments
            return OrderStep()

        if method == "by":
            # This is a modulator for order(), but we'll handle it simply
            # For now, skip it (would require more complex AST)
            return None

        # Count step
        if method == "count":
            return CountStep()

        # Dedup step
        if method == "dedup":
            return DedupStep()

        # Unknown step - raise error
        raise GremlinParseError(f"Unknown Gremlin step: {method}()")

    def _parse_value(self, value: Any) -> GremlinValue:
        """Parse a value into a GremlinValue object.

        Args:
            value: Raw value from tokenizer

        Returns:
            GremlinValue object
        """
        if isinstance(value, str):
            return GremlinValue(value=value, value_type="string")
        elif isinstance(value, bool):
            return GremlinValue(value=value, value_type="boolean")
        elif isinstance(value, (int, float)):
            return GremlinValue(value=value, value_type="number")
        else:
            raise GremlinParseError(f"Unsupported value type: {type(value)}")

    def _parse_predicate(self, predicate_dict: dict[str, Any]) -> Predicate:
        """Parse a predicate dictionary into a Predicate object.

        Args:
            predicate_dict: Dictionary with 'predicate' and 'args' keys

        Returns:
            Predicate object

        Raises:
            GremlinParseError: If predicate is invalid
        """
        operator = predicate_dict["predicate"]
        args = predicate_dict.get("args", [])

        if not args:
            raise GremlinParseError(f"Predicate {operator}() requires an argument")

        value = self._parse_value(args[0])

        # Validate operator
        valid_operators = {"gt", "gte", "lt", "lte", "eq", "neq", "within", "without"}
        if operator not in valid_operators:
            raise GremlinParseError(
                f"Unknown predicate operator: {operator}. Valid: {valid_operators}"
            )

        return Predicate(operator=operator, value=value)


def parse_gremlin(query: str) -> GremlinTraversal:
    """Convenience function to parse a Gremlin query string.

    Args:
        query: Gremlin query string

    Returns:
        GremlinTraversal AST object

    Raises:
        GremlinParseError: If query syntax is invalid

    Example:
        >>> traversal = parse_gremlin("g.V().hasLabel('Person').values('name')")
        >>> len(traversal.steps)
        3
    """
    parser = GremlinParser()
    return parser.parse(query)
