"""
Basic usage examples for the schema mapper.

This module demonstrates common use cases for the schema mapper.
"""

from yellowstone.schema import SchemaMapper, SchemaValidator


def example_basic_initialization():
    """Example: Initialize schema mapper with default schema."""
    print("=" * 60)
    print("Example 1: Basic Initialization")
    print("=" * 60)

    # Load default schema
    mapper = SchemaMapper()

    # Get schema info
    info = mapper.get_schema_info()
    print(f"Schema version: {info['version']}")
    print(f"Available node types: {info['node_count']}")
    print(f"Available relationships: {info['edge_count']}")
    print(f"Sentinel tables: {info['table_count']}")
    print()


def example_label_to_table_mapping():
    """Example: Map Cypher labels to Sentinel tables."""
    print("=" * 60)
    print("Example 2: Label to Table Mapping")
    print("=" * 60)

    mapper = SchemaMapper()

    # Map individual labels
    labels = ["User", "Device", "File", "Process", "SecurityEvent", "IP"]

    for label in labels:
        table = mapper.get_sentinel_table(label)
        print(f"{label:15} → {table}")

    print()


def example_property_mapping():
    """Example: Map Cypher properties to Sentinel fields."""
    print("=" * 60)
    print("Example 3: Property Mapping")
    print("=" * 60)

    mapper = SchemaMapper()

    # Get all properties for User
    props = mapper.get_all_properties("User")
    print("User properties:")
    for prop_name, field_info in props.items():
        print(
            f"  {prop_name:15} → {field_info['sentinel_field']:20} ({field_info['type']})"
        )

    print()

    # Get specific property
    field = mapper.get_property_field("Device", "device_name")
    print(f"Device.device_name → {field['sentinel_field']} ({field['type']})")
    print()


def example_relationships():
    """Example: Work with Cypher relationships."""
    print("=" * 60)
    print("Example 4: Relationships")
    print("=" * 60)

    mapper = SchemaMapper()

    # Find relationships between User and Device
    rels = mapper.find_relationships_between("User", "Device")
    print(f"User → Device relationships: {rels}")

    # Get join condition for LOGGED_IN
    condition = mapper.get_join_condition("LOGGED_IN")
    print(f"LOGGED_IN join: {condition}")

    # Get full mapping
    mapping = mapper.get_relationship_mapping("LOGGED_IN")
    print(f"\nLOGGED_IN mapping:")
    print(f"  From: {mapping['from_label']}")
    print(f"  To: {mapping['to_label']}")
    print(f"  Left table: {mapping['left_table']}")
    print(f"  Right table: {mapping['right_table']}")
    print(f"  Strength: {mapping['strength']}")
    print()


def example_path_finding():
    """Example: Find paths between node types."""
    print("=" * 60)
    print("Example 5: Path Finding")
    print("=" * 60)

    mapper = SchemaMapper()

    # Find tables for a path
    paths = [
        ("User", "Device"),
        ("User", "File"),
        ("Device", "IP"),
        ("Process", "File"),
    ]

    for start, end in paths:
        tables = mapper.find_path_tables(start, end)
        if tables:
            print(f"{start} ⟶ {end}  |  {tables[0]} ⟶ {tables[1]}")
        else:
            print(f"{start} ⟶ {end}  |  NOT FOUND")

    print()


def example_table_metadata():
    """Example: Retrieve table metadata."""
    print("=" * 60)
    print("Example 6: Table Metadata")
    print("=" * 60)

    mapper = SchemaMapper()

    # Get fields for IdentityInfo
    fields = mapper.get_table_fields("IdentityInfo")
    print("IdentityInfo fields:")
    for field in fields:
        print(f"  - {field}")

    print()

    # Get available tables
    tables = mapper.get_schema_info()["sentinel_tables"]
    print(f"Available Sentinel tables: {', '.join(tables)}")
    print()


def example_available_nodes_and_relationships():
    """Example: List all available nodes and relationships."""
    print("=" * 60)
    print("Example 7: Available Nodes and Relationships")
    print("=" * 60)

    mapper = SchemaMapper()

    # All labels
    labels = mapper.get_cypher_labels()
    print(f"Available Cypher labels ({len(labels)}):")
    for label in sorted(labels):
        table = mapper.get_sentinel_table(label)
        print(f"  {label:20} → {table}")

    print()

    # All relationships
    rels = mapper.get_relationships()
    print(f"Available relationships ({len(rels)}):")
    for rel in sorted(rels):
        print(f"  - {rel}")

    print()


def example_validation():
    """Example: Validate schema and properties."""
    print("=" * 60)
    print("Example 8: Schema Validation")
    print("=" * 60)

    mapper = SchemaMapper()
    validator = SchemaValidator()

    # Validate schema
    result = validator.validate(mapper.schema)
    print(f"Schema valid: {result.is_valid}")
    print(f"Nodes: {result.node_count}, Edges: {result.edge_count}, Tables: {result.table_count}")

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")
    else:
        print("No validation errors")

    print()

    # Validate property access
    is_valid, msg = validator.validate_property_access(mapper.schema, "User", "username")
    print(f"User.username valid: {is_valid}")

    is_valid, msg = validator.validate_property_access(mapper.schema, "User", "unknown")
    print(f"User.unknown valid: {is_valid} ({msg if not is_valid else 'OK'})")

    print()

    # Validate relationship
    is_valid, msg = validator.validate_relationship(
        mapper.schema, "LOGGED_IN", "User", "Device"
    )
    print(f"LOGGED_IN(User → Device) valid: {is_valid}")

    is_valid, msg = validator.validate_relationship(
        mapper.schema, "LOGGED_IN", "Device", "User"
    )
    print(f"LOGGED_IN(Device → User) valid: {is_valid} ({msg if not is_valid else 'OK'})")

    print()


def example_field_mapping_details():
    """Example: Get detailed field mapping information."""
    print("=" * 60)
    print("Example 9: Field Mapping Details")
    print("=" * 60)

    mapper = SchemaMapper()
    validator = SchemaValidator()

    # Get field mapping details
    field = validator.get_field_mapping(mapper.schema, "User", "username")
    print("User.username field mapping:")
    print(f"  Sentinel field: {field['sentinel_field']}")
    print(f"  Type: {field['type']}")
    print(f"  Required: {field['required']}")

    print()

    field = validator.get_field_mapping(mapper.schema, "Device", "device_id")
    print("Device.device_id field mapping:")
    print(f"  Sentinel field: {field['sentinel_field']}")
    print(f"  Type: {field['type']}")
    print(f"  Required: {field['required']}")

    print()


def example_schema_info():
    """Example: Get comprehensive schema information."""
    print("=" * 60)
    print("Example 10: Schema Information")
    print("=" * 60)

    mapper = SchemaMapper()

    info = mapper.get_schema_info()
    print(f"Schema version: {info['version']}")
    print(f"Description: {info['description']}")
    print(f"\nCounts:")
    print(f"  Node types: {info['node_count']}")
    print(f"  Relationships: {info['edge_count']}")
    print(f"  Tables: {info['table_count']}")
    print(f"\nNode labels: {len(info['node_labels'])}")
    print(f"Relationship types: {len(info['relationship_types'])}")
    print(f"Sentinel tables: {len(info['sentinel_tables'])}")

    print()


if __name__ == "__main__":
    """Run all examples."""
    example_basic_initialization()
    example_label_to_table_mapping()
    example_property_mapping()
    example_relationships()
    example_path_finding()
    example_table_metadata()
    example_available_nodes_and_relationships()
    example_validation()
    example_field_mapping_details()
    example_schema_info()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
