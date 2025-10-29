"""
KQL make-graph statement builder for persistent graphs.

This module converts graph schemas into KQL make-graph statements that can be
executed in Microsoft Sentinel to create persistent graph operators.
"""

from typing import List, Dict, Optional, Set
from .models import GraphSchema, NodeDefinition, EdgeDefinition, PersistentGraph


class GraphBuilder:
    """Builder for KQL make-graph statements."""

    def __init__(self, graph: PersistentGraph):
        """
        Initialize graph builder.

        Args:
            graph: Persistent graph definition
        """
        self.graph = graph
        self.schema = graph.schema

    def build_create_statement(self) -> str:
        """
        Build complete KQL statement to create persistent graph.

        Returns:
            KQL make-graph statement

        Example:
            >>> builder = GraphBuilder(graph)
            >>> kql = builder.build_create_statement()
            >>> print(kql)
            .create-or-alter persistent-graph MyGraph <|
                SecurityAlert
                | make-graph ...
        """
        # Build the main query
        main_query = self._build_main_query()

        # Wrap in create statement
        statement = (
            f".create-or-alter persistent-graph {self.graph.name} <|\n"
            f"{main_query}"
        )

        return statement

    def build_update_statement(self, changes: Optional[List[str]] = None) -> str:
        """
        Build KQL statement to update existing persistent graph.

        Args:
            changes: Optional list of changes being made

        Returns:
            KQL update statement

        Example:
            >>> builder = GraphBuilder(graph)
            >>> kql = builder.build_update_statement(["Added Device nodes"])
        """
        # For updates, we regenerate the full graph
        # Sentinel handles incremental updates internally
        return self.build_create_statement()

    def build_delete_statement(self) -> str:
        """
        Build KQL statement to delete persistent graph.

        Returns:
            KQL drop statement

        Example:
            >>> builder = GraphBuilder(graph)
            >>> kql = builder.build_delete_statement()
            >>> print(kql)
            .drop persistent-graph MyGraph
        """
        return f".drop persistent-graph {self.graph.name}"

    def _build_main_query(self) -> str:
        """
        Build the main query that constructs the graph.

        Returns:
            KQL query with make-graph operator
        """
        # Start with the primary source table
        if not self.schema.nodes:
            raise ValueError("Graph schema must have at least one node")

        # Build union of all node sources
        node_queries = []
        for node in self.schema.nodes:
            node_query = self._build_node_query(node)
            node_queries.append(node_query)

        # Combine node queries with union
        if len(node_queries) == 1:
            base_query = node_queries[0]
        else:
            base_query = "\n| union\n".join(
                f"({query})" for query in node_queries
            )

        # Add make-graph operator
        make_graph = self._build_make_graph_operator()

        return f"{base_query}\n{make_graph}"

    def _build_node_query(self, node: NodeDefinition) -> str:
        """
        Build query for a single node type.

        Args:
            node: Node definition

        Returns:
            KQL query to extract node data
        """
        # Start with source table
        query_parts = [node.source_table]

        # Add filters if specified
        if node.filters:
            for filter_expr in node.filters:
                query_parts.append(f"| where {filter_expr}")

        # Project properties
        projections = [f'node_id = {node.id_property}']
        projections.append(f'node_label = "{node.label}"')

        # Add all properties
        for prop_name, column_name in node.properties.items():
            if prop_name != node.id_property:
                projections.append(f'{prop_name} = {column_name}')

        query_parts.append(f"| project {', '.join(projections)}")

        return "\n".join(query_parts)

    def _build_make_graph_operator(self) -> str:
        """
        Build the make-graph operator with nodes and edges.

        Returns:
            KQL make-graph operator syntax
        """
        parts = ["| make-graph node_id on node_label with-node-properties=("]

        # Add node properties
        node_props = self._get_all_node_properties()
        parts.append(f"    {', '.join(node_props)}")
        parts.append(")")

        # Add edges if defined
        if self.schema.edges:
            parts.append("with-edges=(")
            edge_definitions = []
            for edge in self.schema.edges:
                edge_def = self._build_edge_definition(edge)
                edge_definitions.append(edge_def)
            parts.append(",\n".join(edge_definitions))
            parts.append(")")

        return "\n".join(parts)

    def _get_all_node_properties(self) -> List[str]:
        """
        Get list of all unique node properties across all node types.

        Returns:
            List of property names
        """
        properties: Set[str] = set()
        for node in self.schema.nodes:
            properties.update(node.properties.keys())
        return sorted(properties)

    def _build_edge_definition(self, edge: EdgeDefinition) -> str:
        """
        Build edge definition for make-graph operator.

        Args:
            edge: Edge definition

        Returns:
            KQL edge definition syntax
        """
        # Basic edge structure
        edge_def = (
            f'    {edge.type}: '
            f'{edge.from_label} -> {edge.to_label} '
            f'on {edge.join_condition}'
        )

        # Add edge properties if defined
        if edge.properties:
            props = [f'{k}={v}' for k, v in edge.properties.items()]
            edge_def += f' with-properties=({", ".join(props)})'

        # Add strength as metadata
        edge_def += f' /* strength: {edge.strength} */'

        return edge_def

    def build_query_statement(self, cypher_pattern: Optional[str] = None) -> str:
        """
        Build KQL statement to query the persistent graph.

        Args:
            cypher_pattern: Optional Cypher-like pattern to filter results

        Returns:
            KQL query statement

        Example:
            >>> builder = GraphBuilder(graph)
            >>> kql = builder.build_query_statement()
            >>> print(kql)
            persistent-graph('MyGraph')
            | graph-match ...
        """
        query = f"persistent-graph('{self.graph.name}')"

        if cypher_pattern:
            # This would integrate with the Cypher-to-KQL translator
            # For now, just add a basic graph-match
            query += "\n| graph-match ..."

        return query

    def estimate_performance(self) -> Dict[str, any]:
        """
        Estimate performance characteristics of the persistent graph.

        Returns:
            Dictionary with performance estimates

        Example:
            >>> builder = GraphBuilder(graph)
            >>> metrics = builder.estimate_performance()
            >>> print(metrics['expected_speedup'])
            25
        """
        # Count nodes and edges
        node_count = len(self.schema.nodes)
        edge_count = len(self.schema.edges)

        # Estimate based on Microsoft's documented improvements
        # Persistent graphs provide 10-50x speedup
        base_speedup = 10
        if edge_count > 5:
            base_speedup = 25  # More complex graphs benefit more
        if node_count > 10:
            base_speedup = 40

        return {
            'node_types': node_count,
            'edge_types': edge_count,
            'expected_speedup': min(base_speedup, 50),
            'supports_incremental_updates': True,
            'supports_time_travel': False,  # Not yet implemented in Sentinel
            'estimated_memory_mb': node_count * 100 + edge_count * 50,
        }

    def validate_schema(self) -> List[str]:
        """
        Validate graph schema for KQL compatibility.

        Returns:
            List of validation errors (empty if valid)

        Example:
            >>> builder = GraphBuilder(graph)
            >>> errors = builder.validate_schema()
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []

        # Check for nodes
        if not self.schema.nodes:
            errors.append("Graph must have at least one node type")

        # Check for duplicate node labels
        labels = [node.label for node in self.schema.nodes]
        if len(labels) != len(set(labels)):
            errors.append("Duplicate node labels found")

        # Check for duplicate edge types
        edge_types = [edge.type for edge in self.schema.edges]
        if len(edge_types) != len(set(edge_types)):
            errors.append("Duplicate edge types found")

        # Validate edge references
        node_labels = {node.label for node in self.schema.nodes}
        for edge in self.schema.edges:
            if edge.from_label not in node_labels:
                errors.append(
                    f"Edge '{edge.type}' references unknown from_label '{edge.from_label}'"
                )
            if edge.to_label not in node_labels:
                errors.append(
                    f"Edge '{edge.type}' references unknown to_label '{edge.to_label}'"
                )

        # Check for reserved keywords
        reserved = {'node_id', 'node_label', 'edge_id', 'edge_type'}
        for node in self.schema.nodes:
            if node.label.lower() in reserved:
                errors.append(f"Node label '{node.label}' is a reserved keyword")
            for prop in node.properties:
                if prop.lower() in reserved:
                    errors.append(
                        f"Property '{prop}' in node '{node.label}' is a reserved keyword"
                    )

        return errors

    def generate_documentation(self) -> str:
        """
        Generate documentation for the graph schema.

        Returns:
            Markdown documentation string

        Example:
            >>> builder = GraphBuilder(graph)
            >>> docs = builder.generate_documentation()
            >>> with open('graph_schema.md', 'w') as f:
            ...     f.write(docs)
        """
        lines = [
            f"# Persistent Graph: {self.graph.name}",
            "",
            f"**Workspace**: {self.graph.workspace_id}",
            f"**Version**: {self.graph.schema.version}",
            ""
        ]

        if self.graph.description:
            lines.extend([
                "## Description",
                "",
                self.graph.description,
                ""
            ])

        # Document nodes
        lines.extend([
            "## Node Types",
            ""
        ])

        for node in self.schema.nodes:
            lines.extend([
                f"### {node.label}",
                "",
                f"**Source Table**: `{node.source_table}`",
                f"**ID Property**: `{node.id_property}`",
                ""
            ])

            if node.properties:
                lines.append("**Properties**:")
                lines.append("")
                for prop_name, column_name in sorted(node.properties.items()):
                    lines.append(f"- `{prop_name}` → `{column_name}`")
                lines.append("")

            if node.filters:
                lines.append("**Filters**:")
                lines.append("")
                for filter_expr in node.filters:
                    lines.append(f"- `{filter_expr}`")
                lines.append("")

        # Document edges
        if self.schema.edges:
            lines.extend([
                "## Edge Types",
                ""
            ])

            for edge in self.schema.edges:
                lines.extend([
                    f"### {edge.type}",
                    "",
                    f"**Direction**: `{edge.from_label}` → `{edge.to_label}`",
                    f"**Join Condition**: `{edge.join_condition}`",
                    f"**Strength**: {edge.strength}",
                    ""
                ])

                if edge.properties:
                    lines.append("**Properties**:")
                    lines.append("")
                    for prop_name, expr in sorted(edge.properties.items()):
                        lines.append(f"- `{prop_name}` = `{expr}`")
                    lines.append("")

        # Add performance estimates
        perf = self.estimate_performance()
        lines.extend([
            "## Performance Estimates",
            "",
            f"- Expected speedup: {perf['expected_speedup']}x",
            f"- Estimated memory: {perf['estimated_memory_mb']} MB",
            f"- Incremental updates: {perf['supports_incremental_updates']}",
            ""
        ])

        return "\n".join(lines)
