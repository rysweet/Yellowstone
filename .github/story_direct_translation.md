## Story: Implement Direct Translation Engine

**Epic**: #1 (Phase 1: Core Graph Operator Translation)
**Priority**: High
**Estimated Complexity**: High

### Description
Build the core translation engine that converts Cypher AST to KQL graph operators.

### Acceptance Criteria
- [ ] MATCH clause → `graph-match` translation working
- [ ] WHERE clause → `where` translation working
- [ ] RETURN clause → `project` translation working
- [ ] Single-hop patterns translate correctly
- [ ] Multi-hop fixed patterns translate correctly
- [ ] Property filters in patterns working
- [ ] 100+ Cypher queries translate to valid KQL

### Technical Approach
1. Implement MATCH translator for node patterns
2. Implement MATCH translator for relationship patterns
3. Implement WHERE clause translator (property comparisons, boolean operators)
4. Implement RETURN clause translator (projections, aliases)
5. Add ORDER BY, LIMIT, SKIP translators
6. Integrate with parser output

### Translation Examples

**Input Cypher**:
```cypher
MATCH (u:User)-[:LOGGED_IN]->(d:Device)
WHERE u.department = 'Finance'
RETURN u.name, d.hostname
```

**Output KQL**:
```kusto
SecurityData
| make-graph user -[login]-> device
  with Users on userId,
       Devices on deviceId,
       SignInLogs on (userId, deviceId) as (user, device)
| graph-match (u:user)-[login]->(d:device)
  where u.department == 'Finance'
  project u.name, d.hostname
```

### Dependencies
- Cypher parser complete
- Schema mapping defined

### Testing
- Unit tests for each translator component
- Integration tests with KQL execution
- openCypher TCK test suite (200+ tests)

### Documentation
- Translation rules documentation
- API documentation
- Example queries
