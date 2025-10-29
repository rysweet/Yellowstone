# Yellowstone CLI Quick Start

## Installation

The CLI is located at: `/home/azureuser/src/Yellowstone/src/yellowstone/cli.py`

Run commands from Python:
```python
from src.yellowstone.cli import cli
import sys

sys.argv = ['yellowstone', 'translate', 'MATCH (u:User) RETURN u.name']
cli()
```

## 30-Second Overview

Four commands for working with Cypher→KQL translation:

| Command | Purpose | Usage |
|---------|---------|-------|
| `translate` | Single query | `yellowstone translate "MATCH (u:User) RETURN u"` |
| `translate-file` | Batch queries | `yellowstone translate-file queries.cypher` |
| `validate-schema` | Check schemas | `yellowstone validate-schema schema.yaml` |
| `repl` | Interactive | `yellowstone repl` |

## Common Tasks

### Translate One Query

```bash
# Basic - displays formatted KQL
yellowstone translate "MATCH (u:User) RETURN u.name"

# Get just the KQL
yellowstone translate "MATCH (u:User) RETURN u.name" --format raw

# Get JSON for programmatic use
yellowstone translate "MATCH (u:User) RETURN u.name" --format json
```

### Translate Many Queries

```bash
# From file (one query per line)
yellowstone translate-file queries.cypher

# Save to JSON
yellowstone translate-file queries.cypher --output results.json --format json

# Skip errors and keep going
yellowstone translate-file queries.cypher --skip-errors
```

### Validate Your Schema

```bash
# Check if schema is valid
yellowstone validate-schema schema.yaml

# See all the details
yellowstone validate-schema schema.yaml --verbose
```

### Interactive Testing

```bash
# Start interactive shell
yellowstone repl

# With a schema
yellowstone repl --schema schema.yaml

# Then type queries and press enter to see translations
```

## Input Files

### Query File Format
```
# comments are supported
MATCH (u:User) RETURN u.name
MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d
# another comment
MATCH (n:Person {name: 'John'}) RETURN n.age
```

### Schema File Format
```yaml
version: "1.0"
description: "My schema"

nodes:
  User:
    sentinel_table: "UserAccount"
    properties:
      username:
        sentinel_field: "AccountName"
        type: "string"

edges:
  LOGGED_IN:
    description: "User login"
    from_label: "User"
    to_label: "Device"
    strength: "high"
    sentinel_join:
      left_table: "UserAccount"
      right_table: "DeviceLogonEvents"
      join_condition: "UserAccount.AccountName == DeviceLogonEvents.Account"

tables:
  UserAccount:
    description: "User table"
    retention_days: 90
    fields: [AccountName, UserEmail]
```

## Output Formats

### Text (Default)
Pretty-printed with colors and formatting.

### JSON
```json
{
  "cypher": "...",
  "kql": "...",
  "strategy": "fast_path",
  "confidence": 0.95
}
```

### CSV
For Excel/spreadsheets.

### Raw
Just the KQL, no formatting.

## Real-World Examples

### Example 1: Single Query Check
```bash
yellowstone translate "MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d" --show-ast
```
Shows AST and translated KQL with metadata.

### Example 2: Batch Translation
```bash
# Create query file
cat > queries.cypher << EOF
MATCH (u:User) RETURN u.name
MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d
EOF

# Translate to JSON
yellowstone translate-file queries.cypher --format json --output results.json

# Results saved to results.json
```

### Example 3: Schema Validation
```bash
# Validate schema before using in production
yellowstone validate-schema prod_schema.yaml --verbose

# Check exit code
echo $?  # 0 = valid, 1 = invalid
```

### Example 4: Interactive Workflow
```bash
# Start REPL with your schema
yellowstone repl --schema sentinel_schema.yaml

# In REPL:
# > MATCH (u:User) RETURN u.email
# Shows translation immediately
# > ast MATCH (n:Device) RETURN n
# Shows AST structure
# > help
# Shows available commands
# > exit
# Quit REPL
```

## Troubleshooting

### Query Not Translating
```bash
# Check syntax
yellowstone translate "YOUR_QUERY" --show-ast

# Look for error message - fix Cypher syntax if needed
```

### Schema Validation Fails
```bash
# Get details
yellowstone validate-schema schema.yaml --verbose

# Common issues:
# - Missing version or description field
# - Edge references unknown node label
# - Missing sentinel_field in property mappings
```

### File Not Found
```bash
# Check file exists
ls -la queries.cypher

# Use absolute path if needed
yellowstone translate-file /full/path/to/queries.cypher
```

## Tips & Tricks

### Pipe Output
```bash
# Get just KQL and pipe to another command
yellowstone translate "MATCH (u:User) RETURN u" --format raw | wc -l
```

### Programmatic Use
```bash
# Get JSON and parse with jq
yellowstone translate "MATCH (u:User) RETURN u" --format json | jq '.kql'
```

### Batch with Error Tracking
```bash
# Translate with error handling
yellowstone translate-file queries.cypher --skip-errors --format json --output log.json
```

### Schema Validation in Scripts
```bash
if yellowstone validate-schema schema.yaml; then
    echo "Schema OK, proceeding..."
    yellowstone translate-file queries.cypher
else
    echo "Schema validation failed!"
    exit 1
fi
```

## Help

Get help for any command:
```bash
yellowstone --help
yellowstone translate --help
yellowstone translate-file --help
yellowstone validate-schema --help
yellowstone repl --help
```

## Performance Notes

- **Single query**: < 100ms typically
- **Batch 100 queries**: ~5-10s depending on query complexity
- **Schema validation**: < 50ms
- **REPL translation**: < 100ms per query

## More Information

For complete command reference:
See: `CLI_REFERENCE.md`

For implementation details:
See: `CLI_IMPLEMENTATION_SUMMARY.md`
