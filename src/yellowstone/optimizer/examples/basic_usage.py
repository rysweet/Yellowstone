"""
Basic usage examples for the Query Optimizer.

This script demonstrates how to use the query optimizer to analyze and
optimize Cypher queries for KQL translation.
"""

from yellowstone.parser.ast_nodes import (
    Query, MatchClause, WhereClause, ReturnClause,
    PathExpression, NodePattern, RelationshipPattern,
    Identifier
)
from yellowstone.optimizer import (
    QueryOptimizer, optimize,
    FilterPushdownRule, JoinOrderRule, TimeRangeRule
)


def example_1_simple_optimization():
    """Example 1: Simple query optimization."""
    print("=" * 70)
    print("Example 1: Simple Query Optimization")
    print("=" * 70)

    # Create a simple query: MATCH (n:Person) WHERE n.age > 30 RETURN n.name
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

    query = Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )

    # Optimize the query
    optimized = optimize(query)

    # Display results
    print(f"\nOriginal Cost: {optimized.metrics.original_estimated_cost_ms:.2f}ms")
    print(f"Optimized Cost: {optimized.metrics.optimized_estimated_cost_ms:.2f}ms")
    print(f"Cost Reduction: {optimized.metrics.cost_reduction_ms:.2f}ms ({optimized.metrics.cost_reduction_percent:.1f}%)")
    print(f"Rules Applied: {optimized.metrics.rules_applied}")
    print(f"Optimization Time: {optimized.metrics.optimization_time_ms:.3f}ms")

    if optimized.metrics.rules_details:
        print("\nOptimization Rules Applied:")
        for i, rule in enumerate(optimized.metrics.rules_details, 1):
            print(f"  {i}. {rule['rule']}: {rule['description']}")
            print(f"     Cost Reduction: {rule['cost_reduction_ms']:.2f}ms")

    print("\nQuery Plan:")
    print(optimized.plan)


def example_2_multi_hop_query():
    """Example 2: Multi-hop graph query optimization."""
    print("\n" + "=" * 70)
    print("Example 2: Multi-Hop Query Optimization")
    print("=" * 70)

    # Create multi-hop query: MATCH (n)-[r1]->(m)-[r2]->(p) RETURN n, p
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

    query = Query(
        match_clause=match_clause,
        return_clause=return_clause
    )

    # Initialize optimizer with custom configuration
    optimizer = QueryOptimizer(
        enable_filter_pushdown=True,
        enable_join_order=True,
        enable_time_range=True
    )

    # Analyze query
    analysis = optimizer.analyze_query(query)
    print(f"\nQuery Analysis:")
    print(f"  Number of nodes: {analysis['num_nodes']}")
    print(f"  Number of hops: {analysis['num_hops']}")
    print(f"  Complexity: {analysis['complexity']}")
    print(f"  Has WHERE clause: {analysis['has_where_clause']}")

    # Optimize
    optimized = optimizer.optimize(query)

    print(f"\nOptimization Results:")
    print(f"  Original Cost: {optimized.metrics.original_estimated_cost_ms:.2f}ms")
    print(f"  Optimized Cost: {optimized.metrics.optimized_estimated_cost_ms:.2f}ms")
    print(f"  Cost Reduction: {optimized.metrics.cost_reduction_percent:.1f}%")
    print(f"  Rules Applied: {optimized.metrics.rules_applied}")


def example_3_custom_optimizer():
    """Example 3: Custom optimizer configuration."""
    print("\n" + "=" * 70)
    print("Example 3: Custom Optimizer Configuration")
    print("=" * 70)

    # Create query
    match_clause = MatchClause(
        paths=[
            PathExpression(
                nodes=[
                    NodePattern(
                        variable=Identifier(name="n"),
                        labels=[Identifier(name="SecurityAlert")]
                    )
                ],
                relationships=[]
            )
        ]
    )

    where_clause = WhereClause(
        conditions={
            "type": "comparison",
            "operator": "=",
            "left": {
                "type": "property",
                "variable": "n",
                "property": "AlertName"
            },
            "right": {
                "type": "literal",
                "value": "Suspicious Login",
                "value_type": "string"
            }
        }
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n")]
    )

    query = Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )

    # Configure optimizer with known indexes
    known_indexes = {
        "SecurityAlert": ["AlertName", "TimeGenerated", "Severity"],
        "Person": ["name", "email"]
    }

    optimizer = QueryOptimizer(
        enable_filter_pushdown=True,
        enable_time_range=True,  # Important for Sentinel queries
        enable_index_hints=True,
        known_indexes=known_indexes
    )

    # Optimize
    optimized = optimizer.optimize(query)

    # Get detailed summary
    summary = optimizer.get_optimization_summary(optimized)
    print(summary)


def example_4_comparison():
    """Example 4: Compare optimization with and without rules."""
    print("\n" + "=" * 70)
    print("Example 4: Optimization Comparison")
    print("=" * 70)

    # Create query
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
                        relationship_type=Identifier(name="KNOWS"),
                        direction="out"
                    )
                ]
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
                    "left": {"type": "property", "variable": "n", "property": "age"},
                    "right": {"type": "literal", "value": 30, "value_type": "number"}
                },
                {
                    "type": "comparison",
                    "operator": "=",
                    "left": {"type": "property", "variable": "m", "property": "name"},
                    "right": {"type": "literal", "value": "John", "value_type": "string"}
                }
            ]
        }
    )

    return_clause = ReturnClause(
        items=[Identifier(name="n"), Identifier(name="m")]
    )

    query = Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )

    # Optimize with all rules
    optimizer_full = QueryOptimizer()
    optimized_full = optimizer_full.optimize(query)

    # Optimize with no rules
    optimizer_none = QueryOptimizer(
        enable_filter_pushdown=False,
        enable_join_order=False,
        enable_time_range=False,
        enable_predicate_pushdown=False,
        enable_index_hints=False
    )
    optimized_none = optimizer_none.optimize(query)

    print("\nComparison:")
    print(f"{'Metric':<30} {'With Rules':<20} {'Without Rules':<20}")
    print("-" * 70)
    print(f"{'Estimated Cost (ms)':<30} "
          f"{optimized_full.metrics.optimized_estimated_cost_ms:<20.2f} "
          f"{optimized_none.metrics.optimized_estimated_cost_ms:<20.2f}")
    print(f"{'Rules Applied':<30} "
          f"{optimized_full.metrics.rules_applied:<20} "
          f"{optimized_none.metrics.rules_applied:<20}")
    print(f"{'Cost Reduction (%)':<30} "
          f"{optimized_full.metrics.cost_reduction_percent:<20.1f} "
          f"{optimized_none.metrics.cost_reduction_percent:<20.1f}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("YELLOWSTONE QUERY OPTIMIZER - BASIC USAGE EXAMPLES")
    print("=" * 70)

    example_1_simple_optimization()
    example_2_multi_hop_query()
    example_3_custom_optimizer()
    example_4_comparison()

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
