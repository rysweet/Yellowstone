"""
Additional path algorithms for Cypher to KQL conversion.

Handles translation of:
- allShortestPaths() - all paths with minimum hops
- allPaths() - enumerate all paths between nodes
- Path filtering and constraints
- Integration with variable-length path translator

Example:
    All shortest paths:
    >>> translator = PathAlgorithmTranslator()
    >>> result = translator.translate_all_shortest_paths(
    ...     source="n",
    ...     target="m",
    ...     relationship="KNOWS"
    ... )
    >>> assert "all_shortest_paths" in result
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .shortest_path import PathConstraint, PathRelationship


@dataclass
class PathFilterConfig:
    """Configuration for path filtering."""

    max_path_length: Optional[int] = None
    min_path_length: Optional[int] = None
    node_filter: Optional[str] = None
    relationship_filter: Optional[str] = None
    excluded_nodes: Optional[List[str]] = None
    excluded_relationships: Optional[List[str]] = None

    def validate(self) -> None:
        """Validate filter configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if (
            self.max_path_length is not None
            and self.min_path_length is not None
            and self.max_path_length < self.min_path_length
        ):
            raise ValueError("max_path_length cannot be less than min_path_length")

        if self.max_path_length is not None and self.max_path_length < 0:
            raise ValueError("max_path_length cannot be negative")

        if self.min_path_length is not None and self.min_path_length < 0:
            raise ValueError("min_path_length cannot be negative")

        if self.excluded_nodes is not None and not isinstance(self.excluded_nodes, list):
            raise ValueError("excluded_nodes must be a list")

        if (
            self.excluded_relationships is not None
            and not isinstance(self.excluded_relationships, list)
        ):
            raise ValueError("excluded_relationships must be a list")


@dataclass
class PathEnumerationConfig:
    """Configuration for path enumeration."""

    max_paths: Optional[int] = None
    max_depth: int = 10
    cycle_detection: bool = True

    def validate(self) -> None:
        """Validate enumeration configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.max_paths is not None and self.max_paths <= 0:
            raise ValueError("max_paths must be positive")

        if self.max_depth <= 0:
            raise ValueError("max_depth must be positive")


class PathAlgorithmTranslator:
    """Translates additional path algorithms from Cypher to KQL.

    Supports:
    - allShortestPaths() enumeration
    - allPaths() pattern matching
    - Path filtering and constraints
    - Integration with variable-length path translator
    """

    def __init__(self) -> None:
        """Initialize the path algorithm translator."""
        self.path_operators = {
            "shortest": "graph-shortest-paths",
            "all_shortest": "all_shortest_paths",
            "all": "all_paths",
        }

    def translate_all_shortest_paths(
        self,
        source: str,
        target: str,
        relationship: Optional[str] = None,
        filters: Optional[PathFilterConfig] = None,
        max_paths: Optional[int] = None,
    ) -> str:
        """Translate allShortestPaths() to KQL.

        Returns all paths with minimum hop count between source and target.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Optional relationship type filter
            filters: Path filter configuration
            max_paths: Maximum number of paths to return

        Returns:
            KQL query for all shortest paths

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> query = translator.translate_all_shortest_paths(
            ...     "n", "m", "KNOWS"
            ... )
            >>> assert "all_shortest_paths" in query
        """
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Source must be non-empty string")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Target must be non-empty string")

        filters = filters or PathFilterConfig()
        filters.validate()

        # Build relationship pattern
        rel_pattern = relationship if relationship else ""

        # Build base query
        query = f"all_shortest_paths (({source})-[{rel_pattern}]->({target}))"

        # Add path length constraints
        if filters.max_path_length is not None:
            query += f" | where array_length(path) <= {filters.max_path_length}"

        if filters.min_path_length is not None:
            query += f" | where array_length(path) >= {filters.min_path_length}"

        # Add node filters
        if filters.node_filter:
            query += f" | where {filters.node_filter}"

        # Add result limits
        if max_paths is not None:
            if max_paths <= 0:
                raise ValueError("max_paths must be positive")
            query += f" | limit {max_paths}"

        return query

    def translate_all_paths(
        self,
        source: str,
        target: str,
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
        filters: Optional[PathFilterConfig] = None,
        enumeration: Optional[PathEnumerationConfig] = None,
    ) -> str:
        """Translate allPaths() to enumerate all paths.

        Enumerates all paths of variable length between source and target.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Optional relationship type
            max_length: Maximum path length (hops)
            filters: Path filter configuration
            enumeration: Path enumeration configuration

        Returns:
            KQL query for path enumeration

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> query = translator.translate_all_paths(
            ...     "n", "m", "KNOWS", max_length=5
            ... )
        """
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Source must be non-empty string")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Target must be non-empty string")

        filters = filters or PathFilterConfig()
        filters.validate()

        enumeration = enumeration or PathEnumerationConfig()
        enumeration.validate()

        if max_length is None:
            max_length = enumeration.max_depth

        if max_length <= 0:
            raise ValueError("max_length must be positive")

        # Build relationship pattern with length constraint
        if relationship:
            rel_pattern = f"[{relationship}*1..{max_length}]"
        else:
            rel_pattern = f"[*1..{max_length}]"

        # Build base query
        query = f"all_paths (({source})-{rel_pattern}->({target}))"

        # Add filters
        if filters.max_path_length is not None:
            query += f" | where array_length(path) <= {filters.max_path_length}"

        if filters.min_path_length is not None:
            query += f" | where array_length(path) >= {filters.min_path_length}"

        if filters.node_filter:
            query += f" | where {filters.node_filter}"

        if filters.relationship_filter:
            query += f" | where {filters.relationship_filter}"

        # Add cycle detection if enabled - use 'no_cycles' in filter
        if enumeration.cycle_detection:
            query += " | where no_cycles"

        # Add result limits
        if enumeration.max_paths is not None:
            query += f" | limit {enumeration.max_paths}"

        return query

    def translate_filtered_paths(
        self,
        source: str,
        target: str,
        filters: PathFilterConfig,
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """Translate path query with comprehensive filters.

        Args:
            source: Source node variable
            target: Target node variable
            filters: Path filter configuration
            relationship: Optional relationship type
            max_length: Optional maximum path length

        Returns:
            KQL query with path filters

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> filters = PathFilterConfig(
            ...     max_path_length=5,
            ...     excluded_nodes=["intermediary_node"]
            ... )
            >>> query = translator.translate_filtered_paths(
            ...     "n", "m", filters, "KNOWS"
            ... )
        """
        filters.validate()

        if max_length is None:
            max_length = 10

        # Build base query
        if relationship:
            rel_pattern = f"[{relationship}*1..{max_length}]"
        else:
            rel_pattern = f"[*1..{max_length}]"

        query = f"all_paths (({source})-{rel_pattern}->({target}))"

        # Build where clause for filters
        where_conditions = []

        if filters.max_path_length is not None:
            where_conditions.append(f"array_length(path) <= {filters.max_path_length}")

        if filters.min_path_length is not None:
            where_conditions.append(f"array_length(path) >= {filters.min_path_length}")

        if filters.excluded_nodes:
            excluded_str = ", ".join(f'"{node}"' for node in filters.excluded_nodes)
            where_conditions.append(
                f"not (any_element(path_nodes) in ({excluded_str}))"
            )

        if filters.excluded_relationships:
            excluded_str = ", ".join(
                f'"{rel}"' for rel in filters.excluded_relationships
            )
            where_conditions.append(
                f"not (any_element(path_relationships) in ({excluded_str}))"
            )

        if filters.node_filter:
            where_conditions.append(f"({filters.node_filter})")

        if filters.relationship_filter:
            where_conditions.append(f"({filters.relationship_filter})")

        # Combine conditions
        if where_conditions:
            combined_conditions = " and ".join(where_conditions)
            query += f" | where {combined_conditions}"

        return query

    def translate_path_with_node_constraints(
        self,
        source: str,
        target: str,
        node_constraints: Dict[str, str],
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """Translate paths with constraints on nodes in the path.

        Args:
            source: Source node variable
            target: Target node variable
            node_constraints: Dict mapping node variables to filter expressions
            relationship: Optional relationship type
            max_length: Optional maximum path length

        Returns:
            KQL query with node constraints

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> constraints = {"n": "n.status='active'", "m": "m.type='Person'"}
            >>> query = translator.translate_path_with_node_constraints(
            ...     "source", "target", constraints, "KNOWS"
            ... )
        """
        if not node_constraints or not isinstance(node_constraints, dict):
            raise ValueError("node_constraints must be non-empty dictionary")

        if max_length is None:
            max_length = 10

        # Build relationship pattern
        if relationship:
            rel_pattern = f"[{relationship}*1..{max_length}]"
        else:
            rel_pattern = f"[*1..{max_length}]"

        # Build base query
        query = f"all_paths (({source})-{rel_pattern}->({target}))"

        # Build constraints for each node
        constraint_expressions = []
        for node_var, constraint in node_constraints.items():
            constraint_expressions.append(f"({node_var} | {constraint})")

        if constraint_expressions:
            combined = " and ".join(constraint_expressions)
            query += f" | where {combined}"

        return query

    def translate_path_with_property_constraints(
        self,
        source: str,
        target: str,
        property_constraints: Dict[str, Any],
        relationship: Optional[str] = None,
        max_length: Optional[int] = None,
    ) -> str:
        """Translate paths with constraints on relationship properties.

        Args:
            source: Source node variable
            target: Target node variable
            property_constraints: Dict mapping property names to filter expressions
            relationship: Optional relationship type
            max_length: Optional maximum path length

        Returns:
            KQL query with property constraints

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> constraints = {"weight": "> 10", "confidence": ">= 0.8"}
            >>> query = translator.translate_path_with_property_constraints(
            ...     "n", "m", constraints, "KNOWS"
            ... )
        """
        if not property_constraints or not isinstance(property_constraints, dict):
            raise ValueError("property_constraints must be non-empty dictionary")

        if max_length is None:
            max_length = 10

        # Build relationship pattern
        if relationship:
            rel_pattern = f"[{relationship}*1..{max_length}]"
        else:
            rel_pattern = f"[*1..{max_length}]"

        # Build base query
        query = f"all_paths (({source})-{rel_pattern}->({target}))"

        # Build property constraints
        property_expressions = []
        for prop_name, constraint in property_constraints.items():
            property_expressions.append(f"relationship.{prop_name} {constraint}")

        if property_expressions:
            combined = " and ".join(property_expressions)
            query += f" | where {combined}"

        return query

    def translate_variable_length_path_with_filter(
        self,
        source: str,
        target: str,
        min_length: int = 1,
        max_length: int = 10,
        relationship: Optional[str] = None,
        filters: Optional[PathFilterConfig] = None,
    ) -> str:
        """Translate variable-length paths with comprehensive filtering.

        Args:
            source: Source node variable
            target: Target node variable
            min_length: Minimum path length
            max_length: Maximum path length
            relationship: Optional relationship type
            filters: Additional path filters

        Returns:
            KQL query for filtered variable-length paths

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> query = translator.translate_variable_length_path_with_filter(
            ...     "n", "m", min_length=2, max_length=5, relationship="KNOWS"
            ... )
        """
        if min_length < 0 or max_length < 0 or min_length > max_length:
            raise ValueError("Invalid path length range")

        filters = filters or PathFilterConfig()
        filters.validate()

        # Build relationship pattern
        if relationship:
            rel_pattern = f"[{relationship}*{min_length}..{max_length}]"
        else:
            rel_pattern = f"[*{min_length}..{max_length}]"

        # Build base query
        query = f"graph-match (({source})-{rel_pattern}->({target}))"

        # Add filters
        if filters.max_path_length is not None:
            query += f" | where path_length <= {filters.max_path_length}"

        if filters.node_filter:
            query += f" | where {filters.node_filter}"

        if filters.relationship_filter:
            query += f" | where {filters.relationship_filter}"

        return query

    def build_combined_path_query(
        self,
        source: str,
        target: str,
        algorithm: str = "shortest",
        relationship: Optional[str] = None,
        constraints: Optional[PathConstraint] = None,
        filters: Optional[PathFilterConfig] = None,
    ) -> str:
        """Build combined path query with specified algorithm and constraints.

        Args:
            source: Source node variable
            target: Target node variable
            algorithm: Algorithm type ("shortest", "all_shortest", "all")
            relationship: Optional relationship type
            constraints: Path constraints
            filters: Path filters

        Returns:
            Combined KQL query

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> translator = PathAlgorithmTranslator()
            >>> query = translator.build_combined_path_query(
            ...     "n", "m", algorithm="shortest"
            ... )
        """
        if algorithm not in self.path_operators:
            raise ValueError(
                f"Unknown algorithm: {algorithm}. "
                f"Must be one of {list(self.path_operators.keys())}"
            )

        if algorithm == "shortest":
            return self._build_shortest_query(
                source, target, relationship, constraints
            )
        elif algorithm == "all_shortest":
            return self.translate_all_shortest_paths(
                source, target, relationship, filters
            )
        else:  # all
            return self.translate_all_paths(
                source, target, relationship, constraints.max_length if constraints else None, filters
            )

    def _build_shortest_query(
        self,
        source: str,
        target: str,
        relationship: Optional[str],
        constraints: Optional[PathConstraint],
    ) -> str:
        """Build shortest path query.

        Args:
            source: Source node variable
            target: Target node variable
            relationship: Optional relationship type
            constraints: Path constraints

        Returns:
            Shortest path query
        """
        constraints = constraints or PathConstraint()
        rel_pattern = relationship if relationship else ""

        query = f"graph-shortest-paths (({source})-[{rel_pattern}]->({target}))"

        if constraints.weighted and constraints.weight_property:
            query += f" with weight({constraints.weight_property})"

        if constraints.max_length is not None:
            query += f" | where path_length <= {constraints.max_length}"

        return query
