# Cypher Parser Module

A robust recursive descent parser for Cypher queries with full Abstract Syntax Tree (AST) support and visitor pattern implementation.

## Overview

This module provides a complete Cypher query parser that converts query strings into a structured Abstract Syntax Tree (AST) for further processing, analysis, and translation. It includes:

- **Lexer**: Tokenizes Cypher query strings with support for keywords, operators, and literals
- **Parser**: Recursive descent parser that builds AST nodes
- **AST Nodes**: Pydantic-based dataclass models for type-safe representations
- **Visitor Pattern**: Base classes and utilities for AST traversal and transformation

## Features

### Supported Cypher Constructs

#### MATCH Clauses
- Simple nodes: `(n)`
- Nodes with labels: `(n:Person)`, `(n:Person:Actor)`
- Nodes with properties: `(n {name: 'John', age: 30})`
- Simple relationships: `(n)-[r]->(m)`
- Relationship types: `(n)-[r:KNOWS]->(m)`
- Directed relationships: `-[r]->` (outgoing), `<-[r]-` (incoming)
- Undirected relationships: `-[r]-` (both directions)
- Complex paths: `(n)-[r1]->(m)-[r2]->(p)`
- Multiple paths: `MATCH (n:Person), (m:Movie)`
- Optional matching: `OPTIONAL MATCH (n)`

#### WHERE Clauses
- Property comparisons: `n.name = 'John'`
- Comparison operators: `=`, `<>`, `!=`, `<`, `>`, `<=`, `>=`
- Logical operators: `AND`, `OR`
- Literal values: strings, numbers, booleans, null

#### RETURN Clauses
- Simple returns: `RETURN n`
- Multiple items: `RETURN n, m, n.name`
- Property access: `RETURN n.name`
- `DISTINCT`: `RETURN DISTINCT n.name`
- `ORDER BY`: `ORDER BY n.name ASC|DESC`
- `LIMIT`: `LIMIT 10`
- `SKIP`: `SKIP 5`

## Architecture

### Module Structure

```
parser/
├── __init__.py           # Public API exports
├── ast_nodes.py          # AST node definitions (Pydantic models)
├── parser.py             # Lexer and recursive descent parser
├── visitor.py            # Visitor pattern implementation
├── README.md             # This file
└── tests/
    ├── test_parser.py    # Parser tests
    └── test_visitor.py   # Visitor pattern tests
```

### Key Components

#### Lexer (`parser.py`)

Tokenizes input Cypher queries using regex patterns for:
- Keywords: `MATCH`, `WHERE`, `RETURN`, `AND`, `OR`, etc.
- Identifiers: Variable and label names
- Operators: `=`, `<>`, `->`, `<-`, `--`, etc.
- Literals: Strings (`'...'`), numbers, keywords (`TRUE`, `FALSE`, `NULL`)
- Delimiters: `()`, `[]`, `{}`, `:`, `.`, etc.

#### Parser (`parser.py`)

Recursive descent parser with the following hierarchy:
- `parse_query()` → Main entry point
- `parse_match()` → MATCH clause
- `parse_path()` → Path expressions
- `parse_node()` → Node patterns
- `parse_relationship()` → Relationship patterns
- `parse_where()` → WHERE clause with condition parsing
- `parse_return()` → RETURN clause

Error handling with detailed syntax error messages including position information.

#### AST Nodes (`ast_nodes.py`)

Pydantic BaseModel subclasses for type safety and validation:

**Core Nodes:**
- `Query` - Root node representing complete query
- `MatchClause` - MATCH clause with paths and optional flag
- `WhereClause` - WHERE clause with condition tree
- `ReturnClause` - RETURN clause with items and modifiers

**Pattern Nodes:**
- `PathExpression` - Path with nodes and relationships
- `NodePattern` - Node with variable, labels, properties
- `RelationshipPattern` - Relationship with type, direction, variable

**Expression Nodes:**
- `Property` - Property access (e.g., `n.name`)
- `Identifier` - Named identifier
- `Literal` - Literal value (string, number, boolean, null)

#### Visitor Pattern (`visitor.py`)

Base classes and utilities for AST traversal:

**Base Classes:**
- `Visitor[T]` - Abstract base with visit_* methods for each node type
- `DefaultVisitor` - Default implementation with simple traversal

**Concrete Visitors:**
- `CollectingVisitor` - Collects all identifiers and literals
- `ValidationVisitor` - Validates query structure and semantics
- `DotVisitor` - Generates GraphViz DOT representation

## Usage

### Basic Parsing

```python
from yellowstone.parser import parse_query

# Parse a simple query
query_str = "MATCH (n:Person) WHERE n.age > 30 RETURN n.name"
ast = parse_query(query_str)

# Access AST nodes
print(ast.match_clause.paths[0].nodes[0].labels[0].name)  # "Person"
```

### Complex Query Example

```python
from yellowstone.parser import parse_query

query_str = """
MATCH (actor:Person)-[r:ACTED_IN]->(movie:Movie)<-[d:DIRECTED]-(director:Person)
WHERE actor.birthYear >= 1960 AND movie.title = 'The Matrix'
RETURN actor.name, movie.title, director.name
ORDER BY actor.name
LIMIT 10
"""

ast = parse_query(query_str)

# Navigate the AST
match = ast.match_clause
path = match.paths[0]
print(f"Nodes: {len(path.nodes)}")      # 3
print(f"Relationships: {len(path.relationships)}")  # 2

where = ast.where_clause
print(f"Condition type: {where.conditions['type']}")  # 'logical'

ret = ast.return_clause
print(f"Return items: {len(ret.items)}")  # 3
print(f"Limit: {ret.limit}")  # 10
```

### Using Visitors

#### CollectingVisitor

```python
from yellowstone.parser import parse_query, CollectingVisitor

query = parse_query("MATCH (n:Person {name: 'John'}) RETURN n")

visitor = CollectingVisitor()
query.accept(visitor)

print("Identifiers:", [i.name for i in visitor.identifiers])
# ['n', 'Person', 'name']

print("Literals:", [(l.value, l.value_type) for l in visitor.literals])
# [('John', 'string')]
```

#### ValidationVisitor

```python
from yellowstone.parser import parse_query, ValidationVisitor

query = parse_query("MATCH (n:Person) RETURN m")  # 'm' not defined!

visitor = ValidationVisitor()
query.accept(visitor)

print("Errors:", visitor.errors)
print("Warnings:", visitor.warnings)
# Warnings: ["RETURN clause references undefined variable: 'm'"]
```

#### DotVisitor (GraphViz)

```python
from yellowstone.parser import parse_query, DotVisitor

query = parse_query("MATCH (n:Person)-[r:KNOWS]->(m) RETURN n, m")

visitor = DotVisitor()
dot = visitor.generate_dot(query)

# Save to file or render
with open("query.dot", "w") as f:
    f.write(dot)

# Generate PNG with: dot -Tpng query.dot -o query.png
```

#### Custom Visitor

```python
from yellowstone.parser import parse_query, DefaultVisitor

class RelationshipCounter(DefaultVisitor):
    def __init__(self):
        super().__init__()
        self.rel_count = 0

    def visit_relationship_pattern(self, node):
        self.rel_count += 1
        super().visit_relationship_pattern(node)

query = parse_query("MATCH (n)-[r1]->(m)-[r2]->(p) RETURN n")
counter = RelationshipCounter()
query.accept(counter)
print(f"Relationships: {counter.rel_count}")  # 2
```

## Error Handling

The parser provides detailed syntax error messages with position information:

```python
from yellowstone.parser import parse_query

try:
    parse_query("MATCH (n RETURN n")  # Missing closing paren
except SyntaxError as e:
    print(e)
    # SyntaxError: Expected RPAREN, got KEYWORD ('RETURN') at position 8
```

Common error scenarios:
- Missing closing parenthesis/bracket/brace
- Unexpected token types
- Invalid operator usage
- Missing required clauses

## Testing

Comprehensive test suite with 40+ tests covering:

### Parser Tests (`test_parser.py`)
- Lexer tokenization of all token types
- Node pattern parsing (labels, properties, variables)
- Relationship pattern parsing (directions, types)
- Path expression validation
- WHERE clause condition parsing
- RETURN clause with modifiers
- Complex multi-clause queries
- Error handling and edge cases

### Visitor Tests (`test_visitor.py`)
- Visitor pattern traversal
- Collection and aggregation
- Validation and error detection
- GraphViz generation
- Custom visitor implementation

### Running Tests

```bash
# Run all parser tests
pytest src/yellowstone/parser/tests/test_parser.py -v

# Run visitor tests
pytest src/yellowstone/parser/tests/test_visitor.py -v

# Run all tests with coverage
pytest src/yellowstone/parser/tests/ --cov=src/yellowstone/parser
```

## Performance Considerations

- **Linear tokenization**: O(n) where n is query length
- **Recursive descent parsing**: O(n) worst case
- **AST traversal**: O(m) where m is number of nodes in tree
- **Typical queries**: Parse in < 1ms

For production use, consider:
- Caching parsed ASTs for repeated queries
- Pre-compiling common query patterns
- Using visitor pattern for efficient transformations

## Design Patterns

### Visitor Pattern
Enables separation of algorithms from AST structure. Add new analyses without modifying node classes.

### Recursive Descent Parsing
Simple, predictable parsing for context-free Cypher grammar. Easy to debug and extend.

### Pydantic Models
Type safety, validation, and serialization built-in. AST nodes can be:
- Validated on creation
- Serialized to JSON/dict
- Used with type checkers (mypy)

## Limitations

Current implementation focuses on basic Cypher constructs:

Not yet supported:
- CRUD operations (CREATE, SET, DELETE, REMOVE)
- Aggregations (COUNT, SUM, etc.)
- Functions (exists, relationships, nodes, etc.)
- UNION queries
- Subqueries
- Parameters (except in WHERE)
- Complex expressions
- Mutations and transactions

These can be added incrementally without breaking the existing API.

## Future Enhancements

1. **ANTLR Integration**: Support full Cypher grammar specification
2. **Query Optimization**: AST-level optimizations before translation
3. **Caching**: Memoization of parsed queries
4. **Streaming**: Incremental parsing for large queries
5. **Error Recovery**: Better error recovery for partial queries
6. **Extensions**: Pluggable extensions for custom syntax

## Related Modules

- `translator.py` - Uses parser AST for KQL translation
- `translator/` - Translation strategies
- `models.py` - Core Yellowstone types
- `schema/` - Graph schema definitions

## Contributing

When extending the parser:

1. Add node definitions to `ast_nodes.py`
2. Implement parsing logic in `parser.py`
3. Add visitor methods to `visitor.py`
4. Update `__init__.py` exports
5. Add comprehensive tests
6. Update this README

## License

MIT - See root LICENSE file
