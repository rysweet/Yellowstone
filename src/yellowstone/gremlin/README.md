# Gremlin Module

Complete Gremlin query parsing and translation for Neptune Analytics compatibility.

## Overview

This module provides:
1. **Gremlin Parser**: Converts Gremlin query strings to AST structures
2. **Cypher Bridge**: Translates Gremlin AST to Cypher query AST for Neptune Analytics

## Module Structure

```
gremlin/
├── __init__.py              # Public interface
├── ast.py                   # Gremlin AST data structures (NEW)
├── parser.py                # Gremlin query parser (NEW)
├── ast_nodes.py             # Legacy Gremlin AST structures
├── cypher_bridge.py         # Translation logic
├── README.md                # This file
├── examples/
│   └── basic_usage.py       # Parser usage examples (NEW)
└── tests/
    ├── __init__.py
    ├── test_parser.py           # Parser tests (NEW - 48 tests)
    └── test_cypher_bridge.py    # Bridge tests
```

---

# Part 1: Gremlin Parser

## Quick Start

```python
from yellowstone.gremlin import parse_gremlin

# Parse a Gremlin query string
traversal = parse_gremlin("g.V().hasLabel('Person').out('KNOWS').values('name')")

# Access parsed steps
for step in traversal.steps:
    print(f"{step.step_type}: {step}")
```

## Supported Gremlin Steps

### Source Steps
- `V()` - All vertices
- `V(id)` - Specific vertex
- `E()` - All edges
- `E(id)` - Specific edge

### Filter Steps
- `hasLabel('label')` - Filter by label
- `has('property', value)` - Filter by property value
- `has('property', predicate)` - Filter by predicate (gt, lt, eq, etc.)
- `hasId('id')`, `hasKey('key')`, `hasValue('value')`

### Traversal Steps
- `out('label')`, `in('label')`, `both('label')` - Navigate relationships
- `outE()`, `inE()`, `bothE()` - Navigate to edges
- `outV()`, `inV()`, `bothV()`, `otherV()` - Navigate from edges to vertices

### Projection Steps
- `values('prop1', 'prop2')` - Property values
- `valueMap()` - All properties as map
- `properties('prop')` - Property objects
- `elementMap()` - Full element with properties

### Modifier Steps
- `limit(n)` - Limit results
- `order()` - Order results
- `count()` - Count results
- `dedup()` - Remove duplicates

### Predicates
- `gt(value)`, `gte(value)`, `lt(value)`, `lte(value)` - Comparisons
- `eq(value)`, `neq(value)` - Equality
- `within(list)`, `without(list)` - List membership

## Parser Examples

### Basic Query
```python
query = "g.V().hasLabel('Person')"
traversal = parse_gremlin(query)
# Result: [VertexStep(), FilterStep(hasLabel, 'Person')]
```

### With Predicates
```python
query = "g.V().hasLabel('Person').has('age', gt(30))"
traversal = parse_gremlin(query)

filter_step = traversal.steps[2]
print(filter_step.predicate.operator)  # 'gt'
print(filter_step.predicate.value.value)  # 30
```

### Complex Multi-Step
```python
query = "g.V().hasLabel('Person').out('knows').dedup().limit(10).values('name')"
traversal = parse_gremlin(query)
# Result: 6 steps with filters, traversal, dedup, limit, projection
```

## Parser Testing

Run 48 comprehensive tests with 85% coverage:

```bash
uv run pytest src/yellowstone/gremlin/tests/test_parser.py -v
```

Test coverage includes:
- Basic parsing (6 tests)
- Filter steps (8 tests)
- Traversal steps (7 tests)
- Projection steps (6 tests)
- Modifier steps (4 tests)
- Complex queries (6 tests)
- Quote handling (2 tests)
- Whitespace (2 tests)
- Error handling (4 tests)
- String representation (3 tests)

## Parser Examples Script

Run comprehensive examples:

```bash
uv run python -m yellowstone.gremlin.examples.basic_usage
```

---

# Part 2: Gremlin-to-Cypher Bridge

## Translation Strategy

The bridge uses a multi-phase translation approach:

### 1. Collect Information
Scans all Gremlin steps to understand query intent:
- **VertexStep/EdgeStep** → Starting point identification
- **FilterStep** → Property filters and label constraints
- **TraversalStep** → Navigation patterns (out/in/both)
- **ProjectionStep** → Return projections (values)
- **LimitStep/OrderStep** → Result modifiers

### 2. Build MATCH Clause
Converts traversal patterns to Cypher path patterns:
- `VertexStep()` + `hasLabel('User')` → `(v:User)`
- `out('OWNS')` → `-[:OWNS]->`
- Chains multiple traversals → `(v0)-[:REL1]->(v1)-[:REL2]->(v2)`

### 3. Build WHERE Clause
Converts filter steps to Cypher predicates:
- `has('prop', value)` → `v.prop = value`
- Multiple filters → Combined with AND logic

### 4. Build RETURN Clause
Converts projections to Cypher return items:
- No projection → `RETURN v`
- `values('name')` → `RETURN v.name`
- With order/limit → Adds ORDER BY and LIMIT modifiers

## Public Interface

### Main Function

```python
from yellowstone.gremlin.cypher_bridge import translate_gremlin_to_cypher
from yellowstone.gremlin.ast_nodes import GremlinTraversal

def translate_gremlin_to_cypher(traversal: GremlinTraversal) -> Query:
    """
    Translate a Gremlin traversal to a Cypher query AST.

    Args:
        traversal: The Gremlin traversal to translate

    Returns:
        Query object representing the equivalent Cypher query

    Raises:
        TranslationError: If traversal cannot be translated
        UnsupportedPatternError: If traversal uses unsupported patterns
    """
```

### Exception Classes

```python
class TranslationError(Exception):
    """Raised when Gremlin traversal cannot be translated to Cypher."""

class UnsupportedPatternError(TranslationError):
    """Raised when encountering unsupported Gremlin patterns."""
```

## Usage Examples

### Basic Query

```python
from yellowstone.gremlin.ast_nodes import GremlinTraversal, VertexStep, FilterStep
from yellowstone.gremlin.cypher_bridge import translate_gremlin_to_cypher

# g.V().hasLabel('User')
traversal = GremlinTraversal(steps=[
    VertexStep(),
    FilterStep(predicate='hasLabel', args=['User'])
])

query = translate_gremlin_to_cypher(traversal)
# Result: MATCH (v:User) RETURN v
```

### Query with Filters

```python
# g.V().hasLabel('User').has('age', 30).has('active', True)
traversal = GremlinTraversal(steps=[
    VertexStep(),
    FilterStep(predicate='hasLabel', args=['User']),
    FilterStep(predicate='has', args=['age', 30]),
    FilterStep(predicate='has', args=['active', True])
])

query = translate_gremlin_to_cypher(traversal)
# Result: MATCH (v:User) WHERE v.age = 30 AND v.active = true RETURN v
```

### Query with Traversal

```python
# g.V().hasLabel('User').out('OWNS').values('name')
traversal = GremlinTraversal(steps=[
    VertexStep(),
    FilterStep(predicate='hasLabel', args=['User']),
    TraversalStep(direction='out', edge_label='OWNS'),
    ProjectionStep(type='values', properties=['name'])
])

query = translate_gremlin_to_cypher(traversal)
# Result: MATCH (v0:User)-[:OWNS]->(v1) RETURN v1.name
```

### Complex Query

```python
# g.V().hasLabel('User').has('active', True)
#   .out('OWNS').values('name').order().by('name').limit(10)
traversal = GremlinTraversal(steps=[
    VertexStep(),
    FilterStep(predicate='hasLabel', args=['User']),
    FilterStep(predicate='has', args=['active', True]),
    TraversalStep(direction='out', edge_label='OWNS'),
    ProjectionStep(type='values', properties=['name']),
    OrderStep(property='name', ascending=True),
    LimitStep(count=10)
])

query = translate_gremlin_to_cypher(traversal)
# Result: MATCH (v0:User)-[:OWNS]->(v1)
#         WHERE v0.active = true
#         RETURN v1.name ORDER BY v1.name ASC LIMIT 10
```

## Supported Patterns (MVP)

### Starting Points
- ✅ `V()` - All vertices
- ✅ `V(id)` - Specific vertex (ID ignored in MVP)
- ❌ `E()` - Edge starting point (not yet supported)

### Filters
- ✅ `hasLabel('Label')` - Node label constraint
- ✅ `has('property', value)` - Property equality filter
- ❌ `where()` - Complex predicates (not yet supported)
- ❌ `is()` - Value comparison (not yet supported)

### Traversals
- ✅ `out('LABEL')` - Outgoing relationships
- ✅ `in('LABEL')` - Incoming relationships
- ✅ `both('LABEL')` - Undirected relationships
- ✅ `out()` - Any outgoing relationship
- ❌ `outE()`, `inE()`, `bothE()` - Edge traversals (not yet supported)
- ❌ `inV()`, `outV()` - Vertex from edge (not yet supported)

### Projections
- ✅ `values('prop1', 'prop2')` - Property values
- ❌ `project()` - Complex projections (not yet supported)
- ❌ `select()` - Variable selection (not yet supported)

### Modifiers
- ✅ `limit(n)` - Result limit
- ✅ `order().by('prop')` - Result ordering (ascending/descending)
- ❌ `skip(n)` - Result offset (not yet supported)
- ❌ `dedup()` - Distinct results (not yet supported)

## Mapping Reference

| Gremlin Pattern | Cypher Equivalent | Example |
|----------------|-------------------|---------|
| `g.V()` | `MATCH (v)` | All vertices |
| `hasLabel('User')` | `(v:User)` | Label constraint |
| `has('age', 30)` | `WHERE v.age = 30` | Property filter |
| `out('OWNS')` | `-[:OWNS]->` | Outgoing relationship |
| `in('OWNS')` | `<-[:OWNS]-` | Incoming relationship |
| `both('KNOWS')` | `-[:KNOWS]-` | Undirected relationship |
| `values('name')` | `RETURN v.name` | Property projection |
| `limit(10)` | `LIMIT 10` | Result limit |
| `order().by('name')` | `ORDER BY v.name` | Result ordering |

## Error Handling

The bridge provides clear error messages for unsupported or invalid patterns:

```python
# Empty traversal
traversal = GremlinTraversal(steps=[])
# Raises: TranslationError("Empty traversal - no steps to translate")

# Invalid starting step
traversal = GremlinTraversal(steps=[FilterStep(...)])
# Raises: TranslationError("Traversal must start with V() or E()")

# Unsupported pattern
traversal = GremlinTraversal(steps=[
    VertexStep(),
    TraversalStep(direction='outE', edge_label='OWNS')
])
# Raises: UnsupportedPatternError("Traversal direction 'outE' not yet supported")
```

## Testing

Comprehensive test suite with 33 tests covering:
- Basic translations
- Filter translations
- Traversal translations
- Projection translations
- Modifiers (limit, order)
- Complex queries
- Error handling
- Edge cases

Run tests:
```bash
uv run pytest src/yellowstone/gremlin/tests/test_cypher_bridge.py -v
```

## Design Principles

### Zero-BS Implementation
- All functions work or don't exist
- Clear error messages for unsupported patterns
- No TODOs without implementation

### Self-Contained Module
- All translation logic in one module
- Clear public interface via exceptions and main function
- Well-documented with examples

### Contract-Based Testing
- Tests verify inputs/outputs match specifications
- No implementation detail testing
- Full coverage of supported patterns and error cases

## Future Extensions

Potential enhancements for future versions:
- Edge starting points (E())
- Complex predicates (where(), is())
- Edge traversals (outE(), inE(), inV(), outV())
- Advanced projections (project(), select())
- Aggregations (count(), sum(), etc.)
- Subqueries and unions
- Variable bindings across steps

## Dependencies

- `yellowstone.gremlin.ast_nodes` - Gremlin AST structures
- `yellowstone.parser.ast_nodes` - Cypher AST structures

## Module Contract

**Input**: `GremlinTraversal` object with list of `Step` objects

**Output**: `Query` object representing equivalent Cypher query

**Behavior**:
- Translates supported Gremlin patterns to Cypher AST
- Raises `TranslationError` for invalid traversals
- Raises `UnsupportedPatternError` for unsupported patterns
- Preserves query semantics during translation
- Generates valid Cypher AST structures

**Guarantees**:
- All returned `Query` objects are valid and executable
- Variable names are unique and consistent (v0, v1, v2, ...)
- Path structures are validated before return
- All property values are correctly typed
