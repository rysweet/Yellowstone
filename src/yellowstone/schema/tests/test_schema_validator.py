"""
Tests for schema validator functionality.
"""

import pytest
from yellowstone.schema import SchemaValidator, SchemaMapper


class TestSchemaValidation:
    """Test schema validation."""

    def test_validator_accepts_valid_default_schema(self):
        """Test that validator accepts default schema."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        result = validator.validate(mapper.schema)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validation_result_has_counts(self):
        """Test that validation result includes counts."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        result = validator.validate(mapper.schema)
        assert result.node_count > 0
        assert result.edge_count > 0
        assert result.table_count > 0

    def test_schema_has_expected_node_count(self):
        """Test that schema has expected number of nodes."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        result = validator.validate(mapper.schema)
        # Should have at least 12 node types (User, Device, etc.)
        assert result.node_count >= 12

    def test_schema_has_expected_edge_count(self):
        """Test that schema has expected number of edges."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        result = validator.validate(mapper.schema)
        # Should have at least 11 relationships
        assert result.edge_count >= 11


class TestPropertyAccessValidation:
    """Test property access validation."""

    def test_validate_user_username_property(self):
        """Test validating User.username property."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_property_access(mapper.schema, "User", "username")
        assert is_valid is True
        assert msg == ""

    def test_validate_device_name_property(self):
        """Test validating Device.device_name property."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_property_access(mapper.schema, "Device", "device_name")
        assert is_valid is True

    def test_validate_unknown_property(self):
        """Test validating unknown property."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_property_access(
            mapper.schema, "User", "unknown_property"
        )
        assert is_valid is False
        assert "unknown" in msg.lower()

    def test_validate_unknown_label(self):
        """Test validating unknown label."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_property_access(mapper.schema, "UnknownLabel", "prop")
        assert is_valid is False
        assert "unknown" in msg.lower()


class TestRelationshipValidation:
    """Test relationship validation."""

    def test_validate_logged_in_relationship(self):
        """Test validating LOGGED_IN relationship."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_relationship(
            mapper.schema, "LOGGED_IN", "User", "Device"
        )
        assert is_valid is True
        assert msg == ""

    def test_validate_accessed_relationship(self):
        """Test validating ACCESSED relationship."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_relationship(
            mapper.schema, "ACCESSED", "User", "File"
        )
        assert is_valid is True

    def test_validate_unknown_relationship(self):
        """Test validating unknown relationship."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_relationship(
            mapper.schema, "UNKNOWN_REL", "User", "Device"
        )
        assert is_valid is False
        assert "unknown" in msg.lower()

    def test_validate_wrong_from_label(self):
        """Test validating relationship with wrong from_label."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_relationship(
            mapper.schema, "LOGGED_IN", "Device", "Device"
        )
        assert is_valid is False

    def test_validate_wrong_to_label(self):
        """Test validating relationship with wrong to_label."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        is_valid, msg = validator.validate_relationship(
            mapper.schema, "LOGGED_IN", "User", "User"
        )
        assert is_valid is False


class TestFieldMappingRetrieval:
    """Test field mapping retrieval."""

    def test_get_user_username_field_mapping(self):
        """Test getting field mapping for User.username."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        mapping = validator.get_field_mapping(mapper.schema, "User", "username")
        assert mapping["sentinel_field"] == "AccountName"
        assert mapping["type"] == "string"

    def test_get_device_name_field_mapping(self):
        """Test getting field mapping for Device.device_name."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        mapping = validator.get_field_mapping(mapper.schema, "Device", "device_name")
        assert mapping["sentinel_field"] == "DeviceName"

    def test_get_unknown_property_mapping(self):
        """Test getting field mapping for unknown property."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        mapping = validator.get_field_mapping(mapper.schema, "User", "unknown")
        assert mapping == {}

    def test_field_mapping_includes_required_flag(self):
        """Test that field mapping includes required flag."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        mapping = validator.get_field_mapping(mapper.schema, "User", "username")
        assert "required" in mapping


class TestValidationErrorHandling:
    """Test validation error handling."""

    def test_validation_reports_referential_integrity(self):
        """Test that validation checks referential integrity."""
        mapper = SchemaMapper()
        validator = SchemaValidator()
        result = validator.validate(mapper.schema)
        # Should not have referential integrity errors for valid schema
        assert result.is_valid is True
