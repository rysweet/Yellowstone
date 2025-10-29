# Yellowstone CLI Reference

Complete command-line interface for the Yellowstone Cypher to KQL translator.

## Overview

The Yellowstone CLI provides four main commands for working with Cypher queries:

1. **translate** - Translate single Cypher queries
2. **translate-file** - Batch translate queries from a file
3. **validate-schema** - Validate schema YAML files
4. **repl** - Interactive REPL mode

## Installation

The CLI is implemented in `/home/azureuser/src/Yellowstone/src/yellowstone/cli.py`

Required dependencies:
- click (>=8.0)
- rich (for formatted output)
- pyyaml (for schema parsing)
- pydantic (for schema validation)

## Commands

### translate

Translate a single Cypher query to KQL.

```bash
yellowstone translate "MATCH (u:User) RETURN u.name"
```

**Options:**

- `--format [text|json|raw]` - Output format (default: text)
  - `text`: Rich formatted output with metadata table
  - `json`: JSON object with all translation details
  - `raw`: Plain KQL query string only

- `--show-ast` - Display the Cypher AST before translation

- `--confidence FLOAT` - Translation confidence score 0.0-1.0 (default: 0.95)

**Examples:**

```bash
# Simple translation with default formatting
yellowstone translate "MATCH (u:User) RETURN u.name"

# Show AST and translated query
yellowstone translate "MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d" --show-ast

# JSON output for programmatic use
yellowstone translate "MATCH (n) RETURN n" --format json

# Raw KQL output only
yellowstone translate "MATCH (n:User) RETURN n.email" --format raw

# Custom confidence score
yellowstone translate "MATCH (u:User) RETURN u" --confidence 0.8
```

### translate-file

Translate multiple Cypher queries from a file.

```bash
yellowstone translate-file queries.cypher
```

**Input Format:**
- One query per line
- Empty lines and comment lines (starting with #) are ignored

**Options:**

- `--output PATH` - Write results to file instead of stdout

- `--format [text|json|csv]` - Output format (default: text)
  - `text`: Readable format with metadata for each query
  - `json`: JSON array of translation results
  - `csv`: CSV format for spreadsheet import

- `--skip-errors` - Continue processing if individual queries fail

- `--confidence FLOAT` - Translation confidence score 0.0-1.0 (default: 0.95)

**Examples:**

```bash
# Translate queries, output to stdout
yellowstone translate-file queries.cypher

# Save results to JSON file
yellowstone translate-file queries.cypher --output results.json --format json

# Save results to CSV for Excel
yellowstone translate-file queries.cypher --output results.csv --format csv

# Continue processing even if some queries fail
yellowstone translate-file queries.cypher --skip-errors

# Text output to file with metadata
yellowstone translate-file queries.cypher --output results.txt --format text
```

### validate-schema

Validate a schema YAML file for correctness and completeness.

```bash
yellowstone validate-schema schema.yaml
```

**Validation Checks:**
- Required fields present (version, description)
- Correct data types
- Referential integrity (edges reference valid nodes)
- Sentinel table consistency
- Property mapping validity

**Options:**

- `-v, --verbose` - Show detailed validation information
  - Displays node and edge mappings
  - Shows property-to-field mappings
  - Lists join conditions and strengths

- `--fix-warnings` - Attempt to auto-fix non-critical issues (reserved for future use)

**Exit Codes:**
- 0: Schema is valid
- 1: Validation errors found

**Examples:**

```bash
# Basic validation
yellowstone validate-schema schema.yaml

# Detailed output with all mappings
yellowstone validate-schema schema.yaml --verbose

# Short form verbose flag
yellowstone validate-schema schema.yaml -v
```

### repl

Start interactive REPL (Read-Eval-Print Loop) for testing translations.

```bash
yellowstone repl
```

**Options:**

- `--schema PATH` - Optional schema file for context-aware translation

**REPL Commands:**

- `query <cypher>` - Translate a Cypher query
- `ast <cypher>` - Show AST for a Cypher query
- `<cypher>` - Direct query string (auto-translates)
- `help` - Show available commands
- `exit` / `quit` - Exit REPL

**Examples:**

```bash
# Start interactive REPL
yellowstone repl

# Load with schema for enhanced validation
yellowstone repl --schema schema.yaml

# In REPL:
yellowstone> MATCH (u:User) RETURN u.name
# [Translation result displayed]

yellowstone> ast MATCH (n:Device) RETURN n
# [AST displayed]

yellowstone> help
# [Commands displayed]

yellowstone> exit
# [Exit REPL]
```

## Global Options

- `--version` - Show version number (0.1.0)
- `--help` - Show help message

## Output Formatting

### Text Format

Rich-formatted output with syntax highlighting:
```
╭──── KQL Translation ─────╮
│   1 graph-match (u:User) │
│   2 | project u.name     │
╰──────────────────────────╯

   Translation Metadata
┏━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Property   ┃ Value     ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Strategy   │ fast_path │
│ Confidence │ 95.00%    │
└────────────┴───────────┘
```

### JSON Format

Machine-readable JSON:
```json
{
  "cypher": "MATCH (u:User) RETURN u.name",
  "kql": "graph-match (u:User)\n| project u.name",
  "strategy": "fast_path",
  "confidence": 0.95,
  "execution_time_ms": null
}
```

### CSV Format

Spreadsheet-compatible CSV:
```csv
query_num,cypher,kql,strategy,confidence,status
1,"MATCH (u:User) RETURN u.name","graph-match (u:User)\n| project u.name",fast_path,0.95,success
```

## Error Handling

The CLI provides clear error messages for common issues:

- **Syntax Error** - Invalid Cypher query syntax
- **Translation Error** - Query cannot be translated to KQL
- **File Not Found** - Input file does not exist
- **Schema Parse Error** - YAML schema is malformed
- **Validation Errors** - Schema validation failed

## Example Workflows

### Batch Translation

```bash
# Create file with multiple queries
cat > queries.cypher << EOF
MATCH (u:User) RETURN u.name
MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d
MATCH (n:Person {name: 'John'}) RETURN n.age
EOF

# Translate to JSON
yellowstone translate-file queries.cypher --format json --output results.json

# Verify output
cat results.json
```

### Schema Validation

```bash
# Validate schema with detailed output
yellowstone validate-schema schema.yaml --verbose

# If validation passes (exit code 0), can use in translation
if yellowstone validate-schema schema.yaml; then
    echo "Schema is valid, proceeding..."
    yellowstone repl --schema schema.yaml
fi
```

### Interactive Development

```bash
# Start REPL with schema
yellowstone repl --schema schema.yaml

# In REPL, iteratively test queries:
yellowstone> MATCH (u:User) RETURN u
# [See result]

yellowstone> ast MATCH (u:User)-[r:LOGGED_IN]->(d:Device) RETURN u, d
# [See AST]

yellowstone> exit
```

## Exit Codes

- **0** - Success (or valid schema)
- **1** - Error or invalid schema

## Implementation Details

- **Location**: `/home/azureuser/src/Yellowstone/src/yellowstone/cli.py`
- **Main Classes**: Uses Click for CLI framework, Rich for formatted output
- **Parser**: Uses `yellowstone.parser.parse_query()` for AST generation
- **Translator**: Uses `yellowstone.translator.translate()` for KQL generation
- **Validator**: Uses `yellowstone.schema.SchemaValidator` for validation
