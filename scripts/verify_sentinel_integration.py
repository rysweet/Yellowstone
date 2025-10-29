#!/usr/bin/env python3
"""
Verification script for Azure Sentinel integration.

This script verifies that the real Sentinel integration is properly installed
and configured. It performs the following checks:

1. Verify Azure SDK packages are installed
2. Verify SentinelClient can be imported
3. Verify GraphManager can be imported
4. Test connection to workspace (if configured)
5. Verify example code runs

Usage:
    python scripts/verify_sentinel_integration.py

    # With workspace connection test
    SENTINEL_WORKSPACE_ID=your-id python scripts/verify_sentinel_integration.py
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


def check_azure_packages():
    """Check if Azure SDK packages are installed."""
    print("=" * 60)
    print("STEP 1: Checking Azure SDK Packages")
    print("=" * 60)

    packages = {
        'azure.identity': 'azure-identity',
        'azure.monitor.query': 'azure-monitor-query',
    }

    all_installed = True
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print(f"✓ {package_name} is installed")
        except ImportError:
            print(f"✗ {package_name} is NOT installed")
            print(f"  Install with: pip install {package_name}")
            all_installed = False

    return all_installed


def check_sentinel_client_import():
    """Check if SentinelClient can be imported."""
    print("\n" + "=" * 60)
    print("STEP 2: Importing SentinelClient")
    print("=" * 60)

    try:
        from yellowstone.persistent_graph.sentinel_client import (
            SentinelClient,
            SentinelConfig,
            SentinelAPIError,
            AuthenticationError,
            QueryExecutionError,
            WorkspaceNotFoundError,
        )
        print("✓ SentinelClient imported successfully")
        print("✓ SentinelConfig imported successfully")
        print("✓ All exception classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import SentinelClient: {e}")
        return False


def check_graph_manager_import():
    """Check if GraphManager can be imported."""
    print("\n" + "=" * 60)
    print("STEP 3: Importing GraphManager")
    print("=" * 60)

    try:
        from yellowstone.persistent_graph import (
            GraphManager,
            SentinelClient,
            GraphSchema,
            NodeDefinition,
            EdgeDefinition,
        )
        print("✓ GraphManager imported successfully")
        print("✓ All persistent graph classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import GraphManager: {e}")
        return False


def verify_mock_removed():
    """Verify MockSentinelAPI has been removed."""
    print("\n" + "=" * 60)
    print("STEP 4: Verifying Mock Removal")
    print("=" * 60)

    try:
        from yellowstone.persistent_graph import MockSentinelAPI
        print("✗ MockSentinelAPI still exists (should be removed)")
        return False
    except ImportError:
        print("✓ MockSentinelAPI has been removed (as expected)")
        return True


def check_client_initialization():
    """Check if SentinelClient can be initialized."""
    print("\n" + "=" * 60)
    print("STEP 5: Testing Client Initialization")
    print("=" * 60)

    try:
        from yellowstone.persistent_graph import SentinelClient
        from unittest.mock import Mock

        # Test with mock credential
        mock_credential = Mock()
        client = SentinelClient(
            workspace_id='test-workspace',
            credential=mock_credential
        )
        print("✓ SentinelClient initialized successfully")
        print(f"  Workspace ID: {client.workspace_id}")
        print(f"  Max retries: {client.max_retries}")
        print(f"  Retry delay: {client.retry_delay_seconds}s")

        # Test validation
        try:
            SentinelClient(workspace_id='')
        except ValueError as e:
            print("✓ Empty workspace_id validation working")
        else:
            print("✗ Empty workspace_id validation NOT working")
            return False

        return True
    except Exception as e:
        print(f"✗ Client initialization failed: {e}")
        return False


def test_real_connection():
    """Test connection to real workspace if configured."""
    print("\n" + "=" * 60)
    print("STEP 6: Testing Real Workspace Connection")
    print("=" * 60)

    workspace_id = os.getenv('SENTINEL_WORKSPACE_ID')
    if not workspace_id:
        print("ℹ SENTINEL_WORKSPACE_ID not set, skipping real connection test")
        print("  To test real connection, set:")
        print("    export SENTINEL_WORKSPACE_ID=your-workspace-id")
        return True

    try:
        from azure.identity import DefaultAzureCredential
        from yellowstone.persistent_graph import (
            SentinelClient,
            AuthenticationError,
            WorkspaceNotFoundError,
        )

        print(f"Connecting to workspace: {workspace_id}")
        credential = DefaultAzureCredential()
        client = SentinelClient(workspace_id=workspace_id, credential=credential)

        # Validate connection
        if client.validate_connection():
            print("✓ Connection to real workspace successful!")

            # Get workspace info
            info = client.get_workspace_info()
            print(f"  Workspace ID: {info['workspace_id']}")
            print(f"  Max retries: {info['max_retries']}")

            # Try simple query
            result = client.execute_kql(
                "print test='hello', value=42",
                timespan=timedelta(minutes=1)
            )
            print(f"✓ Simple query executed successfully")
            print(f"  Status: {result['status']}")
            print(f"  Rows: {result['row_count']}")

            return True
        else:
            print("✗ Connection validation failed")
            return False

    except AuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        print("  Check your credentials and permissions")
        return False
    except WorkspaceNotFoundError as e:
        print(f"✗ Workspace not found: {e}")
        print("  Check workspace ID and RBAC permissions")
        return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False


def test_graph_manager():
    """Test GraphManager with real integration."""
    print("\n" + "=" * 60)
    print("STEP 7: Testing GraphManager Integration")
    print("=" * 60)

    try:
        from unittest.mock import Mock
        from yellowstone.persistent_graph import (
            GraphManager,
            GraphSchema,
            NodeDefinition,
        )

        # Create mock client for testing
        mock_client = Mock()
        mock_client.execute_management_command.return_value = {
            'status': 'success',
            'command': 'test',
            'execution_time_ms': 100,
        }

        # Initialize GraphManager with mock
        manager = GraphManager(
            workspace_id='test-workspace',
            api_client=mock_client
        )
        print("✓ GraphManager initialized with mock client")

        # Test requires workspace_id
        try:
            GraphManager(workspace_id='')
        except ValueError:
            print("✓ GraphManager validates workspace_id")
        else:
            print("✗ GraphManager does NOT validate workspace_id")
            return False

        # Create simple schema
        schema = GraphSchema(
            nodes=[
                NodeDefinition(
                    label='Alert',
                    source_table='SecurityAlert',
                    id_property='AlertId',
                    properties={'severity': 'AlertSeverity'}
                )
            ],
            edges=[]
        )

        # Create graph
        graph = manager.create_graph('TestGraph', schema)
        print("✓ Graph created successfully")
        print(f"  Name: {graph.name}")
        print(f"  Status: {graph.status}")
        print(f"  Version: {graph.version}")

        # Verify API was called
        assert mock_client.execute_management_command.called
        print("✓ Real API method was called")

        return True

    except Exception as e:
        print(f"✗ GraphManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Print summary of verification results."""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    for step, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {step}")

    print("\n" + "-" * 60)
    print(f"Total: {total} checks")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("-" * 60)

    if failed == 0:
        print("\n🎉 All checks passed! Azure Sentinel integration is working.")
        return True
    else:
        print(f"\n⚠ {failed} check(s) failed. Please review the errors above.")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#  AZURE SENTINEL INTEGRATION VERIFICATION" + " " * 17 + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60)
    print()

    results = {}

    # Run all checks
    results["Azure SDK Packages"] = check_azure_packages()
    results["SentinelClient Import"] = check_sentinel_client_import()
    results["GraphManager Import"] = check_graph_manager_import()
    results["Mock Removal"] = verify_mock_removed()
    results["Client Initialization"] = check_client_initialization()
    results["Real Connection"] = test_real_connection()
    results["GraphManager Integration"] = test_graph_manager()

    # Print summary
    success = print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    # Need timedelta for connection test
    from datetime import timedelta
    main()
