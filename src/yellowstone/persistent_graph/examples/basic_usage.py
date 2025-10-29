"""
Basic usage example for persistent graph module.

This example demonstrates creating, querying, and managing persistent graphs
in Microsoft Sentinel (using mock API for demonstration).
"""

from yellowstone.persistent_graph import (
    GraphManager,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition,
    GraphStatus,
    SnapshotType,
)


def main():
    """Run basic persistent graph example."""
    print("=" * 70)
    print("Persistent Graph Basic Example")
    print("=" * 70)

    # 1. Define graph schema
    print("\n1. Defining graph schema...")

    alert_node = NodeDefinition(
        label='Alert',
        source_table='SecurityAlert',
        id_property='AlertId',
        properties={
            'AlertId': 'SystemAlertId',
            'severity': 'AlertSeverity',
            'timestamp': 'TimeGenerated',
        }
    )

    user_node = NodeDefinition(
        label='User',
        source_table='IdentityInfo',
        id_property='UserId',
        properties={
            'UserId': 'AccountObjectId',
            'name': 'AccountDisplayName',
            'email': 'AccountUPN',
        }
    )

    device_node = NodeDefinition(
        label='Device',
        source_table='DeviceInfo',
        id_property='DeviceId',
        properties={
            'DeviceId': 'DeviceName',
            'os': 'OSPlatform',
        }
    )

    triggered_edge = EdgeDefinition(
        type='TRIGGERED_BY',
        from_label='Alert',
        to_label='User',
        join_condition='Alert.UserId == User.UserId',
        strength='high',
    )

    originated_edge = EdgeDefinition(
        type='ORIGINATED_FROM',
        from_label='Alert',
        to_label='Device',
        join_condition='Alert.DeviceId == Device.DeviceId',
        strength='medium',
    )

    schema = GraphSchema(
        nodes=[alert_node, user_node, device_node],
        edges=[triggered_edge, originated_edge],
        version='1.0.0'
    )

    print(f"  Created schema with {len(schema.nodes)} node types")
    print(f"  and {len(schema.edges)} edge types")

    # 2. Create graph manager
    print("\n2. Initializing graph manager...")
    manager = GraphManager(workspace_id='demo-workspace-123')
    print("  Manager initialized (using mock API)")

    # 3. Create persistent graph
    print("\n3. Creating persistent graph...")
    graph = manager.create_graph(
        name='SecurityThreatGraph',
        schema=schema,
        description='Security alerts with user and device relationships',
        create_snapshot=True
    )

    print(f"  Graph created: {graph.name}")
    print(f"  Status: {graph.status}")
    print(f"  Version: {graph.version}")
    print(f"  Snapshot ID: {graph.last_snapshot_id}")

    # 4. Build and display KQL
    print("\n4. Generated KQL statement:")
    from yellowstone.persistent_graph import GraphBuilder
    builder = GraphBuilder(graph)
    kql = builder.build_create_statement()
    print("  " + "\n  ".join(kql.split("\n")[:5]))
    print("  ...")

    # 5. Query the graph
    print("\n5. Querying persistent graph...")
    results = manager.query_graph(
        'SecurityThreatGraph',
        "persistent-graph('SecurityThreatGraph') | take 10"
    )
    print(f"  Query executed successfully")
    print(f"  Rows returned: {results['row_count']}")
    print(f"  Execution time: {results['execution_time_ms']}ms")

    # 6. View metrics
    print("\n6. Performance metrics:")
    metrics = manager.get_metrics('SecurityThreatGraph')
    print(f"  Query count: {metrics.query_count}")
    print(f"  Avg query time: {metrics.avg_query_time_ms}ms")
    print(f"  Speedup factor: {metrics.speedup_factor}x")

    # 7. Create additional snapshot
    print("\n7. Creating manual snapshot...")
    snapshot = manager.snapshot_manager.create_snapshot(
        graph,
        retention_days=90
    )
    print(f"  Snapshot created: {snapshot.snapshot_id}")
    print(f"  Status: {snapshot.status}")
    print(f"  Nodes: {snapshot.node_count:,}")
    print(f"  Edges: {snapshot.edge_count:,}")
    print(f"  Size: {snapshot.size_bytes:,} bytes")

    # 8. List all snapshots
    print("\n8. Listing all snapshots:")
    snapshots = manager.snapshot_manager.list_snapshots(
        graph_name='SecurityThreatGraph'
    )
    for i, snap in enumerate(snapshots, 1):
        print(f"  {i}. {snap.snapshot_id} (v{snap.graph_version}) - "
              f"{snap.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # 9. Update graph schema
    print("\n9. Updating graph schema...")
    # Add filter to alert node
    alert_node_filtered = NodeDefinition(
        label='Alert',
        source_table='SecurityAlert',
        id_property='AlertId',
        properties={
            'AlertId': 'SystemAlertId',
            'severity': 'AlertSeverity',
            'timestamp': 'TimeGenerated',
        },
        filters=['AlertSeverity in ("High", "Critical")']
    )

    updated_schema = GraphSchema(
        nodes=[alert_node_filtered, user_node, device_node],
        edges=[triggered_edge, originated_edge],
        version='1.1.0'
    )

    updated_graph = manager.update_graph(
        'SecurityThreatGraph',
        updated_schema,
        changes=['Added severity filter to Alert nodes']
    )

    print(f"  Graph updated to version {updated_graph.version}")
    print(f"  Status: {updated_graph.status}")

    # 10. View version history
    print("\n10. Version history:")
    versions = manager.get_version_history('SecurityThreatGraph')
    for v in versions:
        print(f"  v{v.version}: {', '.join(v.changes)}")

    # 11. List all graphs
    print("\n11. All graphs in workspace:")
    all_graphs = manager.list_graphs()
    for g in all_graphs:
        print(f"  - {g.name} (v{g.version}) - {g.status}")

    # 12. Performance estimate
    print("\n12. Performance estimate:")
    perf = builder.estimate_performance()
    print(f"  Expected speedup: {perf['expected_speedup']}x")
    print(f"  Estimated memory: {perf['estimated_memory_mb']} MB")
    print(f"  Incremental updates: {perf['supports_incremental_updates']}")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    main()
