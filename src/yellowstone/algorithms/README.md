# Algorithms Module - Cypher to KQL Path Algorithms

## Overview

The algorithms module provides comprehensive translators for graph path operations, converting Cypher graph algorithms to KQL (Kusto Query Language) operations. It leverages KQL's native graph-shortest-paths operator and path enumeration capabilities.

## Features

### 1. Shortest Path Translation

Translates Cypher `shortestPath()` function to KQL `graph-shortest-paths` operator.

**Supported Capabilities:**
- Unweighted shortest path (minimum hop count)
- Weighted shortest path (minimum cost)
- Bidirectional search
- Multiple source/target nodes
- Path length constraints

**Example:**

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

# Basic shortest path
query = translator.translate_shortest_path("n", "m", "KNOWS")
# Output: graph-shortest-paths (n)-[KNOWS]->(m)

# With constraints
query = translator.translate_shortest_path(
    "n", "m", "KNOWS",
    constraints=PathConstraint(max_length=5)
)
# Output: graph-shortest-paths (n)-[KNOWS]->(m) | where path_length <= 5

# Weighted path
query = translator.translate_weighted_shortest_path(
    "n", "m", "ROAD", "distance"
)
# Output: graph-shortest-paths weight=distance (n)-[ROAD]->(m)

# Bidirectional search
query = translator.translate_bidirectional_shortest_path("n", "m")
# Output: graph-shortest-paths(bidirectional) (n)-[]->(m)
```

### 2. Path Algorithm Translation

Comprehensive path algorithms including all-shortest-paths and path enumeration.

**Supported Operations:**
- `allShortestPaths()` - All paths with minimum hop count
- `allPaths()` - Complete path enumeration
- Path filtering and constraints
- Variable-length path patterns
- Node and property-based filters

**Example:**

```python
from yellowstone.algorithms import PathAlgorithmTranslator, PathFilterConfig

translator = PathAlgorithmTranslator()

# All shortest paths
query = translator.translate_all_shortest_paths("n", "m", "KNOWS")
# Output: all_shortest_paths ((n)-[KNOWS]->(m))

# All paths with length constraints
query = translator.translate_all_paths(
    "n", "m", "KNOWS", max_length=5,
    enumeration=PathEnumerationConfig(cycle_detection=True)
)
# Output: all_paths ((n)-[KNOWS*1..5]->(m)) | where no_cycles

# Filtered paths
filters = PathFilterConfig(
    max_path_length=5,
    excluded_nodes=["intermediary"],
    min_path_length=2
)
query = translator.translate_filtered_paths(
    "n", "m", filters, "KNOWS"
)
```

## Core Classes

### ShortestPathTranslator

Main translator for shortest path operations.

**Key Methods:**

- `translate_shortest_path()` - Basic shortest path translation
- `translate_shortest_path_multiple_targets()` - Multiple target nodes
- `translate_shortest_path_multiple_sources()` - Multiple source nodes
- `translate_weighted_shortest_path()` - Weighted path search
- `translate_bidirectional_shortest_path()` - Bidirectional search
- `translate_constrained_shortest_path()` - Multiple constraints
- `extract_path_length_from_result()` - Extract path length from result
- `validate_cypher_shortest_path_syntax()` - Validate Cypher syntax

### PathAlgorithmTranslator

Handles additional path algorithms and complex queries.

**Key Methods:**

- `translate_all_shortest_paths()` - All shortest paths enumeration
- `translate_all_paths()` - Complete path enumeration
- `translate_filtered_paths()` - Paths with comprehensive filters
- `translate_path_with_node_constraints()` - Filter by node properties
- `translate_path_with_property_constraints()` - Filter by relationship properties
- `translate_variable_length_path_with_filter()` - Variable-length with filters
- `build_combined_path_query()` - Unified query builder

## Configuration Classes

### PathConstraint

Specifies path search constraints.

```python
@dataclass
class PathConstraint:
    max_length: Optional[int] = None      # Maximum path hops
    weighted: bool = False                 # Enable weighted search
    bidirectional: bool = False            # Enable bidirectional search
    weight_property: Optional[str] = None  # Property name for weights
```

### PathFilterConfig

Defines filtering criteria for paths.

```python
@dataclass
class PathFilterConfig:
    max_path_length: Optional[int] = None
    min_path_length: Optional[int] = None
    node_filter: Optional[str] = None
    relationship_filter: Optional[str] = None
    excluded_nodes: Optional[List[str]] = None
    excluded_relationships: Optional[List[str]] = None
```

### PathEnumerationConfig

Controls path enumeration behavior.

```python
@dataclass
class PathEnumerationConfig:
    max_paths: Optional[int] = None  # Result limit
    max_depth: int = 10               # Maximum search depth
    cycle_detection: bool = True      # Detect cycles
```

### PathNode

Represents a node in path configuration.

```python
@dataclass
class PathNode:
    variable: str                    # Node variable name
    labels: Optional[List[str]] = None  # Node labels
```

### PathRelationship

Represents a relationship in path configuration.

```python
@dataclass
class PathRelationship:
    variable: Optional[str] = None       # Relationship variable
    types: Optional[List[str]] = None    # Relationship types
    direction: str = "out"               # "out", "in", or "both"
```

## Usage Examples

### Example 1: Simple Shortest Path

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()
query = translator.translate_shortest_path("person", "destination", "TRAVELS_TO")
print(query)
# graph-shortest-paths (person)-[TRAVELS_TO]->(destination)
```

### Example 2: Weighted Shortest Path (Dijkstra-like)

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()
query = translator.translate_weighted_shortest_path(
    source="warehouse",
    target="store",
    relationship="SHIPPING_ROUTE",
    weight_property="cost",
    max_length=10
)
# graph-shortest-paths weight=cost (warehouse)-[SHIPPING_ROUTE]->(store) | where path_length <= 10
```

### Example 3: All Paths with Filters

```python
from yellowstone.algorithms import PathAlgorithmTranslator, PathFilterConfig

translator = PathAlgorithmTranslator()

# Find all paths but exclude certain nodes
filters = PathFilterConfig(
    max_path_length=5,
    min_path_length=2,
    excluded_nodes=["spam", "malicious"]
)

query = translator.translate_filtered_paths(
    source="A",
    target="Z",
    filters=filters,
    relationship="CONNECTS",
    max_length=8
)
```

### Example 4: Multiple Source/Target

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

# Find shortest path from one source to multiple destinations
query = translator.translate_shortest_path_multiple_targets(
    source="server",
    targets=["database1", "database2", "cache1"],
    relationship="CONNECTS_TO"
)
```

### Example 5: Bidirectional Search

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

# Search from both ends simultaneously
query = translator.translate_bidirectional_shortest_path(
    source="personA",
    target="personB",
    relationship="KNOWS",
    max_length=6
)
```

### Example 6: Path Validation

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

# Validate Cypher expression format
try:
    translator.validate_cypher_shortest_path_syntax(
        "shortestPath((n)-[r*1..5]-(m))"
    )
    print("Valid Cypher syntax")
except ValueError as e:
    print(f"Invalid: {e}")
```

## KQL Integration

The module translates Cypher operations to KQL operators:

| Cypher Function | KQL Operator | Use Case |
|---|---|---|
| `shortestPath()` | `graph-shortest-paths` | Minimum hop count |
| `shortestPath()` with weight | `graph-shortest-paths weight=` | Minimum cost |
| `allShortestPaths()` | `all_shortest_paths` | All minimum paths |
| `allPaths()` | `all_paths` | Complete enumeration |
| Variable-length paths | `[*min..max]` | Bounded traversal |

## Error Handling

All translators include comprehensive error handling:

```python
from yellowstone.algorithms import ShortestPathTranslator, PathConstraint

translator = ShortestPathTranslator()

# Empty source raises error
try:
    translator.translate_shortest_path("", "target")
except ValueError as e:
    print(f"Error: {e}")  # "Source must be non-empty string"

# Invalid constraints raise error
try:
    constraint = PathConstraint(max_length=-1)
    constraint.validate()
except ValueError as e:
    print(f"Error: {e}")  # "Maximum path length cannot be negative"

# Weighted search without weight property
try:
    constraint = PathConstraint(weighted=True)  # Missing weight_property
    constraint.validate()
except ValueError as e:
    print(f"Error: {e}")  # "Weight property required when weighted=True"
```

## Type Hints

All functions include comprehensive type hints for IDE support:

```python
def translate_shortest_path(
    self,
    source: str,
    target: str,
    relationship: Optional[str] = None,
    constraints: Optional[PathConstraint] = None,
    relationship_config: Optional[PathRelationship] = None,
) -> str:
    """..."""
```

## Test Coverage

The module includes 71 comprehensive tests covering:

- Basic shortest path translation
- Multiple source/target nodes
- Weighted path search
- Bidirectional search
- Path constraints and filters
- Node and property filtering
- Error conditions and validation
- Integration workflows

Run tests:

```bash
python -m pytest src/yellowstone/algorithms/tests/test_algorithms.py -v
```

## Performance Notes

- Shortest path queries leverage KQL's native optimized implementation
- Weighted search uses KQL's graph-shortest-paths with weight property
- Bidirectional search reduces search space from both directions
- Path enumeration should use constraints (max_length, cycle_detection) to avoid explosion
- Filter early using excluded_nodes and max_path_length

## Future Enhancements

- A* pathfinding with heuristics
- Community detection algorithms
- Centrality algorithms (betweenness, closeness)
- K-shortest paths
- Pattern matching on paths
- Path-based anomaly detection

## See Also

- `/home/azureuser/src/Yellowstone/src/yellowstone/translator/paths.py` - Variable-length path translator
- `/home/azureuser/src/Yellowstone/src/yellowstone/translator/graph_match.py` - Graph pattern matching
- `/home/azureuser/src/Yellowstone/src/yellowstone/models.py` - Core data models
