# Schema Mapping Guide

This guide explains how to create, validate, and use schema mappings to translate Cypher graph node labels and relationships to Microsoft Sentinel tables and join conditions.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Schema Format](#schema-format)
3. [Node Mappings](#node-mappings)
4. [Relationship Mappings](#relationship-mappings)
5. [Property Mappings](#property-mappings)
6. [Validation Rules](#validation-rules)
7. [Adding Custom Mappings](#adding-custom-mappings)
8. [Examples](#examples)
9. [Best Practices](#best-practices)

## Quick Start

The simplest way to get started is to use the default schema:

```python
from yellowstone.schema import SchemaMapper

# Load default schema
mapper = SchemaMapper()

# Map Cypher label to Sentinel table
table = mapper.get_node_table("User")  # Returns "IdentityInfo"

# Check if relationship exists
join_info = mapper.get_edge_join("LOGGED_IN")
# Returns: {
#   "from_label": "User",
#   "to_label": "Device",
#   "left_table": "IdentityInfo",
#   "right_table": "DeviceInfo",
#   "join_condition": "IdentityInfo.AccountName == DeviceInfo.UserName"
# }
```

To use a custom schema:

```python
from yellowstone.schema import SchemaMapper

# Load custom schema
mapper = SchemaMapper(schema_file="/path/to/custom_schema.yaml")

# Use as normal
table = mapper.get_node_table("CustomEntity")
```

## Schema Format

A schema is a YAML file that defines node and edge mappings.

### Basic Structure

```yaml
version: "1.0.0"
description: "Schema mapping Cypher to Sentinel"

nodes:
  NodeLabel:
    sentinel_table: TableName
    properties:
      cypher_property:
        sentinel_field: SentinelField
        type: string
        required: true

edges:
  RELATIONSHIP_TYPE:
    description: "Relationship description"
    from_label: SourceNode
    to_label: TargetNode
    sentinel_join:
      left_table: LeftTable
      right_table: RightTable
      join_condition: "LeftTable.Field == RightTable.Field"
    strength: high
    properties:
      edge_property:
        type: string
        required: false

tables:
  TableName:
    description: "Table description"
    retention_days: 30
    fields:
      - FieldName1
      - FieldName2
```

### Version and Metadata

```yaml
version: "1.0.0"
# Semantic versioning: MAJOR.MINOR.PATCH
# Increment MAJOR for breaking changes (e.g., label removal)
# Increment MINOR for non-breaking additions (e.g., new nodes)
# Increment PATCH for fixes (e.g., corrected join condition)

description: "Schema mapping Cypher to Microsoft Sentinel"
# Human-readable description of schema purpose and scope
```

## Node Mappings

Node mappings define how Cypher node labels map to Sentinel tables.

### Basic Node Mapping

```yaml
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true
      username:
        sentinel_field: AccountName
        type: string
        required: true
      email:
        sentinel_field: AccountUpn
        type: string
        required: false
```

**Structure:**
- `User`: Cypher node label
- `sentinel_table`: Sentinel table name (case-sensitive)
- `properties`: Map of Cypher properties to Sentinel fields

### Supported Property Types

```yaml
properties:
  string_property:
    sentinel_field: StringField
    type: string          # Text values
    required: true

  numeric_property:
    sentinel_field: NumericField
    type: int             # Integer values
    required: true

  date_property:
    sentinel_field: DateField
    type: datetime        # Date/time values
    required: false

  bool_property:
    sentinel_field: BoolField
    type: bool            # Boolean values
    required: false

  float_property:
    sentinel_field: FloatField
    type: float           # Floating point values
    required: false

  array_property:
    sentinel_field: ArrayField
    type: array           # Array/list values
    required: false

  object_property:
    sentinel_field: ObjectField
    type: object          # Complex objects
    required: false
```

### Multiple Properties

```yaml
nodes:
  Device:
    sentinel_table: DeviceInfo
    properties:
      device_id:
        sentinel_field: DeviceId
        type: string
        required: true
      device_name:
        sentinel_field: DeviceName
        type: string
        required: true
      os_platform:
        sentinel_field: OSPlatform
        type: string
        required: false
      ip_address:
        sentinel_field: IPAddress
        type: string
        required: false
      device_type:
        sentinel_field: DeviceType
        type: string
        required: false
      memory_mb:
        sentinel_field: PhysicalMemory
        type: int
        required: false
```

### Optional Properties

```yaml
nodes:
  SecurityEvent:
    sentinel_table: SecurityEvent
    properties:
      event_id:
        sentinel_field: EventID
        type: int
        required: true
        # required: true means query will fail if property not available

      timestamp:
        sentinel_field: TimeGenerated
        type: datetime
        required: true

      source_ip:
        sentinel_field: SourceIpAddr
        type: string
        required: false
        # required: false means property is optional
```

## Relationship Mappings

Relationship mappings define how Cypher relationships map to Sentinel join conditions.

### Basic Relationship Mapping

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

**Structure:**
- `LOGGED_IN`: Cypher relationship type
- `from_label`: Source node label in Cypher
- `to_label`: Target node label in Cypher
- `sentinel_join`: How to join tables in Sentinel
- `strength`: Confidence level of the join

### Join Condition Examples

#### Simple Equality Join

```yaml
edges:
  OWNS:
    description: "User owns a device"
    from_label: User
    to_label: Device
    sentinel_join:
      left_table: IdentityInfo
      right_table: DeviceInfo
      join_condition: "IdentityInfo.AccountName == DeviceInfo.ManagedBy"
    strength: high
```

#### Multi-Column Join

```yaml
edges:
  REPORTED_EVENT:
    description: "User reported a security event"
    from_label: User
    to_label: SecurityEvent
    sentinel_join:
      left_table: IdentityInfo
      right_table: SecurityEvent
      join_condition: |
        IdentityInfo.AccountName == SecurityEvent.Account
        and IdentityInfo.AccountDomain == SecurityEvent.Domain
    strength: high
```

#### Time-Windowed Join

```yaml
edges:
  EXECUTED:
    description: "User executed a process"
    from_label: User
    to_label: Process
    sentinel_join:
      left_table: IdentityInfo
      right_table: ProcessEvents
      join_condition: |
        IdentityInfo.AccountName == ProcessEvents.InitiatingProcessAccountName
    strength: high
    # Time constraints handled in query WHERE clause
```

### Relationship Strength

The `strength` field indicates confidence in the join:

```yaml
edges:
  HIGH_CONFIDENCE:
    strength: high
    # Reliable join, low ambiguity
    # Examples: AccountName == UserName, ProcessID == ProcessId

  MEDIUM_CONFIDENCE:
    strength: medium
    # Reasonable join, some ambiguity possible
    # Examples: IP-to-Location mappings, Device name to IP

  LOW_CONFIDENCE:
    strength: low
    # Weak join, significant ambiguity
    # Examples: Generic associations, inferred relationships
```

### Edge Properties

Relationships can have properties (metadata about the relationship):

```yaml
edges:
  LOGGED_IN:
    description: "User logged into device"
    from_label: User
    to_label: Device
    sentinel_join:
      left_table: IdentityInfo
      right_table: DeviceInfo
      join_condition: "IdentityInfo.AccountName == DeviceInfo.UserName"
    strength: high
    properties:
      login_time:
        type: datetime
        required: false
      logout_time:
        type: datetime
        required: false
      success:
        type: bool
        required: false
      logon_type:
        type: string
        required: false
```

### Bidirectional Relationships

```yaml
edges:
  COMMUNICATES_WITH:
    description: "Network communication between IPs"
    from_label: IP
    to_label: IP
    sentinel_join:
      left_table: NetworkSession
      right_table: NetworkSession
      join_condition: |
        NetworkSession.SourceIp == NetworkSession.RemoteIp
    strength: medium
    # Bidirectional: can match (a)-[r]->(b) or (b)-[r]->(a)
```

## Property Mappings

Property mappings define how Cypher properties map to Sentinel fields.

### Direct Property Mapping

The most common case: Cypher property directly maps to Sentinel field.

```yaml
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true
      email:
        sentinel_field: AccountUpn
        type: string
        required: false
```

**Translation:**
```cypher
-- Cypher
MATCH (u:User) WHERE u.user_id = '12345' RETURN u.email

-- KQL (after schema mapping)
graph-match (u:IdentityInfo)
| where u.AccountObjectId == '12345'
| project u.AccountUpn
```

### Type Conversion

The translator handles type conversions:

```yaml
nodes:
  Process:
    sentinel_table: ProcessEvents
    properties:
      process_id:
        sentinel_field: ProcessId
        type: int          # Converts string PID to integer
        required: true
      memory_bytes:
        sentinel_field: PhysicalMemory
        type: float        # Converts to floating point
        required: false
```

### Complex Property Mapping

For complex scenarios, properties can be computed fields:

```yaml
nodes:
  Device:
    sentinel_table: DeviceInfo
    properties:
      full_identifier:
        # Synthetic property combining multiple fields
        sentinel_field: strcat(DeviceName, ".", AccountDomain)
        type: string
        required: false
```

## Validation Rules

The schema validator enforces consistency and completeness.

### Automatic Validation

```python
from yellowstone.schema import SchemaValidator

# Validate schema file
result = SchemaValidator.validate_file("/path/to/schema.yaml")

if result.is_valid:
    print(f"Schema valid: {result.node_count} nodes, {result.edge_count} edges")
else:
    for error in result.errors:
        print(f"ERROR: {error}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
```

### Validation Checks

#### 1. Node Mapping Validity

```yaml
# VALID: All required fields present
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true

# INVALID: Missing sentinel_field
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        type: string        # ERROR: missing sentinel_field
        required: true

# INVALID: Unknown type
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: unknown_type  # ERROR: invalid type
        required: true
```

#### 2. Relationship Endpoint Validation

```yaml
# VALID: from_label and to_label defined in nodes
edges:
  LOGGED_IN:
    from_label: User      # Defined in nodes
    to_label: Device      # Defined in nodes
    ...

# INVALID: from_label not defined
edges:
  LOGGED_IN:
    from_label: Unknown   # ERROR: not defined in nodes
    to_label: Device
    ...
```

#### 3. Join Condition Syntax

```yaml
# VALID: Standard SQL equality
sentinel_join:
  join_condition: "LeftTable.Column == RightTable.Column"

# VALID: Multi-column join
sentinel_join:
  join_condition: |
    LeftTable.Col1 == RightTable.Col1
    and LeftTable.Col2 == RightTable.Col2

# INVALID: Wrong operator
sentinel_join:
  join_condition: "LeftTable.Column = RightTable.Column"  # ERROR: use == in KQL
```

#### 4. Circular Dependency Detection

```yaml
# INVALID: Circular relationships
edges:
  OWNS:
    from_label: User
    to_label: Device
  CONTAINED_IN:
    from_label: Device
    to_label: User  # Creates cycle
```

#### 5. Property Consistency

```yaml
# INVALID: Property name conflicts
nodes:
  Device:
    properties:
      device_id:
        sentinel_field: DeviceId
        type: string
  ...
edges:
  OWNS:
    properties:
      device_id:        # ERROR: conflicts with node property
        type: string
```

### Custom Validation

```python
from yellowstone.schema import SchemaValidator, SchemaValidationResult

class CustomValidator(SchemaValidator):
    def validate_custom_rules(self, schema) -> SchemaValidationResult:
        """Add domain-specific validation."""
        result = SchemaValidationResult(is_valid=True, node_count=0, edge_count=0)

        # Example: Ensure all security-related nodes have timestamp
        for node_label in schema.nodes:
            if "Security" in node_label:
                props = schema.nodes[node_label].properties
                if "timestamp" not in props:
                    result.warnings.append(
                        f"{node_label} missing timestamp property"
                    )

        return result
```

## Adding Custom Mappings

### Method 1: Extend Default Schema (YAML)

Create a custom schema file that extends the default:

```yaml
# custom_sentinel_schema.yaml
version: "1.0.1"
description: "Extended schema with custom entities"

# All nodes from default schema are inherited
# Add new nodes here:
nodes:
  CustomEntity:
    sentinel_table: CustomTable
    properties:
      entity_id:
        sentinel_field: EntityID
        type: string
        required: true
      entity_name:
        sentinel_field: EntityName
        type: string
        required: true

  Incident:
    sentinel_table: IncidentsTable
    properties:
      incident_id:
        sentinel_field: IncidentId
        type: string
        required: true
      severity:
        sentinel_field: Severity
        type: string
        required: true

# New relationships
edges:
  RELATED_TO:
    description: "Entity related to incident"
    from_label: CustomEntity
    to_label: Incident
    sentinel_join:
      left_table: CustomTable
      right_table: IncidentsTable
      join_condition: "CustomTable.EntityID == IncidentsTable.AffectedEntityId"
    strength: high

  ESCALATED_FROM:
    description: "Alert escalated to incident"
    from_label: Alert
    to_label: Incident
    sentinel_join:
      left_table: AlertsTable
      right_table: IncidentsTable
      join_condition: "AlertsTable.AlertId == IncidentsTable.SourceAlertId"
    strength: high

# Additional table metadata
tables:
  CustomTable:
    description: "Custom entity data"
    retention_days: 90
    fields:
      - EntityID
      - EntityName
      - CreatedTime
      - LastModified

  IncidentsTable:
    description: "Security incidents"
    retention_days: 180
    fields:
      - IncidentId
      - Severity
      - AffectedEntityId
      - SourceAlertId
```

Usage:

```python
from yellowstone.schema import SchemaMapper

# Load custom schema
mapper = SchemaMapper(schema_file="custom_sentinel_schema.yaml")

# Use new mappings
table = mapper.get_node_table("CustomEntity")      # Returns "CustomTable"
join = mapper.get_edge_join("RELATED_TO")         # Returns join info
```

### Method 2: Programmatic Schema Creation

Create schema programmatically:

```python
from yellowstone.schema.models import (
    SchemaMapping, NodeMapping, EdgeMapping, JoinCondition,
    PropertyMapping, EdgeProperty, TableMetadata
)

# Create custom schema
schema = SchemaMapping(
    version="1.0.0",
    description="Programmatic schema",

    nodes={
        "CustomEntity": NodeMapping(
            sentinel_table="CustomTable",
            properties={
                "entity_id": PropertyMapping(
                    sentinel_field="EntityID",
                    type="string",
                    required=True
                ),
                "entity_name": PropertyMapping(
                    sentinel_field="EntityName",
                    type="string",
                    required=True
                )
            }
        )
    },

    edges={
        "RELATED_TO": EdgeMapping(
            description="Entity related to incident",
            from_label="CustomEntity",
            to_label="Incident",
            sentinel_join=JoinCondition(
                left_table="CustomTable",
                right_table="IncidentsTable",
                join_condition="CustomTable.EntityID == IncidentsTable.AffectedEntityId"
            ),
            strength="high",
            properties={
                "relationship_strength": EdgeProperty(
                    type="float",
                    required=False
                )
            }
        )
    },

    tables={
        "CustomTable": TableMetadata(
            description="Custom entity data",
            retention_days=90,
            fields=["EntityID", "EntityName", "CreatedTime"]
        )
    }
)

# Save schema
import yaml
with open("custom_schema.yaml", "w") as f:
    yaml.dump(schema.model_dump(), f)
```

### Method 3: Dynamic Schema Injection

Inject mappings at runtime:

```python
from yellowstone.schema import SchemaMapper

mapper = SchemaMapper()

# Add custom node mapping
mapper.register_node(
    label="CustomEntity",
    table="CustomTable",
    properties={
        "entity_id": ("EntityID", "string", True),
        "entity_name": ("EntityName", "string", True)
    }
)

# Add custom relationship
mapper.register_edge(
    rel_type="RELATED_TO",
    from_label="CustomEntity",
    to_label="Incident",
    join_condition="CustomTable.EntityID == IncidentsTable.AffectedEntityId",
    strength="high"
)

# Use mappings
table = mapper.get_node_table("CustomEntity")
```

## Examples

### Example 1: Basic User-Device Schema

```yaml
version: "1.0.0"
description: "Basic user and device mapping"

nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true
      name:
        sentinel_field: AccountName
        type: string
        required: true
      email:
        sentinel_field: AccountUpn
        type: string
        required: false

  Device:
    sentinel_table: DeviceInfo
    properties:
      device_id:
        sentinel_field: DeviceId
        type: string
        required: true
      name:
        sentinel_field: DeviceName
        type: string
        required: true
      os:
        sentinel_field: OSPlatform
        type: string
        required: false

edges:
  LOGGED_IN:
    description: "User logged into device"
    from_label: User
    to_label: Device
    sentinel_join:
      left_table: IdentityInfo
      right_table: DeviceInfo
      join_condition: "IdentityInfo.AccountName == DeviceInfo.UserName"
    strength: high
    properties:
      timestamp:
        type: datetime
        required: false
      success:
        type: bool
        required: false

tables:
  IdentityInfo:
    description: "User identities"
    retention_days: 30
    fields:
      - AccountObjectId
      - AccountName
      - AccountUpn

  DeviceInfo:
    description: "Device information"
    retention_days: 30
    fields:
      - DeviceId
      - DeviceName
      - OSPlatform
      - UserName
```

### Example 2: Threat Investigation Schema

```yaml
version: "1.0.0"
description: "Schema for security threat investigation"

nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true
      name:
        sentinel_field: AccountName
        type: string
        required: true
      risk_level:
        sentinel_field: AccountRiskLevel
        type: string
        required: false

  Device:
    sentinel_table: DeviceInfo
    properties:
      device_id:
        sentinel_field: DeviceId
        type: string
        required: true
      name:
        sentinel_field: DeviceName
        type: string
        required: true

  Process:
    sentinel_table: ProcessEvents
    properties:
      process_id:
        sentinel_field: ProcessId
        type: int
        required: true
      name:
        sentinel_field: FileName
        type: string
        required: true
      command_line:
        sentinel_field: CommandLine
        type: string
        required: false

  File:
    sentinel_table: FileEvents
    properties:
      file_path:
        sentinel_field: FilePath
        type: string
        required: true
      file_name:
        sentinel_field: FileName
        type: string
        required: true
      hash:
        sentinel_field: SHA256
        type: string
        required: false

edges:
  LOGGED_IN:
    description: "User logged into device"
    from_label: User
    to_label: Device
    sentinel_join:
      left_table: IdentityInfo
      right_table: DeviceInfo
      join_condition: "IdentityInfo.AccountName == DeviceInfo.UserName"
    strength: high

  EXECUTED:
    description: "User executed process"
    from_label: User
    to_label: Process
    sentinel_join:
      left_table: IdentityInfo
      right_table: ProcessEvents
      join_condition: "IdentityInfo.AccountName == ProcessEvents.InitiatingProcessAccountName"
    strength: high

  ACCESSED:
    description: "Process accessed file"
    from_label: Process
    to_label: File
    sentinel_join:
      left_table: ProcessEvents
      right_table: FileEvents
      join_condition: "ProcessEvents.ProcessId == FileEvents.InitiatingProcessId"
    strength: high

  CONTAINS_MALWARE:
    description: "File contains malware"
    from_label: File
    to_label: Malware
    sentinel_join:
      left_table: FileEvents
      right_table: DeviceEvents
      join_condition: "FileEvents.SHA256 == DeviceEvents.FileHash"
    strength: high

tables:
  IdentityInfo:
    description: "User identities and accounts"
    retention_days: 30
    fields:
      - AccountObjectId
      - AccountName
      - AccountRiskLevel

  DeviceInfo:
    description: "Devices in the organization"
    retention_days: 30
    fields:
      - DeviceId
      - DeviceName
      - UserName

  ProcessEvents:
    description: "Process creation and execution"
    retention_days: 30
    fields:
      - ProcessId
      - FileName
      - CommandLine
      - InitiatingProcessAccountName
      - InitiatingProcessId

  FileEvents:
    description: "File system events"
    retention_days: 30
    fields:
      - FilePath
      - FileName
      - SHA256
      - InitiatingProcessId

  DeviceEvents:
    description: "Device security events"
    retention_days: 30
    fields:
      - FileHash
      - Title
```

## Best Practices

### 1. Version Your Schemas

Always use semantic versioning:

```yaml
version: "1.0.0"  # MAJOR.MINOR.PATCH
```

- Increment MAJOR for breaking changes
- Increment MINOR for backwards-compatible additions
- Increment PATCH for fixes

### 2. Document Relationships

Provide clear descriptions:

```yaml
edges:
  LOGGED_IN:
    description: "User successfully authenticated and established session on device"
    # Good: Clear, specific, explains meaning

    # Bad:
    # description: "Login"
```

### 3. Specify Required Properties

Mark critical properties as required:

```yaml
properties:
  user_id:
    required: true      # Query will fail without this
  email:
    required: false     # Query succeeds, property may be null
```

### 4. Validate Join Strength

Choose appropriate strength levels:

```yaml
edges:
  LOGGED_IN:
    strength: high      # Reliable: AccountName is unique identifier

  CONNECTED_TO:
    strength: medium    # Reasonable: IP addresses can be shared

  SIMILAR_BEHAVIOR:
    strength: low       # Weak: Inferred relationship
```

### 5. Include Metadata

Add table metadata for completeness:

```yaml
tables:
  IdentityInfo:
    description: "User and account information"
    retention_days: 30
    fields:
      - AccountObjectId
      - AccountName
      - AccountUpn
```

### 6. Test Your Schema

Validate schema before deployment:

```python
from yellowstone.schema import SchemaValidator

result = SchemaValidator.validate_file("schema.yaml")
assert result.is_valid, "Schema validation failed"
assert result.edge_count > 0, "Schema has no relationships"
print(f"Valid schema: {result.node_count} nodes, {result.edge_count} edges")
```

### 7. Handle Optional Fields

Always provide fallbacks:

```yaml
properties:
  email:
    required: false
    # Queries still work if email is missing

  # Avoid:
  # email:
  #   required: true
  #   # Query fails if email is missing
```

### 8. Use Consistent Naming

Follow naming conventions:

```yaml
nodes:
  User:          # PascalCase for node labels
    sentinel_table: IdentityInfo  # PascalCase for table names
    properties:
      user_id:   # snake_case for properties
        sentinel_field: AccountObjectId  # PascalCase for fields

edges:
  LOGGED_IN:     # UPPER_SNAKE_CASE for relationships
```

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [TRANSLATION_GUIDE.md](./TRANSLATION_GUIDE.md) - How queries are translated
- [CLI_REFERENCE.md](../CLI_REFERENCE.md) - Command-line schema tools
- [YAML Specification](https://yaml.org/spec/) - YAML format reference
