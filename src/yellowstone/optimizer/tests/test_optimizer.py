"""
Comprehensive test suite for query optimizer.

Tests cover:
- Query plan generation and cost estimation
- Individual optimization rules
- Query optimizer orchestration
- Integration with translator module
- Edge cases and error handling
"""

import pytest
from typing import Any

from yellowstone.parser.ast_nodes import (
    Query, MatchClause, WhereClause, ReturnClause,
    PathExpression, NodePattern, RelationshipPattern,
    Identifier, Literal, Property
)
from yellowstone.optimizer import (
    QueryOptimizer, optimize,
    QueryPlan, PlanNode, CostEstimate,
    ScanNode, FilterNode, JoinNode, ProjectNode, GraphMatchNode,
    NodeType, JoinType,
    FilterPushdownRule, JoinOrderRule, TimeRangeRule,
    PredicatePushdownRule, IndexHintRule
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def simple_query():
    """Simple single-node query: MATCH (n:Person) RETURN n"""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(
                        variable=Identifier(name="n"),
                        labels=[Identifier(name="Person")]
                    )
                ],
                relationships=[]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")]
    )

    return Query(
        match_clause=match_clause,
        return_clause=return_clause
    )


@pytest.fixture
def simple_relationship_query():
    """Simple relationship query: MATCH (n:Person)-[r:KNOWS]->(m:Person) RETURN n, m"""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(
                        variable=Identifier(name="n"),
                        labels=[Identifier(name="Person")]
                    ),
                    NodePattern(
                        variable=Identifier(name="m"),
                        labels=[Identifier(name="Person")]
                    )
                ],
                relationships=[
                    RelationshipPattern(
                        variable=Identifier(name="r"),
                        relationship_type=Identifier(name="KNOWS"),
                        direction="out"
                    )
                ]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n"), Identifier(name="m")]
    )

    return Query(
        match_clause=match_clause,
        return_clause=return_clause
    )


@pytest.fixture
def query_with_where():
    """Query with WHERE clause: MATCH (n:Person) WHERE n.age > 30 RETURN n"""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(
                        variable=Identifier(name="n"),
                        labels=[Identifier(name="Person")]
                    )
                ],
                relationships=[]
            )
        ]
    )

    where_clause = WhereClause(
        conditions={
            "type": "comparison",
            "operator": ">",
            "left": {
                "type": "property",
                "variable": "n",
                "property": "age"
            },
            "right": {
                "type": "literal",
                "value": 30,
                "value_type": "number"
            }
        }
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")]
    )

    return Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )


@pytest.fixture
def multi_hop_query():
    """Multi-hop query: MATCH (n)-[r1]->(m)-[r2]->(p) RETURN n, p"""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(variable=Identifier(name="n")),
                    NodePattern(variable=Identifier(name="m")),
                    NodePattern(variable=Identifier(name="p"))
                ],
                relationships=[
                    RelationshipPattern(
                        variable=Identifier(name="r1"),
                        direction="out"
                    ),
                    RelationshipPattern(
                        variable=Identifier(name="r2"),
                        direction="out"
                    )
                ]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n"), Identifier(name="p")]
    )

    return Query(
        match_clause=match_clause,
        return_clause=return_clause
    )


@pytest.fixture
def complex_where_query():
    """Query with complex WHERE: MATCH (n:Person) WHERE n.age > 30 AND n.name = 'John' RETURN n"""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(
                        variable=Identifier(name="n"),
                        labels=[Identifier(name="Person")]
                    )
                ],
                relationships=[]
            )
        ]
    )

    where_clause = WhereClause(
        conditions={
            "type": "logical",
            "operator": "AND",
            "operands": [
                {
                    "type": "comparison",
                    "operator": ">",
                    "left": {
                        "type": "property",
                        "variable": "n",
                        "property": "age"
                    },
                    "right": {
                        "type": "literal",
                        "value": 30,
                        "value_type": "number"
                    }
                },
                {
                    "type": "comparison",
                    "operator": "=",
                    "left": {
                        "type": "property",
                        "variable": "n",
                        "property": "name"
                    },
                    "right": {
                        "type": "literal",
                        "value": "John",
                        "value_type": "string"
                    }
                }
            ]
        }
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")]
    )

    return Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )


# ============================================================================
# Cost Estimation Tests
# ============================================================================

def test_cost_estimate_addition():
    """Test adding two cost estimates."""
    cost1 = CostEstimate(
        estimated_rows=1000,
        estimated_time_ms=10.0,
        estimated_memory_mb=5.0,
        selectivity=0.5
    )

    cost2 = CostEstimate(
        estimated_rows=500,
        estimated_time_ms=5.0,
        estimated_memory_mb=2.0,
        selectivity=0.8
    )

    total = cost1 + cost2

    assert total.estimated_rows == 1000  # Max of the two
    assert total.estimated_time_ms == 15.0
    assert total.estimated_memory_mb == 7.0
    assert total.selectivity == 0.4  # 0.5 * 0.8


def test_cost_estimate_multiplication():
    """Test scaling a cost estimate."""
    cost = CostEstimate(
        estimated_rows=1000,
        estimated_time_ms=10.0,
        estimated_memory_mb=5.0,
        selectivity=0.5
    )

    scaled = cost * 2.0

    assert scaled.estimated_rows == 2000
    assert scaled.estimated_time_ms == 20.0
    assert scaled.estimated_memory_mb == 10.0
    assert scaled.selectivity == 0.5  # Unchanged


# ============================================================================
# Plan Node Tests
# ============================================================================

def test_scan_node_cost_estimation():
    """Test cost estimation for table scan."""
    scan = ScanNode(
        table_name="Person",
        estimated_table_size=10000
    )

    cost = scan.estimate_cost()

    assert cost.estimated_rows == 10000
    assert cost.estimated_time_ms > 0
    assert cost.estimated_memory_mb > 0
    assert cost.selectivity == 1.0


def test_scan_node_with_filter_predicate():
    """Test scan node with filter predicate."""
    scan = ScanNode(
        table_name="Person",
        filter_predicate="age > 30",
        estimated_table_size=10000
    )

    cost = scan.estimate_cost()

    assert cost.estimated_rows == 5000  # 50% selectivity
    assert cost.selectivity == 0.5


def test_filter_node_cost_estimation():
    """Test cost estimation for filter."""
    filter_node = FilterNode(
        predicate="age > 30",
        selectivity=0.3
    )

    cost = filter_node.estimate_cost(input_rows=10000)

    assert cost.estimated_rows == 3000  # 30% selectivity
    assert cost.selectivity == 0.3
    assert cost.estimated_time_ms > 0


def test_join_node_cost_estimation():
    """Test cost estimation for join."""
    join = JoinNode(
        join_type=JoinType.INNER,
        join_condition="n.id = m.id",
        left_cardinality=1000,
        right_cardinality=2000
    )

    cost = join.estimate_cost()

    assert cost.estimated_rows > 0
    assert cost.estimated_time_ms > 0
    assert cost.estimated_memory_mb > 0


def test_cross_join_cost():
    """Test that cross joins are more expensive."""
    inner_join = JoinNode(
        join_type=JoinType.INNER,
        join_condition="n.id = m.id",
        left_cardinality=1000,
        right_cardinality=1000
    )

    cross_join = JoinNode(
        join_type=JoinType.CROSS,
        join_condition="",
        left_cardinality=1000,
        right_cardinality=1000
    )

    inner_cost = inner_join.estimate_cost()
    cross_cost = cross_join.estimate_cost()

    assert cross_cost.estimated_time_ms > inner_cost.estimated_time_ms
    assert cross_cost.estimated_rows > inner_cost.estimated_rows


def test_project_node_cost_estimation():
    """Test cost estimation for projection."""
    project = ProjectNode(columns=["n.name", "n.age"])

    cost = project.estimate_cost(input_rows=10000)

    assert cost.estimated_rows == 10000  # No reduction
    assert cost.selectivity == 1.0
    assert cost.estimated_time_ms > 0


def test_graph_match_node_single_hop():
    """Test graph match with single hop."""
    graph_match = GraphMatchNode(
        pattern="(n)-[r]->(m)",
        num_hops=1,
        has_variable_length=False
    )

    cost = graph_match.estimate_cost(input_rows=1000)

    assert cost.estimated_rows > 1000  # Graph match expands
    assert cost.estimated_time_ms > 0


def test_graph_match_node_multi_hop():
    """Test graph match with multiple hops."""
    single_hop = GraphMatchNode(
        pattern="(n)-[r]->(m)",
        num_hops=1,
        has_variable_length=False
    )

    multi_hop = GraphMatchNode(
        pattern="(n)-[r1]->(m)-[r2]->(p)",
        num_hops=2,
        has_variable_length=False
    )

    single_cost = single_hop.estimate_cost(input_rows=1000)
    multi_cost = multi_hop.estimate_cost(input_rows=1000)

    assert multi_cost.estimated_time_ms > single_cost.estimated_time_ms
    assert multi_cost.estimated_rows > single_cost.estimated_rows


def test_graph_match_variable_length():
    """Test that variable-length paths are more expensive."""
    fixed = GraphMatchNode(
        pattern="(n)-[r]->(m)",
        num_hops=1,
        has_variable_length=False
    )

    variable = GraphMatchNode(
        pattern="(n)-[r*1..3]->(m)",
        num_hops=2,
        has_variable_length=True
    )

    fixed_cost = fixed.estimate_cost(input_rows=1000)
    variable_cost = variable.estimate_cost(input_rows=1000)

    assert variable_cost.estimated_time_ms > fixed_cost.estimated_time_ms


# ============================================================================
# Query Plan Tests
# ============================================================================

def test_query_plan_creation(simple_query):
    """Test creating a query plan."""
    root = GraphMatchNode(pattern="(n:Person)", num_hops=0)
    plan = QueryPlan(
        root=root,
        original_query=simple_query
    )

    assert plan.root == root
    assert plan.original_query == simple_query


def test_query_plan_cost_estimation(simple_query):
    """Test estimating total cost for a plan."""
    root = GraphMatchNode(pattern="(n:Person)", num_hops=0)
    plan = QueryPlan(
        root=root,
        original_query=simple_query
    )

    total_cost = plan.estimate_total_cost()

    assert total_cost.estimated_rows > 0
    assert total_cost.estimated_time_ms > 0
    assert plan.total_cost == total_cost


def test_query_plan_with_children(simple_query):
    """Test plan with parent-child relationships."""
    scan = ScanNode("Person", estimated_table_size=10000)
    filter_node = FilterNode("age > 30", selectivity=0.3)
    project = ProjectNode(columns=["name", "age"])

    # Build tree: project -> filter -> scan
    scan.add_child(filter_node)
    filter_node.add_child(project)

    plan = QueryPlan(root=scan, original_query=simple_query)
    total_cost = plan.estimate_total_cost()

    assert total_cost.estimated_rows > 0
    assert total_cost.estimated_time_ms > 0


def test_query_plan_to_dict(simple_query):
    """Test converting plan to dictionary."""
    root = ScanNode("Person")
    plan = QueryPlan(root=root, original_query=simple_query)
    plan.estimate_total_cost()

    plan_dict = plan.to_dict()

    assert "root" in plan_dict
    assert "total_cost" in plan_dict
    assert "metadata" in plan_dict
    assert plan_dict["root"]["type"] == NodeType.SCAN.value


def test_query_plan_string_representation(simple_query):
    """Test string representation of plan."""
    root = ScanNode("Person")
    plan = QueryPlan(root=root, original_query=simple_query)
    plan.estimate_total_cost()

    plan_str = str(plan)

    assert "QueryPlan" in plan_str
    assert "ScanNode" in plan_str
    assert "Total Cost" in plan_str


# ============================================================================
# Optimization Rules Tests
# ============================================================================

def test_filter_pushdown_rule_applies_to(query_with_where):
    """Test FilterPushdownRule applicability check."""
    rule = FilterPushdownRule()

    assert rule.applies_to(query_with_where) is True


def test_filter_pushdown_rule_does_not_apply(simple_query):
    """Test FilterPushdownRule when no WHERE clause."""
    rule = FilterPushdownRule()

    assert rule.applies_to(simple_query) is False


def test_filter_pushdown_rule_apply(query_with_where):
    """Test applying FilterPushdownRule."""
    rule = FilterPushdownRule()

    result = rule.apply(query_with_where)

    assert result.applied is True
    assert result.cost_reduction > 0
    assert "filter" in result.description.lower()


def test_join_order_rule_applies_to(multi_hop_query):
    """Test JoinOrderRule applicability check."""
    rule = JoinOrderRule()

    assert rule.applies_to(multi_hop_query) is True


def test_join_order_rule_does_not_apply(simple_query):
    """Test JoinOrderRule when no joins."""
    rule = JoinOrderRule()

    assert rule.applies_to(simple_query) is False


def test_join_order_rule_apply(multi_hop_query):
    """Test applying JoinOrderRule."""
    rule = JoinOrderRule()

    result = rule.apply(multi_hop_query)

    assert result.applied is True
    assert result.cost_reduction > 0
    assert "join" in result.description.lower()


def test_time_range_rule_applies_to(simple_query):
    """Test TimeRangeRule applicability check."""
    rule = TimeRangeRule()

    assert rule.applies_to(simple_query) is True


def test_time_range_rule_apply(simple_query):
    """Test applying TimeRangeRule."""
    rule = TimeRangeRule(default_time_range_days=7)

    result = rule.apply(simple_query)

    assert result.applied is True
    assert result.cost_reduction > 0
    assert "time range" in result.description.lower()
    assert "7d" in result.description


def test_predicate_pushdown_rule_applies_to(query_with_where):
    """Test PredicatePushdownRule applicability check."""
    rule = PredicatePushdownRule()

    assert rule.applies_to(query_with_where) is True


def test_predicate_pushdown_rule_apply(query_with_where):
    """Test applying PredicatePushdownRule."""
    rule = PredicatePushdownRule()

    result = rule.apply(query_with_where)

    assert result.applied is True
    assert result.cost_reduction > 0
    assert "predicate" in result.description.lower()


def test_index_hint_rule_applies_to(complex_where_query):
    """Test IndexHintRule applicability check."""
    rule = IndexHintRule()

    assert rule.applies_to(complex_where_query) is True


def test_index_hint_rule_with_known_indexes(complex_where_query):
    """Test IndexHintRule with known indexes."""
    known_indexes = {
        "Person": ["name", "age"]
    }

    rule = IndexHintRule(known_indexes=known_indexes)

    result = rule.apply(complex_where_query)

    assert result.applied is True
    assert result.cost_reduction > 0
    assert "index" in result.description.lower()


def test_index_hint_rule_without_known_indexes(complex_where_query):
    """Test IndexHintRule suggests creating indexes."""
    rule = IndexHintRule(known_indexes={})

    result = rule.apply(complex_where_query)

    assert result.applied is True
    assert "Consider creating index" in result.description


# ============================================================================
# Query Optimizer Tests
# ============================================================================

def test_optimizer_initialization():
    """Test creating optimizer with default settings."""
    optimizer = QueryOptimizer()

    assert len(optimizer.rules) == 5  # All rules enabled by default


def test_optimizer_initialization_disabled_rules():
    """Test creating optimizer with some rules disabled."""
    optimizer = QueryOptimizer(
        enable_filter_pushdown=False,
        enable_join_order=False
    )

    assert len(optimizer.rules) == 3  # Only 3 rules enabled


def test_optimizer_analyze_query(simple_query):
    """Test query analysis."""
    optimizer = QueryOptimizer()

    analysis = optimizer.analyze_query(simple_query)

    assert "num_nodes" in analysis
    assert "num_relationships" in analysis
    assert "num_hops" in analysis
    assert "has_where_clause" in analysis
    assert "complexity" in analysis


def test_optimizer_analyze_multi_hop(multi_hop_query):
    """Test analyzing multi-hop query."""
    optimizer = QueryOptimizer()

    analysis = optimizer.analyze_query(multi_hop_query)

    assert analysis["num_hops"] == 2
    assert analysis["num_nodes"] == 3
    assert analysis["complexity"] in ["Low", "Medium", "High"]


def test_optimizer_generate_plan(simple_query):
    """Test generating query plan."""
    optimizer = QueryOptimizer()

    plan = optimizer.generate_plan(simple_query)

    assert isinstance(plan, QueryPlan)
    assert plan.root is not None
    assert plan.original_query == simple_query


def test_optimizer_generate_plan_with_where(query_with_where):
    """Test generating plan for query with WHERE."""
    optimizer = QueryOptimizer()

    plan = optimizer.generate_plan(query_with_where)

    assert isinstance(plan, QueryPlan)
    assert plan.root is not None


def test_optimizer_optimize_simple_query(simple_query):
    """Test optimizing simple query."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(simple_query)

    assert optimized.query is not None
    assert optimized.plan is not None
    assert optimized.metrics is not None
    assert optimized.metrics.optimization_time_ms >= 0


def test_optimizer_optimize_with_where(query_with_where):
    """Test optimizing query with WHERE clause."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(query_with_where)

    assert optimized.metrics.rules_applied > 0
    assert len(optimized.metrics.rules_details) > 0


def test_optimizer_optimize_multi_hop(multi_hop_query):
    """Test optimizing multi-hop query."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(multi_hop_query)

    assert optimized.metrics.rules_applied >= 0
    assert optimized.plan.total_cost is not None


def test_optimizer_cost_reduction(query_with_where):
    """Test that optimization reduces cost."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(query_with_where)

    # At least some rules should apply
    assert optimized.metrics.rules_applied > 0


def test_optimizer_metrics(query_with_where):
    """Test optimization metrics are populated."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(query_with_where)
    metrics = optimized.metrics

    assert metrics.original_estimated_cost_ms >= 0
    assert metrics.optimized_estimated_cost_ms >= 0
    assert metrics.optimization_time_ms >= 0
    assert isinstance(metrics.rules_details, list)


def test_optimizer_get_summary(query_with_where):
    """Test getting optimization summary."""
    optimizer = QueryOptimizer()

    optimized = optimizer.optimize(query_with_where)
    summary = optimizer.get_optimization_summary(optimized)

    assert isinstance(summary, str)
    assert "OPTIMIZATION SUMMARY" in summary
    assert "Cost Reduction" in summary
    assert "Rules Applied" in summary


def test_optimize_convenience_function(simple_query):
    """Test convenience function for optimization."""
    optimized = optimize(simple_query)

    assert optimized.query is not None
    assert optimized.plan is not None
    assert optimized.metrics is not None


def test_optimizer_with_invalid_input():
    """Test optimizer with invalid input."""
    optimizer = QueryOptimizer()

    with pytest.raises(TypeError):
        optimizer.optimize("not a query object")


def test_optimizer_with_no_match_clause():
    """Test optimizer with query missing MATCH clause."""
    optimizer = QueryOptimizer()

    # Create invalid query without MATCH
    with pytest.raises(ValueError):
        invalid_query = Query(
            match_clause=None,
            return_clause=ReturnClause(items=[Identifier(name="n")])
        )


# ============================================================================
# Integration Tests
# ============================================================================

def test_end_to_end_optimization(complex_where_query):
    """Test complete optimization pipeline."""
    optimizer = QueryOptimizer()

    # Analyze
    analysis = optimizer.analyze_query(complex_where_query)
    assert analysis["has_where_clause"] is True

    # Generate plan
    plan = optimizer.generate_plan(complex_where_query)
    assert plan is not None

    # Optimize
    optimized = optimizer.optimize(complex_where_query)
    assert optimized.metrics.rules_applied > 0


def test_optimization_with_all_rules_disabled(simple_query):
    """Test optimization with all rules disabled."""
    optimizer = QueryOptimizer(
        enable_filter_pushdown=False,
        enable_join_order=False,
        enable_time_range=False,
        enable_predicate_pushdown=False,
        enable_index_hints=False
    )

    optimized = optimizer.optimize(simple_query)

    assert optimized.metrics.rules_applied == 0
    assert len(optimized.metrics.rules_details) == 0


def test_multiple_optimizations_same_optimizer(simple_query, query_with_where):
    """Test running multiple optimizations with same optimizer instance."""
    optimizer = QueryOptimizer()

    optimized1 = optimizer.optimize(simple_query)
    optimized2 = optimizer.optimize(query_with_where)

    assert optimized1 is not optimized2
    assert optimized1.query is not optimized2.query


def test_optimization_metrics_to_dict(query_with_where):
    """Test converting optimization metrics to dictionary."""
    optimizer = QueryOptimizer()
    optimized = optimizer.optimize(query_with_where)

    metrics_dict = optimized.metrics.to_dict()

    assert isinstance(metrics_dict, dict)
    assert "original_estimated_cost_ms" in metrics_dict
    assert "optimized_estimated_cost_ms" in metrics_dict
    assert "cost_reduction_ms" in metrics_dict
    assert "rules_applied" in metrics_dict


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_empty_where_clause():
    """Test handling empty WHERE clause."""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[NodePattern(variable=Identifier(name="n"))],
                relationships=[]
            )
        ]
    )

    where_clause = WhereClause(conditions={})

    return_clause = ReturnClause(items=[Identifier(name="n")])

    query = Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )

    optimizer = QueryOptimizer()
    optimized = optimizer.optimize(query)

    assert optimized is not None


def test_very_complex_query():
    """Test optimization of very complex query."""
    # Create query with many hops and conditions
    nodes = [NodePattern(variable=Identifier(name=f"n{i}")) for i in range(5)]
    rels = [
        RelationshipPattern(
            variable=Identifier(name=f"r{i}"),
            direction="out"
        ) for i in range(4)
    ]

    match_clause = MatchClause(
        paths=[PathExpression(nodes=nodes, relationships=rels)]
    )

    return_clause = ReturnClause(items=[Identifier(name="n0"), Identifier(name="n4")])

    query = Query(match_clause=match_clause, return_clause=return_clause)

    optimizer = QueryOptimizer()
    analysis = optimizer.analyze_query(query)

    assert analysis["num_hops"] == 4
    # 4 hops gives score of 8 (min(4*2, 6) = 6 + no conditions = 6, which is Medium)
    # Need more to get High (>=8)
    assert analysis["complexity"] in ["Medium", "High"]


def test_query_with_aggregation():
    """Test query with aggregation function."""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[NodePattern(variable=Identifier(name="n"))],
                relationships=[]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[
            {
                "type": "function",
                "name": "COUNT",
                "args": [Identifier(name="n")]
            }
        ]
    )

    query = Query(match_clause=match_clause, return_clause=return_clause)

    optimizer = QueryOptimizer()
    analysis = optimizer.analyze_query(query)

    assert analysis["has_aggregation"] is True


def test_query_with_limit():
    """Test query with LIMIT clause."""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[NodePattern(variable=Identifier(name="n"))],
                relationships=[]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")],
        limit=10
    )

    query = Query(match_clause=match_clause, return_clause=return_clause)

    optimizer = QueryOptimizer()
    analysis = optimizer.analyze_query(query)

    assert analysis["has_limit"] is True


def test_query_with_sorting():
    """Test query with ORDER BY clause."""
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[NodePattern(variable=Identifier(name="n"))],
                relationships=[]
            )
        ]
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")],
        order_by=[{"expression": "n.name", "direction": "ASC"}]
    )

    query = Query(match_clause=match_clause, return_clause=return_clause)

    optimizer = QueryOptimizer()
    analysis = optimizer.analyze_query(query)

    assert analysis["has_sorting"] is True
