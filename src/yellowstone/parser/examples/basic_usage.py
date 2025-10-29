"""
Basic usage examples for the Cypher parser.

This file demonstrates common parsing tasks and AST navigation patterns.
Run with: python -m yellowstone.parser.examples.basic_usage
"""

from yellowstone.parser import (
    parse_query,
    CollectingVisitor,
    ValidationVisitor,
    DotVisitor,
)


def example_simple_query() -> None:
    """Example 1: Parse and inspect a simple query."""
    print("\n" + "=" * 70)
    print("Example 1: Simple Query Parsing")
    print("=" * 70)

    query_str = "MATCH (n:Person) RETURN n"
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)

    # Inspect match clause
    match = ast.match_clause
    path = match.paths[0]
    node = path.nodes[0]

    print(f"\nMatch clause optional: {match.optional}")
    print(f"Number of paths: {len(match.paths)}")
    print(f"Number of nodes in path: {len(path.nodes)}")
    print(f"Node variable: {node.variable.name if node.variable else 'None'}")
    print(f"Node labels: {[label.name for label in node.labels]}")

    # Inspect return clause
    ret = ast.return_clause
    print(f"\nReturn items: {[str(item) for item in ret.items]}")
    print(f"Return distinct: {ret.distinct}")


def example_complex_query() -> None:
    """Example 2: Parse and inspect a complex query."""
    print("\n" + "=" * 70)
    print("Example 2: Complex Query with All Clauses")
    print("=" * 70)

    query_str = (
        "MATCH (actor:Person)-[r:ACTED_IN]->(movie:Movie) "
        "WHERE actor.birthYear >= 1960 AND movie.title = 'Inception' "
        "RETURN DISTINCT actor.name, movie.title ORDER BY actor.name DESC LIMIT 5"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)

    # Inspect match clause
    print("\n--- MATCH Clause ---")
    path = ast.match_clause.paths[0]
    print(f"Number of nodes: {len(path.nodes)}")
    print(f"Number of relationships: {len(path.relationships)}")

    for i, node in enumerate(path.nodes):
        labels = [l.name for l in node.labels]
        var = node.variable.name if node.variable else "None"
        print(f"  Node {i}: variable={var}, labels={labels}")

    for i, rel in enumerate(path.relationships):
        var = rel.variable.name if rel.variable else "None"
        typ = rel.relationship_type.name if rel.relationship_type else "None"
        print(f"  Rel {i}: variable={var}, type={typ}, direction={rel.direction}")

    # Inspect where clause
    print("\n--- WHERE Clause ---")
    if ast.where_clause:
        cond = ast.where_clause.conditions
        print(f"Condition type: {cond['type']}")
        print(f"Operator: {cond['operator']}")

    # Inspect return clause
    print("\n--- RETURN Clause ---")
    ret = ast.return_clause
    print(f"Distinct: {ret.distinct}")
    print(f"Items: {[str(item) for item in ret.items]}")
    print(f"Order by: {ret.order_by}")
    print(f"Limit: {ret.limit}")


def example_property_traversal() -> None:
    """Example 3: Traverse properties in a node pattern."""
    print("\n" + "=" * 70)
    print("Example 3: Node Properties")
    print("=" * 70)

    query_str = "MATCH (n:Person {name: 'Alice', age: 30, active: true}) RETURN n"
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)
    node = ast.match_clause.paths[0].nodes[0]

    print(f"\nNode variable: {node.variable.name if node.variable else 'None'}")
    print(f"Node labels: {[l.name for l in node.labels]}")

    if node.properties:
        print("\nNode properties:")
        for key, value in node.properties.items():
            print(f"  {key}: {value.value} ({value.value_type})")


def example_path_navigation() -> None:
    """Example 4: Navigate complex path expressions."""
    print("\n" + "=" * 70)
    print("Example 4: Complex Path Navigation")
    print("=" * 70)

    query_str = (
        "MATCH (a:Person)-[r1:KNOWS]->(b:Person)-[r2:WORKS_AT]->(c:Company) "
        "RETURN a, b, c"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)
    path = ast.match_clause.paths[0]

    print(f"\nPath structure:")
    print(f"  Nodes: {len(path.nodes)}")
    print(f"  Relationships: {len(path.relationships)}")

    # Visualize the path
    for i, node in enumerate(path.nodes):
        var = node.variable.name if node.variable else "?"
        labels = ":".join(l.name for l in node.labels) if node.labels else "?"
        print(f"  ({var}:{labels})", end="")

        if i < len(path.relationships):
            rel = path.relationships[i]
            rel_type = rel.relationship_type.name if rel.relationship_type else "?"
            arrow = "-[" + rel_type + "]->"
            print(f" {arrow} ", end="")

    print("\n")


def example_multiple_paths() -> None:
    """Example 5: Parse queries with multiple paths."""
    print("\n" + "=" * 70)
    print("Example 5: Multiple Paths in MATCH")
    print("=" * 70)

    query_str = "MATCH (n:Person), (m:Movie), (p:Person)-[r:DIRECTED]->(m) RETURN n, m, p"
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)
    match = ast.match_clause

    print(f"\nNumber of paths: {len(match.paths)}")

    for i, path in enumerate(match.paths):
        print(f"\nPath {i}:")
        print(f"  Nodes: {len(path.nodes)}")
        print(f"  Relationships: {len(path.relationships)}")

        for node in path.nodes:
            var = node.variable.name if node.variable else "?"
            labels = ":".join(l.name for l in node.labels) if node.labels else "?"
            print(f"    ({var}:{labels})")


def example_collecting_visitor() -> None:
    """Example 6: Use CollectingVisitor to gather identifiers and literals."""
    print("\n" + "=" * 70)
    print("Example 6: CollectingVisitor")
    print("=" * 70)

    query_str = (
        "MATCH (n:Person {name: 'Alice', age: 25})-[r:KNOWS]->(m:Person) "
        "WHERE n.status = 'active' "
        "RETURN n, m"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)

    visitor = CollectingVisitor()
    ast.accept(visitor)

    print(f"\nIdentifiers found: {len(visitor.identifiers)}")
    print(f"  {[i.name for i in visitor.identifiers]}")

    print(f"\nLiterals found: {len(visitor.literals)}")
    for lit in visitor.literals:
        print(f"  {lit.value} ({lit.value_type})")


def example_validation_visitor() -> None:
    """Example 7: Use ValidationVisitor to check query validity."""
    print("\n" + "=" * 70)
    print("Example 7: ValidationVisitor")
    print("=" * 70)

    # Valid query
    valid_query = "MATCH (n:Person) RETURN n"
    print(f"\nValid query: {valid_query}")

    ast = parse_query(valid_query)
    validator = ValidationVisitor()
    ast.accept(validator)

    print(f"Errors: {len(validator.errors)}")
    print(f"Warnings: {len(validator.warnings)}")

    # Invalid query - undefined variable
    print("\n---")
    invalid_query = "MATCH (n:Person) RETURN m"
    print(f"\nInvalid query: {invalid_query}")

    ast = parse_query(invalid_query)
    validator = ValidationVisitor()
    ast.accept(validator)

    print(f"Errors: {len(validator.errors)}")
    print(f"Warnings: {len(validator.warnings)}")
    for warning in validator.warnings:
        print(f"  - {warning}")


def example_dot_visitor() -> None:
    """Example 8: Generate GraphViz DOT representation."""
    print("\n" + "=" * 70)
    print("Example 8: DotVisitor - GraphViz Generation")
    print("=" * 70)

    query_str = (
        "MATCH (n:Person)-[r:KNOWS]->(m:Person) "
        "WHERE n.age > 30 "
        "RETURN n, m"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)

    visitor = DotVisitor()
    dot = visitor.generate_dot(ast)

    print("\nGenerated DOT (first 500 chars):")
    print(dot[:500] + "..." if len(dot) > 500 else dot)

    # Show how to save
    print("\nTo save to file and render:")
    print("  with open('query.dot', 'w') as f:")
    print("      f.write(dot)")
    print("  # Then: dot -Tpng query.dot -o query.png")


def example_where_conditions() -> None:
    """Example 9: Parse and inspect WHERE clauses."""
    print("\n" + "=" * 70)
    print("Example 9: WHERE Clause Conditions")
    print("=" * 70)

    query_str = (
        "MATCH (n:Person) "
        "WHERE n.age > 30 AND n.status = 'active' OR n.admin = true "
        "RETURN n"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)

    if ast.where_clause:
        cond = ast.where_clause.conditions

        def print_condition(cond: dict, indent: int = 0) -> None:
            prefix = "  " * indent
            if cond.get("type") == "comparison":
                left = cond.get("left", {})
                right = cond.get("right", {})
                op = cond.get("operator")
                print(f"{prefix}Comparison: {op}")
                print(f"{prefix}  Left: {left}")
                print(f"{prefix}  Right: {right}")
            elif cond.get("type") == "logical":
                op = cond.get("operator")
                print(f"{prefix}Logical: {op}")
                print(f"{prefix}  Left:")
                print_condition(cond.get("left", {}), indent + 2)
                print(f"{prefix}  Right:")
                print_condition(cond.get("right", {}), indent + 2)
            else:
                print(f"{prefix}{cond}")

        print_condition(cond)


def example_return_modifiers() -> None:
    """Example 10: Parse RETURN with modifiers."""
    print("\n" + "=" * 70)
    print("Example 10: RETURN Clause Modifiers")
    print("=" * 70)

    query_str = (
        "MATCH (n:Person) "
        "RETURN DISTINCT n.name, n.age "
        "ORDER BY n.age DESC "
        "SKIP 10 "
        "LIMIT 5"
    )
    print(f"\nQuery: {query_str}")

    ast = parse_query(query_str)
    ret = ast.return_clause

    print(f"\nReturn clause analysis:")
    print(f"  Distinct: {ret.distinct}")
    print(f"  Items: {len(ret.items)}")
    for item in ret.items:
        print(f"    - {item}")
    print(f"  Order by: {ret.order_by}")
    print(f"  Skip: {ret.skip}")
    print(f"  Limit: {ret.limit}")


if __name__ == "__main__":
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Cypher Parser - Usage Examples")
    print("=" * 70)

    example_simple_query()
    example_complex_query()
    example_property_traversal()
    example_path_navigation()
    example_multiple_paths()
    example_collecting_visitor()
    example_validation_visitor()
    example_dot_visitor()
    example_where_conditions()
    example_return_modifiers()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70 + "\n")
