"""
Tests for schema mapper functionality.
"""

import pytest
from pathlib import Path

from yellowstone.schema import SchemaMapper


class TestSchemaMapperInitialization:
    """Test SchemaMapper initialization and schema loading."""

    def test_initialization_with_default_schema(self):
        """Test that mapper initializes with default schema."""
        mapper = SchemaMapper()
        assert mapper.schema is not None
        assert mapper.schema.version == "1.0.0"

    def test_schema_loaded_with_node_mappings(self):
        """Test that schema loads node mappings."""
        mapper = SchemaMapper()
        labels = mapper.get_cypher_labels()
        assert "User" in labels
        assert "Device" in labels
        assert "SecurityEvent" in labels
        assert "File" in labels
        assert "Process" in labels

    def test_schema_loaded_with_edge_mappings(self):
        """Test that schema loads edge/relationship mappings."""
        mapper = SchemaMapper()
        relationships = mapper.get_relationships()
        assert "LOGGED_IN" in relationships
        assert "OWNS" in relationships
        assert "ACCESSED" in relationships
        assert "EXECUTED" in relationships
        assert "CONNECTED_TO" in relationships


class TestLabelToTableMapping:
    """Test Cypher label to Sentinel table mappings."""

    def test_user_to_identity_info(self):
        """Test User maps to IdentityInfo."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("User") == "IdentityInfo"

    def test_device_to_device_info(self):
        """Test Device maps to DeviceInfo."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("Device") == "DeviceInfo"

    def test_security_event_to_security_event_table(self):
        """Test SecurityEvent maps to SecurityEvent table."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("SecurityEvent") == "SecurityEvent"

    def test_file_to_file_events(self):
        """Test File maps to FileEvents."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("File") == "FileEvents"

    def test_process_to_process_events(self):
        """Test Process maps to ProcessEvents."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("Process") == "ProcessEvents"

    def test_ip_to_network_session(self):
        """Test IP maps to NetworkSession."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("IP") == "NetworkSession"

    def test_unknown_label_returns_none(self):
        """Test that unknown label returns None."""
        mapper = SchemaMapper()
        assert mapper.get_sentinel_table("UnknownLabel") is None


class TestPropertyFieldMapping:
    """Test property to Sentinel field mappings."""

    def test_user_username_property(self):
        """Test User.username maps to AccountName."""
        mapper = SchemaMapper()
        field = mapper.get_property_field("User", "username")
        assert field is not None
        assert field["sentinel_field"] == "AccountName"
        assert field["type"] == "string"

    def test_user_email_property(self):
        """Test User.email maps to AccountUpn."""
        mapper = SchemaMapper()
        field = mapper.get_property_field("User", "email")
        assert field is not None
        assert field["sentinel_field"] == "AccountUpn"

    def test_device_name_property(self):
        """Test Device.device_name maps to DeviceName."""
        mapper = SchemaMapper()
        field = mapper.get_property_field("Device", "device_name")
        assert field is not None
        assert field["sentinel_field"] == "DeviceName"

    def test_file_path_property(self):
        """Test File.file_path maps to FilePath."""
        mapper = SchemaMapper()
        field = mapper.get_property_field("File", "file_path")
        assert field is not None
        assert field["sentinel_field"] == "FilePath"

    def test_unknown_property_returns_none(self):
        """Test that unknown property returns None."""
        mapper = SchemaMapper()
        field = mapper.get_property_field("User", "unknown_property")
        assert field is None

    def test_get_all_properties(self):
        """Test retrieving all properties for a node."""
        mapper = SchemaMapper()
        props = mapper.get_all_properties("User")
        assert "username" in props
        assert "email" in props
        assert "domain" in props
        assert props["username"]["sentinel_field"] == "AccountName"


class TestRelationshipMappings:
    """Test Cypher relationship to Sentinel join mappings."""

    def test_logged_in_relationship(self):
        """Test LOGGED_IN relationship mapping."""
        mapper = SchemaMapper()
        mapping = mapper.get_relationship_mapping("LOGGED_IN")
        assert mapping is not None
        assert mapping["from_label"] == "User"
        assert mapping["to_label"] == "Device"
        assert mapping["strength"] == "high"

    def test_owns_relationship(self):
        """Test OWNS relationship mapping."""
        mapper = SchemaMapper()
        mapping = mapper.get_relationship_mapping("OWNS")
        assert mapping is not None
        assert mapping["from_label"] == "User"
        assert mapping["to_label"] == "Device"

    def test_accessed_relationship(self):
        """Test ACCESSED relationship mapping."""
        mapper = SchemaMapper()
        mapping = mapper.get_relationship_mapping("ACCESSED")
        assert mapping is not None
        assert mapping["from_label"] == "User"
        assert mapping["to_label"] == "File"

    def test_executed_relationship(self):
        """Test EXECUTED relationship mapping."""
        mapper = SchemaMapper()
        mapping = mapper.get_relationship_mapping("EXECUTED")
        assert mapping is not None
        assert mapping["from_label"] == "User"
        assert mapping["to_label"] == "Process"

    def test_connected_to_relationship(self):
        """Test CONNECTED_TO relationship mapping."""
        mapper = SchemaMapper()
        mapping = mapper.get_relationship_mapping("CONNECTED_TO")
        assert mapping is not None
        assert mapping["from_label"] == "Device"
        assert mapping["to_label"] == "IP"

    def test_join_condition_exists(self):
        """Test that join conditions are defined."""
        mapper = SchemaMapper()
        condition = mapper.get_join_condition("LOGGED_IN")
        assert condition is not None
        assert len(condition) > 0


class TestPathFinding:
    """Test path finding and relationship discovery."""

    def test_find_path_tables(self):
        """Test finding Sentinel tables for a path."""
        mapper = SchemaMapper()
        tables = mapper.find_path_tables("User", "Device")
        assert tables is not None
        assert tables == ("IdentityInfo", "DeviceInfo")

    def test_find_path_tables_with_file(self):
        """Test finding path to file."""
        mapper = SchemaMapper()
        tables = mapper.find_path_tables("User", "File")
        assert tables == ("IdentityInfo", "FileEvents")

    def test_find_path_tables_unknown_label(self):
        """Test finding path with unknown label."""
        mapper = SchemaMapper()
        tables = mapper.find_path_tables("Unknown", "Device")
        assert tables is None

    def test_find_relationships_between(self):
        """Test finding relationships between labels."""
        mapper = SchemaMapper()
        rels = mapper.find_relationships_between("User", "Device")
        assert "LOGGED_IN" in rels
        assert "OWNS" in rels

    def test_find_relationships_between_user_file(self):
        """Test finding relationships between User and File."""
        mapper = SchemaMapper()
        rels = mapper.find_relationships_between("User", "File")
        assert "ACCESSED" in rels


class TestTableMetadata:
    """Test Sentinel table metadata and field information."""

    def test_get_table_fields(self):
        """Test retrieving fields for a table."""
        mapper = SchemaMapper()
        fields = mapper.get_table_fields("IdentityInfo")
        assert "AccountName" in fields
        assert "AccountDomain" in fields
        assert len(fields) > 0

    def test_get_device_info_fields(self):
        """Test retrieving DeviceInfo fields."""
        mapper = SchemaMapper()
        fields = mapper.get_table_fields("DeviceInfo")
        assert "DeviceName" in fields
        assert "DeviceId" in fields

    def test_get_nonexistent_table_fields(self):
        """Test retrieving fields for non-existent table."""
        mapper = SchemaMapper()
        fields = mapper.get_table_fields("NonExistentTable")
        assert fields == []


class TestSchemaInfo:
    """Test schema information methods."""

    def test_get_schema_info(self):
        """Test retrieving schema info."""
        mapper = SchemaMapper()
        info = mapper.get_schema_info()
        assert info["version"] == "1.0.0"
        assert "node_labels" in info
        assert "relationship_types" in info
        assert info["node_count"] > 0
        assert info["edge_count"] > 0

    def test_validate_schema(self):
        """Test schema validation."""
        mapper = SchemaMapper()
        result = mapper.validate_schema()
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0


class TestCypherLabels:
    """Test getting available Cypher labels."""

    def test_get_cypher_labels(self):
        """Test getting all Cypher labels."""
        mapper = SchemaMapper()
        labels = mapper.get_cypher_labels()
        assert isinstance(labels, list)
        assert len(labels) > 0

    def test_standard_labels_present(self):
        """Test that standard labels are present."""
        mapper = SchemaMapper()
        labels = mapper.get_cypher_labels()
        standard_labels = {"User", "Device", "File", "Process", "SecurityEvent", "IP"}
        assert standard_labels.issubset(set(labels))


class TestGetRelationships:
    """Test getting available relationships."""

    def test_get_relationships(self):
        """Test getting all relationships."""
        mapper = SchemaMapper()
        rels = mapper.get_relationships()
        assert isinstance(rels, list)
        assert len(rels) > 0

    def test_standard_relationships_present(self):
        """Test that standard relationships are present."""
        mapper = SchemaMapper()
        rels = mapper.get_relationships()
        standard_rels = {
            "LOGGED_IN",
            "OWNS",
            "ACCESSED",
            "EXECUTED",
            "CONNECTED_TO",
        }
        assert standard_rels.issubset(set(rels))
