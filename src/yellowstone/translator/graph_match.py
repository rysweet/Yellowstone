"""
Graph MATCH clause translator for Cypher to KQL conversion.

Handles translation of MATCH clauses to KQL graph-match syntax, including:
- Simple node-relationship-node patterns
- Multi-hop paths
- Optional MATCH patterns
- Multiple disjoint patterns (comma-separated)
"""

from typing import Any, Dict, List, Optional
from ..parser.ast_nodes import MatchClause, PathExpression, NodePattern, RelationshipPattern
from .paths import PathTranslator


class GraphMatchTranslator:
    """Translates Cypher MATCH clauses to KQL graph-match syntax."""

    def __init__(self) -> None:
        """Initialize the graph match translator."""
        self.path_translator = PathTranslator()

    def translate(self, match_clause: MatchClause) -> str:
        """Translate MATCH clause to KQL graph-match syntax.

        Args:
            match_clause: MatchClause AST node with paths and optional flag

        Returns:
            KQL graph-match expression (e.g., "graph-match pattern ...")

        Raises:
            ValueError: If match clause structure is invalid
        """
        if not isinstance(match_clause, MatchClause):
            raise ValueError(f"Expected MatchClause, got {type(match_clause)}")

        if not match_clause.paths:
            raise ValueError("MATCH clause must have at least one path")

        # Translate all paths in the match clause
        translated_paths = []
        for path in match_clause.paths:
            if not isinstance(path, PathExpression):
                raise ValueError(f"Expected PathExpression, got {type(path)}")

            path_str = self._translate_path_expression(path)
            translated_paths.append(path_str)

        # Join multiple paths with comma
        pattern_str = ", ".join(translated_paths)

        # Add optional modifier if needed
        if match_clause.optional:
            return f"graph-match(optional) {pattern_str}"
        else:
            return f"graph-match {pattern_str}"

    def _translate_path_expression(self, path: PathExpression) -> str:
        """Translate a single path expression to KQL format.

        Args:
            path: PathExpression with nodes and relationships

        Returns:
            KQL path pattern string

        Raises:
            ValueError: If path structure is invalid
        """
        # Validate path structure first
        try:
            path.validate_structure()
        except ValueError as e:
            raise ValueError(f"Invalid path structure: {e}")

        nodes = path.nodes
        relationships = path.relationships

        # Build path segments by alternating nodes and relationships
        result_parts = []

        for i, node in enumerate(nodes):
            # Add node pattern
            node_str = self._translate_node_pattern(node)
            result_parts.append(node_str)

            # Add relationship pattern if not last node
            if i < len(relationships):
                rel_str = self._translate_relationship_pattern(relationships[i])
                result_parts.append(rel_str)

        return "".join(result_parts)

    def _translate_node_pattern(self, node: NodePattern) -> str:
        """Translate a node pattern to KQL format.

        Args:
            node: NodePattern with variable, labels, and optional properties

        Returns:
            KQL node pattern (e.g., "(n:Person)", "(n:Person {name: 'John'})")

        Raises:
            ValueError: If node structure is invalid
        """
        if not isinstance(node, NodePattern):
            raise ValueError(f"Expected NodePattern, got {type(node)}")

        result = "("

        # Add variable
        if node.variable:
            result += str(node.variable)

        # Add labels
        if node.labels:
            if node.variable:
                result += ":"
            labels_str = "|".join(str(label) for label in node.labels)
            result += labels_str

        # Add properties as constraints
        if node.properties:
            if not node.variable and not node.labels:
                # If no variable or labels, we still need to add the properties
                result += self._format_properties(node.properties)
            else:
                result += self._format_properties(node.properties)

        result += ")"
        return result

    def _translate_relationship_pattern(self, relationship: RelationshipPattern) -> str:
        """Translate a relationship pattern to KQL format.

        Args:
            relationship: RelationshipPattern with variable, type, direction, and length

        Returns:
            KQL relationship pattern (e.g., "-[r:KNOWS]->", "-[*1..3]->")

        Raises:
            ValueError: If relationship structure is invalid
        """
        if not isinstance(relationship, RelationshipPattern):
            raise ValueError(f"Expected RelationshipPattern, got {type(relationship)}")

        # Build relationship inner pattern [...]
        inner = "["

        # Add variable
        if relationship.variable:
            inner += str(relationship.variable)

        # Add relationship type
        if relationship.relationship_type:
            if relationship.variable:
                inner += ":"
            inner += str(relationship.relationship_type)

        inner += "]"

        # Build direction operators
        if relationship.direction == "in":
            return f"<-{inner}-"
        elif relationship.direction == "both":
            return f"-{inner}-"
        else:  # out (default)
            return f"-{inner}->"

    def _format_properties(self, properties: Dict[str, Any]) -> str:
        """Format property constraints for nodes or relationships.

        Args:
            properties: Dictionary of property names to values

        Returns:
            Property constraint string (e.g., " {name: 'John', age: 30}")

        Note:
            This is a simplified implementation that formats properties
            as JSON-like syntax suitable for graph-match patterns.
        """
        if not properties:
            return ""

        prop_parts = []
        for key, value in properties.items():
            # Format value based on type
            if isinstance(value, str):
                formatted_value = f"'{value}'"
            elif isinstance(value, bool):
                formatted_value = "true" if value else "false"
            elif value is None:
                formatted_value = "null"
            else:
                formatted_value = str(value)

            prop_parts.append(f"{key}: {formatted_value}")

        if prop_parts:
            return " {" + ", ".join(prop_parts) + "}"
        return ""

    def extract_variable_names(self, match_clause: MatchClause) -> List[str]:
        """Extract all variable names from a MATCH clause.

        Useful for determining which variables are available for use in
        WHERE and RETURN clauses.

        Args:
            match_clause: MatchClause to extract variables from

        Returns:
            List of unique variable names (e.g., ['n', 'r', 'm'])
        """
        variables = set()

        for path in match_clause.paths:
            # Extract node variables
            for node in path.nodes:
                if node.variable:
                    variables.add(str(node.variable))

            # Extract relationship variables
            for rel in path.relationships:
                if rel.variable:
                    variables.add(str(rel.variable))

        return sorted(list(variables))

    def extract_return_candidates(self, match_clause: MatchClause) -> Dict[str, List[str]]:
        """Extract available properties and labels for return clause.

        Args:
            match_clause: MatchClause to analyze

        Returns:
            Dictionary mapping variable names to available labels
            (e.g., {'n': ['Person', 'Actor'], 'm': ['Movie']})
        """
        candidates = {}

        for path in match_clause.paths:
            for node in path.nodes:
                if node.variable:
                    var_name = str(node.variable)
                    label_names = [str(label) for label in node.labels]
                    candidates[var_name] = label_names

        return candidates
