"""
Basic Usage Examples for Gremlin-to-Cypher Bridge

Demonstrates how to use the cypher_bridge module to translate
Gremlin traversals to Cypher queries.
"""

from yellowstone.gremlin.ast_nodes import (
    GremlinTraversal,
    VertexStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    OrderStep,
)
from yellowstone.gremlin.cypher_bridge import translate_gremlin_to_cypher


def example_simple_query():
    """Example 1: Simple vertex query with label"""
    print("=" * 60)
    print("Example 1: g.V().hasLabel('User')")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User'])
    ])

    query = translate_gremlin_to_cypher(traversal)

    print(f"Match Clause: {query.match_clause.paths[0]}")
    print(f"Where Clause: {query.where_clause}")
    print(f"Return Items: {query.return_clause.items}")
    print()


def example_with_filters():
    """Example 2: Query with property filters"""
    print("=" * 60)
    print("Example 2: g.V().hasLabel('User').has('age', 30).has('active', True)")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User']),
        FilterStep(predicate='has', args=['age', 30]),
        FilterStep(predicate='has', args=['active', True])
    ])

    query = translate_gremlin_to_cypher(traversal)

    print(f"Match: (v0:User)")
    print(f"Where: v0.age = 30 AND v0.active = true")
    print(f"Return: v0")
    print(f"\nWhere Clause Conditions: {query.where_clause.conditions}")
    print()


def example_with_traversal():
    """Example 3: Query with relationship traversal"""
    print("=" * 60)
    print("Example 3: g.V().hasLabel('User').out('OWNS')")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User']),
        TraversalStep(direction='out', edge_label='OWNS')
    ])

    query = translate_gremlin_to_cypher(traversal)

    path = query.match_clause.paths[0]
    print(f"Match Pattern: (v0:User)-[:OWNS]->(v1)")
    print(f"Nodes: {len(path.nodes)}")
    print(f"Relationships: {len(path.relationships)}")
    print(f"Source: {path.nodes[0].variable.name}, Labels: {[l.name for l in path.nodes[0].labels]}")
    print(f"Relationship: {path.relationships[0].relationship_type.name}, Direction: {path.relationships[0].direction}")
    print(f"Target: {path.nodes[1].variable.name}")
    print(f"Return: {query.return_clause.items[0].name}")
    print()


def example_with_projection():
    """Example 4: Query with property projection"""
    print("=" * 60)
    print("Example 4: g.V().hasLabel('User').values('name', 'email')")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User']),
        ProjectionStep(type='values', properties=['name', 'email'])
    ])

    query = translate_gremlin_to_cypher(traversal)

    print(f"Match: (v0:User)")
    print(f"Return: v0.name, v0.email")
    print(f"\nReturn Items:")
    for item in query.return_clause.items:
        print(f"  - {item.variable.name}.{item.property_name.name}")
    print()


def example_with_modifiers():
    """Example 5: Query with order and limit"""
    print("=" * 60)
    print("Example 5: g.V().hasLabel('User').order().by('name').limit(10)")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User']),
        OrderStep(property='name', ascending=True),
        LimitStep(count=10)
    ])

    query = translate_gremlin_to_cypher(traversal)

    print(f"Match: (v0:User)")
    print(f"Return: v0")
    print(f"Order By: {query.return_clause.order_by[0]['expression']['property']} {query.return_clause.order_by[0]['direction']}")
    print(f"Limit: {query.return_clause.limit}")
    print()


def example_complex_query():
    """Example 6: Complex query combining multiple features"""
    print("=" * 60)
    print("Example 6: Complex Query")
    print("g.V().hasLabel('User').has('active', True)")
    print("  .out('OWNS').values('name').order().by('name').limit(5)")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        FilterStep(predicate='hasLabel', args=['User']),
        FilterStep(predicate='has', args=['active', True]),
        TraversalStep(direction='out', edge_label='OWNS'),
        ProjectionStep(type='values', properties=['name']),
        OrderStep(property='name', ascending=True),
        LimitStep(count=5)
    ])

    query = translate_gremlin_to_cypher(traversal)

    path = query.match_clause.paths[0]
    print(f"\nTranslated to:")
    print(f"Match: (v0:User)-[:OWNS]->(v1)")
    print(f"Where: v0.active = true")
    print(f"Return: v1.name ORDER BY v1.name ASC LIMIT 5")
    print(f"\nStructure:")
    print(f"  - Path nodes: {len(path.nodes)}")
    print(f"  - Relationships: {len(path.relationships)}")
    print(f"  - Where conditions present: {query.where_clause is not None}")
    print(f"  - Return items: {len(query.return_clause.items)}")
    print(f"  - Order by: {query.return_clause.order_by is not None}")
    print(f"  - Limit: {query.return_clause.limit}")
    print()


def example_chained_traversals():
    """Example 7: Chained relationship traversals"""
    print("=" * 60)
    print("Example 7: g.V().out('OWNS').out('HAS_PART').values('serial')")
    print("=" * 60)

    traversal = GremlinTraversal(steps=[
        VertexStep(),
        TraversalStep(direction='out', edge_label='OWNS'),
        TraversalStep(direction='out', edge_label='HAS_PART'),
        ProjectionStep(type='values', properties=['serial'])
    ])

    query = translate_gremlin_to_cypher(traversal)

    path = query.match_clause.paths[0]
    print(f"Match Pattern: (v0)-[:OWNS]->(v1)-[:HAS_PART]->(v2)")
    print(f"Return: v2.serial")
    print(f"\nPath Structure:")
    for i, node in enumerate(path.nodes):
        print(f"  Node {i}: {node.variable.name}")
        if i < len(path.relationships):
            rel = path.relationships[i]
            print(f"  Rel {i}: {rel.relationship_type.name if rel.relationship_type else 'ANY'} ({rel.direction})")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Gremlin-to-Cypher Bridge - Basic Usage Examples")
    print("=" * 60 + "\n")

    example_simple_query()
    example_with_filters()
    example_with_traversal()
    example_with_projection()
    example_with_modifiers()
    example_complex_query()
    example_chained_traversals()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
