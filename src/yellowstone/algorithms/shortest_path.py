"""
Shortest path algorithm translator for Cypher to KQL conversion.

Translates Cypher shortestPath() function to KQL graph-shortest-paths operator,
supporting weighted and unweighted paths, bidirectional search, multiple sources/targets,
and path length constraints.

Example:
    Basic shortest path:
    >>> translator = ShortestPathTranslator()
    >>> result = translator.translate_shortest_path(
    ...     source="n",
    ...     target="m",
    ...     relationship="KNOWS",
    ...     weighted=False
    ... )
    >>> assert "graph-shortest-paths" in result
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class PathConstraint:
    """Represents constraints on path search."""

    max_length: Optional[int] = None
    weighted: bool = False
    bidirectional: bool = False
    weight_property: Optional[str] = None

    def validate(self) -> None:
        """Validate constraint configuration.

        Raises:
            ValueError: If constraints are invalid
        """
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("Maximum path length cannot be negative")

        if self.weighted and not self.weight_property:
            raise ValueError("Weight property required when weighted=True")


@dataclass
class PathNode:
    """Represents a node in path configuration."""

    variable: str
    labels: Optional[List[str]] = None

    def to_kql_format(self) -> str:
        """Convert to KQL format.

        Returns:
            KQL node reference (e.g., "n", "n:Person")
        """
        if not self.labels:
            return self.variable

        label_str = "|".join(self.labels)
        if self.variable:
            return f"{self.variable}:{label_str}"
        return label_str


@dataclass
class PathRelationship:
    """Represents a relationship in path configuration."""

    variable: Optional[str] = None
    types: Optional[List[str]] = None
    direction: str = "out"

    def validate(self) -> None:
        """Validate relationship configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.direction not in ("out", "in", "both"):
            raise ValueError(f"Invalid direction: {self.direction}")

    def to_kql_format(self) -> str:
        """Convert to KQL format.

        Returns:
            KQL relationship reference (e.g., "r", "r:KNOWS")
        """
        result = ""
        if self.variable:
            result = self.variable

        if self.types:
            type_str = "|".join(self.types)
            if result:
                result += f":{type_str}"
            else:
                result = type_str

        return result


class ShortestPathTranslator:
    """Translates Cypher shortestPath() to KQL graph-shortest-paths.

    Handles:
    - Unweighted shortest path
    - Weighted shortest path with cost properties
    - Bidirectional search
    - Multiple source/target nodes
    - Path length constraints
    """

    def __init__(self) -> None:
        """Initialize the shortest path translator."""
        self.direction_operators = {
            "out": "->",
            "in": "<-",
            "both": "--",
        }

    def translate_shortest_path(
        self,
        source: str,
        target: str,
        relationship: Optional[str] = None,
        constraints: Optional[PathConstraint] = None,
        relationship_config: Optional[PathRelationship] = None,
    ) -> str:
        """Translate single shortest path query.

        Args:
            source: Source node variable (e.g., "n")
            target: Target node variable (e.g., "m")
            relationship: Relationship type to traverse (e.g., "KNOWS")
            constraints: Path constraints (weighted, max length, etc.)
            relationship_config: Detailed relationship configuration

        Returns:
            KQL graph-shortest-paths expression

        Raises:
            ValueError: If configuration is invalid
            TypeError: If arguments have wrong types

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_shortest_path("n", "m", "KNOWS")
            >>> assert query.startswith("graph-shortest-paths")
        """
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Source must be non-empty string")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Target must be non-empty string")

        constraints = constraints or PathConstraint()
        constraints.validate()

        relationship_config = relationship_config or PathRelationship()
        relationship_config.validate()

        # Build relationship reference
        if relationship:
            if relationship_config.variable:
                rel_ref = f"{relationship_config.variable}:{relationship}"
            else:
                rel_ref = relationship
        else:
            rel_ref = relationship_config.to_kql_format()

        # Build edge operator
        direction_op = self.direction_operators.get(
            relationship_config.direction, "->"
        )

        # Build path pattern
        if relationship_config.direction == "in":
            path_pattern = f"({source})<-[{rel_ref}]-({target})"
        elif relationship_config.direction == "both":
            path_pattern = f"({source})-[{rel_ref}]-({target})"
        else:
            path_pattern = f"({source})-[{rel_ref}]->({target})"

        # Build shortest path operator
        if constraints.weighted:
            weight_expr = f" weight={constraints.weight_property}" if constraints.weight_property else ""
            query = f"graph-shortest-paths{weight_expr} {path_pattern}"
        else:
            query = f"graph-shortest-paths {path_pattern}"

        # Add constraints if specified
        if constraints.max_length is not None:
            query += f" | where path_length <= {constraints.max_length}"

        if constraints.bidirectional:
            query = query.replace("graph-shortest-paths", "graph-shortest-paths(bidirectional)")

        return query

    def translate_shortest_path_multiple_targets(
        self,
        source: str,
        targets: List[str],
        relationship: Optional[str] = None,
        constraints: Optional[PathConstraint] = None,
    ) -> str:
        """Translate shortest path with multiple target nodes.

        Args:
            source: Source node variable
            targets: List of target node variables
            relationship: Relationship type to traverse
            constraints: Path constraints

        Returns:
            KQL query with union of shortest paths

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_shortest_path_multiple_targets(
            ...     "n", ["m", "p"], "KNOWS"
            ... )
        """
        if not targets or not isinstance(targets, list):
            raise ValueError("Targets must be non-empty list")

        paths = []
        for target in targets:
            path = self.translate_shortest_path(
                source=source,
                target=target,
                relationship=relationship,
                constraints=constraints,
            )
            paths.append(f"({path})")

        return " union ".join(paths)

    def translate_shortest_path_multiple_sources(
        self,
        sources: List[str],
        target: str,
        relationship: Optional[str] = None,
        constraints: Optional[PathConstraint] = None,
    ) -> str:
        """Translate shortest path with multiple source nodes.

        Args:
            sources: List of source node variables
            target: Target node variable
            relationship: Relationship type to traverse
            constraints: Path constraints

        Returns:
            KQL query with union of shortest paths

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_shortest_path_multiple_sources(
            ...     ["n", "p"], "m", "KNOWS"
            ... )
        """
        if not sources or not isinstance(sources, list):
            raise ValueError("Sources must be non-empty list")

        paths = []
        for source in sources:
            path = self.translate_shortest_path(
                source=source,
                target=target,
                relationship=relationship,
                constraints=constraints,
            )
            paths.append(f"({path})")

        return " union ".join(paths)

    def translate_weighted_shortest_path(
        self,
        source: str,
        target: str,
        relationship: str,
        weight_property: str,
        max_length: Optional[int] = None,
    ) -> str:
        """Translate weighted shortest path query.

        Finds path with minimum total edge weight rather than minimum hops.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Relationship type
            weight_property: Property name containing edge weights
            max_length: Optional maximum path length

        Returns:
            KQL weighted shortest path query

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_weighted_shortest_path(
            ...     "n", "m", "ROAD", "distance"
            ... )
        """
        if not weight_property or not isinstance(weight_property, str):
            raise ValueError("Weight property must be non-empty string")

        constraints = PathConstraint(
            weighted=True,
            weight_property=weight_property,
            max_length=max_length,
        )

        return self.translate_shortest_path(
            source=source,
            target=target,
            relationship=relationship,
            constraints=constraints,
        )

    def translate_bidirectional_shortest_path(
        self,
        source: str,
        target: str,
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """Translate bidirectional shortest path query.

        Searches from both source and target simultaneously.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Optional relationship type
            max_length: Optional maximum path length

        Returns:
            KQL bidirectional shortest path query

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_bidirectional_shortest_path("n", "m")
        """
        constraints = PathConstraint(
            bidirectional=True,
            max_length=max_length,
        )

        return self.translate_shortest_path(
            source=source,
            target=target,
            relationship=relationship,
            constraints=constraints,
        )

    def translate_constrained_shortest_path(
        self,
        source: str,
        target: str,
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
        weight_property: Optional[str] = None,
    ) -> str:
        """Translate shortest path with multiple constraints.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Optional relationship type
            max_length: Maximum number of hops
            weight_property: Optional weight property for weighted search

        Returns:
            KQL constrained shortest path query

        Raises:
            ValueError: If constraints are invalid

        Example:
            >>> translator = ShortestPathTranslator()
            >>> query = translator.translate_constrained_shortest_path(
            ...     "n", "m", "KNOWS", max_length=5
            ... )
        """
        constraints = PathConstraint(
            max_length=max_length,
            weighted=weight_property is not None,
            weight_property=weight_property,
        )

        return self.translate_shortest_path(
            source=source,
            target=target,
            relationship=relationship,
            constraints=constraints,
        )

    def extract_path_length_from_result(self, kql_result: Dict[str, Any]) -> int:
        """Extract path length from KQL result.

        Args:
            kql_result: KQL query result containing path_length field

        Returns:
            Number of hops in the path

        Raises:
            ValueError: If result doesn't contain path_length

        Example:
            >>> translator = ShortestPathTranslator()
            >>> length = translator.extract_path_length_from_result(
            ...     {"path_length": 3}
            ... )
            >>> assert length == 3
        """
        if not isinstance(kql_result, dict):
            raise ValueError("Result must be dictionary")

        if "path_length" not in kql_result:
            raise ValueError("Result must contain 'path_length' field")

        path_length = kql_result["path_length"]
        if not isinstance(path_length, int) or path_length < 0:
            raise ValueError("path_length must be non-negative integer")

        return path_length

    def validate_cypher_shortest_path_syntax(self, cypher_expr: str) -> bool:
        """Validate Cypher shortestPath() expression format.

        Args:
            cypher_expr: Cypher expression to validate

        Returns:
            True if valid shortestPath() syntax

        Raises:
            ValueError: If syntax is invalid

        Example:
            >>> translator = ShortestPathTranslator()
            >>> valid = translator.validate_cypher_shortest_path_syntax(
            ...     "shortestPath((n)-[*]-(m))"
            ... )
            >>> assert valid
        """
        if not isinstance(cypher_expr, str):
            raise TypeError("Cypher expression must be string")

        cypher_expr = cypher_expr.strip()

        if not cypher_expr.startswith("shortestPath("):
            raise ValueError("Expression must start with 'shortestPath('")

        # Count opening and closing parens to ensure they're balanced
        open_count = cypher_expr.count("(")
        close_count = cypher_expr.count(")")

        if open_count != close_count:
            raise ValueError("Expression must end with ')'")

        if not cypher_expr.endswith(")"):
            raise ValueError("Expression must end with ')'")

        if not "-[" in cypher_expr or not "]-" in cypher_expr:
            raise ValueError("Expression must contain relationship pattern [-]")

        return True
