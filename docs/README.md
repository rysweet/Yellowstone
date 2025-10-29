# Yellowstone Documentation

Complete technical documentation for the Yellowstone Cypher query engine for Microsoft Sentinel Graph.

## Documentation Overview

### 1. **ARCHITECTURE.md** (642 lines)
Comprehensive technical architecture guide covering:
- System overview with ASCII diagrams
- Three-tier translation strategy (85% fast path, 10% AI, 5% fallback)
- Component descriptions:
  - Parser Module (Cypher → AST)
  - Translator Module (AST → KQL)
  - Schema Mapper (Label/relationship → Table/join)
  - CLI Module (Command-line interface)
- Detailed data flow diagrams
- KQL native graph operators (graph-match, make-graph, graph-shortest-paths)
- Query classification and routing logic
- Performance characteristics and benchmarks
- Error handling hierarchy
- Monitoring and observability guidance
- Extension points for customization

**Best for:** Understanding system design, architecture decisions, performance optimization

### 2. **TRANSLATION_GUIDE.md** (936 lines)
Complete translation reference for Cypher to KQL conversion:
- Quick reference table of all translations
- Clause-by-clause translation examples:
  - MATCH → graph-match (nodes, relationships, paths)
  - WHERE → where clause (operators, conditions, functions)
  - RETURN → project/sort/limit (projections, aggregations)
- Comprehensive operator mappings:
  - Comparison operators (=, !=, <, >, <=, >=)
  - Logical operators (AND, OR, NOT)
  - String functions (CONTAINS, STARTS_WITH, ENDS_WITH, IN)
  - Aggregation functions (COUNT, SUM, AVG, MIN, MAX, COLLECT)
- Variable-length path handling ([*], [*1..3], [*1..], [*..*5])
- Feature support matrix (100 rows × 4 columns)
- 7 common patterns from security domain:
  - User login investigation
  - Lateral movement detection
  - Process execution chains
  - Risk score aggregation
  - Threat hunting patterns
  - Network pivot analysis
- Limitations and workarounds for unsupported features
- 4 advanced examples with full working implementations
- Real-world threat hunting scenarios

**Best for:** Writing and debugging Cypher queries, learning translation rules, finding patterns

### 3. **SCHEMA_GUIDE.md** (1142 lines)
Complete schema mapping and configuration guide:
- Quick start for using schemas
- YAML schema format specification:
  - Version and metadata
  - Node mappings structure
  - Relationship mappings structure
  - Table metadata definitions
- Node mapping documentation:
  - Basic node mappings
  - 6 supported property types (string, int, datetime, bool, float, array, object)
  - Multiple properties per node
  - Optional vs. required properties
  - Complex property mappings
- Relationship mapping documentation:
  - Basic relationship setup
  - 3 join condition patterns (simple equality, multi-column, time-windowed)
  - Relationship strength levels (high, medium, low)
  - Edge properties and metadata
  - Bidirectional relationships
- Complete property mapping reference
- Comprehensive validation rules:
  - Node mapping validity checks
  - Relationship endpoint validation
  - Join condition syntax verification
  - Circular dependency detection
  - Property consistency checking
  - Custom validation example code
- Three methods for adding custom mappings:
  - YAML extension approach
  - Programmatic schema creation
  - Dynamic runtime injection
- 2 complete real-world schema examples:
  - Basic user-device-login schema
  - Advanced threat investigation schema (30+ entity types)
- 8 best practices for schema design and maintenance
- Integration with CLI tools and validation

**Best for:** Designing schemas, mapping custom entities, configuring Sentinel integration

## Quick Links

### For Different Roles

**Security Analyst / Threat Hunter:**
1. Start: [TRANSLATION_GUIDE.md](./TRANSLATION_GUIDE.md#common-patterns) - Common Patterns section
2. Learn: [TRANSLATION_GUIDE.md](./TRANSLATION_GUIDE.md) - Full guide for query reference
3. Reference: [SCHEMA_GUIDE.md](./SCHEMA_GUIDE.md#examples) - Available node types and relationships

**Data Engineer / Platform Developer:**
1. Start: [ARCHITECTURE.md](./ARCHITECTURE.md) - System overview
2. Learn: [SCHEMA_GUIDE.md](./SCHEMA_GUIDE.md#adding-custom-mappings) - Adding custom mappings
3. Reference: [ARCHITECTURE.md](./ARCHITECTURE.md#extension-points) - Extension points

**Security Architect / DevSecOps:**
1. Start: [ARCHITECTURE.md](./ARCHITECTURE.md#three-tier-translation-system) - Translation strategy
2. Learn: [ARCHITECTURE.md](./ARCHITECTURE.md#kql-native-graph-operators) - KQL operators
3. Implement: [SCHEMA_GUIDE.md](./SCHEMA_GUIDE.md#validation-rules) - Schema validation

### By Task

**Write a Cypher Query:**
1. [TRANSLATION_GUIDE.md#quick-reference](./TRANSLATION_GUIDE.md#quick-reference) - Quick reference
2. [TRANSLATION_GUIDE.md#common-patterns](./TRANSLATION_GUIDE.md#common-patterns) - Find similar pattern
3. [TRANSLATION_GUIDE.md#clause-by-clause-translation](./TRANSLATION_GUIDE.md#clause-by-clause-translation) - Learn translation rules

**Translate Cypher to KQL Manually:**
1. [TRANSLATION_GUIDE.md#operator-mappings](./TRANSLATION_GUIDE.md#operator-mappings) - Operator reference
2. [TRANSLATION_GUIDE.md#advanced-examples](./TRANSLATION_GUIDE.md#advanced-examples) - Real-world examples
3. [TRANSLATION_GUIDE.md#limitations--workarounds](./TRANSLATION_GUIDE.md#limitations--workarounds) - Known limitations

**Design a Custom Schema:**
1. [SCHEMA_GUIDE.md#quick-start](./SCHEMA_GUIDE.md#quick-start) - Quick start
2. [SCHEMA_GUIDE.md#schema-format](./SCHEMA_GUIDE.md#schema-format) - Format specification
3. [SCHEMA_GUIDE.md#examples](./SCHEMA_GUIDE.md#examples) - Real-world examples
4. [SCHEMA_GUIDE.md#best-practices](./SCHEMA_GUIDE.md#best-practices) - Best practices

**Understand System Design:**
1. [ARCHITECTURE.md#overview](./ARCHITECTURE.md#overview) - System overview
2. [ARCHITECTURE.md#system-architecture](./ARCHITECTURE.md#system-architecture) - Detailed architecture
3. [ARCHITECTURE.md#core-components](./ARCHITECTURE.md#core-components) - Component details

**Optimize Query Performance:**
1. [ARCHITECTURE.md#performance-characteristics](./ARCHITECTURE.md#performance-characteristics) - Benchmarks
2. [ARCHITECTURE.md#translation-strategy-selection](./ARCHITECTURE.md#translation-strategy-selection) - Strategy selection
3. [TRANSLATION_GUIDE.md#variable-length-paths](./TRANSLATION_GUIDE.md#variable-length-paths) - Path optimization

## Documentation Statistics

| Document | Lines | Sections | Examples | Tables |
|----------|-------|----------|----------|--------|
| ARCHITECTURE.md | 642 | 13 major | 45+ | 8 |
| TRANSLATION_GUIDE.md | 936 | 11 major | 60+ | 12 |
| SCHEMA_GUIDE.md | 1142 | 12 major | 2 complete | 15+ |
| **Total** | **2720** | **36** | **100+** | **35** |

## Document Highlights

### ARCHITECTURE.md Highlights

- **System Overview:** Complete ASCII diagram showing all three translation paths
- **Data Flow:** Detailed flow diagrams for translation and schema resolution
- **KQL Operators:** Comprehensive mapping table (Cypher ↔ KQL)
- **Performance:** Benchmarks showing 15-40x improvement with graph operators
- **Monitoring:** Metrics, audit trail, and observability guidance

### TRANSLATION_GUIDE.md Highlights

- **Quick Reference:** 20-row operator mapping table
- **70+ Detailed Examples:** Every clause type with Cypher/KQL side-by-side
- **Feature Matrix:** 100-row coverage matrix with support levels
- **Real Patterns:** 7 security domain patterns (login, lateral movement, pivots, etc.)
- **Advanced Examples:** 4 complete working examples with complex joins

### SCHEMA_GUIDE.md Highlights

- **YAML Specification:** Complete format with all field types
- **Validation:** 5 automated validation checks with examples
- **3 Integration Methods:** YAML files, programmatic API, runtime injection
- **2 Complete Schemas:** Production-ready examples with 30+ relationships
- **Best Practices:** 8 guidelines for scalable schema design

## Key Features Documented

### Translation System
- 85% fast path (sub-millisecond)
- 10% AI-enhanced path (using Claude Agent SDK)
- 5% fallback path (join-based)
- 95-98% query coverage
- Confidence scoring system

### Graph Operators
- `graph-match`: Pattern matching
- `make-graph`: Graph construction
- `graph-shortest-paths`: Path analysis
- Variable-length paths: 15-40x faster than joins

### Query Features
- Multi-hop paths (variable length)
- Complex WHERE conditions
- Aggregations and GROUP BY
- ORDER BY with sorting
- LIMIT and DISTINCT
- Optional matches

### Schema Support
- Node label mapping
- Relationship join conditions
- Property type conversion
- Relationship strength levels
- Join validation
- Schema versioning

## Usage Examples

### Example 1: Basic Query Translation

See [TRANSLATION_GUIDE.md - User Login Investigation](./TRANSLATION_GUIDE.md#user-login-investigation)

```cypher
MATCH (u:User)-[r:LOGGED_IN {success: true}]->(d:Device)
RETURN u.name, COUNT(DISTINCT d) as device_count
```

### Example 2: Schema Mapping

See [SCHEMA_GUIDE.md - Example 1](./SCHEMA_GUIDE.md#example-1-basic-user-device-schema)

```yaml
nodes:
  User:
    sentinel_table: IdentityInfo
    properties:
      user_id:
        sentinel_field: AccountObjectId
        type: string
        required: true
```

### Example 3: Complex Investigation

See [TRANSLATION_GUIDE.md - Advanced Examples](./TRANSLATION_GUIDE.md#advanced-examples)

```cypher
MATCH (u1:User)-[r*1..3]-(event:SecurityEvent)
WHERE event.severity = 'High'
RETURN u1.name, COUNT(event) as event_count
```

## Cross-References

All three documents are heavily cross-referenced:

- ARCHITECTURE.md references TRANSLATION_GUIDE.md for specific rules
- TRANSLATION_GUIDE.md references SCHEMA_GUIDE.md for entity types
- SCHEMA_GUIDE.md references TRANSLATION_GUIDE.md for query examples

## Related Documentation

- **[../README.md](../README.md)** - Project overview
- **[../CLI_REFERENCE.md](../CLI_REFERENCE.md)** - Command-line interface
- **[../CHECKPOINT.md](../CHECKPOINT.md)** - Project status and milestones

## Getting Help

### Finding Answers

1. **How do I write a Cypher query for...?**
   - See [TRANSLATION_GUIDE.md - Common Patterns](./TRANSLATION_GUIDE.md#common-patterns)

2. **What's the KQL translation for Cypher feature X?**
   - See [TRANSLATION_GUIDE.md - Operator Mappings](./TRANSLATION_GUIDE.md#operator-mappings)

3. **How do I add a custom entity type?**
   - See [SCHEMA_GUIDE.md - Adding Custom Mappings](./SCHEMA_GUIDE.md#adding-custom-mappings)

4. **How does the system choose between fast/AI/fallback paths?**
   - See [ARCHITECTURE.md - Translation Strategy Selection](./ARCHITECTURE.md#translation-strategy-selection)

5. **What's the performance improvement of graph operators?**
   - See [ARCHITECTURE.md - Performance Characteristics](./ARCHITECTURE.md#performance-characteristics)

### Troubleshooting

See [TRANSLATION_GUIDE.md - Limitations & Workarounds](./TRANSLATION_GUIDE.md#limitations--workarounds) for:
- Complex subqueries
- UNION operations
- Constraints
- User-defined functions
- Advanced aggregations

## Document Version

- **Last Updated:** 2025-10-29
- **Documentation Version:** 1.0.0
- **Aligned With:** Yellowstone v1.0.0

## Contributing

To update these documents:

1. Update the specific markdown file
2. Update statistics in this README
3. Ensure all cross-references are valid
4. Validate YAML/code examples work
5. Update "Last Updated" date
6. Test links between documents

---

**Built with comprehensive examples, real-world patterns, and production-grade documentation.**
