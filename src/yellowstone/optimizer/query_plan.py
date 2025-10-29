"""
Query plan data structures and cost estimation for KQL optimization.

This module defines the query plan representation used by the optimizer to model
and estimate the cost of various execution strategies. Plans are built from
PlanNode objects arranged in a tree structure.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from ..parser.ast_nodes import Query, PathExpression, NodePattern, RelationshipPattern


class NodeType(Enum):
    """Types of nodes in a query execution plan."""
    SCAN = "scan"  # Table/entity scan
    FILTER = "filter"  # WHERE clause filtering
    JOIN = "join"  # Relationship join
    PROJECT = "project"  # RETURN clause projection
    AGGREGATE = "aggregate"  # Aggregation operations
    SORT = "sort"  # ORDER BY operations
    LIMIT = "limit"  # LIMIT/SKIP operations
    GRAPH_MATCH = "graph_match"  # Graph pattern matching


class JoinType(Enum):
    """Types of join operations."""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    CROSS = "cross"


@dataclass
class CostEstimate:
    """Estimated cost for a query plan node.

    Attributes:
        estimated_rows: Estimated number of rows produced
        estimated_time_ms: Estimated execution time in milliseconds
        estimated_memory_mb: Estimated memory usage in megabytes
        selectivity: Selectivity factor (0.0-1.0), fraction of rows passing filter
        confidence: Confidence in the estimate (0.0-1.0)
    """
    estimated_rows: int
    estimated_time_ms: float
    estimated_memory_mb: float
    selectivity: float = 1.0
    confidence: float = 0.8

    def __add__(self, other: 'CostEstimate') -> 'CostEstimate':
        """Combine two cost estimates (sum costs)."""
        return CostEstimate(
            estimated_rows=max(self.estimated_rows, other.estimated_rows),
            estimated_time_ms=self.estimated_time_ms + other.estimated_time_ms,
            estimated_memory_mb=self.estimated_memory_mb + other.estimated_memory_mb,
            selectivity=self.selectivity * other.selectivity,
            confidence=min(self.confidence, other.confidence)
        )

    def __mul__(self, factor: float) -> 'CostEstimate':
        """Scale cost estimate by a factor."""
        return CostEstimate(
            estimated_rows=int(self.estimated_rows * factor),
            estimated_time_ms=self.estimated_time_ms * factor,
            estimated_memory_mb=self.estimated_memory_mb * factor,
            selectivity=self.selectivity,
            confidence=self.confidence
        )


class PlanNode(ABC):
    """Abstract base class for query plan nodes.

    A plan node represents a single operation in the query execution plan.
    Nodes form a tree structure with parent-child relationships.
    """

    def __init__(self, node_type: NodeType):
        """Initialize plan node.

        Args:
            node_type: The type of operation this node represents
        """
        self.node_type = node_type
        self.children: list[PlanNode] = []
        self.cost: Optional[CostEstimate] = None
        self.metadata: dict[str, Any] = {}

    @abstractmethod
    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate the cost of executing this node.

        Args:
            input_rows: Number of input rows (from child nodes or table)

        Returns:
            Cost estimate for this operation
        """
        pass

    def add_child(self, child: 'PlanNode') -> None:
        """Add a child node to this plan node.

        Args:
            child: Child plan node to add
        """
        self.children.append(child)

    def __repr__(self) -> str:
        """Return string representation of plan node."""
        return f"{self.__class__.__name__}(type={self.node_type.value})"


class ScanNode(PlanNode):
    """Represents a table or entity scan operation.

    Attributes:
        table_name: Name of the table/entity to scan
        filter_predicate: Optional filter predicate applied during scan
        estimated_table_size: Estimated number of rows in table
    """

    def __init__(
        self,
        table_name: str,
        filter_predicate: Optional[str] = None,
        estimated_table_size: int = 10000
    ):
        """Initialize scan node.

        Args:
            table_name: Name of table to scan
            filter_predicate: Optional filter to apply during scan
            estimated_table_size: Estimated number of rows in table
        """
        super().__init__(NodeType.SCAN)
        self.table_name = table_name
        self.filter_predicate = filter_predicate
        self.estimated_table_size = estimated_table_size

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of scanning the table.

        Full table scans are expensive. Cost is proportional to table size.

        Args:
            input_rows: Unused for scan nodes

        Returns:
            Cost estimate for the scan operation
        """
        # Base cost: 0.1ms per 1000 rows
        time_ms = (self.estimated_table_size / 1000) * 0.1

        # Memory: assume 1KB per row on average
        memory_mb = (self.estimated_table_size * 1024) / (1024 * 1024)

        # If we have a filter predicate, apply selectivity
        selectivity = 0.5 if self.filter_predicate else 1.0
        output_rows = int(self.estimated_table_size * selectivity)

        self.cost = CostEstimate(
            estimated_rows=output_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=selectivity,
            confidence=0.7
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ScanNode(table={self.table_name}, rows~{self.estimated_table_size})"


class FilterNode(PlanNode):
    """Represents a filter operation (WHERE clause).

    Attributes:
        predicate: Filter predicate expression
        selectivity: Expected fraction of rows passing filter (0.0-1.0)
    """

    def __init__(self, predicate: str, selectivity: float = 0.5):
        """Initialize filter node.

        Args:
            predicate: Filter predicate expression
            selectivity: Expected selectivity (default 0.5)
        """
        super().__init__(NodeType.FILTER)
        self.predicate = predicate
        self.selectivity = selectivity

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of filtering.

        Filtering is relatively cheap - mainly CPU cost to evaluate predicates.

        Args:
            input_rows: Number of input rows to filter

        Returns:
            Cost estimate for the filter operation
        """
        # Cost: 0.01ms per 1000 rows
        time_ms = (input_rows / 1000) * 0.01

        # Memory: minimal overhead
        memory_mb = 0.1

        output_rows = int(input_rows * self.selectivity)

        self.cost = CostEstimate(
            estimated_rows=output_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=self.selectivity,
            confidence=0.8
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        return f"FilterNode(predicate={self.predicate}, sel={self.selectivity:.2f})"


class JoinNode(PlanNode):
    """Represents a join operation.

    Attributes:
        join_type: Type of join (inner, left, right, cross)
        join_condition: Join condition expression
        left_cardinality: Estimated rows from left input
        right_cardinality: Estimated rows from right input
    """

    def __init__(
        self,
        join_type: JoinType,
        join_condition: str,
        left_cardinality: int = 1000,
        right_cardinality: int = 1000
    ):
        """Initialize join node.

        Args:
            join_type: Type of join operation
            join_condition: Join condition
            left_cardinality: Estimated rows from left side
            right_cardinality: Estimated rows from right side
        """
        super().__init__(NodeType.JOIN)
        self.join_type = join_type
        self.join_condition = join_condition
        self.left_cardinality = left_cardinality
        self.right_cardinality = right_cardinality

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of join operation.

        Join cost depends on cardinalities of both inputs and join type.

        Args:
            input_rows: Unused (we use left/right cardinality)

        Returns:
            Cost estimate for the join operation
        """
        # Cost model: time proportional to product of cardinalities
        # Assume hash join: O(left + right) with constant factor
        time_ms = ((self.left_cardinality + self.right_cardinality) / 1000) * 0.5

        # For cross joins, much more expensive
        if self.join_type == JoinType.CROSS:
            time_ms *= 10
            output_rows = self.left_cardinality * self.right_cardinality
        else:
            # Assume join reduces size (selectivity ~0.1)
            output_rows = int(max(self.left_cardinality, self.right_cardinality) * 0.1)

        # Memory: need to hold hash table for smaller side
        memory_mb = (min(self.left_cardinality, self.right_cardinality) * 1024) / (1024 * 1024)

        self.cost = CostEstimate(
            estimated_rows=output_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=0.1,
            confidence=0.6
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        return f"JoinNode(type={self.join_type.value}, left={self.left_cardinality}, right={self.right_cardinality})"


class ProjectNode(PlanNode):
    """Represents a projection operation (SELECT/RETURN clause).

    Attributes:
        columns: List of columns/expressions to project
    """

    def __init__(self, columns: list[str]):
        """Initialize project node.

        Args:
            columns: List of columns to project
        """
        super().__init__(NodeType.PROJECT)
        self.columns = columns

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of projection.

        Projection is very cheap - just selecting columns.

        Args:
            input_rows: Number of input rows

        Returns:
            Cost estimate for the projection operation
        """
        # Cost: 0.001ms per 1000 rows
        time_ms = (input_rows / 1000) * 0.001

        # Memory: minimal
        memory_mb = 0.01

        self.cost = CostEstimate(
            estimated_rows=input_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=1.0,
            confidence=0.95
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ProjectNode(columns={len(self.columns)})"


class AggregateNode(PlanNode):
    """Represents an aggregation operation (GROUP BY, COUNT, SUM, etc.).

    Attributes:
        group_by: List of grouping columns
        aggregates: List of aggregate functions
    """

    def __init__(self, group_by: list[str], aggregates: list[str]):
        """Initialize aggregate node.

        Args:
            group_by: Columns to group by
            aggregates: Aggregate functions to compute
        """
        super().__init__(NodeType.AGGREGATE)
        self.group_by = group_by
        self.aggregates = aggregates

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of aggregation.

        Aggregation requires sorting or hashing, relatively expensive.

        Args:
            input_rows: Number of input rows

        Returns:
            Cost estimate for the aggregation operation
        """
        # Cost: 0.1ms per 1000 rows
        time_ms = (input_rows / 1000) * 0.1

        # Output rows depend on grouping cardinality
        # Assume ~10% unique groups
        output_rows = max(1, int(input_rows * 0.1))

        # Memory: need to hold intermediate aggregates
        memory_mb = (input_rows * 512) / (1024 * 1024)

        self.cost = CostEstimate(
            estimated_rows=output_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=0.1,
            confidence=0.7
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        return f"AggregateNode(group_by={len(self.group_by)}, aggs={len(self.aggregates)})"


class GraphMatchNode(PlanNode):
    """Represents a graph pattern matching operation.

    This is specific to KQL's graph-match operator.

    Attributes:
        pattern: The graph pattern to match
        num_hops: Number of relationship hops
        has_variable_length: Whether pattern has variable-length paths
    """

    def __init__(
        self,
        pattern: str,
        num_hops: int = 1,
        has_variable_length: bool = False
    ):
        """Initialize graph match node.

        Args:
            pattern: Graph pattern expression
            num_hops: Number of relationship hops
            has_variable_length: Whether pattern has variable-length paths
        """
        super().__init__(NodeType.GRAPH_MATCH)
        self.pattern = pattern
        self.num_hops = num_hops
        self.has_variable_length = has_variable_length

    def estimate_cost(self, input_rows: int = 1000) -> CostEstimate:
        """Estimate cost of graph matching.

        Graph matching cost grows exponentially with number of hops.
        Variable-length paths are very expensive.

        Args:
            input_rows: Number of input rows

        Returns:
            Cost estimate for the graph match operation
        """
        # Base cost per hop
        base_cost = 1.0  # ms per 1000 rows

        # Cost grows with hops
        hop_factor = 2 ** self.num_hops
        time_ms = (input_rows / 1000) * base_cost * hop_factor

        # Variable-length paths are much more expensive
        if self.has_variable_length:
            time_ms *= 5

        # Output rows: assume each node matches ~10 neighbors per hop
        output_rows = int(input_rows * (10 ** self.num_hops))

        # Memory: need to hold intermediate paths
        memory_mb = (output_rows * 2048) / (1024 * 1024)

        self.cost = CostEstimate(
            estimated_rows=output_rows,
            estimated_time_ms=time_ms,
            estimated_memory_mb=memory_mb,
            selectivity=10 ** self.num_hops,
            confidence=0.5 if self.has_variable_length else 0.7
        )
        return self.cost

    def __repr__(self) -> str:
        """Return string representation."""
        var_len = ", var_len" if self.has_variable_length else ""
        return f"GraphMatchNode(hops={self.num_hops}{var_len})"


@dataclass
class QueryPlan:
    """Represents a complete query execution plan.

    Attributes:
        root: Root node of the plan tree
        original_query: Original Cypher query AST
        metadata: Additional plan metadata
        total_cost: Total estimated cost of the plan
    """
    root: PlanNode
    original_query: Query
    metadata: dict[str, Any] = field(default_factory=dict)
    total_cost: Optional[CostEstimate] = None

    def estimate_total_cost(self) -> CostEstimate:
        """Calculate total cost for the entire plan.

        Traverses the plan tree bottom-up, computing costs for each node.

        Returns:
            Total cost estimate for the entire plan
        """
        self.total_cost = self._estimate_node_cost(self.root, input_rows=10000)
        return self.total_cost

    def _estimate_node_cost(self, node: PlanNode, input_rows: int) -> CostEstimate:
        """Recursively estimate cost for a node and its children.

        Args:
            node: Plan node to estimate
            input_rows: Number of input rows to this node

        Returns:
            Cost estimate for this node and all descendants
        """
        if not node.children:
            # Leaf node - just estimate its cost
            return node.estimate_cost(input_rows)

        # Estimate children first
        child_costs = []
        current_rows = input_rows

        for child in node.children:
            child_cost = self._estimate_node_cost(child, current_rows)
            child_costs.append(child_cost)
            # Output of this child becomes input to next
            current_rows = child_cost.estimated_rows

        # Estimate this node's cost based on child outputs
        node_cost = node.estimate_cost(current_rows)

        # Total cost is sum of child costs plus this node
        total_cost = node_cost
        for child_cost in child_costs:
            total_cost = total_cost + child_cost

        return total_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert plan to dictionary representation.

        Returns:
            Dictionary representation of the plan
        """
        return {
            "root": self._node_to_dict(self.root),
            "total_cost": {
                "estimated_rows": self.total_cost.estimated_rows if self.total_cost else 0,
                "estimated_time_ms": self.total_cost.estimated_time_ms if self.total_cost else 0,
                "estimated_memory_mb": self.total_cost.estimated_memory_mb if self.total_cost else 0,
                "confidence": self.total_cost.confidence if self.total_cost else 0,
            } if self.total_cost else None,
            "metadata": self.metadata
        }

    def _node_to_dict(self, node: PlanNode) -> dict[str, Any]:
        """Convert a plan node to dictionary.

        Args:
            node: Plan node to convert

        Returns:
            Dictionary representation of the node
        """
        result = {
            "type": node.node_type.value,
            "class": node.__class__.__name__,
            "cost": {
                "estimated_rows": node.cost.estimated_rows if node.cost else 0,
                "estimated_time_ms": node.cost.estimated_time_ms if node.cost else 0,
            } if node.cost else None,
            "children": [self._node_to_dict(child) for child in node.children]
        }

        # Add node-specific fields
        if isinstance(node, ScanNode):
            result["table_name"] = node.table_name
            result["filter_predicate"] = node.filter_predicate
        elif isinstance(node, FilterNode):
            result["predicate"] = node.predicate
            result["selectivity"] = node.selectivity
        elif isinstance(node, JoinNode):
            result["join_type"] = node.join_type.value
            result["join_condition"] = node.join_condition
        elif isinstance(node, ProjectNode):
            result["columns"] = node.columns
        elif isinstance(node, GraphMatchNode):
            result["pattern"] = node.pattern
            result["num_hops"] = node.num_hops

        return result

    def __str__(self) -> str:
        """Return string representation of the plan."""
        lines = ["QueryPlan:"]
        self._format_node(self.root, lines, indent=1)
        if self.total_cost:
            lines.append(f"\nTotal Cost: {self.total_cost.estimated_time_ms:.2f}ms, "
                        f"{self.total_cost.estimated_rows} rows")
        return "\n".join(lines)

    def _format_node(self, node: PlanNode, lines: list[str], indent: int) -> None:
        """Format a node for string representation.

        Args:
            node: Node to format
            lines: List of output lines
            indent: Current indentation level
        """
        prefix = "  " * indent
        cost_str = ""
        if node.cost:
            cost_str = f" [{node.cost.estimated_time_ms:.2f}ms, {node.cost.estimated_rows} rows]"
        lines.append(f"{prefix}{repr(node)}{cost_str}")

        for child in node.children:
            self._format_node(child, lines, indent + 1)
