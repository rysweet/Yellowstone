"""
Recursive descent parser for Cypher queries.

This module provides a simple recursive descent parser that handles basic
Cypher query patterns: MATCH, WHERE, and RETURN clauses. It tokenizes input
and builds an Abstract Syntax Tree (AST) represented by the node classes
in ast_nodes.py.

Supported patterns:
    - MATCH (n:Label) RETURN n
    - MATCH (n:Label {prop: value}) RETURN n
    - MATCH (n:Label)-[r:REL]->(m:Label) RETURN n, m
    - WHERE with comparison operators and logical operators
    - RETURN with DISTINCT, ORDER BY, LIMIT, SKIP
"""

import re
from dataclasses import dataclass
from typing import Any, Optional
from .ast_nodes import (
    Query,
    MatchClause,
    WhereClause,
    ReturnClause,
    PathExpression,
    NodePattern,
    RelationshipPattern,
    Property,
    Identifier,
    Literal,
)


# ============================================================================
# Token Definition and Lexer
# ============================================================================


@dataclass(frozen=True)
class Token:
    """Represents a single token from the input."""

    type: str
    value: str
    position: int

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Token({self.type}, '{self.value}')"


class Lexer:
    """Tokenizes Cypher query strings.

    Recognizes keywords, identifiers, operators, and delimiters.
    """

    # Token type patterns (order matters - longer patterns must come first)
    TOKEN_PATTERNS = [
        ("KEYWORD", r"\b(MATCH|WHERE|RETURN|OPTIONAL|DISTINCT|ORDER|BY|ASC|DESC|LIMIT|SKIP|AND|OR|NOT|AS|TRUE|FALSE|NULL)\b"),
        ("NUMBER", r"\d+(\.\d+)?"),
        ("STRING", r"'([^'\\\\]|\\\\.)*'|\"([^\"\\\\]|\\\\.)*\""),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        # Multi-character operators must come before single-char variants
        ("ARROW_OUT", r"->"),
        ("ARROW_IN", r"<-"),
        ("NOT_EQUALS", r"<>|!="),
        ("LTE", r"<="),
        ("GTE", r">="),
        # Single-character operators
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACKET", r"\["),
        ("RBRACKET", r"\]"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("COLON", r":"),
        ("DOT", r"\."),
        ("COMMA", r","),
        ("SEMICOLON", r";"),
        ("DASH", r"-"),
        ("PIPE", r"\|"),
        ("EQUALS", r"="),
        ("LT", r"<"),
        ("GT", r">"),
        ("WHITESPACE", r"\s+"),
    ]

    def __init__(self, query: str):
        """Initialize lexer with a query string.

        Args:
            query: The Cypher query to tokenize
        """
        self.query = query
        self.tokens: list[Token] = []
        self.position = 0
        self._tokenize()

    def _tokenize(self) -> None:
        """Tokenize the input query string."""
        position = 0

        while position < len(self.query):
            match_found = False

            for token_type, pattern in self.TOKEN_PATTERNS:
                regex = re.compile(pattern, re.IGNORECASE)
                match = regex.match(self.query, position)

                if match:
                    value = match.group(0)

                    # Skip whitespace tokens but track position
                    if token_type != "WHITESPACE":
                        self.tokens.append(
                            Token(type=token_type, value=value, position=position)
                        )

                    position = match.end()
                    match_found = True
                    break

            if not match_found:
                raise SyntaxError(
                    f"Invalid character at position {position}: '{self.query[position]}'"
                )

    def peek(self, offset: int = 0) -> Optional[Token]:
        """Look ahead at a token without consuming it.

        Args:
            offset: How many tokens to look ahead (0 = current)

        Returns:
            The token at offset, or None if beyond the end
        """
        index = self.position + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None

    def consume(self, expected_type: Optional[str] = None) -> Token:
        """Consume and return the current token.

        Args:
            expected_type: If provided, verify the token type matches

        Returns:
            The consumed token

        Raises:
            SyntaxError: If expected_type is provided and doesn't match
        """
        if self.position >= len(self.tokens):
            raise SyntaxError("Unexpected end of input")

        token = self.tokens[self.position]

        if expected_type and token.type != expected_type:
            raise SyntaxError(
                f"Expected {expected_type}, got {token.type} "
                f"('{token.value}') at position {token.position}"
            )

        self.position += 1
        return token

    def match_keyword(self, keyword: str) -> bool:
        """Check if current token is a specific keyword.

        Args:
            keyword: The keyword to match (case-insensitive)

        Returns:
            True if current token is the keyword, False otherwise
        """
        token = self.peek()
        return (
            token is not None
            and token.type == "KEYWORD"
            and token.value.upper() == keyword.upper()
        )

    def is_at_end(self) -> bool:
        """Check if we've reached the end of tokens.

        Returns:
            True if at end of input
        """
        return self.position >= len(self.tokens)


# ============================================================================
# Parser Implementation
# ============================================================================


class CypherParser:
    """Recursive descent parser for Cypher queries.

    Parses basic Cypher patterns into an AST. Supports:
        - Node patterns with labels and properties
        - Relationship patterns with types and directions
        - WHERE clauses with conditions
        - RETURN clauses with various options
    """

    def __init__(self, query: str):
        """Initialize parser with a query string.

        Args:
            query: The Cypher query to parse

        Raises:
            SyntaxError: If query contains invalid tokens
        """
        self.lexer = Lexer(query)
        self.query = query

    def parse(self) -> Query:
        """Parse the query and return the AST root node.

        Returns:
            A Query AST node representing the parsed query

        Raises:
            SyntaxError: If the query syntax is invalid
        """
        match_clause = self.parse_match()

        # Parse optional WHERE clause
        where_clause = None
        if self.lexer.match_keyword("WHERE"):
            self.lexer.consume()
            where_clause = self.parse_where()

        return_clause = self.parse_return()

        # Verify we've consumed all tokens
        if not self.lexer.is_at_end():
            token = self.lexer.peek()
            raise SyntaxError(
                f"Unexpected token: {token.type} ('{token.value}') "
                f"at position {token.position}"
            )

        return Query(
            match_clause=match_clause,
            where_clause=where_clause,
            return_clause=return_clause,
        )

    def parse_match(self) -> MatchClause:
        """Parse a MATCH clause.

        Syntax:
            MATCH path [, path]*
            path := (node)-[rel]->(node) | (node)

        Returns:
            A MatchClause AST node

        Raises:
            SyntaxError: If MATCH syntax is invalid
        """
        optional = False

        # Check for OPTIONAL MATCH
        if self.lexer.match_keyword("OPTIONAL"):
            self.lexer.consume()
            optional = True

        self.lexer.consume()  # Consume MATCH keyword
        paths = []

        # Parse first path
        paths.append(self.parse_path())

        # Parse additional paths separated by commas
        while self.lexer.peek() and self.lexer.peek().type == "COMMA":
            self.lexer.consume()  # Consume comma
            paths.append(self.parse_path())

        return MatchClause(paths=paths, optional=optional)

    def parse_path(self) -> PathExpression:
        """Parse a path expression.

        Syntax:
            path := node [relationship node]*

        Returns:
            A PathExpression AST node
        """
        nodes = []
        relationships = []

        # Parse first node
        nodes.append(self.parse_node())

        # Parse relationships and subsequent nodes
        while self.lexer.peek() and self.lexer.peek().type in ("DASH", "ARROW_OUT", "ARROW_IN"):
            rel = self.parse_relationship()
            relationships.append(rel)

            # Must have a node after relationship
            if not self.lexer.peek() or self.lexer.peek().type != "LPAREN":
                raise SyntaxError(
                    f"Expected node after relationship at position "
                    f"{self.lexer.peek().position if self.lexer.peek() else 'EOF'}"
                )

            nodes.append(self.parse_node())

        path = PathExpression(nodes=nodes, relationships=relationships)
        path.validate_structure()
        return path

    def parse_node(self) -> NodePattern:
        """Parse a node pattern.

        Syntax:
            node := ( [variable] [label]* [{properties}] )

        Returns:
            A NodePattern AST node

        Raises:
            SyntaxError: If node syntax is invalid
        """
        self.lexer.consume("LPAREN")

        variable: Optional[Identifier] = None
        labels: list[Identifier] = []
        properties: Optional[dict[str, Any]] = None

        # Parse optional variable
        if self.lexer.peek() and self.lexer.peek().type == "IDENTIFIER":
            variable = Identifier(name=self.lexer.consume().value)

        # Parse optional labels
        while self.lexer.peek() and self.lexer.peek().type == "COLON":
            self.lexer.consume()  # Consume colon
            if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                raise SyntaxError("Expected label name after ':'")
            labels.append(Identifier(name=self.lexer.consume().value))

        # Parse optional properties
        if self.lexer.peek() and self.lexer.peek().type == "LBRACE":
            properties = self.parse_properties()

        self.lexer.consume("RPAREN")

        return NodePattern(variable=variable, labels=labels, properties=properties)

    def parse_properties(self) -> dict[str, Any]:
        """Parse a properties dictionary.

        Syntax:
            properties := { key: value [, key: value]* }

        Returns:
            Dictionary of property names to values
        """
        self.lexer.consume("LBRACE")
        properties = {}

        while self.lexer.peek() and self.lexer.peek().type != "RBRACE":
            # Parse key
            if self.lexer.peek().type != "IDENTIFIER":
                raise SyntaxError("Expected property name")
            key = self.lexer.consume().value

            self.lexer.consume("COLON")

            # Parse value
            value = self.parse_literal()
            properties[key] = value

            # Handle comma
            if self.lexer.peek() and self.lexer.peek().type == "COMMA":
                self.lexer.consume()
            elif self.lexer.peek() and self.lexer.peek().type != "RBRACE":
                raise SyntaxError("Expected ',' or '}' in properties")

        self.lexer.consume("RBRACE")
        return properties

    def parse_relationship(self) -> RelationshipPattern:
        """Parse a relationship pattern.

        Syntax:
            rel := -[variable:type]-> | <-[variable:type]- | -[variable:type]-

        Returns:
            A RelationshipPattern AST node
        """
        # Determine direction from prefix and parse it
        direction = "out"  # default

        token = self.lexer.peek()
        if not token:
            raise SyntaxError("Expected relationship pattern")

        if token.type == "ARROW_IN":
            # Pattern: <-...-
            direction = "in"
            self.lexer.consume()
        elif token.type == "DASH":
            # Pattern: -...-> or -...-
            self.lexer.consume()
            # Prefix dash consumed, now check for bracket or arrow
            if self.lexer.peek() and self.lexer.peek().type == "LBRACKET":
                # Will check for arrow after bracket
                pass
            elif self.lexer.peek() and self.lexer.peek().type == "ARROW_OUT":
                # This shouldn't happen: -)-> is invalid
                raise SyntaxError("Invalid relationship syntax")
        else:
            raise SyntaxError(f"Expected '-' or '<-', got {token.type}")

        variable: Optional[Identifier] = None
        relationship_type: Optional[Identifier] = None

        # Parse optional [variable:type]
        if self.lexer.peek() and self.lexer.peek().type == "LBRACKET":
            self.lexer.consume()

            # Parse optional variable
            if self.lexer.peek() and self.lexer.peek().type == "IDENTIFIER":
                variable = Identifier(name=self.lexer.consume().value)

            # Parse optional type
            if self.lexer.peek() and self.lexer.peek().type == "COLON":
                self.lexer.consume()
                if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                    raise SyntaxError("Expected relationship type after ':'")
                relationship_type = Identifier(name=self.lexer.consume().value)

            self.lexer.consume("RBRACKET")

        # Parse arrow suffix
        if direction == "in":
            # Already consumed the <-, now need to consume the trailing -
            self.lexer.consume("DASH")
        elif self.lexer.peek() and self.lexer.peek().type == "ARROW_OUT":
            # Outgoing: ->
            direction = "out"
            self.lexer.consume()
        elif self.lexer.peek() and self.lexer.peek().type == "DASH":
            # Undirected: -
            direction = "both"
            self.lexer.consume()
        else:
            raise SyntaxError("Expected arrow or dash to close relationship")

        return RelationshipPattern(
            variable=variable,
            relationship_type=relationship_type,
            directed=(direction != "both"),
            direction=direction,
        )

    def parse_where(self) -> WhereClause:
        """Parse a WHERE clause.

        Syntax:
            WHERE condition [AND condition]*

        Returns:
            A WhereClause AST node
        """
        conditions = self.parse_condition()
        return WhereClause(conditions=conditions)

    def parse_condition(self) -> dict[str, Any]:
        """Parse a condition expression.

        Handles comparison and logical operators.

        Returns:
            Dictionary representing the condition tree
        """
        left = self.parse_comparison()

        # Handle AND/OR operators
        while self.lexer.peek() and self.lexer.peek().type == "KEYWORD":
            if self.lexer.peek().value.upper() in ("AND", "OR"):
                operator = self.lexer.consume().value.upper()
                right = self.parse_comparison()
                left = {
                    "type": "logical",
                    "operator": operator,
                    "left": left,
                    "right": right,
                }
            else:
                break

        return left

    def parse_comparison(self) -> dict[str, Any]:
        """Parse a comparison expression.

        Handles: =, <>, !=, <, >, <=, >=, property access, etc.

        Returns:
            Dictionary representing the comparison
        """
        left = self.parse_expression()

        # Check for comparison operators
        token = self.lexer.peek()
        if token and token.type in ("EQUALS", "NOT_EQUALS", "LT", "GT", "LTE", "GTE"):
            operator = self.lexer.consume().value
            right = self.parse_expression()
            return {
                "type": "comparison",
                "operator": operator,
                "left": left,
                "right": right,
            }

        return left

    def parse_expression(self) -> dict[str, Any]:
        """Parse an expression (property, identifier, or literal).

        Returns:
            Dictionary representing the expression
        """
        token = self.lexer.peek()

        if not token:
            raise SyntaxError("Unexpected end of input in expression")

        # Parse property access (e.g., n.name)
        if token.type == "IDENTIFIER":
            variable_name = self.lexer.consume().value

            if self.lexer.peek() and self.lexer.peek().type == "DOT":
                self.lexer.consume()  # Consume dot
                if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                    raise SyntaxError("Expected property name after '.'")
                property_name = self.lexer.consume().value

                return {
                    "type": "property",
                    "variable": variable_name,
                    "property": property_name,
                }

            return {"type": "identifier", "name": variable_name}

        # Parse literal values
        if token.type == "STRING":
            value = self.lexer.consume().value
            # Remove quotes
            cleaned = value[1:-1]
            return {"type": "literal", "value": cleaned, "value_type": "string"}

        if token.type == "NUMBER":
            value = self.lexer.consume().value
            num_value = float(value) if "." in value else int(value)
            return {
                "type": "literal",
                "value": num_value,
                "value_type": "number",
            }

        if token.type == "KEYWORD":
            if token.value.upper() == "TRUE":
                self.lexer.consume()
                return {
                    "type": "literal",
                    "value": True,
                    "value_type": "boolean",
                }
            elif token.value.upper() == "FALSE":
                self.lexer.consume()
                return {
                    "type": "literal",
                    "value": False,
                    "value_type": "boolean",
                }
            elif token.value.upper() == "NULL":
                self.lexer.consume()
                return {"type": "literal", "value": None, "value_type": "null"}

        raise SyntaxError(
            f"Unexpected token in expression: {token.type} "
            f"('{token.value}') at position {token.position}"
        )

    def parse_return(self) -> ReturnClause:
        """Parse a RETURN clause.

        Syntax:
            RETURN [DISTINCT] item [, item]* [ORDER BY ...] [LIMIT n] [SKIP n]

        Returns:
            A ReturnClause AST node
        """
        self.lexer.consume()  # Consume RETURN keyword

        distinct = False
        if self.lexer.peek() and self.lexer.peek().type == "KEYWORD":
            if self.lexer.peek().value.upper() == "DISTINCT":
                distinct = True
                self.lexer.consume()

        # Parse return items
        items = []
        items.append(self.parse_return_item())

        while self.lexer.peek() and self.lexer.peek().type == "COMMA":
            self.lexer.consume()  # Consume comma
            items.append(self.parse_return_item())

        # Parse optional ORDER BY
        order_by = None
        if self.lexer.peek() and self.lexer.match_keyword("ORDER"):
            self.lexer.consume()
            self.lexer.consume()  # Consume BY
            order_by = self.parse_order_by()

        # Parse optional LIMIT and SKIP (in either order)
        limit = None
        skip = None

        while self.lexer.peek() and self.lexer.peek().type == "KEYWORD":
            if self.lexer.match_keyword("LIMIT"):
                if limit is not None:
                    raise SyntaxError("LIMIT specified multiple times")
                self.lexer.consume()
                if not self.lexer.peek() or self.lexer.peek().type != "NUMBER":
                    raise SyntaxError("Expected number after LIMIT")
                limit = int(self.lexer.consume().value)

            elif self.lexer.match_keyword("SKIP"):
                if skip is not None:
                    raise SyntaxError("SKIP specified multiple times")
                self.lexer.consume()
                if not self.lexer.peek() or self.lexer.peek().type != "NUMBER":
                    raise SyntaxError("Expected number after SKIP")
                skip = int(self.lexer.consume().value)
            else:
                break

        return ReturnClause(
            items=items, distinct=distinct, order_by=order_by, limit=limit, skip=skip
        )

    def parse_return_item(self) -> Any:
        """Parse a single return item (identifier or property).

        Returns:
            An Identifier or Property node
        """
        if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
            raise SyntaxError("Expected identifier in RETURN clause")

        variable_name = self.lexer.consume().value
        variable = Identifier(name=variable_name)

        # Check for property access
        if self.lexer.peek() and self.lexer.peek().type == "DOT":
            self.lexer.consume()  # Consume dot
            if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                raise SyntaxError("Expected property name after '.'")
            property_name = Identifier(name=self.lexer.consume().value)
            return Property(variable=variable, property_name=property_name)

        return variable

    def parse_order_by(self) -> list[dict[str, Any]]:
        """Parse ORDER BY clause items.

        Returns:
            List of ordering specifications
        """
        items = []

        # Helper to parse a single order item
        def parse_order_item() -> dict[str, Any]:
            """Parse a single ORDER BY item (variable or property)."""
            if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                raise SyntaxError("Expected identifier in ORDER BY")

            var_name = self.lexer.consume().value
            expr = var_name

            # Check for property access
            if self.lexer.peek() and self.lexer.peek().type == "DOT":
                self.lexer.consume()
                if not self.lexer.peek() or self.lexer.peek().type != "IDENTIFIER":
                    raise SyntaxError("Expected property name after '.' in ORDER BY")
                prop_name = self.lexer.consume().value
                expr = f"{var_name}.{prop_name}"

            direction = "ASC"  # Default

            # Check for ASC/DESC
            if self.lexer.peek() and self.lexer.peek().type == "KEYWORD":
                if self.lexer.peek().value.upper() in ("ASC", "DESC"):
                    direction = self.lexer.consume().value.upper()

            return {"expression": expr, "direction": direction}

        # Parse first item
        items.append(parse_order_item())

        # Parse additional items
        while self.lexer.peek() and self.lexer.peek().type == "COMMA":
            self.lexer.consume()
            items.append(parse_order_item())

        return items

    def parse_literal(self) -> Literal:
        """Parse a literal value.

        Returns:
            A Literal AST node
        """
        token = self.lexer.peek()

        if not token:
            raise SyntaxError("Expected literal value")

        if token.type == "STRING":
            value = self.lexer.consume().value
            cleaned = value[1:-1]  # Remove quotes
            return Literal(value=cleaned, value_type="string")

        if token.type == "NUMBER":
            value = self.lexer.consume().value
            num_value = float(value) if "." in value else int(value)
            return Literal(value=num_value, value_type="number")

        if token.type == "KEYWORD":
            if token.value.upper() == "TRUE":
                self.lexer.consume()
                return Literal(value=True, value_type="boolean")
            elif token.value.upper() == "FALSE":
                self.lexer.consume()
                return Literal(value=False, value_type="boolean")
            elif token.value.upper() == "NULL":
                self.lexer.consume()
                return Literal(value=None, value_type="null")

        raise SyntaxError(
            f"Unexpected token in literal: {token.type} "
            f"('{token.value}') at position {token.position}"
        )


def parse_query(query_string: str) -> Query:
    """Parse a Cypher query string into an AST.

    This is the main entry point for parsing Cypher queries.

    Args:
        query_string: The Cypher query to parse

    Returns:
        The root Query AST node

    Raises:
        SyntaxError: If the query syntax is invalid

    Example:
        >>> query = parse_query("MATCH (n:Person) RETURN n")
        >>> query.match_clause.paths[0].nodes[0].labels[0].name
        'Person'
    """
    parser = CypherParser(query_string)
    return parser.parse()
