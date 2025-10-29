# Algorithms Module - Quick Start Guide

## Installation

The algorithms module is part of Yellowstone. It's automatically available when you import from `yellowstone.algorithms`.

```python
from yellowstone.algorithms import (
    ShortestPathTranslator,
    PathAlgorithmTranslator,
    PathConstraint,
)
```

## 5-Minute Quick Start

### 1. Basic Shortest Path

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

# Translate Cypher shortestPath to KQL
query = translator.translate_shortest_path(
    source="person",
    target="friend",
    relationship="KNOWS"
)

print(query)
# Output: graph-shortest-paths (person)-[KNOWS]->(friend)
```

### 2. Weighted Shortest Path (Like Dijkstra)

```python
# Find shortest distance, not shortest number of hops
query = translator.translate_weighted_shortest_path(
    source="warehouse",
    target="store",
    relationship="SHIPPING_ROUTE",
    weight_property="distance"
)

print(query)
# Output: graph-shortest-paths weight=distance (warehouse)-[SHIPPING_ROUTE]->(store)
```

### 3. All Shortest Paths

```python
from yellowstone.algorithms import PathAlgorithmTranslator

algo_translator = PathAlgorithmTranslator()

# Find ALL paths with minimum hops
query = algo_translator.translate_all_shortest_paths(
    source="A",
    target="B",
    relationship="CONNECTS"
)

print(query)
# Output: all_shortest_paths ((A)-[CONNECTS]->(B))
```

### 4. Bidirectional Search

```python
# Search from both ends simultaneously
query = translator.translate_bidirectional_shortest_path(
    source="personA",
    target="personB",
    relationship="KNOWS",
    max_length=6
)

print(query)
# Output: graph-shortest-paths(bidirectional) (personA)-[KNOWS]->(personB) | where path_length <= 6
```

### 5. Path Enumeration with Filters

```python
from yellowstone.algorithms import PathFilterConfig

# Enumerate all paths with constraints
filters = PathFilterConfig(
    max_path_length=5,
    min_path_length=2,
    excluded_nodes=["blocked_node"]
)

query = algo_translator.translate_filtered_paths(
    source="start",
    target="end",
    filters=filters,
    relationship="LINKS",
    max_length=10
)

print(query)
# Output: all_paths ((start)-[LINKS*1..10]->(end)) | where array_length(path) <= 5 ...
```

## Common Use Cases

### Use Case 1: Find Shortest Route
```python
translator = ShortestPathTranslator()
query = translator.translate_shortest_path("warehouse", "customer", "DELIVERY_ROUTE")
```

### Use Case 2: Find Minimum Cost Path
```python
query = translator.translate_weighted_shortest_path(
    "startPoint", "endPoint", "ROUTE", weight_property="cost"
)
```

### Use Case 3: Find All Connected Paths
```python
algo_translator = PathAlgorithmTranslator()
query = algo_translator.translate_all_paths(
    "node1", "node2", "CONNECTS", max_length=5
)
```

### Use Case 4: Exclude Problem Nodes
```python
filters = PathFilterConfig(excluded_nodes=["problematic_node", "dangerous_node"])
query = algo_translator.translate_filtered_paths(
    "source", "destination", filters, "ROUTE"
)
```

### Use Case 5: Multiple Destinations
```python
query = translator.translate_shortest_path_multiple_targets(
    "server", ["db1", "db2", "cache"], "CONNECTS_TO"
)
```

## Configuration Classes Quick Reference

### PathConstraint - Search constraints
```python
from yellowstone.algorithms import PathConstraint

constraint = PathConstraint(
    max_length=10,              # Maximum hops
    weighted=True,              # Use weights?
    weight_property="cost",     # Weight field name
    bidirectional=True          # Search from both ends?
)
```

### PathFilterConfig - Path filtering
```python
from yellowstone.algorithms import PathFilterConfig

filters = PathFilterConfig(
    max_path_length=5,          # Max nodes in path
    min_path_length=2,          # Min nodes in path
    excluded_nodes=["x", "y"],  # Skip these nodes
    excluded_relationships=[],  # Skip these relationships
    node_filter="n.status='active'",  # Custom filter
)
```

### PathEnumerationConfig - Enumeration control
```python
from yellowstone.algorithms import PathEnumerationConfig

enum_config = PathEnumerationConfig(
    max_paths=100,              # Return limit
    max_depth=10,               # Search depth
    cycle_detection=True        # Detect cycles?
)
```

## Error Handling

All translators validate inputs and provide clear error messages:

```python
from yellowstone.algorithms import ShortestPathTranslator

translator = ShortestPathTranslator()

try:
    # This will raise ValueError
    translator.translate_shortest_path("", "target")
except ValueError as e:
    print(f"Error: {e}")  # "Source must be non-empty string"

try:
    # Weighted without weight property
    constraint = PathConstraint(weighted=True)  # Missing weight_property
    constraint.validate()
except ValueError as e:
    print(f"Error: {e}")  # "Weight property required when weighted=True"
```

## Next Steps

1. **Read Full Documentation**: See `README.md` in this directory
2. **Check Examples**: Look at test file for complete examples
3. **Explore Methods**: Use IDE autocomplete to discover all methods
4. **Integrate**: Add translators to your Cypher→KQL pipeline

## Tips & Tricks

### Tip 1: Chain Constraints
```python
constraint = PathConstraint(
    max_length=5,
    weighted=True,
    weight_property="distance",
    bidirectional=True
)
query = translator.translate_shortest_path("A", "B", "ROUTE", constraint)
```

### Tip 2: Validate Before Translating
```python
if translator.validate_cypher_shortest_path_syntax("shortestPath((n)-[*]-(m))"):
    # Now safe to translate
    query = translator.translate_shortest_path("n", "m")
```

### Tip 3: Combine Multiple Filters
```python
filters = PathFilterConfig(
    max_path_length=5,
    excluded_nodes=["node1", "node2"],
    node_filter="n.status='active'"
)
query = algo_translator.translate_filtered_paths("A", "B", filters)
```

### Tip 4: Extract Results
```python
result = {"path_length": 3, "nodes": [...]}
length = translator.extract_path_length_from_result(result)
print(f"Path has {length} hops")
```

## Common Patterns

### Pattern 1: Shortest Path Query
```python
translator = ShortestPathTranslator()
query = translator.translate_shortest_path("source", "target", "RELATIONSHIP")
```

### Pattern 2: Shortest Path with Max Distance
```python
constraint = PathConstraint(max_length=5)
query = translator.translate_shortest_path("A", "B", "ROUTE", constraint)
```

### Pattern 3: Weighted Shortest Path
```python
query = translator.translate_weighted_shortest_path(
    "A", "B", "ROUTE", "distance"
)
```

### Pattern 4: All Paths Enumeration
```python
algo_translator = PathAlgorithmTranslator()
query = algo_translator.translate_all_paths(
    "A", "B", "CONNECTS", max_length=5
)
```

### Pattern 5: Filtered Path Search
```python
filters = PathFilterConfig(
    max_path_length=5,
    excluded_nodes=["node_x"]
)
query = algo_translator.translate_filtered_paths("A", "B", filters)
```

## API Reference (Quick)

### ShortestPathTranslator

| Method | Purpose |
|--------|---------|
| `translate_shortest_path()` | Basic shortest path |
| `translate_weighted_shortest_path()` | Dijkstra-style search |
| `translate_bidirectional_shortest_path()` | Search from both ends |
| `translate_shortest_path_multiple_targets()` | Multiple destinations |
| `translate_shortest_path_multiple_sources()` | Multiple origins |
| `validate_cypher_shortest_path_syntax()` | Validate input |
| `extract_path_length_from_result()` | Parse result |

### PathAlgorithmTranslator

| Method | Purpose |
|--------|---------|
| `translate_all_shortest_paths()` | All minimum paths |
| `translate_all_paths()` | Path enumeration |
| `translate_filtered_paths()` | Filtered enumeration |
| `translate_path_with_node_constraints()` | Node filtering |
| `translate_path_with_property_constraints()` | Property filtering |
| `build_combined_path_query()` | Unified builder |

## Need Help?

1. Check the full `README.md` for detailed documentation
2. Look at test examples in `tests/test_algorithms.py`
3. Review inline docstrings with IDE help
4. Check error messages - they're detailed and helpful

## Performance Tips

- Use `max_length` constraints to limit search space
- Enable `bidirectional=True` for long paths
- Use `excluded_nodes` to skip known dead ends
- For weighted paths, ensure weight values are reasonable
- Enable `cycle_detection` for acyclic graphs to avoid revisits

---

**Ready to translate paths? Start with the simple examples above!**
