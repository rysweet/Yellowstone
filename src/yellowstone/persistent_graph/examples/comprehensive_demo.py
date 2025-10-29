"""
Comprehensive demonstration of persistent graph module capabilities.

This script demonstrates all major features of the persistent graph module
including graph lifecycle, snapshots, versioning, and error handling.
"""

from yellowstone.persistent_graph import (
    GraphManager,
    GraphBuilder,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition,
    GraphStatus,
    SnapshotType,
)


def demonstrate_graph_creation():
    """Demonstrate graph creation and validation."""
    print("\n" + "=" * 70)
    print("1. GRAPH CREATION AND VALIDATION")
    print("=" * 70)

    # Create schema
    schema = GraphSchema(
        nodes=[
            NodeDefinition(
                label='Alert',
                source_table='SecurityAlert',
                id_property='AlertId',
                properties={'severity': 'AlertSeverity'},
                filters=['AlertSeverity in ("High", "Critical")']
            ),
            NodeDefinition(
                label='User',
                source_table='IdentityInfo',
                id_property='UserId',
                properties={'name': 'AccountDisplayName'}
            )
        ],
        edges=[
            EdgeDefinition(
                type='TRIGGERED_BY',
                from_label='Alert',
                to_label='User',
                join_condition='Alert.UserId == User.UserId',
                strength='high'
            )
        ]
    )

    # Validate schema
    errors = schema.validate_edges()
    print(f"Schema validation: {'✅ PASSED' if not errors else '❌ FAILED'}")
    print(f"Node types: {len(schema.nodes)}")
    print(f"Edge types: {len(schema.edges)}")

    # Create graph
    manager = GraphManager(workspace_id='demo-workspace')
    graph = manager.create_graph('DemoGraph', schema, create_snapshot=True)

    print(f"\nGraph created:")
    print(f"  Name: {graph.name}")
    print(f"  Status: {graph.status}")
    print(f"  Version: {graph.version}")
    print(f"  Initial snapshot: {graph.last_snapshot_id}")

    return manager, graph


def demonstrate_kql_generation(graph):
    """Demonstrate KQL statement generation."""
    print("\n" + "=" * 70)
    print("2. KQL STATEMENT GENERATION")
    print("=" * 70)

    builder = GraphBuilder(graph)

    # Create statement
    create_kql = builder.build_create_statement()
    print("\nCreate statement (first 5 lines):")
    for line in create_kql.split('\n')[:5]:
        print(f"  {line}")

    # Query statement
    query_kql = builder.build_query_statement()
    print(f"\nQuery statement: {query_kql[:50]}...")

    # Delete statement
    delete_kql = builder.build_delete_statement()
    print(f"Delete statement: {delete_kql}")

    # Performance estimation
    perf = builder.estimate_performance()
    print(f"\nPerformance estimate:")
    print(f"  Expected speedup: {perf['expected_speedup']}x")
    print(f"  Memory usage: {perf['estimated_memory_mb']} MB")
    print(f"  Incremental updates: {perf['supports_incremental_updates']}")


def demonstrate_snapshot_operations(manager, graph):
    """Demonstrate snapshot creation and management."""
    print("\n" + "=" * 70)
    print("3. SNAPSHOT OPERATIONS")
    print("=" * 70)

    sm = manager.snapshot_manager

    # Create full snapshot
    full_snap = sm.create_snapshot(graph, retention_days=90)
    print(f"\nFull snapshot created:")
    print(f"  ID: {full_snap.snapshot_id}")
    print(f"  Type: {full_snap.snapshot_type}")
    print(f"  Nodes: {full_snap.node_count:,}")
    print(f"  Edges: {full_snap.edge_count:,}")
    print(f"  Size: {full_snap.size_bytes:,} bytes")

    # Create differential snapshot
    diff_snap = sm.create_snapshot(
        graph,
        snapshot_type=SnapshotType.DIFFERENTIAL,
        base_snapshot_id=full_snap.snapshot_id
    )
    print(f"\nDifferential snapshot created:")
    print(f"  ID: {diff_snap.snapshot_id}")
    print(f"  Base: {diff_snap.base_snapshot_id}")
    print(f"  Size: {diff_snap.size_bytes:,} bytes (smaller than full)")

    # Compare snapshots
    comparison = sm.compare_snapshots(full_snap.snapshot_id, diff_snap.snapshot_id)
    print(f"\nSnapshot comparison:")
    print(f"  Node delta: {comparison['node_count_delta']:,}")
    print(f"  Edge delta: {comparison['edge_count_delta']:,}")
    print(f"  Version delta: {comparison['version_delta']}")

    # Estimate restore time
    estimate = sm.estimate_restore_time(full_snap.snapshot_id)
    print(f"\nRestore time estimate:")
    print(f"  Chain length: {estimate['snapshot_chain_length']}")
    print(f"  Data size: {estimate['total_data_size_bytes']:,} bytes")
    print(f"  Estimated time: {estimate['estimated_seconds']} seconds")

    return full_snap


def demonstrate_version_management(manager, graph):
    """Demonstrate version control and rollback."""
    print("\n" + "=" * 70)
    print("4. VERSION MANAGEMENT")
    print("=" * 70)

    # Current version
    print(f"\nCurrent version: {graph.version}")

    # Update schema (add a node)
    new_schema = GraphSchema(
        nodes=graph.schema.nodes + [
            NodeDefinition(
                label='Device',
                source_table='DeviceInfo',
                id_property='DeviceId',
                properties={'os': 'OSPlatform'}
            )
        ],
        edges=graph.schema.edges
    )

    updated = manager.update_graph(
        graph.name,
        new_schema,
        changes=['Added Device node type']
    )
    print(f"Updated to version: {updated.version}")

    # Another update
    newer_schema = GraphSchema(
        nodes=new_schema.nodes,
        edges=new_schema.edges + [
            EdgeDefinition(
                type='USES',
                from_label='User',
                to_label='Device',
                join_condition='User.UserId == Device.UserId',
                strength='medium'
            )
        ]
    )

    updated = manager.update_graph(
        graph.name,
        newer_schema,
        changes=['Added USES edge type']
    )
    print(f"Updated to version: {updated.version}")

    # View version history
    versions = manager.get_version_history(graph.name)
    print(f"\nVersion history ({len(versions)} versions):")
    for v in versions:
        print(f"  v{v.version}: {', '.join(v.changes)}")

    # Rollback to version 1
    rolled_back = manager.rollback_version(graph.name, 1)
    print(f"\nRolled back to v1 schema, now at version: {rolled_back.version}")


def demonstrate_graph_operations(manager, graph):
    """Demonstrate query execution and metrics."""
    print("\n" + "=" * 70)
    print("5. GRAPH OPERATIONS")
    print("=" * 70)

    # Execute query
    results = manager.query_graph(
        graph.name,
        f"persistent-graph('{graph.name}') | take 100"
    )
    print(f"\nQuery executed:")
    print(f"  Rows returned: {results['row_count']}")
    print(f"  Execution time: {results['execution_time_ms']}ms")

    # Another query
    results2 = manager.query_graph(
        graph.name,
        f"persistent-graph('{graph.name}') | graph-match (a:Alert)-[:TRIGGERED_BY]->(u:User)"
    )
    print(f"\nPattern match query:")
    print(f"  Rows returned: {results2['row_count']}")
    print(f"  Execution time: {results2['execution_time_ms']}ms")

    # Get metrics
    metrics = manager.get_metrics(graph.name)
    print(f"\nPerformance metrics:")
    print(f"  Total queries: {metrics.query_count}")
    print(f"  Avg query time: {metrics.avg_query_time_ms:.2f}ms")
    print(f"  Speedup factor: {metrics.speedup_factor}x")
    print(f"  Cache hit rate: {metrics.cache_hit_rate * 100:.1f}%")

    # List operations
    operations = manager.list_operations(graph_name=graph.name)
    print(f"\nOperations log ({len(operations)} operations):")
    for op in operations[:5]:
        print(f"  {op.operation_type}: {op.status} ({op.started_at.strftime('%H:%M:%S')})")


def demonstrate_snapshot_restore(manager, snapshot):
    """Demonstrate snapshot restoration."""
    print("\n" + "=" * 70)
    print("6. SNAPSHOT RESTORATION")
    print("=" * 70)

    # Restore to new graph
    restored = manager.snapshot_manager.restore_snapshot(
        snapshot.snapshot_id,
        target_graph_name='RestoredGraph'
    )

    print(f"\nGraph restored from snapshot:")
    print(f"  Original: {snapshot.graph_name}")
    print(f"  Restored as: {restored.name}")
    print(f"  Version: {restored.version}")
    print(f"  Nodes: {restored.estimated_node_count:,}")
    print(f"  Edges: {restored.estimated_edge_count:,}")


def demonstrate_error_handling(manager):
    """Demonstrate error handling and validation."""
    print("\n" + "=" * 70)
    print("7. ERROR HANDLING")
    print("=" * 70)

    # Try to create duplicate graph
    print("\nTest 1: Duplicate graph name")
    try:
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Test',
                    source_table='TestTable',
                    id_property='Id',
                    properties={}
                )
            ]
        )
        manager.create_graph('DemoGraph', schema)  # Already exists
        print("  ❌ Should have failed")
    except ValueError as e:
        print(f"  ✅ Caught: {str(e)}")

    # Try invalid node label
    print("\nTest 2: Invalid node label")
    try:
        NodeDefinition(
            label='invalid',  # Must start with uppercase
            source_table='Table',
            id_property='Id',
            properties={}
        )
        print("  ❌ Should have failed")
    except ValueError as e:
        print(f"  ✅ Caught: {str(e)}")

    # Try invalid edge reference
    print("\nTest 3: Invalid edge reference")
    try:
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Node1',
                    source_table='Table1',
                    id_property='Id',
                    properties={}
                )
            ],
            edges=[
                EdgeDefinition(
                    type='CONNECTS_TO',
                    from_label='Node1',
                    to_label='NonExistent',  # Doesn't exist
                    join_condition='x == y'
                )
            ]
        )
        errors = schema.validate_edges()
        if errors:
            print(f"  ✅ Validation caught: {errors[0]}")
        else:
            print("  ❌ Should have caught error")
    except Exception as e:
        print(f"  ✅ Caught: {str(e)}")


def demonstrate_graph_listing(manager):
    """Demonstrate listing and filtering graphs."""
    print("\n" + "=" * 70)
    print("8. GRAPH LISTING AND FILTERING")
    print("=" * 70)

    # List all graphs
    all_graphs = manager.list_graphs()
    print(f"\nAll graphs in workspace: {len(all_graphs)}")
    for g in all_graphs:
        print(f"  - {g.name} (v{g.version}) - {g.status}")

    # Filter by status
    active_graphs = manager.list_graphs(status=GraphStatus.ACTIVE)
    print(f"\nActive graphs: {len(active_graphs)}")


def demonstrate_cleanup(manager):
    """Demonstrate cleanup operations."""
    print("\n" + "=" * 70)
    print("9. CLEANUP OPERATIONS")
    print("=" * 70)

    # Cleanup expired snapshots
    deleted = manager.snapshot_manager.cleanup_expired_snapshots()
    print(f"\nExpired snapshots cleaned up: {len(deleted)}")

    # Delete graph
    deleted_graph = manager.delete_graph('RestoredGraph', force=True)
    print(f"Deleted restored graph: {deleted_graph}")


def main():
    """Run comprehensive demonstration."""
    print("\n" + "=" * 70)
    print("PERSISTENT GRAPH MODULE - COMPREHENSIVE DEMONSTRATION")
    print("=" * 70)

    try:
        # 1. Graph creation and validation
        manager, graph = demonstrate_graph_creation()

        # 2. KQL generation
        demonstrate_kql_generation(graph)

        # 3. Snapshot operations
        snapshot = demonstrate_snapshot_operations(manager, graph)

        # 4. Version management
        demonstrate_version_management(manager, graph)

        # 5. Graph operations
        demonstrate_graph_operations(manager, graph)

        # 6. Snapshot restore
        demonstrate_snapshot_restore(manager, snapshot)

        # 7. Error handling
        demonstrate_error_handling(manager)

        # 8. Graph listing
        demonstrate_graph_listing(manager)

        # 9. Cleanup
        demonstrate_cleanup(manager)

        print("\n" + "=" * 70)
        print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == '__main__':
    main()
