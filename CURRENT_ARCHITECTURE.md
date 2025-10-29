# Current Architecture

**Last Updated**: 2025-10-29 (after simplification)

## What This Project Is

A **Cypher-to-KQL translator** that converts Cypher graph queries into KQL queries using Kusto's native `make-graph` operator.

## Core Modules (Essential)

### 1. Parser (`src/yellowstone/parser/`)
- Converts Cypher text to AST
- Supports: MATCH, WHERE, RETURN, LIMIT
- **Status**: Working, 64 tests

### 2. Translator (`src/yellowstone/translator/`)
- Converts AST to KQL components
- `graph_match.py` - MATCH → graph-match
- `where_clause.py` - WHERE → where
- `return_clause.py` - RETURN → project
- `paths.py` - Variable-length paths
- **Status**: Working for simple queries

### 3. Main Translator (`src/yellowstone/main_translator.py`)
- Orchestrates parser + translators
- Generates complete KQL
- **Status**: Working, 35 integration tests passing

### 4. Schema Mapper (`src/yellowstone/schema/`)
- Maps Cypher labels → Sentinel tables
- User → IdentityInfo, Device → DeviceInfo, etc.
- **Status**: Working, YAML-based

### 5. Security (`src/yellowstone/security/`)
- Authorization and tenant isolation
- Injection prevention (AST-based)
- Audit logging
- **Status**: Implemented, not tested

### 6. AI Translator (`src/yellowstone/ai_translator/`)
- Handles complex queries via Anthropic API
- Query classification and routing
- Pattern caching
- **Status**: Implemented, requires CLAUDE_API_KEY

### 7. CLI (`src/yellowstone/cli.py`)
- Command-line interface
- Commands: translate, translate-file, validate-schema
- **Status**: Implemented

## Supporting Module (Review Needed)

### Optimizer (`src/yellowstone/optimizer/`)
- KQL query optimization (filter pushdown, join ordering)
- **Question**: Is this premature optimization?
- **Size**: ~650 lines
- **Decision**: Keep for now, review if actually needed

## What Was Removed

Based on architecture review against Microsoft documentation:

### Removed: persistent_graph/ (2,100 lines)
- **Why**: Based on misunderstanding of `make-graph`
- KQL make-graph creates TRANSIENT graphs (exist only during query)
- Module implemented lifecycle management for graphs that don't persist
- Not needed for translation

### Removed: algorithms/ (~800 lines)
- **Why**: KQL has native graph algorithms
- We translate to `graph-shortest-paths`, we don't implement it
- Not needed

### Removed: load_testing/ (~700 lines)
- **Why**: Testing query execution performance, not translation
- Translation is microseconds, not worth load testing
- Not needed

### Removed: monitoring/ (~800 lines)
- **Why**: Over-engineered for translation monitoring
- If needed: Simple metrics in translator, not separate module
- Not needed currently

### Removed: benchmarks/ (~700 lines)
- **Why**: Benchmarking Sentinel query execution
- Should benchmark translation time (microseconds), not query execution
- Not needed

**Total removed**: ~5,100 lines (70% of codebase)

## Translation Pipeline

```
Cypher Query String
    ↓
[Parser] → AST
    ↓
[Schema Mapper] → Get table mappings
    ↓
[Translator] → Generate KQL components
    ↓
[Main Translator] → Assemble complete KQL
    ↓
KQL Query String (with make-graph)
```

## Current Issues

### Critical
1. **Translator doesn't generate make-graph operator**
   - Generates: `graph-match (n:User) | project n`
   - Should generate: `IdentityInfo | make-graph ... | graph-match (n:User) | project n`
   - Status: Needs fixing

2. **Parser doesn't handle property access in RETURN**
   - Can't parse: `RETURN n.name, n.age`
   - Can parse: `RETURN n`
   - Status: Needs fixing

### Non-Critical
- Schema mapper not integrated with translator
- Optimizer may be unnecessary complexity
- AI translator requires API key setup

## Validated Against Azure

- ✓ Can create/delete Log Analytics workspaces
- ✓ Can execute KQL queries
- ✓ Cypher parsing works
- ✓ KQL generation works (incomplete)
- **Cost**: ~$0.20 for validation tests

## Current Code Size

- **Python files**: 55
- **Total lines**: ~6,000 (down from ~31,000)
- **Focus**: Translation, not graph management

## Next Steps

1. Fix make-graph generation in translator
2. Fix parser for property access
3. Review if optimizer is actually needed
4. Simplify further if possible
