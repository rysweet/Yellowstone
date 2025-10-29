"""Generate realistic security test data for Azure Sentinel.

This module creates graph-structured security data that mimics real-world
scenarios for testing Cypher-to-KQL translation and query execution.
"""

import random
import string
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import hashlib


class EventType(Enum):
    """Types of security events."""
    SIGN_IN = "SignIn"
    DEVICE_LOGON = "DeviceLogon"
    FILE_ACCESS = "FileAccess"
    NETWORK_CONNECTION = "NetworkConnection"
    PROCESS_CREATION = "ProcessCreation"


class RiskLevel(Enum):
    """Risk levels for events."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class Identity:
    """User identity information."""
    user_id: str
    user_principal_name: str
    display_name: str
    department: str
    job_title: str
    location: str
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ingestion."""
        return {
            'TimeGenerated': datetime.utcnow().isoformat() + 'Z',
            'UserId': self.user_id,
            'UserPrincipalName': self.user_principal_name,
            'DisplayName': self.display_name,
            'Department': self.department,
            'JobTitle': self.job_title,
            'Location': self.location,
            'RiskLevel': self.risk_level
        }


@dataclass
class Device:
    """Device information."""
    device_id: str
    device_name: str
    device_type: str
    os_platform: str
    os_version: str
    owner_user_id: str
    location: str
    last_seen: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ingestion."""
        return {
            'TimeGenerated': self.last_seen.isoformat() + 'Z',
            'DeviceId': self.device_id,
            'DeviceName': self.device_name,
            'DeviceType': self.device_type,
            'OSPlatform': self.os_platform,
            'OSVersion': self.os_version,
            'OwnerUserId': self.owner_user_id,
            'Location': self.location,
            'LastSeen': self.last_seen.isoformat() + 'Z'
        }


@dataclass
class SignInEvent:
    """User sign-in event."""
    event_id: str
    timestamp: datetime
    user_id: str
    user_principal_name: str
    device_id: str
    ip_address: str
    location: str
    app_name: str
    result: str
    risk_level: str
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ingestion."""
        return {
            'TimeGenerated': self.timestamp.isoformat() + 'Z',
            'EventId': self.event_id,
            'UserId': self.user_id,
            'UserPrincipalName': self.user_principal_name,
            'DeviceId': self.device_id,
            'IPAddress': self.ip_address,
            'Location': self.location,
            'AppName': self.app_name,
            'Result': self.result,
            'RiskLevel': self.risk_level,
            'FailureReason': self.failure_reason or ''
        }


@dataclass
class FileAccessEvent:
    """File access event."""
    event_id: str
    timestamp: datetime
    user_id: str
    device_id: str
    file_path: str
    file_name: str
    action: str
    file_hash: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ingestion."""
        return {
            'TimeGenerated': self.timestamp.isoformat() + 'Z',
            'EventId': self.event_id,
            'UserId': self.user_id,
            'DeviceId': self.device_id,
            'FilePath': self.file_path,
            'FileName': self.file_name,
            'Action': self.action,
            'FileHash': self.file_hash
        }


@dataclass
class NetworkConnectionEvent:
    """Network connection event."""
    event_id: str
    timestamp: datetime
    device_id: str
    source_ip: str
    destination_ip: str
    destination_port: int
    protocol: str
    bytes_sent: int
    bytes_received: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ingestion."""
        return {
            'TimeGenerated': self.timestamp.isoformat() + 'Z',
            'EventId': self.event_id,
            'DeviceId': self.device_id,
            'SourceIP': self.source_ip,
            'DestinationIP': self.destination_ip,
            'DestinationPort': self.destination_port,
            'Protocol': self.protocol,
            'BytesSent': self.bytes_sent,
            'BytesReceived': self.bytes_received
        }


class TestDataGenerator:
    """Generates realistic graph-structured security test data.

    Creates interconnected security data that represents realistic scenarios:
    - Users with identities and devices
    - Sign-in events linking users to devices
    - File access events
    - Network connections
    - Multi-hop attack paths

    Example:
        >>> generator = TestDataGenerator(seed=42)
        >>> scenario = generator.generate_lateral_movement_scenario()
        >>> print(f"Generated {len(scenario['identities'])} users")
        >>> print(f"Generated {len(scenario['sign_in_events'])} sign-in events")
    """

    def __init__(self, seed: Optional[int] = None):
        """Initialize test data generator.

        Args:
            seed: Random seed for reproducible data generation
        """
        if seed is not None:
            random.seed(seed)

        self.departments = ['IT', 'Finance', 'HR', 'Sales', 'Engineering', 'Marketing']
        self.locations = ['New York', 'London', 'Tokyo', 'Sydney', 'Singapore', 'Paris']
        self.app_names = ['Office365', 'Salesforce', 'GitHub', 'Jira', 'Slack', 'Azure Portal']
        self.os_platforms = ['Windows', 'macOS', 'Linux']
        self.device_types = ['Workstation', 'Laptop', 'Server', 'Mobile']

    def generate_user_id(self, name: str) -> str:
        """Generate a consistent user ID from name."""
        return hashlib.sha256(name.encode()).hexdigest()[:16]

    def generate_device_id(self, name: str) -> str:
        """Generate a consistent device ID from name."""
        return hashlib.sha256(f"device-{name}".encode()).hexdigest()[:16]

    def generate_event_id(self) -> str:
        """Generate a unique event ID."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    def generate_ip_address(self, subnet: str = "10.0") -> str:
        """Generate a random IP address."""
        return f"{subnet}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def generate_file_hash(self, file_name: str) -> str:
        """Generate a consistent file hash."""
        return hashlib.sha256(file_name.encode()).hexdigest()

    def create_identity(
        self,
        name: str,
        department: str,
        job_title: str,
        risk_level: str = "Low"
    ) -> Identity:
        """Create a user identity.

        Args:
            name: User's display name
            department: Department name
            job_title: Job title
            risk_level: Risk assessment level

        Returns:
            Identity object
        """
        user_id = self.generate_user_id(name)
        email = f"{name.lower().replace(' ', '.')}@contoso.com"

        return Identity(
            user_id=user_id,
            user_principal_name=email,
            display_name=name,
            department=department,
            job_title=job_title,
            location=random.choice(self.locations),
            risk_level=risk_level
        )

    def create_device(
        self,
        device_name: str,
        owner_user_id: str,
        device_type: str = "Workstation"
    ) -> Device:
        """Create a device.

        Args:
            device_name: Device name
            owner_user_id: ID of device owner
            device_type: Type of device

        Returns:
            Device object
        """
        device_id = self.generate_device_id(device_name)
        os_platform = random.choice(self.os_platforms)

        os_versions = {
            'Windows': f'10.0.{random.randint(19041, 22631)}',
            'macOS': f'14.{random.randint(0, 6)}.0',
            'Linux': f'5.{random.randint(4, 19)}.0'
        }

        return Device(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            os_platform=os_platform,
            os_version=os_versions[os_platform],
            owner_user_id=owner_user_id,
            location=random.choice(self.locations),
            last_seen=datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
        )

    def create_sign_in_event(
        self,
        user_id: str,
        user_principal_name: str,
        device_id: str,
        timestamp: Optional[datetime] = None,
        result: str = "Success",
        risk_level: str = "Low"
    ) -> SignInEvent:
        """Create a sign-in event.

        Args:
            user_id: User ID
            user_principal_name: User email
            device_id: Device ID
            timestamp: Event timestamp (now if None)
            result: Success or Failure
            risk_level: Risk level

        Returns:
            SignInEvent object
        """
        return SignInEvent(
            event_id=self.generate_event_id(),
            timestamp=timestamp or datetime.utcnow(),
            user_id=user_id,
            user_principal_name=user_principal_name,
            device_id=device_id,
            ip_address=self.generate_ip_address(),
            location=random.choice(self.locations),
            app_name=random.choice(self.app_names),
            result=result,
            risk_level=risk_level,
            failure_reason="Invalid password" if result == "Failure" else None
        )

    def create_file_access_event(
        self,
        user_id: str,
        device_id: str,
        file_path: str,
        action: str = "Read",
        timestamp: Optional[datetime] = None
    ) -> FileAccessEvent:
        """Create a file access event.

        Args:
            user_id: User ID
            device_id: Device ID
            file_path: Full file path
            action: Read, Write, Delete, etc.
            timestamp: Event timestamp

        Returns:
            FileAccessEvent object
        """
        file_name = file_path.split('/')[-1]

        return FileAccessEvent(
            event_id=self.generate_event_id(),
            timestamp=timestamp or datetime.utcnow(),
            user_id=user_id,
            device_id=device_id,
            file_path=file_path,
            file_name=file_name,
            action=action,
            file_hash=self.generate_file_hash(file_name)
        )

    def create_network_connection(
        self,
        device_id: str,
        destination_ip: str,
        destination_port: int,
        protocol: str = "TCP",
        timestamp: Optional[datetime] = None
    ) -> NetworkConnectionEvent:
        """Create a network connection event.

        Args:
            device_id: Source device ID
            destination_ip: Destination IP address
            destination_port: Destination port
            protocol: TCP, UDP, etc.
            timestamp: Event timestamp

        Returns:
            NetworkConnectionEvent object
        """
        return NetworkConnectionEvent(
            event_id=self.generate_event_id(),
            timestamp=timestamp or datetime.utcnow(),
            device_id=device_id,
            source_ip=self.generate_ip_address(),
            destination_ip=destination_ip,
            destination_port=destination_port,
            protocol=protocol,
            bytes_sent=random.randint(100, 100000),
            bytes_received=random.randint(100, 100000)
        )

    def generate_basic_scenario(self, num_users: int = 10) -> Dict[str, List[Any]]:
        """Generate basic test scenario with users and devices.

        Args:
            num_users: Number of users to generate

        Returns:
            Dictionary with identities, devices, and events
        """
        identities = []
        devices = []
        sign_in_events = []

        for i in range(num_users):
            # Create user
            name = f"User{i:03d}"
            department = random.choice(self.departments)
            identity = self.create_identity(
                name=name,
                department=department,
                job_title=f"{department} Analyst"
            )
            identities.append(identity)

            # Create device for user
            device = self.create_device(
                device_name=f"WKS-{name}",
                owner_user_id=identity.user_id
            )
            devices.append(device)

            # Create sign-in events
            for _ in range(random.randint(1, 5)):
                sign_in = self.create_sign_in_event(
                    user_id=identity.user_id,
                    user_principal_name=identity.user_principal_name,
                    device_id=device.device_id,
                    timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 24))
                )
                sign_in_events.append(sign_in)

        return {
            'identities': identities,
            'devices': devices,
            'sign_in_events': sign_in_events
        }

    def generate_lateral_movement_scenario(self) -> Dict[str, List[Any]]:
        """Generate lateral movement attack scenario.

        Simulates an attacker compromising accounts and moving through network.

        Returns:
            Dictionary with complete attack scenario data
        """
        identities = []
        devices = []
        sign_in_events = []
        file_access_events = []
        network_events = []

        # Create compromised user (Patient Zero)
        patient_zero = self.create_identity(
            name="Alice Johnson",
            department="Finance",
            job_title="Financial Analyst",
            risk_level="High"
        )
        identities.append(patient_zero)

        patient_zero_device = self.create_device(
            device_name="WKS-ALICE",
            owner_user_id=patient_zero.user_id
        )
        devices.append(patient_zero_device)

        # Initial compromise
        base_time = datetime.utcnow() - timedelta(hours=24)
        sign_in_events.append(self.create_sign_in_event(
            user_id=patient_zero.user_id,
            user_principal_name=patient_zero.user_principal_name,
            device_id=patient_zero_device.device_id,
            timestamp=base_time,
            result="Failure",
            risk_level="High"
        ))

        # Successful compromise
        sign_in_events.append(self.create_sign_in_event(
            user_id=patient_zero.user_id,
            user_principal_name=patient_zero.user_principal_name,
            device_id=patient_zero_device.device_id,
            timestamp=base_time + timedelta(minutes=5),
            result="Success",
            risk_level="High"
        ))

        # Lateral movement targets
        targets = [
            ("Bob Smith", "IT", "System Administrator", "High"),
            ("Carol White", "Finance", "Finance Manager", "Medium"),
            ("Dave Brown", "IT", "Security Engineer", "Critical")
        ]

        for i, (name, dept, title, risk) in enumerate(targets):
            # Create target user
            target = self.create_identity(
                name=name,
                department=dept,
                job_title=title,
                risk_level=risk
            )
            identities.append(target)

            target_device = self.create_device(
                device_name=f"WKS-{name.split()[0].upper()}",
                owner_user_id=target.user_id
            )
            devices.append(target_device)

            # Network reconnaissance from previous device
            prev_device = devices[i]
            network_events.append(self.create_network_connection(
                device_id=prev_device.device_id,
                destination_ip=self.generate_ip_address(),
                destination_port=445,  # SMB
                timestamp=base_time + timedelta(hours=i+1, minutes=10)
            ))

            # Credential access
            file_access_events.append(self.create_file_access_event(
                user_id=identities[i].user_id,
                device_id=prev_device.device_id,
                file_path=f"C:/Windows/System32/config/SAM",
                action="Read",
                timestamp=base_time + timedelta(hours=i+1, minutes=20)
            ))

            # Lateral movement sign-in
            sign_in_events.append(self.create_sign_in_event(
                user_id=target.user_id,
                user_principal_name=target.user_principal_name,
                device_id=target_device.device_id,
                timestamp=base_time + timedelta(hours=i+1, minutes=30),
                result="Success",
                risk_level=risk
            ))

        return {
            'identities': identities,
            'devices': devices,
            'sign_in_events': sign_in_events,
            'file_access_events': file_access_events,
            'network_events': network_events
        }

    def generate_device_ownership_scenario(self) -> Dict[str, List[Any]]:
        """Generate scenario for testing device ownership queries.

        Returns:
            Dictionary with users, devices, and multiple devices per user
        """
        identities = []
        devices = []
        sign_in_events = []

        # Create users with multiple devices
        for i in range(5):
            name = f"PowerUser{i}"
            identity = self.create_identity(
                name=name,
                department="IT",
                job_title="Senior Engineer"
            )
            identities.append(identity)

            # Each user has 2-4 devices
            for device_num in range(random.randint(2, 4)):
                device_types = ["Workstation", "Laptop", "Mobile"]
                device = self.create_device(
                    device_name=f"DEV-{name}-{device_num}",
                    owner_user_id=identity.user_id,
                    device_type=random.choice(device_types)
                )
                devices.append(device)

                # Sign-ins on each device
                for _ in range(random.randint(1, 3)):
                    sign_in = self.create_sign_in_event(
                        user_id=identity.user_id,
                        user_principal_name=identity.user_principal_name,
                        device_id=device.device_id,
                        timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 72))
                    )
                    sign_in_events.append(sign_in)

        return {
            'identities': identities,
            'devices': devices,
            'sign_in_events': sign_in_events
        }

    def generate_file_access_pattern_scenario(self) -> Dict[str, List[Any]]:
        """Generate scenario for file access pattern analysis.

        Returns:
            Dictionary with users, devices, and file access events
        """
        identities = []
        devices = []
        file_access_events = []

        sensitive_files = [
            "/home/shared/financials/Q4_Report.xlsx",
            "/home/shared/hr/salaries.csv",
            "/home/shared/legal/contracts.pdf",
            "/home/shared/secrets/api_keys.txt"
        ]

        # Create users accessing files
        for i in range(8):
            name = f"Employee{i}"
            identity = self.create_identity(
                name=name,
                department=random.choice(self.departments),
                job_title="Analyst"
            )
            identities.append(identity)

            device = self.create_device(
                device_name=f"WKS-{name}",
                owner_user_id=identity.user_id
            )
            devices.append(device)

            # Some users access sensitive files
            if i < 3:  # First 3 users access sensitive files
                for file_path in random.sample(sensitive_files, k=random.randint(1, 3)):
                    file_access_events.append(self.create_file_access_event(
                        user_id=identity.user_id,
                        device_id=device.device_id,
                        file_path=file_path,
                        action=random.choice(["Read", "Write", "Delete"]),
                        timestamp=datetime.utcnow() - timedelta(hours=random.randint(0, 48))
                    ))

        return {
            'identities': identities,
            'devices': devices,
            'file_access_events': file_access_events
        }
