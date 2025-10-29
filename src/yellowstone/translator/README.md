# KQL Translator Module

Translates Cypher query AST structures into KQL (Kusto Query Language) queries for Azure Data Explorer.

## Module Overview

The translator module provides end-to-end translation of Cypher queries to KQL using a modular architecture:

- **translator.py**: Main orchestrator coordinating all clause translators
- **graph_match.py**: Translates MATCH clauses to graph-match syntax
- **where_clause.py**: Translates WHERE clauses with operator conversion
- **return_clause.py**: Translates RETURN clauses with projection and aggregation
- **paths.py**: Handles variable-length path specifications

## Features

### Supported Cypher Constructs

**MATCH Clauses:**
- Simple node-relationship-node patterns
- Multi-hop paths
- Optional MATCH patterns
- Multiple disjoint patterns (comma-separated)
- Node labels and properties
- Relationship types and directions

**WHERE Clauses:**
- Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Logical operators: `AND`, `OR`, `NOT`
- Property access: `n.name`, `r.weight`
- Literals: strings, numbers, booleans, null
- Functions: `SIZE()`, `LENGTH()`, `CONTAINS()`, `UPPER()`, etc.

**RETURN Clauses:**
- Simple projections: `RETURN n, m.name`
- DISTINCT modifier
- Aggregation functions: `COUNT()`, `SUM()`, `AVG()`, `MIN()`, `MAX()`
- ORDER BY with ASC/DESC
- LIMIT and SKIP

**Path Patterns:**
- Fixed-length paths: `(n)-[r1]->(m)-[r2]->(p)`
- Variable-length paths: `(n)-[r*1..3]->(m)`
- Unbounded paths: `(n)-[r*]->(m)`

## Architecture

### Class Hierarchy

```
CypherToKQLTranslator (main orchestrator)
├── GraphMatchTranslator
├── WhereClauseTranslator
├── ReturnClauseTranslator
└── PathTranslator
```

### Translation Pipeline

1. **Parse**: Input Cypher query string parsed to AST (handled by parser module)
2. **Match**: Translate MATCH patterns to `graph-match` syntax
3. **Filter**: Translate WHERE conditions with operator mapping
4. **Project**: Translate RETURN items and aggregations
5. **Assemble**: Combine clauses into complete KQL query

## Usage

### Basic Translation

```python
from yellowstone.translator import translate
from yellowstone.parser.ast_nodes import Query, MatchClause, ReturnClause

# Assuming you have a parsed Query AST
kql_result = translate(query)
print(kql_result.query)
print(kql_result.confidence)  # 0.95
```

### Direct Translator Usage

```python
from yellowstone.translator import CypherToKQLTranslator

translator = CypherToKQLTranslator()

# Translate specific clause types
match_kql = translator.translate_match(match_clause)
where_kql = translator.translate_where(where_clause)
return_kql = translator.translate_return(return_clause)

# Get full translation
kql_query = translator.translate(query)
```

### Analysis and Metadata

```python
# Get translation summary without full translation
summary = translator.get_translation_summary(query)
print(summary["num_hops"])
print(summary["estimated_complexity"])  # "Low", "Medium", or "High"
```

## Translation Examples

### Example 1: Simple Path

**Cypher:**
```cypher
MATCH (n:Person)-[r:KNOWS]->(m:Person)
WHERE n.name = 'Alice'
RETURN n, m.name
```

**KQL:**
```kql
graph-match (n:Person)-[r:KNOWS]->(m:Person)
| where n.name == 'Alice'
| project n, m.name
```

### Example 2: Variable-Length Path

**Cypher:**
```cypher
MATCH (n:Person)-[r*1..3]->(m:Person)
RETURN n, m
```

**KQL:**
```kql
graph-match (n:Person)-[r*1..3]->(m:Person)
| project n, m
```

### Example 3: Aggregation

**Cypher:**
```cypher
MATCH (n:Person)-[r:KNOWS]->(m:Person)
RETURN n.name, COUNT(m) as known_people
ORDER BY known_people DESC
LIMIT 10
```

**KQL:**
```kql
graph-match (n:Person)-[r:KNOWS]->(m:Person)
| project n.name, count(m) as known_people
| sort by known_people desc
| limit 10
```

## Operator Mapping

### Comparison Operators

| Cypher | KQL |
|--------|-----|
| `=`    | `==` |
| `!=`   | `!=` |
| `<`    | `<`  |
| `>`    | `>`  |
| `<=`   | `<=` |
| `>=`   | `>=` |

### Logical Operators

| Cypher | KQL |
|--------|-----|
| `AND`  | `and` |
| `OR`   | `or` |
| `NOT`  | `not()` |

### Function Mapping

| Cypher       | KQL                |
|--------------|-------------------|
| `COUNT()`    | `count()`         |
| `SUM()`      | `sum()`           |
| `AVG()`      | `avg()`           |
| `MIN()`      | `min()`           |
| `MAX()`      | `max()`           |
| `COLLECT()`  | `make_set()`      |
| `SIZE()`     | `array_length()`  |
| `LENGTH()`   | `array_length()`  |
| `UPPER()`    | `toupper()`       |
| `LOWER()`    | `tolower()`       |
| `TRIM()`     | `trim()`          |
| `SUBSTRING()`| `substring()`     |

## Error Handling

All translators use comprehensive error handling:

- **ValueError**: Invalid structure, unsupported constructs, invalid values
- **KeyError**: Missing required fields in AST nodes
- **TypeError**: Wrong input types

Example:
```python
from yellowstone.translator import translate

try:
    kql_result = translate(invalid_query)
except ValueError as e:
    print(f"Translation failed: {e}")
except TypeError as e:
    print(f"Invalid input type: {e}")
```

## Type Hints

All functions include full type hints for IDE support and type checking:

```python
def translate(query: Query, confidence: float = 0.95) -> KQLQuery:
    """Translate Cypher query AST to KQL."""
    ...
```

## Performance Characteristics

- **Time Complexity**: O(n) where n is the size of the AST
- **Space Complexity**: O(n) for building result strings
- **Typical Execution**: < 1ms for average queries

## Limitations and Future Work

### Current Limitations

1. **Subqueries**: Not yet supported
2. **Complex Path Expressions**: Some advanced patterns may need AI translation
3. **Custom Cypher Functions**: User-defined functions not supported
4. **UNION**: Multiple RETURN branches not supported
5. **CREATE/UPDATE/DELETE**: Only READ queries supported

### Planned Enhancements

1. Subquery support with nested graph-match
2. Complex expression simplification
3. Query optimization and reordering
4. Better error messages with suggestions
5. Performance metrics and profiling

## Testing

See `tests/` directory for comprehensive test coverage:

- `test_translator.py`: Main translator orchestration
- `test_graph_match.py`: MATCH clause translation
- `test_where_clause.py`: WHERE clause translation
- `test_return_clause.py`: RETURN clause translation
- `test_paths.py`: Path pattern handling

## Module Contract

### Input
- Cypher query AST (from `yellowstone.parser.ast_nodes`)
- Query must have MATCH and RETURN clauses
- WHERE clause is optional

### Output
- KQLQuery object with:
  - `query`: Translated KQL string
  - `strategy`: TranslationStrategy (FAST_PATH for all AST translations)
  - `confidence`: Float between 0.0-1.0
  - `estimated_execution_time_ms`: Optional timing estimate

### Guarantees

1. **Deterministic**: Same input always produces same output
2. **Lossless for Graph Patterns**: All graph matching semantics preserved
3. **Error on Invalid**: Raises exception rather than silent failure
4. **Immutable**: Translator instances don't modify inputs

## Dependencies

- **Pydantic**: AST validation (via ast_nodes.py)
- **Python 3.12+**: Type hints, dataclasses, match statements

## Integration Points

- **Parser**: Accepts Query AST from `yellowstone.parser`
- **Models**: Returns KQLQuery from `yellowstone.models`
- **Schema**: May use schema information for validation (future)
