# Yellowstone

Cypher-to-KQL translator for Microsoft Sentinel, enabling graph query capabilities for security analysts.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

Yellowstone translates Cypher graph queries into KQL (Kusto Query Language) for Microsoft Sentinel. Security analysts can use familiar graph query syntax to investigate relationships between entities like users, devices, and security events.

**Status**: Core translation functional.

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Microsoft Sentinel workspace access (optional, for execution)
- Claude API key (optional, for AI-enhanced translation)

### Installation

```bash
git clone https://github.com/rysweet/Yellowstone.git
cd Yellowstone
pip install -e .
```

### Basic Usage

```python
from yellowstone.parser import parse_cypher
from yellowstone.translator import CypherToKQLTranslator

# Parse Cypher query
cypher = "MATCH (u:User)-[:LOGGED_IN]->(d:Device) WHERE u.age > 25 RETURN u.name"
ast = parse_cypher(cypher)

# Translate to KQL
translator = CypherToKQLTranslator()
result = translator.translate(ast)

print(result.query)
```

**Output:**
```kql
IdentityInfo
| make-graph AccountObjectId with_node_id=AccountObjectId
| graph-match (u:User)-[:LOGGED_IN]->(d:Device)
| where u.age > 25
| project u.name
```

## Features

### Implemented

- **Cypher Parsing**: Full MATCH, WHERE, RETURN clause support
- **KQL Generation**: Uses native `make-graph` and `graph-match` operators
- **Schema Mapping**: Maps Cypher labels to Sentinel tables (IdentityInfo, DeviceInfo, SecurityEvent, etc.)
- **Property Access**: Node and relationship property filtering
- **AI Enhancement**: Optional Claude-powered translation for complex queries

### Current Limitations

- Variable-length paths (`-[*1..3]->`) not fully validated
- Multi-hop queries (>3 hops) have limited testing
- Schema mappings are generic and may need tuning for specific environments

## Architecture

```
Cypher Query
     |
     v
Parser (ANTLR + openCypher grammar)
     |
     v
Translation Routing
     |
     +-- Fast Path (85%): Direct KQL operators
     +-- AI Path (10%): Claude SDK for complex patterns
     +-- Fallback (5%): Join-based translation
     |
     v
KQL Output -> Microsoft Sentinel
```

**Key Components:**
- `yellowstone.parser`: Cypher parsing and AST generation
- `yellowstone.translator`: KQL generation and query assembly
- `yellowstone.schema`: Sentinel table and relationship mappings
- `yellowstone.ai_translator`: Claude SDK integration (optional)

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Usage Examples

### Basic Node Query

**Cypher:**
```cypher
MATCH (u:User) WHERE u.age > 30 RETURN u.name LIMIT 10
```

**Generated KQL:**
```kql
IdentityInfo
| make-graph AccountObjectId with_node_id=AccountObjectId
| graph-match (u:User)
| where u.age > 30
| project u.name
| limit 10
```

### Relationship Query

**Cypher:**
```cypher
MATCH (u:User)-[:LOGGED_IN]->(d:Device)
WHERE d.os_type == "Windows"
RETURN u.name, d.device_id
```

**Generated KQL:**
```kql
IdentityInfo
| join kind=inner (DeviceInfo) on AccountName == DeviceName
| make-graph AccountObjectId with_node_id=AccountObjectId
| graph-match (u:User)-[:LOGGED_IN]->(d:Device)
| where d.os_type == "Windows"
| project u.name, d.device_id
```

### Multi-Node Pattern

**Cypher:**
```cypher
MATCH (u:User)-[:ACCESSED]->(f:File)<-[:CREATED_BY]-(p:Process)
RETURN u.name, f.path, p.name
```

**Generated KQL:**
```kql
IdentityInfo
| join kind=inner (FileInfo) on AccountObjectId == FileOwnerId
| join kind=inner (ProcessInfo) on FileId == ProcessCreatedFileId
| make-graph AccountObjectId with_node_id=AccountObjectId
| graph-match (u:User)-[:ACCESSED]->(f:File)<-[:CREATED_BY]-(p:Process)
| project u.name, f.path, p.name
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/yellowstone --cov-report=html

# Run specific test suite
pytest tests/integration
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed system architecture and design
- [TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md) - Translation rules and patterns
- [SCHEMA_GUIDE.md](docs/SCHEMA_GUIDE.md) - Schema mapping configuration
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Command reference and examples

Research and planning documents are in the [context/](context/) directory.

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/rysweet/Yellowstone.git
cd Yellowstone

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/
```

### Project Structure

```
src/yellowstone/
├── parser/              # Cypher parsing (ANTLR)
├── translator/          # KQL generation
├── schema/              # Sentinel schema mappings
├── ai_translator/       # Claude SDK integration
└── security/            # Input validation

tests/
├── integration/         # End-to-end tests
└── sentinel_integration/ # Azure validation tests

docs/                    # Detailed documentation
context/                 # Research and planning
```

## Contributing

This is currently a development project. Contribution guidelines will be published upon initial release.

For questions or discussions, open an issue on GitHub.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Resources

- [openCypher Specification](https://opencypher.org)
- [KQL Graph Semantics](https://learn.microsoft.com/en-us/kusto/query/graph-semantics-overview)
- [Microsoft Sentinel Documentation](https://learn.microsoft.com/en-us/azure/sentinel/)
- [Claude Agent SDK](https://docs.anthropic.com/en/api)

## Contact

Project Lead: Ryan Sweet (@rysweet)
