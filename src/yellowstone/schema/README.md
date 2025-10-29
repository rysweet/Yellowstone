# Schema Module

## Overview

The schema module provides comprehensive mapping from Cypher graph constructs to Microsoft Sentinel tables. It defines:

- **Node mappings**: Cypher labels → Sentinel tables
- **Property mappings**: Cypher properties → Sentinel fields
- **Relationship mappings**: Cypher relationships → Sentinel join conditions
- **Table metadata**: Sentinel table structure and field information

This enables the Yellowstone query translator to convert Cypher queries into equivalent KQL queries that work against Sentinel data.

## Architecture

### Components

1. **SchemaMapper**: Main API for schema lookups and path finding
2. **SchemaValidator**: Validates schema integrity and consistency
3. **Models**: Pydantic models for type-safe schema handling
4. **default_sentinel_schema.yaml**: Default schema definition with 12+ node types and 11+ relationships

### Design Principles

- **YAML-based**: Schema defined in human-readable YAML
- **Pydantic validation**: Type-safe schema parsing and validation
- **Cached lookups**: In-memory cache for O(1) lookups
- **Extensible**: Easy to add custom node/edge types
- **Validated**: Comprehensive schema validation on load

## Schema Structure

### Node Types

Maps Cypher node labels to Sentinel tables:

```yaml
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      username:
        sentinel_field: AccountName
        type: string
        required: true
```

Supported node types:
- User → IdentityInfo
- Device → DeviceInfo
- SecurityEvent → SecurityEvent
- File → FileEvents
- Process → ProcessEvents
- IP → NetworkSession
- Account → IdentityInfo
- Credential → IdentityLogonEvents
- Network → NetworkSession
- Malware → DeviceEvents
- Alert → AlertsTable
- RegistryKey → DeviceRegistryEvents

### Relationships

Maps Cypher relationships to Sentinel join conditions:

```yaml
edges:
  LOGGED_IN:
    description: "User logged into a device"
    from_label: User
    to_label: Device
    sentinel_join:
      left_table: IdentityInfo
      right_table: DeviceInfo
      join_condition: "IdentityInfo.AccountName == DeviceInfo.UserName"
    strength: high
```

Supported relationships:
- LOGGED_IN: User → Device
- OWNS: User → Device
- ACCESSED: User → File
- EXECUTED: User → Process
- CONNECTED_TO: Device → IP
- TRIGGERED: SecurityEvent → Alert
- CONTAINS_MALWARE: File → Malware
- MODIFIED: Process → RegistryKey
- AUTHENTICATES: Account → Credential
- ATTEMPTS_ACCESS: Account → Device
- COMMUNICATES_WITH: IP → IP
- ASSOCIATED_WITH: Any → Any (generic)

## Usage

### Basic Setup

```python
from yellowstone.schema import SchemaMapper

# Load default schema
mapper = SchemaMapper()

# Or load custom schema
mapper = SchemaMapper("/path/to/custom_schema.yaml")
```

### Node and Label Queries

```python
# Get Sentinel table for a Cypher label
table = mapper.get_sentinel_table("User")
# Returns: "IdentityInfo"

# Get all available labels
labels = mapper.get_cypher_labels()
# Returns: ["User", "Device", "File", ...]

# Get all properties for a label
props = mapper.get_all_properties("User")
# Returns: {
#   "username": {"sentinel_field": "AccountName", "type": "string", ...},
#   "email": {"sentinel_field": "AccountUpn", "type": "string", ...},
#   ...
# }
```

### Property Mapping

```python
# Get field mapping for a property
field = mapper.get_property_field("User", "username")
# Returns: {
#   "sentinel_field": "AccountName",
#   "type": "string",
#   "required": True
# }

# Get all properties for a label
props = mapper.get_all_properties("Device")
```

### Relationship Queries

```python
# Get relationships between two labels
rels = mapper.find_relationships_between("User", "Device")
# Returns: ["LOGGED_IN", "OWNS"]

# Get relationship mapping details
mapping = mapper.get_relationship_mapping("LOGGED_IN")
# Returns: {
#   "from_label": "User",
#   "to_label": "Device",
#   "left_table": "IdentityInfo",
#   "right_table": "DeviceInfo",
#   "join_condition": "IdentityInfo.AccountName == DeviceInfo.UserName",
#   "strength": "high"
# }

# Get join condition
condition = mapper.get_join_condition("LOGGED_IN")
# Returns: "IdentityInfo.AccountName == DeviceInfo.UserName"
```

### Path Finding

```python
# Find Sentinel tables for a path
tables = mapper.find_path_tables("User", "Device")
# Returns: ("IdentityInfo", "DeviceInfo")

# Get all relationships
rels = mapper.get_relationships()
# Returns: ["LOGGED_IN", "OWNS", "ACCESSED", ...]
```

### Table Metadata

```python
# Get fields available for a table
fields = mapper.get_table_fields("IdentityInfo")
# Returns: ["AccountObjectId", "AccountName", "AccountDomain", ...]

# Get schema information
info = mapper.get_schema_info()
# Returns: {
#   "version": "1.0.0",
#   "description": "...",
#   "node_labels": [...],
#   "relationship_types": [...],
#   "sentinel_tables": [...],
#   "node_count": 12,
#   "edge_count": 11,
#   "table_count": 9
# }
```

### Schema Validation

```python
from yellowstone.schema import SchemaValidator

validator = SchemaValidator()

# Validate complete schema
result = validator.validate(mapper.schema)
if result.is_valid:
    print(f"Valid: {result.node_count} nodes, {result.edge_count} edges")
else:
    for error in result.errors:
        print(f"Error: {error}")

# Validate specific property access
is_valid, msg = validator.validate_property_access(
    mapper.schema, "User", "username"
)

# Validate relationship
is_valid, msg = validator.validate_relationship(
    mapper.schema, "LOGGED_IN", "User", "Device"
)

# Get field mapping
mapping = validator.get_field_mapping(mapper.schema, "User", "username")
```

## Default Schema

The module includes a comprehensive default schema (`default_sentinel_schema.yaml`) with:

### 12+ Node Types
- User, Device, SecurityEvent, File, Process, IP
- Account, Credential, Network, Malware, Alert, RegistryKey

### 11+ Relationships
- LOGGED_IN, OWNS, ACCESSED, EXECUTED, CONNECTED_TO
- TRIGGERED, CONTAINS_MALWARE, MODIFIED, AUTHENTICATES, ATTEMPTS_ACCESS
- COMMUNICATES_WITH, ASSOCIATED_WITH

### 9 Sentinel Tables
- IdentityInfo, DeviceInfo, SecurityEvent, NetworkSession, FileEvents
- ProcessEvents, IdentityLogonEvents, DeviceEvents, AlertsTable, DeviceRegistryEvents

## Extending the Schema

### Adding a Custom Node Type

Create a custom schema YAML file:

```yaml
version: "1.0.0"
description: "Custom schema with additional nodes"

nodes:
  Container:
    sentinel_table: ContainerEvents
    properties:
      container_id:
        sentinel_field: ContainerId
        type: string
        required: true
      container_name:
        sentinel_field: ContainerName
        type: string
        required: true

tables:
  ContainerEvents:
    description: "Container events"
    retention_days: 30
    fields:
      - ContainerId
      - ContainerName
```

Then load it:

```python
mapper = SchemaMapper("/path/to/custom_schema.yaml")
```

### Adding a Custom Relationship

```yaml
edges:
  DEPLOYED_IN:
    description: "Container deployed in cluster"
    from_label: Container
    to_label: Device
    sentinel_join:
      left_table: ContainerEvents
      right_table: DeviceInfo
      join_condition: "ContainerEvents.HostId == DeviceInfo.DeviceId"
    strength: high
```

## Testing

Run tests with pytest:

```bash
pytest src/yellowstone/schema/tests/
```

Tests cover:
- Schema loading and initialization
- Label to table mappings
- Property to field mappings
- Relationship mappings
- Path finding
- Table metadata
- Schema validation
- Error handling

## Type Safety

All components use Pydantic models for type safety:

```python
from yellowstone.schema.models import (
    SchemaMapping,
    NodeMapping,
    EdgeMapping,
    PropertyMapping,
    SchemaValidationResult,
)

# All models are validated automatically on creation
schema = SchemaMapping(**yaml_dict)  # Will raise if invalid
```

## Performance

- **O(1) lookups**: All mappings cached in memory
- **Fast schema loading**: YAML parsed once on startup
- **Minimal memory**: Compact cache representation
- **Thread-safe**: Immutable after initialization

## File Structure

```
schema/
├── __init__.py                    # Public API
├── schema_mapper.py               # Main mapper implementation
├── schema_validator.py            # Validation logic
├── models.py                      # Pydantic models
├── default_sentinel_schema.yaml   # Default schema definition
├── tests/
│   ├── __init__.py
│   ├── test_schema_mapper.py      # Mapper tests
│   └── test_schema_validator.py   # Validator tests
└── README.md                      # This file
```

## Error Handling

Schema loading validates structure and referential integrity:

```python
try:
    mapper = SchemaMapper("/invalid/path.yaml")
except FileNotFoundError:
    print("Schema file not found")

try:
    mapper = SchemaMapper("/malformed.yaml")
except yaml.YAMLError:
    print("YAML parsing failed")

try:
    mapper = SchemaMapper("/invalid_schema.yaml")
except ValueError as e:
    print(f"Schema validation failed: {e}")
```

## Contributing

When adding new node types or relationships:

1. Update `default_sentinel_schema.yaml`
2. Add comprehensive property mappings
3. Add corresponding join conditions
4. Add table metadata
5. Update tests in `tests/`
6. Validate with `SchemaValidator`

## Related

- **CypherTranslator**: Uses schema to translate Cypher queries
- **Parser**: Parses Cypher queries for translation
- **Models**: Shares Pydantic models with other modules
