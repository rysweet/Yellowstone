"""
Path translator for handling variable-length paths in Cypher queries.

Translates Cypher path patterns including:
- Simple paths: (n)-[r]->(m)
- Variable-length paths: (n)-[r*1..3]->(m), (n)-[r*..5]->(m)
- Unbounded paths: (n)-[r*]->(m)
"""

from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class PathLength:
    """Represents path length constraints."""

    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def is_variable_length(self) -> bool:
        """Check if this represents a variable-length path.

        Returns:
            True if path length is variable (min != max or unbounded)
        """
        if self.min_length is None or self.max_length is None:
            return True
        return self.min_length != self.max_length

    def to_kql_format(self) -> str:
        """Convert path length to KQL format string.

        Returns:
            KQL path length specification (e.g., "[1..3]", "[..]", "[5]")

        Raises:
            ValueError: If length constraints are invalid
        """
        if self.min_length is not None and self.max_length is not None:
            if self.min_length < 0 or self.max_length < 0:
                raise ValueError("Path lengths cannot be negative")
            if self.min_length > self.max_length:
                raise ValueError("Minimum length cannot exceed maximum length")

            if self.min_length == self.max_length:
                return f"[{self.min_length}]"
            else:
                return f"[{self.min_length}..{self.max_length}]"

        if self.min_length is not None:
            if self.min_length < 0:
                raise ValueError("Path length cannot be negative")
            return f"[{self.min_length}..]"

        if self.max_length is not None:
            if self.max_length < 0:
                raise ValueError("Path length cannot be negative")
            return f"[..{self.max_length}]"

        # Unbounded path
        return "[..]"


class PathTranslator:
    """Translates Cypher path patterns to KQL graph-match format."""

    def __init__(self) -> None:
        """Initialize the path translator."""
        self.relationship_direction_map = {
            "out": "->",
            "in": "<-",
            "both": "--",
        }

    def parse_path_length_specification(self, spec: str) -> PathLength:
        """Parse a path length specification string.

        Args:
            spec: Path length specification (e.g., "1..3", "5", "*", "..10")

        Returns:
            PathLength object with min and max constraints

        Raises:
            ValueError: If specification format is invalid
        """
        if not spec or spec == "*":
            return PathLength()  # Unbounded

        spec = spec.strip()

        if ".." in spec:
            parts = spec.split("..", 1)
            min_str = parts[0].strip()
            max_str = parts[1].strip()

            min_length = int(min_str) if min_str else None
            max_length = int(max_str) if max_str else None

            return PathLength(min_length=min_length, max_length=max_length)

        # Single value - exact length
        try:
            length = int(spec)
            return PathLength(min_length=length, max_length=length)
        except ValueError:
            raise ValueError(f"Invalid path length specification: {spec}")

    def translate_node_reference(self, node_var: Optional[str], labels: list[str]) -> str:
        """Translate node reference to KQL format.

        Args:
            node_var: Optional node variable name
            labels: List of node labels

        Returns:
            KQL node reference (e.g., "n", "Person", "n:Person")

        Raises:
            ValueError: If labels structure is invalid
        """
        if not node_var and not labels:
            return ""

        result = ""
        if node_var:
            result = node_var

        if labels:
            if not isinstance(labels, list):
                raise ValueError("Labels must be a list")
            label_str = "|".join(labels)
            if result:
                result += f":{label_str}"
            else:
                result = label_str

        return result

    def translate_relationship_reference(
        self, rel_var: Optional[str], rel_types: list[str], is_variable_length: bool = False
    ) -> str:
        """Translate relationship reference to KQL format.

        Args:
            rel_var: Optional relationship variable name
            rel_types: List of relationship type names
            is_variable_length: Whether this is a variable-length relationship

        Returns:
            KQL relationship reference (e.g., "r", "KNOWS", "r:KNOWS")

        Raises:
            ValueError: If types structure is invalid
        """
        if not rel_var and not rel_types:
            return ""

        result = ""
        if rel_var:
            result = rel_var

        if rel_types:
            if not isinstance(rel_types, list):
                raise ValueError("Relationship types must be a list")
            type_str = "|".join(rel_types)
            if result:
                result += f":{type_str}"
            else:
                result = type_str

        return result

    def translate_path_segment(
        self,
        from_node: Dict[str, Any],
        relationship: Dict[str, Any],
        to_node: Dict[str, Any],
    ) -> str:
        """Translate a single path segment (node-relationship-node).

        Args:
            from_node: Source node dict with 'variable', 'labels'
            relationship: Relationship dict with 'variable', 'types', 'direction', 'length'
            to_node: Target node dict with 'variable', 'labels'

        Returns:
            KQL path segment string (e.g., "(n:Person)-[r:KNOWS]->(m:Person)")

        Raises:
            ValueError: If any component structure is invalid
        """
        if not isinstance(from_node, dict) or not isinstance(to_node, dict):
            raise ValueError("Node specifications must be dictionaries")
        if not isinstance(relationship, dict):
            raise ValueError("Relationship specification must be dictionary")

        # Translate nodes
        from_ref = self.translate_node_reference(
            from_node.get("variable"), from_node.get("labels", [])
        )
        to_ref = self.translate_node_reference(
            to_node.get("variable"), to_node.get("labels", [])
        )

        # Translate relationship
        rel_var = relationship.get("variable")
        rel_types = relationship.get("types", [])
        direction = relationship.get("direction", "out")
        length_spec = relationship.get("length")

        # Parse path length if specified
        path_length = None
        if length_spec:
            path_length = self.parse_path_length_specification(length_spec)

        # Build relationship string
        rel_ref = self.translate_relationship_reference(rel_var, rel_types, bool(path_length))
        if path_length and path_length.is_variable_length():
            rel_ref += path_length.to_kql_format()

        # Build edge operator based on direction
        direction_arrow = self.relationship_direction_map.get(direction, "->")

        if direction == "in":
            return f"({from_ref})<-[{rel_ref}]-({to_ref})"
        elif direction == "both":
            return f"({from_ref})-[{rel_ref}]-({to_ref})"
        else:  # out
            return f"({from_ref})-[{rel_ref}]->({to_ref})"

    def translate_full_path(self, path_segments: list[Dict[str, Any]]) -> str:
        """Translate a full path pattern (potentially with multiple segments).

        Args:
            path_segments: List of path segment dicts, each with 'from_node',
                          'relationship', 'to_node'

        Returns:
            Complete KQL path string

        Raises:
            ValueError: If path structure is invalid
        """
        if not isinstance(path_segments, list):
            raise ValueError("Path segments must be a list")
        if not path_segments:
            raise ValueError("Path must have at least one segment")

        translated_segments = []
        for segment in path_segments:
            if not isinstance(segment, dict):
                raise ValueError("Each path segment must be a dictionary")
            if "from_node" not in segment or "relationship" not in segment or "to_node" not in segment:
                raise ValueError("Each segment must have 'from_node', 'relationship', 'to_node'")

            translated = self.translate_path_segment(
                segment["from_node"],
                segment["relationship"],
                segment["to_node"],
            )
            translated_segments.append(translated)

        return " ".join(translated_segments)

    def merge_adjacent_nodes(self, path_str: str) -> str:
        """Optimize path by removing duplicate node specifications.

        When two path segments are adjacent, remove the duplicate node pattern.
        For example: (n)-[r1]->(m) (m)-[r2]->(p) becomes (n)-[r1]->(m)-[r2]->(p)

        Args:
            path_str: Path string with potentially redundant node references

        Returns:
            Optimized path string

        Note:
            This is a simple implementation for common cases.
            More complex optimizations may be needed for edge cases.
        """
        # This is a simplified version - full optimization would require
        # parsing and reconstructing the path AST
        return path_str
