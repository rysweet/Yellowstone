"""Real Azure Sentinel integration tests.

This package provides infrastructure for testing Yellowstone's Cypher-to-KQL
translation against actual Azure Sentinel workspaces.

WARNING: These tests create real Azure resources and may incur costs.
"""

from .sentinel_workspace_manager import SentinelWorkspaceManager
from .test_data_generator import TestDataGenerator
from .data_populator import DataPopulator

__all__ = [
    'SentinelWorkspaceManager',
    'TestDataGenerator',
    'DataPopulator',
]
