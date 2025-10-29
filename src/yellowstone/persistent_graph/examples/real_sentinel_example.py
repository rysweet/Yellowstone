"""
Example: Using real Azure Sentinel integration with Yellowstone.

This example demonstrates how to use the real SentinelClient to connect
to an Azure Sentinel workspace and manage persistent graphs.

Requirements:
    - Azure credentials configured (DefaultAzureCredential or explicit)
    - Valid workspace ID
    - Appropriate RBAC permissions on the workspace

Environment Variables (optional):
    SENTINEL_WORKSPACE_ID: Your Azure Log Analytics workspace ID
    AZURE_CLIENT_ID: Service principal client ID
    AZURE_CLIENT_SECRET: Service principal secret
    AZURE_TENANT_ID: Azure tenant ID
"""

import os
from datetime import timedelta
from azure.identity import DefaultAzureCredential, ClientSecretCredential

from yellowstone.persistent_graph import (
    GraphManager,
    SentinelClient,
    GraphSchema,
    NodeDefinition,
    EdgeDefinition,
    AuthenticationError,
    WorkspaceNotFoundError,
    QueryExecutionError,
)


def get_credential():
    """
    Get Azure credential for authentication.

    Uses service principal if environment variables are set,
    otherwise falls back to DefaultAzureCredential.
    """
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    tenant_id = os.getenv('AZURE_TENANT_ID')

    if client_id and client_secret and tenant_id:
        print("Using service principal authentication")
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    else:
        print("Using DefaultAzureCredential")
        return DefaultAzureCredential()


def example_basic_connection():
    """Example: Basic connection to Sentinel workspace."""
    print("\n=== Example 1: Basic Connection ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        # Create Sentinel client
        credential = get_credential()
        client = SentinelClient(
            workspace_id=workspace_id,
            credential=credential
        )

        # Validate connection
        print(f"Connecting to workspace: {workspace_id}")
        if client.validate_connection():
            print("Connection successful!")

        # Get workspace info
        info = client.get_workspace_info()
        print(f"Workspace info: {info}")

    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
    except WorkspaceNotFoundError as e:
        print(f"Workspace not found: {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_simple_query():
    """Example: Execute a simple KQL query."""
    print("\n=== Example 2: Simple Query ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        credential = get_credential()
        client = SentinelClient(workspace_id=workspace_id, credential=credential)

        # Execute simple query
        print("Executing query: print test='hello', value=42")
        result = client.execute_kql(
            "print test='hello', value=42",
            timespan=timedelta(minutes=1)
        )

        print(f"Status: {result['status']}")
        print(f"Rows returned: {result['row_count']}")
        print(f"Execution time: {result['execution_time_ms']:.2f} ms")

        if result['rows']:
            print("\nResults:")
            for row in result['rows']:
                print(f"  {row}")

    except QueryExecutionError as e:
        print(f"Query failed: {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_security_alerts():
    """Example: Query SecurityAlert table."""
    print("\n=== Example 3: Query Security Alerts ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        credential = get_credential()
        client = SentinelClient(workspace_id=workspace_id, credential=credential)

        # Query recent alerts
        query = """
        SecurityAlert
        | where TimeGenerated > ago(7d)
        | summarize Count=count() by AlertSeverity
        | order by Count desc
        """

        print("Querying SecurityAlert table (last 7 days)...")
        result = client.execute_kql(query, timespan=timedelta(days=7))

        print(f"Status: {result['status']}")
        print(f"Rows returned: {result['row_count']}")

        if result['rows']:
            print("\nAlert counts by severity:")
            for row in result['rows']:
                print(f"  {row}")
        else:
            print("No alerts found in the last 7 days")

    except QueryExecutionError as e:
        print(f"Query failed: {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_create_persistent_graph():
    """Example: Create a persistent graph with real Sentinel integration."""
    print("\n=== Example 4: Create Persistent Graph ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        # Create GraphManager with real credentials
        credential = get_credential()
        manager = GraphManager(
            workspace_id=workspace_id,
            credential=credential
        )

        # Define graph schema
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='SystemAlertId',
                    properties={
                        'AlertId': 'SystemAlertId',
                        'severity': 'AlertSeverity',
                        'timestamp': 'TimeGenerated',
                        'title': 'AlertName',
                    },
                    filters=['AlertSeverity in ("High", "Medium")']
                ),
                NodeDefinition(
                    label='User',
                    source_table='IdentityInfo',
                    id_property='AccountObjectId',
                    properties={
                        'UserId': 'AccountObjectId',
                        'name': 'AccountDisplayName',
                        'email': 'AccountUPN',
                    }
                ),
            ],
            edges=[
                EdgeDefinition(
                    type='AFFECTED_USER',
                    from_label='Alert',
                    to_label='User',
                    join_condition='Alert.CompromisedEntity == User.AccountUPN',
                    strength='high',
                )
            ]
        )

        # Create persistent graph
        print("Creating persistent graph 'SecurityGraph'...")
        graph = manager.create_graph(
            name='SecurityGraph',
            schema=schema,
            description='Security alerts and affected users'
        )

        print(f"Graph created successfully!")
        print(f"  Name: {graph.name}")
        print(f"  Status: {graph.status}")
        print(f"  Version: {graph.version}")
        print(f"  Workspace: {graph.workspace_id}")

    except ValueError as e:
        print(f"Validation error: {e}")
    except QueryExecutionError as e:
        print(f"Execution error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def example_query_graph():
    """Example: Query a persistent graph."""
    print("\n=== Example 5: Query Persistent Graph ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        credential = get_credential()
        manager = GraphManager(workspace_id=workspace_id, credential=credential)

        # First create a simple graph for testing
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='SystemAlertId',
                    properties={'AlertId': 'SystemAlertId', 'severity': 'AlertSeverity'}
                )
            ],
            edges=[]
        )

        print("Creating test graph...")
        graph = manager.create_graph('TestGraph', schema)

        # Query the graph
        print("\nQuerying graph...")
        query = """
        persistent-graph('TestGraph')
        | graph-match (alert:Alert)
        | project alert.AlertId, alert.severity
        | take 10
        """

        results = manager.query_graph('TestGraph', query)

        print(f"Status: {results.get('status')}")
        print(f"Rows: {results.get('row_count')}")

        if results.get('rows'):
            print("\nResults:")
            for row in results['rows']:
                print(f"  {row}")

    except Exception as e:
        print(f"Error: {e}")


def example_error_handling():
    """Example: Comprehensive error handling."""
    print("\n=== Example 6: Error Handling ===\n")

    # Test with invalid workspace
    print("Testing with invalid workspace...")
    try:
        credential = get_credential()
        client = SentinelClient(
            workspace_id='invalid-workspace-id',
            credential=credential
        )
        client.validate_connection()
    except WorkspaceNotFoundError as e:
        print(f"Expected error caught: {type(e).__name__}")
    except AuthenticationError as e:
        print(f"Authentication error: {type(e).__name__}")
    except Exception as e:
        print(f"Other error: {type(e).__name__}")

    # Test with empty workspace ID
    print("\nTesting with empty workspace ID...")
    try:
        client = SentinelClient(workspace_id='')
    except ValueError as e:
        print(f"Expected error caught: {type(e).__name__}")


def example_retry_logic():
    """Example: Demonstrate retry logic with custom configuration."""
    print("\n=== Example 7: Custom Retry Configuration ===\n")

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ERROR: SENTINEL_WORKSPACE_ID environment variable not set")
        return

    try:
        credential = get_credential()

        # Create client with custom retry settings
        client = SentinelClient(
            workspace_id=workspace_id,
            credential=credential,
            max_retries=5,
            retry_delay_seconds=2.0,
            timeout_seconds=600
        )

        print(f"Client configured with:")
        info = client.get_workspace_info()
        print(f"  Max retries: {info['max_retries']}")
        print(f"  Retry delay: {info['retry_delay_seconds']}s")
        print(f"  Timeout: {info['timeout_seconds']}s")

        # Test connection
        if client.validate_connection():
            print("Connection successful with custom retry settings")

    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Yellowstone - Real Azure Sentinel Integration Examples")
    print("=" * 60)

    examples = [
        example_basic_connection,
        example_simple_query,
        example_security_alerts,
        example_create_persistent_graph,
        example_query_graph,
        example_error_handling,
        example_retry_logic,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nExample failed with error: {e}")

    print("\n" + "=" * 60)
    print("Examples completed")
    print("=" * 60)


if __name__ == '__main__':
    main()
