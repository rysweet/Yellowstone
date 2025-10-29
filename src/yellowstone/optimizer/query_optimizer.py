"""
Main query optimizer orchestrator.

This module provides the primary interface for optimizing Cypher queries.
It coordinates AST analysis, optimization rule application, and query plan
generation to produce optimized KQL queries.
"""

from dataclasses import dataclass, field
from typing import Optional
import time

from ..parser.ast_nodes import Query
from ..models import KQLQuery
from .query_plan import (
    QueryPlan, PlanNode, ScanNode, FilterNode, JoinNode,
    ProjectNode, GraphMatchNode, CostEstimate, NodeType
)
from .optimization_rules import (
    OptimizationRule, OptimizationResult,
    FilterPushdownRule, JoinOrderRule, TimeRangeRule,
    PredicatePushdownRule, IndexHintRule
)


@dataclass
class OptimizationMetrics:
    """Metrics tracking optimization process.

    Attributes:
        original_estimated_cost_ms: Estimated cost before optimization
        optimized_estimated_cost_ms: Estimated cost after optimization
        cost_reduction_ms: Reduction in estimated cost
        cost_reduction_percent: Percentage reduction in cost
        rules_applied: Number of optimization rules applied
        optimization_time_ms: Time spent optimizing
        rules_details: Details of each rule application
    """
    original_estimated_cost_ms: float
    optimized_estimated_cost_ms: float
    cost_reduction_ms: float
    cost_reduction_percent: float
    rules_applied: int
    optimization_time_ms: float
    rules_details: list[dict[str, any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, any]:
        """Convert metrics to dictionary.

        Returns:
            Dictionary representation of metrics
        """
        return {
            "original_estimated_cost_ms": self.original_estimated_cost_ms,
            "optimized_estimated_cost_ms": self.optimized_estimated_cost_ms,
            "cost_reduction_ms": self.cost_reduction_ms,
            "cost_reduction_percent": self.cost_reduction_percent,
            "rules_applied": self.rules_applied,
            "optimization_time_ms": self.optimization_time_ms,
            "rules_details": self.rules_details
        }


@dataclass
class OptimizedQuery:
    """Result of query optimization.

    Attributes:
        query: Optimized query AST
        plan: Query execution plan
        metrics: Optimization metrics
        kql_query: Generated KQL query string (if translated)
    """
    query: Query
    plan: QueryPlan
    metrics: OptimizationMetrics
    kql_query: Optional[str] = None


class QueryOptimizer:
    """Main query optimizer orchestrator.

    The optimizer analyzes Cypher query ASTs, applies optimization rules,
    generates query plans, and estimates costs to produce optimized queries.

    Example:
        >>> optimizer = QueryOptimizer()
        >>> optimized = optimizer.optimize(query_ast)
        >>> print(f"Cost reduced by {optimized.metrics.cost_reduction_percent}%")
    """

    def __init__(
        self,
        enable_filter_pushdown: bool = True,
        enable_join_order: bool = True,
        enable_time_range: bool = True,
        enable_predicate_pushdown: bool = True,
        enable_index_hints: bool = True,
        known_indexes: Optional[dict[str, list[str]]] = None
    ):
        """Initialize query optimizer with configuration.

        Args:
            enable_filter_pushdown: Enable filter pushdown optimization
            enable_join_order: Enable join order optimization
            enable_time_range: Enable time range injection for Sentinel
            enable_predicate_pushdown: Enable predicate pushdown into patterns
            enable_index_hints: Enable index hint suggestions
            known_indexes: Dictionary of known indexes (table -> columns)
        """
        self.rules: list[OptimizationRule] = []

        # Initialize optimization rules based on configuration
        if enable_filter_pushdown:
            self.rules.append(FilterPushdownRule())

        if enable_join_order:
            self.rules.append(JoinOrderRule())

        if enable_time_range:
            self.rules.append(TimeRangeRule())

        if enable_predicate_pushdown:
            self.rules.append(PredicatePushdownRule())

        if enable_index_hints:
            self.rules.append(IndexHintRule(known_indexes=known_indexes))

    def optimize(self, query: Query) -> OptimizedQuery:
        """Optimize a Cypher query.

        This is the main entry point for query optimization. It:
        1. Analyzes the query AST
        2. Generates initial query plan
        3. Applies optimization rules
        4. Generates optimized query plan
        5. Returns optimized query with metrics

        Args:
            query: Cypher query AST to optimize

        Returns:
            OptimizedQuery with optimized AST, plan, and metrics

        Raises:
            ValueError: If query is invalid
            TypeError: If input is not a Query AST node

        Example:
            >>> optimizer = QueryOptimizer()
            >>> optimized = optimizer.optimize(query_ast)
            >>> print(f"Cost: {optimized.plan.total_cost.estimated_time_ms}ms")
        """
        if not isinstance(query, Query):
            raise TypeError(f"Expected Query AST node, got {type(query)}")

        start_time = time.time()

        # Step 1: Analyze query structure
        analysis = self.analyze_query(query)

        # Step 2: Generate initial query plan
        initial_plan = self.generate_plan(query)
        initial_cost = initial_plan.estimate_total_cost()

        # Step 3: Apply optimization rules
        optimized_query = query
        total_cost_reduction = 0.0
        rules_applied = 0
        rules_details = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.applies_to(optimized_query):
                result = rule.apply(optimized_query)

                if result.applied:
                    rules_applied += 1
                    total_cost_reduction += result.cost_reduction
                    rules_details.append({
                        "rule": rule.name,
                        "description": result.description,
                        "cost_reduction_ms": result.cost_reduction
                    })

                    if result.modified_query:
                        optimized_query = result.modified_query

        # Step 4: Generate optimized query plan
        optimized_plan = self.generate_plan(optimized_query)
        optimized_cost = optimized_plan.estimate_total_cost()

        # Calculate actual cost reduction
        actual_cost_reduction = initial_cost.estimated_time_ms - optimized_cost.estimated_time_ms

        # Use the maximum of estimated and actual reduction
        final_cost_reduction = max(total_cost_reduction, actual_cost_reduction)

        cost_reduction_percent = 0.0
        if initial_cost.estimated_time_ms > 0:
            cost_reduction_percent = (final_cost_reduction / initial_cost.estimated_time_ms) * 100

        optimization_time_ms = (time.time() - start_time) * 1000

        # Build metrics
        metrics = OptimizationMetrics(
            original_estimated_cost_ms=initial_cost.estimated_time_ms,
            optimized_estimated_cost_ms=optimized_cost.estimated_time_ms,
            cost_reduction_ms=final_cost_reduction,
            cost_reduction_percent=cost_reduction_percent,
            rules_applied=rules_applied,
            optimization_time_ms=optimization_time_ms,
            rules_details=rules_details
        )

        return OptimizedQuery(
            query=optimized_query,
            plan=optimized_plan,
            metrics=metrics
        )

    def analyze_query(self, query: Query) -> dict[str, any]:
        """Analyze query structure and characteristics.

        Extracts metadata about the query structure to inform optimization
        decisions.

        Args:
            query: Query AST to analyze

        Returns:
            Dictionary with query characteristics:
            - num_nodes: Number of nodes in graph pattern
            - num_relationships: Number of relationships
            - num_hops: Total relationship hops
            - has_where_clause: Whether WHERE clause exists
            - num_conditions: Number of WHERE conditions
            - has_aggregation: Whether aggregation is used
            - has_sorting: Whether ORDER BY is present
            - has_limit: Whether LIMIT is present
            - complexity: Estimated complexity (Low/Medium/High)

        Example:
            >>> analysis = optimizer.analyze_query(query)
            >>> print(f"Query has {analysis['num_hops']} hops")
        """
        analysis = {
            "num_nodes": 0,
            "num_relationships": 0,
            "num_hops": 0,
            "has_where_clause": False,
            "num_conditions": 0,
            "has_aggregation": False,
            "has_sorting": False,
            "has_limit": False,
            "complexity": "Low"
        }

        # Analyze MATCH clause
        if query.match_clause:
            for path in query.match_clause.paths:
                analysis["num_nodes"] += len(path.nodes)
                analysis["num_relationships"] += len(path.relationships)
                analysis["num_hops"] += len(path.relationships)

        # Analyze WHERE clause
        if query.where_clause:
            analysis["has_where_clause"] = True
            analysis["num_conditions"] = self._count_conditions(query.where_clause.conditions)

        # Analyze RETURN clause
        if query.return_clause:
            analysis["has_aggregation"] = self._has_aggregation(query.return_clause)
            analysis["has_sorting"] = query.return_clause.order_by is not None
            analysis["has_limit"] = query.return_clause.limit is not None

        # Estimate complexity
        analysis["complexity"] = self._estimate_complexity(analysis)

        return analysis

    def generate_plan(self, query: Query) -> QueryPlan:
        """Generate query execution plan from AST.

        Creates a tree of PlanNode objects representing the query execution
        strategy.

        Args:
            query: Query AST to generate plan for

        Returns:
            QueryPlan with estimated costs

        Raises:
            ValueError: If query structure is invalid

        Example:
            >>> plan = optimizer.generate_plan(query)
            >>> print(plan)
        """
        if not query.match_clause:
            raise ValueError("Query must have MATCH clause")

        # Build plan tree bottom-up
        plan_nodes = []

        # Step 1: Create graph match nodes for each path
        for path in query.match_clause.paths:
            num_hops = len(path.relationships)
            has_var_length = any(
                rel.variable for rel in path.relationships
            )

            graph_node = GraphMatchNode(
                pattern=str(path),
                num_hops=num_hops,
                has_variable_length=has_var_length
            )
            plan_nodes.append(graph_node)

        # Step 2: Add filter nodes for WHERE clause
        if query.where_clause:
            # Extract filter predicates
            predicates = self._extract_predicates(query.where_clause)

            for predicate in predicates:
                selectivity = self._estimate_selectivity(predicate)
                filter_node = FilterNode(
                    predicate=str(predicate),
                    selectivity=selectivity
                )
                # Attach filter to last graph node
                if plan_nodes:
                    plan_nodes[-1].add_child(filter_node)
                else:
                    plan_nodes.append(filter_node)

        # Step 3: Add join nodes if multiple paths
        if len(plan_nodes) > 1:
            # Create join nodes to combine paths
            from .query_plan import JoinType

            left_node = plan_nodes[0]
            for right_node in plan_nodes[1:]:
                join_node = JoinNode(
                    join_type=JoinType.INNER,
                    join_condition="graph_join",
                    left_cardinality=1000,
                    right_cardinality=1000
                )
                join_node.add_child(left_node)
                join_node.add_child(right_node)
                left_node = join_node

            root_node = left_node
        else:
            root_node = plan_nodes[0] if plan_nodes else ScanNode("default")

        # Step 4: Add projection node for RETURN clause
        if query.return_clause:
            columns = [str(item) for item in query.return_clause.items]
            project_node = ProjectNode(columns=columns)
            project_node.add_child(root_node)
            root_node = project_node

        # Create query plan
        plan = QueryPlan(
            root=root_node,
            original_query=query,
            metadata={
                "generated_at": time.time(),
                "optimizer_version": "1.0.0"
            }
        )

        return plan

    def _count_conditions(self, conditions: dict[str, any]) -> int:
        """Count number of conditions in WHERE clause.

        Args:
            conditions: Conditions dictionary

        Returns:
            Count of condition nodes
        """
        if not conditions:
            return 0

        condition_type = conditions.get("type")

        if condition_type == "logical":
            operands = conditions.get("operands", [])
            return sum(self._count_conditions(op) for op in operands)
        elif condition_type in ("comparison", "function"):
            return 1
        else:
            return 0

    def _has_aggregation(self, return_clause) -> bool:
        """Check if RETURN clause has aggregation.

        Args:
            return_clause: ReturnClause to check

        Returns:
            True if aggregation is present
        """
        aggregation_funcs = {"COUNT", "SUM", "AVG", "MIN", "MAX", "COLLECT"}

        for item in return_clause.items:
            if isinstance(item, dict):
                if item.get("type") == "function":
                    func_name = item.get("name", "").upper()
                    if func_name in aggregation_funcs:
                        return True

        return False

    def _estimate_complexity(self, analysis: dict[str, any]) -> str:
        """Estimate query complexity.

        Args:
            analysis: Query analysis dictionary

        Returns:
            Complexity level: "Low", "Medium", or "High"
        """
        score = 0

        # Hops contribute to complexity
        score += min(analysis["num_hops"] * 2, 6)

        # Conditions add complexity
        score += min(analysis["num_conditions"], 4)

        # Aggregations add complexity
        if analysis["has_aggregation"]:
            score += 2

        # Sorting adds complexity
        if analysis["has_sorting"]:
            score += 1

        if score >= 8:
            return "High"
        elif score >= 4:
            return "Medium"
        else:
            return "Low"

    def _extract_predicates(self, where_clause) -> list[dict[str, any]]:
        """Extract individual predicates from WHERE clause.

        Args:
            where_clause: WhereClause to extract from

        Returns:
            List of predicate dictionaries
        """
        predicates = []

        def extract_condition(condition: dict[str, any]) -> None:
            """Recursively extract predicates."""
            if not condition:
                return

            cond_type = condition.get("type")

            if cond_type == "comparison":
                predicates.append(condition)
            elif cond_type == "logical":
                for operand in condition.get("operands", []):
                    extract_condition(operand)

        extract_condition(where_clause.conditions)
        return predicates

    def _estimate_selectivity(self, predicate: dict[str, any]) -> float:
        """Estimate selectivity of a predicate.

        Args:
            predicate: Predicate dictionary

        Returns:
            Selectivity estimate (0.0-1.0)
        """
        operator = predicate.get("operator", "")

        # Equality is very selective
        if operator in ("=", "=="):
            return 0.1

        # Range comparisons less selective
        if operator in ("<", ">", "<=", ">="):
            return 0.5

        # Other operators
        if operator in ("!=", "<>"):
            return 0.9

        # Default selectivity
        return 0.5

    def get_optimization_summary(self, optimized: OptimizedQuery) -> str:
        """Get human-readable optimization summary.

        Args:
            optimized: OptimizedQuery result

        Returns:
            Formatted summary string

        Example:
            >>> summary = optimizer.get_optimization_summary(optimized)
            >>> print(summary)
        """
        lines = []
        lines.append("=" * 60)
        lines.append("QUERY OPTIMIZATION SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        metrics = optimized.metrics

        lines.append(f"Original Estimated Cost: {metrics.original_estimated_cost_ms:.2f}ms")
        lines.append(f"Optimized Estimated Cost: {metrics.optimized_estimated_cost_ms:.2f}ms")
        lines.append(f"Cost Reduction: {metrics.cost_reduction_ms:.2f}ms ({metrics.cost_reduction_percent:.1f}%)")
        lines.append(f"Optimization Time: {metrics.optimization_time_ms:.2f}ms")
        lines.append(f"Rules Applied: {metrics.rules_applied}")
        lines.append("")

        if metrics.rules_details:
            lines.append("Optimization Rules Applied:")
            for i, rule in enumerate(metrics.rules_details, 1):
                lines.append(f"  {i}. {rule['rule']}")
                lines.append(f"     {rule['description']}")
                lines.append(f"     Cost Reduction: {rule['cost_reduction_ms']:.2f}ms")

        lines.append("")
        lines.append("Query Plan:")
        lines.append(str(optimized.plan))

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


def optimize(query: Query, **kwargs) -> OptimizedQuery:
    """Convenience function to optimize a single query.

    Args:
        query: Query AST to optimize
        **kwargs: Additional arguments passed to QueryOptimizer

    Returns:
        OptimizedQuery result

    Example:
        >>> from yellowstone.optimizer import optimize
        >>> optimized = optimize(query_ast)
        >>> print(f"Cost reduced by {optimized.metrics.cost_reduction_percent}%")
    """
    optimizer = QueryOptimizer(**kwargs)
    return optimizer.optimize(query)
