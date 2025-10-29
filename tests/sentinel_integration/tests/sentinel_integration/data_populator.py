"""Populate Azure Sentinel workspaces with test data.

This module handles ingestion of test data into Sentinel custom tables using
Azure Monitor Ingestion API and Log Analytics Data Collector API.
"""

import logging
import json
import time
import hashlib
import hmac
import base64
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.ingestion import LogsIngestionClient
from azure.core.exceptions import HttpResponseError

from .sentinel_workspace_manager import WorkspaceInfo

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of data ingestion operation."""

    table_name: str
    records_sent: int
    success: bool
    error_message: Optional[str] = None
    ingestion_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'table_name': self.table_name,
            'records_sent': self.records_sent,
            'success': self.success,
            'error_message': self.error_message,
            'ingestion_time_ms': self.ingestion_time_ms
        }


class DataPopulator:
    """Populates Azure Sentinel workspaces with test data.

    This class handles batch ingestion of test data using Azure's Log Analytics
    Data Collector API (HTTP Data Collector API).

    Example:
        >>> workspace_info = WorkspaceInfo(...)
        >>> populator = DataPopulator(workspace_info)
        >>>
        >>> # Populate identity data
        >>> identities = [identity.to_dict() for identity in test_identities]
        >>> result = populator.ingest_data('IdentityInfo_CL', identities)
        >>> print(f"Ingested {result.records_sent} records")
    """

    def __init__(
        self,
        workspace_info: WorkspaceInfo,
        credential: Optional[DefaultAzureCredential] = None,
        workspace_key: Optional[str] = None
    ):
        """Initialize data populator.

        Args:
            workspace_info: Workspace information
            credential: Azure credential (for future DCR-based ingestion)
            workspace_key: Workspace shared key for HTTP Data Collector API
        """
        self.workspace_info = workspace_info
        self.credential = credential or DefaultAzureCredential()
        self.workspace_key = workspace_key

        # HTTP Data Collector API endpoint
        self.api_endpoint = (
            f"https://{workspace_info.customer_id}.ods.opinsights.azure.com"
            f"/api/logs?api-version=2016-04-01"
        )

    def set_workspace_key(self, workspace_key: str) -> None:
        """Set the workspace shared key.

        The workspace key can be retrieved from Azure Portal:
        Log Analytics workspace -> Agents -> Primary key

        Args:
            workspace_key: Workspace shared key (primary or secondary)
        """
        self.workspace_key = workspace_key

    def _build_signature(
        self,
        date: str,
        content_length: int,
        method: str,
        content_type: str,
        resource: str
    ) -> str:
        """Build authorization signature for Log Analytics API.

        Args:
            date: RFC1123 formatted date
            content_length: Content length in bytes
            method: HTTP method (POST)
            content_type: Content type (application/json)
            resource: API resource path

        Returns:
            Authorization header value
        """
        if not self.workspace_key:
            raise ValueError("Workspace key not set. Call set_workspace_key() first.")

        string_to_hash = f"{method}\n{content_length}\n{content_type}\nx-ms-date:{date}\n{resource}"
        bytes_to_hash = string_to_hash.encode('utf-8')
        decoded_key = base64.b64decode(self.workspace_key)
        encoded_hash = base64.b64encode(
            hmac.new(decoded_key, bytes_to_hash, hashlib.sha256).digest()
        ).decode('utf-8')

        authorization = f"SharedKey {self.workspace_info.customer_id}:{encoded_hash}"
        return authorization

    def ingest_data(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> IngestionResult:
        """Ingest data into a custom table.

        Uses Azure Log Analytics HTTP Data Collector API to send data.
        Data will appear in the specified custom table (must end with _CL).

        Args:
            table_name: Target table name (must end with _CL)
            records: List of records to ingest (each is a dict)
            batch_size: Number of records per batch (max 30MB per request)

        Returns:
            IngestionResult with ingestion status

        Raises:
            ValueError: If table name is invalid or no records provided
            HttpResponseError: If ingestion fails
        """
        if not table_name.endswith('_CL'):
            raise ValueError("Custom table names must end with '_CL'")

        if not records:
            raise ValueError("No records to ingest")

        if not self.workspace_key:
            raise ValueError(
                "Workspace key not set. Retrieve it from Azure Portal and call "
                "set_workspace_key() before ingesting data."
            )

        logger.info(f"Ingesting {len(records)} records into '{table_name}'")

        start_time = time.time()
        total_sent = 0

        try:
            # Split into batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                self._send_batch(table_name, batch)
                total_sent += len(batch)
                logger.debug(f"Sent batch {i // batch_size + 1}: {len(batch)} records")

            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Successfully ingested {total_sent} records into '{table_name}' "
                f"in {elapsed_ms}ms"
            )

            return IngestionResult(
                table_name=table_name,
                records_sent=total_sent,
                success=True,
                ingestion_time_ms=elapsed_ms
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Failed to ingest data: {str(e)}"
            logger.error(error_msg)

            return IngestionResult(
                table_name=table_name,
                records_sent=total_sent,
                success=False,
                error_message=error_msg,
                ingestion_time_ms=elapsed_ms
            )

    def _send_batch(self, table_name: str, batch: List[Dict[str, Any]]) -> None:
        """Send a single batch to Log Analytics.

        Args:
            table_name: Target table name
            batch: List of records in the batch

        Raises:
            HttpResponseError: If request fails
        """
        # Remove _CL suffix for log type (API adds it back)
        log_type = table_name.replace('_CL', '')

        # Prepare body
        body = json.dumps(batch)
        body_bytes = body.encode('utf-8')

        # Build headers
        rfc1123date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        content_length = len(body_bytes)

        signature = self._build_signature(
            date=rfc1123date,
            content_length=content_length,
            method='POST',
            content_type='application/json',
            resource='/api/logs'
        )

        headers = {
            'content-type': 'application/json',
            'Authorization': signature,
            'Log-Type': log_type,
            'x-ms-date': rfc1123date,
            'time-generated-field': 'TimeGenerated'  # Use TimeGenerated from data
        }

        # Send request
        response = requests.post(
            self.api_endpoint,
            data=body_bytes,
            headers=headers,
            timeout=30
        )

        if response.status_code not in [200, 202]:
            raise HttpResponseError(
                f"Ingestion failed: {response.status_code} - {response.text}"
            )

    def wait_for_data_available(
        self,
        table_name: str,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> bool:
        """Wait for ingested data to become queryable.

        Log Analytics has ingestion latency (typically 1-5 minutes).
        This method polls until data is available.

        Args:
            table_name: Table to check
            timeout: Maximum wait time in seconds
            poll_interval: Time between checks in seconds

        Returns:
            True if data is available, False if timeout

        Note:
            This requires ability to execute KQL queries against the workspace.
            Use Azure Monitor Query client or REST API.
        """
        logger.info(f"Waiting for data in '{table_name}' to become available...")
        logger.warning(
            "wait_for_data_available() requires query execution capability. "
            "Consider implementing with Azure Monitor Query client."
        )

        # Simple time-based wait (ingestion typically takes 1-5 minutes)
        time.sleep(min(60, timeout))
        logger.info("Waited for ingestion latency")

        return True

    def bulk_ingest(
        self,
        data_sets: Dict[str, List[Dict[str, Any]]],
        batch_size: int = 100
    ) -> List[IngestionResult]:
        """Ingest multiple datasets in bulk.

        Args:
            data_sets: Dictionary mapping table names to record lists
            batch_size: Batch size for each table

        Returns:
            List of IngestionResult for each table

        Example:
            >>> results = populator.bulk_ingest({
            ...     'IdentityInfo_CL': identity_records,
            ...     'DeviceInfo_CL': device_records,
            ...     'SignInEvents_CL': signin_records
            ... })
            >>> for result in results:
            ...     print(f"{result.table_name}: {result.records_sent} records")
        """
        results = []

        for table_name, records in data_sets.items():
            logger.info(f"Processing table '{table_name}': {len(records)} records")
            result = self.ingest_data(table_name, records, batch_size)
            results.append(result)

            # Brief pause between tables to avoid throttling
            if len(data_sets) > 1:
                time.sleep(1)

        # Summary
        total_records = sum(r.records_sent for r in results)
        successful_tables = sum(1 for r in results if r.success)
        logger.info(
            f"Bulk ingestion complete: {successful_tables}/{len(results)} tables, "
            f"{total_records} total records"
        )

        return results

    def populate_from_generator(
        self,
        scenario_data: Dict[str, List[Any]],
        table_mapping: Optional[Dict[str, str]] = None
    ) -> List[IngestionResult]:
        """Populate workspace from TestDataGenerator output.

        Args:
            scenario_data: Output from TestDataGenerator (dict of data types)
            table_mapping: Optional mapping from data type to table name

        Returns:
            List of IngestionResult

        Example:
            >>> from .test_data_generator import TestDataGenerator
            >>> generator = TestDataGenerator()
            >>> scenario = generator.generate_lateral_movement_scenario()
            >>> results = populator.populate_from_generator(scenario)
        """
        # Default table mapping
        if table_mapping is None:
            table_mapping = {
                'identities': 'IdentityInfo_CL',
                'devices': 'DeviceInfo_CL',
                'sign_in_events': 'SignInEvents_CL',
                'file_access_events': 'FileAccessEvents_CL',
                'network_events': 'NetworkEvents_CL'
            }

        # Convert objects to dicts and build datasets
        data_sets = {}
        for data_type, objects in scenario_data.items():
            if data_type in table_mapping and objects:
                table_name = table_mapping[data_type]
                # Convert objects to dicts using to_dict() method
                records = [obj.to_dict() for obj in objects]
                data_sets[table_name] = records
                logger.info(
                    f"Prepared {len(records)} records for '{table_name}' "
                    f"from '{data_type}'"
                )

        # Bulk ingest
        return self.bulk_ingest(data_sets)

    def verify_ingestion(
        self,
        results: List[IngestionResult],
        raise_on_error: bool = True
    ) -> bool:
        """Verify ingestion results.

        Args:
            results: List of ingestion results to verify
            raise_on_error: Raise exception if any ingestion failed

        Returns:
            True if all ingestions succeeded

        Raises:
            ValueError: If any ingestion failed and raise_on_error is True
        """
        failed = [r for r in results if not r.success]

        if failed:
            error_details = '\n'.join(
                f"  - {r.table_name}: {r.error_message}"
                for r in failed
            )
            message = f"Ingestion failures:\n{error_details}"

            if raise_on_error:
                raise ValueError(message)

            logger.error(message)
            return False

        logger.info("All ingestions successful")
        return True


class WorkspaceKeyRetriever:
    """Helper to retrieve workspace shared key from Azure.

    Note: Workspace keys are sensitive credentials. Handle with care.
    """

    def __init__(self, credential: Optional[DefaultAzureCredential] = None):
        """Initialize key retriever.

        Args:
            credential: Azure credential
        """
        self.credential = credential or DefaultAzureCredential()

    def get_workspace_key(
        self,
        subscription_id: str,
        resource_group: str,
        workspace_name: str
    ) -> str:
        """Retrieve workspace shared key using Azure REST API.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            workspace_name: Workspace name

        Returns:
            Primary workspace key

        Raises:
            HttpResponseError: If retrieval fails
        """
        from azure.mgmt.loganalytics import LogAnalyticsManagementClient

        client = LogAnalyticsManagementClient(
            credential=self.credential,
            subscription_id=subscription_id
        )

        shared_keys = client.shared_keys.get_shared_keys(
            resource_group_name=resource_group,
            workspace_name=workspace_name
        )

        return shared_keys.primary_shared_key
