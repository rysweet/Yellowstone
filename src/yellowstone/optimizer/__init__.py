"""
Query Optimizer module for Yellowstone.

This module provides query optimization capabilities including AST analysis,
optimization rule application, query plan generation, and cost estimation.
"""

from .query_optimizer import QueryOptimizer, optimize, OptimizedQuery, OptimizationMetrics
from .query_plan import (
    QueryPlan, PlanNode, CostEstimate,
    ScanNode, FilterNode, JoinNode, ProjectNode, AggregateNode, GraphMatchNode,
    NodeType, JoinType
)
from .optimization_rules import (
    OptimizationRule, OptimizationResult,
    FilterPushdownRule, JoinOrderRule, TimeRangeRule,
    PredicatePushdownRule, IndexHintRule
)

__all__ = [
    # Main optimizer interface
    "QueryOptimizer",
    "optimize",
    "OptimizedQuery",
    "OptimizationMetrics",

    # Query plan components
    "QueryPlan",
    "PlanNode",
    "CostEstimate",
    "ScanNode",
    "FilterNode",
    "JoinNode",
    "ProjectNode",
    "AggregateNode",
    "GraphMatchNode",
    "NodeType",
    "JoinType",

    # Optimization rules
    "OptimizationRule",
    "OptimizationResult",
    "FilterPushdownRule",
    "JoinOrderRule",
    "TimeRangeRule",
    "PredicatePushdownRule",
    "IndexHintRule",
]
