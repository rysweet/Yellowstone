# Cypher to KQL Translation Guide

This guide explains how Cypher queries are translated to KQL (Kusto Query Language) for Microsoft Sentinel Graph. It covers translation rules, operator mappings, and practical examples.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Clause-by-Clause Translation](#clause-by-clause-translation)
3. [Operator Mappings](#operator-mappings)
4. [Variable-Length Paths](#variable-length-paths)
5. [Feature Support Matrix](#feature-support-matrix)
6. [Common Patterns](#common-patterns)
7. [Limitations & Workarounds](#limitations--workarounds)
8. [Advanced Examples](#advanced-examples)

## Quick Reference

| Cypher | KQL | Notes |
|--------|-----|-------|
| `MATCH (n)` | `graph-match (n)` | Single node match |
| `MATCH (n)-[r]->(m)` | `graph-match (n)-[r]->(m)` | Node-relationship-node |
| `MATCH (n)-[r*1..3]-(m)` | `graph-match (n)-[r*1..3]-(m)` | Variable-length paths |
| `WHERE n.x = v` | `where n.x == v` | Equality check |
| `WHERE n.x AND m.y` | `where n.x and m.y` | Logical AND |
| `WHERE n.x OR m.y` | `where n.x or m.y` | Logical OR |
| `RETURN n, m` | `project n, m` | Projection |
| `RETURN COUNT(n)` | `project count()` | Aggregation |
| `ORDER BY n.x` | `sort by n.x asc` | Sorting |
| `LIMIT 10` | `limit 10` | Row limit |

## Clause-by-Clause Translation

### MATCH Clause → graph-match

The MATCH clause defines the graph pattern to search for.

#### Simple Node Matching

```cypher
-- Cypher
MATCH (n)
RETURN n

-- KQL
graph-match (n)
| project n
```

#### Node with Label

```cypher
-- Cypher
MATCH (n:User)
RETURN n

-- KQL
graph-match (n:User)
| project n
```

**Note:** Node labels in KQL represent node types. The schema mapper translates them to actual table names during execution.

#### Node with Properties

```cypher
-- Cypher
MATCH (n:User {name: 'Alice'})
RETURN n

-- KQL
graph-match (n:User {name: 'Alice'})
| project n

-- Or with WHERE clause (preferred)
graph-match (n:User)
| where n.name == 'Alice'
| project n
```

#### Multiple Labels (Alternative Patterns)

```cypher
-- Cypher: Multiple patterns (logical OR)
MATCH (n:Person|Employee)
RETURN n

-- KQL: Use union of patterns
graph-match (n:Person)
| union (graph-match (n:Employee))
| project n
```

#### Node-Relationship-Node Pattern

```cypher
-- Cypher
MATCH (u:User)-[r:LOGGED_IN]->(d:Device)
RETURN u, d

-- KQL
graph-match (u:User)-[r:LOGGED_IN]->(d:Device)
| project u, d
```

**Translation Rules:**
- `->` becomes `-` in KQL (direction implicit in pattern)
- `<-` becomes `-` (direction handled by node order)
- `-` becomes `--` (bidirectional)

#### Relationship Direction Mapping

```cypher
-- Outgoing (Cypher) → Outgoing (KQL)
MATCH (a)-[r]->(b)
KQL: graph-match (a)-[r]->(b)

-- Incoming (Cypher) → Incoming (KQL)
MATCH (a)<-[r]-(b)
KQL: graph-match (a)<-[r]-(b)

-- Bidirectional (Cypher) → Bidirectional (KQL)
MATCH (a)-[r]-(b)
KQL: graph-match (a)-[r]-(b)
```

#### Multi-Hop Paths

```cypher
-- Cypher: 3-hop path
MATCH (a:User)-[r1:LOGGED_IN]->(d:Device)
      -[r2:CONNECTED_TO]->(ip:IP)
      -[r3:ORIGINATES_FROM]->(loc:Location)
RETURN a, d, ip, loc

-- KQL: Same pattern
graph-match (a:User)-[r1:LOGGED_IN]->(d:Device)
           -[r2:CONNECTED_TO]->(ip:IP)
           -[r3:ORIGINATES_FROM]->(loc:Location)
| project a, d, ip, loc
```

#### Multiple Disconnected Patterns

```cypher
-- Cypher: Two separate patterns
MATCH (u:User)-[r1]->(d:Device),
      (p:Process)-[r2]->(f:File)
RETURN u, d, p, f

-- KQL: Comma-separated patterns
graph-match (u:User)-[r1]->(d:Device),
            (p:Process)-[r2]->(f:File)
| project u, d, p, f
```

#### OPTIONAL MATCH

```cypher
-- Cypher
MATCH (u:User)
OPTIONAL MATCH (u)-[r]->(d:Device)
RETURN u, d

-- KQL: Use optional directive
graph-match(optional) (u:User)-[r]->(d:Device)
| project u, d
```

### WHERE Clause → where

The WHERE clause filters graph patterns based on node/relationship properties.

#### Simple Equality

```cypher
-- Cypher: Single equals (=)
MATCH (n:User) WHERE n.name = 'Alice' RETURN n

-- KQL: Double equals (==)
graph-match (n:User)
| where n.name == 'Alice'
| project n

-- Reason: KQL uses == for comparison, = for assignment
```

#### Comparison Operators

```cypher
-- Cypher
MATCH (n:User) WHERE n.age > 30 RETURN n
KQL: graph-match (n:User) | where n.age > 30 | project n

-- Cypher
MATCH (n:User) WHERE n.age >= 30 RETURN n
KQL: graph-match (n:User) | where n.age >= 30 | project n

-- Cypher
MATCH (n:User) WHERE n.age < 30 RETURN n
KQL: graph-match (n:User) | where n.age < 30 | project n

-- Cypher
MATCH (n:User) WHERE n.age <= 30 RETURN n
KQL: graph-match (n:User) | where n.age <= 30 | project n

-- Cypher
MATCH (n:User) WHERE n.status <> 'active' RETURN n
KQL: graph-match (n:User) | where n.status != 'active' | project n
```

#### Logical Operators

```cypher
-- Cypher: AND becomes 'and' (lowercase)
MATCH (n:User) WHERE n.age > 30 AND n.status = 'active' RETURN n
KQL: graph-match (n:User)
     | where n.age > 30 and n.status == 'active'
     | project n

-- Cypher: OR becomes 'or' (lowercase)
MATCH (n:User) WHERE n.age > 30 OR n.status = 'admin' RETURN n
KQL: graph-match (n:User)
     | where n.age > 30 or n.status == 'admin'
     | project n

-- Cypher: NOT becomes 'not' (lowercase)
MATCH (n:User) WHERE NOT (n.status = 'inactive') RETURN n
KQL: graph-match (n:User)
     | where not (n.status == 'inactive')
     | project n
```

#### Complex Boolean Expressions

```cypher
-- Cypher: Multi-condition with parentheses
MATCH (n:User)
WHERE (n.age > 30 AND n.department = 'IT')
   OR (n.role = 'admin' AND n.active = true)
RETURN n

-- KQL: Direct translation preserving parentheses
graph-match (n:User)
| where (n.age > 30 and n.department == 'IT')
        or (n.role == 'admin' and n.active == true)
| project n
```

#### String Functions

```cypher
-- Cypher: CONTAINS
MATCH (n:User) WHERE n.email CONTAINS '@company.com' RETURN n
KQL: graph-match (n:User)
     | where n.email contains '@company.com'
     | project n

-- Cypher: STARTS_WITH
MATCH (n:User) WHERE n.username STARTS_WITH 'admin' RETURN n
KQL: graph-match (n:User)
     | where n.username startswith 'admin'
     | project n

-- Cypher: ENDS_WITH
MATCH (n:User) WHERE n.email ENDS_WITH '.gov' RETURN n
KQL: graph-match (n:User)
     | where n.email endswith '.gov'
     | project n
```

#### IN Operator

```cypher
-- Cypher
MATCH (n:User) WHERE n.status IN ['active', 'pending'] RETURN n

-- KQL
graph-match (n:User)
| where n.status in ('active', 'pending')
| project n

-- Note: Cypher uses [list], KQL uses (tuple)
```

#### NULL Checking

```cypher
-- Cypher: IS NULL
MATCH (n:User) WHERE n.phone IS NULL RETURN n
KQL: graph-match (n:User)
     | where n.phone == null or isempty(n.phone)
     | project n

-- Cypher: IS NOT NULL
MATCH (n:User) WHERE n.phone IS NOT NULL RETURN n
KQL: graph-match (n:User)
     | where n.phone != null and isnotempty(n.phone)
     | project n
```

#### Relationship Filtering

```cypher
-- Cypher: Filter on relationship properties
MATCH (u:User)-[r:LOGGED_IN {success: true}]->(d:Device) RETURN u, d

-- KQL
graph-match (u:User)-[r:LOGGED_IN {success: true}]->(d:Device)
| project u, d

-- Or using WHERE clause (preferred)
graph-match (u:User)-[r:LOGGED_IN]->(d:Device)
| where r.success == true
| project u, d
```

### RETURN Clause → project/limit/sort

The RETURN clause specifies what to output and how to sort/limit results.

#### Simple Projection

```cypher
-- Cypher
MATCH (n) RETURN n

-- KQL
graph-match (n)
| project n
```

#### Multiple Variables

```cypher
-- Cypher
MATCH (n)-[r]->(m) RETURN n, r, m

-- KQL
graph-match (n)-[r]->(m)
| project n, r, m
```

#### Property Selection

```cypher
-- Cypher
MATCH (n:User)-[r]->(m:Device) RETURN n.name, n.email, m.device_id

-- KQL
graph-match (n:User)-[r]->(m:Device)
| project n.name, n.email, m.device_id
```

#### Aliases

```cypher
-- Cypher
MATCH (n:User) RETURN n.name AS user_name, n.email AS user_email

-- KQL
graph-match (n:User)
| project user_name=n.name, user_email=n.email
```

#### DISTINCT

```cypher
-- Cypher
MATCH (n:User) RETURN DISTINCT n.department

-- KQL
graph-match (n:User)
| project n.department
| distinct
```

#### LIMIT

```cypher
-- Cypher
MATCH (n:User) RETURN n LIMIT 10

-- KQL
graph-match (n:User)
| project n
| limit 10
```

#### ORDER BY

```cypher
-- Cypher: Ascending (default)
MATCH (n:User) RETURN n ORDER BY n.name

-- KQL
graph-match (n:User)
| project n
| sort by n.name asc

-- Cypher: Descending
MATCH (n:User) RETURN n ORDER BY n.age DESC

-- KQL
graph-match (n:User)
| project n
| sort by n.age desc

-- Cypher: Multiple columns
MATCH (n:User) RETURN n ORDER BY n.department, n.name

-- KQL
graph-match (n:User)
| project n
| sort by n.department asc, n.name asc
```

#### Aggregation Functions

```cypher
-- Cypher: COUNT
MATCH (n:User) RETURN COUNT(n)
KQL: graph-match (n:User)
     | summarize count = count()

-- Cypher: COUNT with GROUP BY
MATCH (n:User) RETURN n.department, COUNT(n)
KQL: graph-match (n:User)
     | summarize count = count() by n.department

-- Cypher: SUM
MATCH (n:Device) RETURN SUM(n.memory_mb)
KQL: graph-match (n:Device)
     | summarize total_memory = sum(n.memory_mb)

-- Cypher: AVG
MATCH (n:Device) RETURN AVG(n.memory_mb)
KQL: graph-match (n:Device)
     | summarize avg_memory = avg(n.memory_mb)

-- Cypher: MIN
MATCH (n:Device) RETURN MIN(n.memory_mb)
KQL: graph-match (n:Device)
     | summarize min_memory = min(n.memory_mb)

-- Cypher: MAX
MATCH (n:Device) RETURN MAX(n.memory_mb)
KQL: graph-match (n:Device)
     | summarize max_memory = max(n.memory_mb)

-- Cypher: COLLECT
MATCH (u:User)-[r]->(d:Device) RETURN u.name, COLLECT(d.device_id)
KQL: graph-match (u:User)-[r]->(d:Device)
     | summarize devices = make_list(d.device_id) by u.name
```

## Operator Mappings

### Comparison Operators

| Cypher | KQL | Example |
|--------|-----|---------|
| `=` | `==` | `n.age = 30` → `n.age == 30` |
| `!=` | `!=` | `n.status != 'inactive'` → `n.status != 'inactive'` |
| `<>` | `!=` | `n.status <> 'inactive'` → `n.status != 'inactive'` |
| `<` | `<` | `n.age < 30` → `n.age < 30` |
| `>` | `>` | `n.age > 30` → `n.age > 30` |
| `<=` | `<=` | `n.age <= 30` → `n.age <= 30` |
| `>=` | `>=` | `n.age >= 30` → `n.age >= 30` |

### Logical Operators

| Cypher | KQL | Example |
|--------|-----|---------|
| `AND` | `and` | `n.x AND m.y` → `n.x and m.y` |
| `OR` | `or` | `n.x OR m.y` → `n.x or m.y` |
| `NOT` | `not` | `NOT n.active` → `not n.active` |

### String Functions

| Cypher | KQL | Example |
|--------|-----|---------|
| `CONTAINS` | `contains` | `n.email CONTAINS '@'` → `n.email contains '@'` |
| `STARTS_WITH` | `startswith` | `n.name STARTS_WITH 'A'` → `n.name startswith 'A'` |
| `ENDS_WITH` | `endswith` | `n.email ENDS_WITH '.com'` → `n.email endswith '.com'` |
| `IN` | `in` | `n.status IN [...]` → `n.status in (...)` |

### Aggregation Functions

| Cypher | KQL | Notes |
|--------|-----|-------|
| `COUNT(x)` | `count()` | Requires summarize |
| `SUM(x)` | `sum(x)` | Requires summarize |
| `AVG(x)` | `avg(x)` | Requires summarize |
| `MIN(x)` | `min(x)` | Requires summarize |
| `MAX(x)` | `max(x)` | Requires summarize |
| `COLLECT(x)` | `make_list(x)` | Requires summarize |

## Variable-Length Paths

Variable-length paths match any number of hops between two nodes.

### Basic Variable-Length Paths

```cypher
-- Cypher: Any number of hops (1 to infinity)
MATCH (a)-[r*]-(b) RETURN a, b
KQL: graph-match (a)-[r*]-{b)

-- Cypher: 1 to 3 hops
MATCH (a)-[r*1..3]-(b) RETURN a, b
KQL: graph-match (a)-[r*1..3]-(b)

-- Cypher: 1 or more hops
MATCH (a)-[r*1..]-(b) RETURN a, b
KQL: graph-match (a)-[r*1..]-{b)

-- Cypher: Up to 5 hops
MATCH (a)-[r*..5]-(b) RETURN a, b
KQL: graph-match (a)-[r*..5]-(b)

-- Cypher: Exactly 3 hops
MATCH (a)-[r*3]-(b) RETURN a, b
KQL: graph-match (a)-[r*3]-{b)
```

### Practical Examples

#### Finding Attack Paths (Variable Hops)

```cypher
-- Cypher: Find all paths from compromised user to admin
MATCH (compromised:User {compromise_level: 'high'})
      -[r:CONNECTED_VIA*1..5]->
      (admin:User {role: 'admin'})
RETURN compromised, admin

-- KQL
graph-match (compromised:User)-[r:CONNECTED_VIA*1..5]->(admin:User)
| where compromised.compromise_level == 'high' and admin.role == 'admin'
| project compromised, admin
```

#### Finding Lateral Movement Chains

```cypher
-- Cypher: User login chain within time window
MATCH (u1:User)-[r:LOGGED_INTO*1..4]->(u2:User)
WHERE r.timestamp > now() - duration('P7D')
RETURN u1, u2

-- KQL
graph-match (u1:User)-[r:LOGGED_INTO*1..4]->(u2:User)
| where r.timestamp > now(-7d)
| project u1, u2
```

### Path Length Constraints

```cypher
-- Cypher: Minimum hops constraint
MATCH (a)-[r*2..5]-(b)
RETURN a, b, length(r)

-- KQL: Direct translation
graph-match (a)-[r*2..5]-(b)
| project a, b, length = array_length(r)
```

## Feature Support Matrix

### Comprehensive Feature Coverage

| Feature | Support | Notes |
|---------|---------|-------|
| **MATCH Clause** | | |
| Single node | 100% | ✓ Full support |
| Node with labels | 100% | ✓ Full support |
| Node with properties | 100% | ✓ Full support via WHERE |
| Simple relationships | 100% | ✓ Full support |
| Multi-hop paths | 100% | ✓ Full support |
| Variable-length paths | 95% | ✓ Bounds required for AI optimization |
| Multiple patterns | 100% | ✓ Comma-separated patterns |
| OPTIONAL MATCH | 95% | ✓ Supported with limitations |
| **WHERE Clause** | | |
| Comparison operators | 100% | ✓ All operators mapped |
| Logical operators | 100% | ✓ AND, OR, NOT |
| String functions | 90% | ✓ CONTAINS, STARTS_WITH, ENDS_WITH |
| IN operator | 100% | ✓ Full support |
| Complex expressions | 95% | ✓ With parentheses |
| NULL checking | 95% | ✓ IS NULL, IS NOT NULL |
| Relationship filtering | 100% | ✓ Via properties |
| **RETURN Clause** | | |
| Simple projection | 100% | ✓ Full support |
| Property selection | 100% | ✓ Full support |
| Aliases | 100% | ✓ Full support |
| DISTINCT | 100% | ✓ Full support |
| ORDER BY | 100% | ✓ Multi-column, ASC/DESC |
| LIMIT | 100% | ✓ Full support |
| **Aggregations** | | |
| COUNT | 100% | ✓ Full support |
| SUM | 100% | ✓ Full support |
| AVG | 100% | ✓ Full support |
| MIN/MAX | 100% | ✓ Full support |
| GROUP BY | 100% | ✓ Full support via summarize |
| COLLECT | 95% | ✓ Translated to make_list |
| **Advanced** | | |
| Subqueries | 40% | ⚠ Limited support, AI recommended |
| UNION | 50% | ⚠ Limited support, workarounds available |
| Functions (user-defined) | 20% | ⚠ Not supported, use UDFs |
| Constraints | 30% | ⚠ Limited support |

### Support Key

- **100%**: Full support, direct translation
- **95-99%**: Supported with minor limitations
- **50-94%**: Supported with workarounds or AI enhancement
- **20-49%**: Limited support, manual intervention recommended
- **<20%**: Not supported

## Common Patterns

### User Login Investigation

```cypher
-- Cypher: Find users who logged into multiple devices
MATCH (u:User)-[r:LOGGED_IN {success: true}]->(d:Device)
RETURN u.name, COUNT(DISTINCT d) as device_count
ORDER BY device_count DESC
LIMIT 10

-- KQL
graph-match (u:User)-[r:LOGGED_IN]->(d:Device)
| where r.success == true
| project u.name, d.device_id
| summarize device_count = dcount(d.device_id) by u.name
| sort by device_count desc
| limit 10
```

### Lateral Movement Detection

```cypher
-- Cypher: Find unusual login chains
MATCH (u1:User)-[r1:LOGGED_INTO]->(d1:Device)
      -[r2:CONNECTED_TO]->(d2:Device)
      <-[r3:LOGGED_INTO]-(u2:User)
WHERE u1 != u2
RETURN u1.name, u2.name, COUNT(*) as interactions
ORDER BY interactions DESC

-- KQL
graph-match (u1:User)-[r1:LOGGED_INTO]->(d1:Device)
           -[r2:CONNECTED_TO]->(d2:Device)
           <-[r3:LOGGED_INTO]-(u2:User)
| where u1.user_id != u2.user_id
| project u1.name, u2.name
| summarize interactions = count() by u1.name, u2.name
| sort by interactions desc
```

### Threat Hunting: Process Execution Chain

```cypher
-- Cypher: Find suspicious process chains
MATCH (u:User)-[r1:EXECUTED]->(p1:Process)
      -[r2:SPAWNED]->(p2:Process)
      -[r3:ACCESSED]->(f:File)
WHERE p1.command_line CONTAINS 'powershell'
  AND f.file_path CONTAINS 'System32'
RETURN u.name, p1.name, p2.name, f.file_path

-- KQL
graph-match (u:User)-[r1:EXECUTED]->(p1:Process)
           -[r2:SPAWNED]->(p2:Process)
           -[r3:ACCESSED]->(f:File)
| where p1.command_line contains 'powershell'
        and f.file_path contains 'System32'
| project u.name, p1.name, p2.name, f.file_path
```

### Risk Score Aggregation

```cypher
-- Cypher: Calculate user risk based on related events
MATCH (u:User)-[r*1..2]-(event:SecurityEvent)
WHERE event.severity = 'High'
RETURN u.name, COUNT(event) as event_count,
       event.severity as severity
ORDER BY event_count DESC

-- KQL
graph-match (u:User)-[r*1..2]-(event:SecurityEvent)
| where event.severity == 'High'
| project u.name, event.event_id, event.severity
| summarize event_count = count() by u.name, severity
| sort by event_count desc
```

## Limitations & Workarounds

### Limitation 1: Complex Subqueries

**Issue:** Nested subqueries not directly supported

```cypher
-- Cypher (NOT SUPPORTED)
MATCH (u:User)
WHERE u.user_id IN [
  MATCH (d:Device) WHERE d.compromised = true RETURN d.owner_user_id
]
RETURN u
```

**Workaround:** Use AI path or split into multiple queries

```cypher
-- Split approach
-- Step 1: Find compromised devices
MATCH (d:Device) WHERE d.compromised = true RETURN d.owner_user_id

-- Step 2: Query users
MATCH (u:User) WHERE u.user_id IN [list_from_step1] RETURN u
```

### Limitation 2: UNION Operations

**Issue:** UNION requires manual pattern handling

```cypher
-- Cypher (LIMITED)
MATCH (u:User)-[:LOGGED_IN]->(d:Device)
UNION
MATCH (p:Process)-[:EXECUTED_ON]->(d:Device)
RETURN d.device_id
```

**Workaround:** Use multiple graph-match queries with union

```kusto
-- KQL workaround
(graph-match (u:User)-[:LOGGED_IN]->(d:Device)
 | project d.device_id)
| union (graph-match (p:Process)-[:EXECUTED_ON]->(d:Device)
         | project d.device_id)
| distinct
```

### Limitation 3: Constraints

**Issue:** Global constraints not supported in graph-match

```cypher
-- Cypher (NOT SUPPORTED)
MATCH (n) WHERE EXISTS { MATCH (n)-[:HAS]->(other) }
RETURN n
```

**Workaround:** Use aggregation to check existence

```kusto
-- KQL workaround
graph-match (n)-[:HAS]->(other)
| distinct n
```

### Limitation 4: Complex Path Filtering

**Issue:** Cannot directly filter on path length or intermediate nodes

```cypher
-- Cypher (PARTIAL SUPPORT)
MATCH path = (a)-[r*1..5]-(b)
WHERE length(path) > 3
RETURN path
```

**Workaround:** Use minimum path length specification

```kusto
-- KQL workaround
graph-match (a)-[r*4..5]-(b)
| project path=r
```

### Limitation 5: User-Defined Functions

**Issue:** Custom Cypher functions not supported

```cypher
-- Cypher (NOT SUPPORTED)
MATCH (n:User) RETURN n, custom_risk_score(n)
```

**Workaround:** Move computation to KQL UDF or post-process results

```kusto
-- KQL approach
graph-match (n:User)
| project n, risk_score = case(
    n.failed_logins > 5, 100,
    n.last_login > ago(30d), 50,
    0)
```

### Limitation 6: Complex Aggregations

**Issue:** Multi-level aggregations limited

```cypher
-- Cypher (PARTIAL)
MATCH (u:User)-[:ACCESSED]->(f:File)
RETURN u.name, COUNT(DISTINCT f.extension) as ext_count
```

**Workaround:** Use two-stage summarization

```kusto
-- KQL approach
graph-match (u:User)-[:ACCESSED]->(f:File)
| project u.name, f.extension
| distinct u.name, f.extension
| summarize ext_count = count() by u.name
```

## Advanced Examples

### Example 1: Compromise Chain Detection

```cypher
-- Goal: Find all users who could have compromised another user
CYPHER:
MATCH (u1:User {compromise_status: 'high'})
      -[r:SHARED_RESOURCE*1..3]->
      (u2:User)
WHERE r.shared_at > now() - duration('P30D')
RETURN u1.name, u2.name, length(r) as hops

KQL:
graph-match (u1:User)-[r:SHARED_RESOURCE*1..3]->(u2:User)
| where u1.compromise_status == 'high'
        and r.shared_at > now(-30d)
| project u1.name, u2.name, hops = array_length(r)
| order by hops asc
```

### Example 2: Multi-Criteria Risk Scoring

```cypher
-- Goal: Score users based on multiple threat indicators
CYPHER:
MATCH (u:User)-[r1:FAILED_LOGIN]->(auth)
      (u)-[r2:ACCESSED_SENSITIVE]->(file)
      (u)-[r3:EXECUTED]->(process)
RETURN u.name,
       COUNT(r1) as failed_login_count,
       COUNT(r2) as sensitive_file_access,
       COUNT(r3) as process_executions,
       COUNT(r1)*10 + COUNT(r2)*5 + COUNT(r3)*2 as risk_score
ORDER BY risk_score DESC
LIMIT 20

KQL:
graph-match (u:User)-[r1:FAILED_LOGIN]->(auth)
| project user_id = u.user_id, u.name
| summarize failed_logins = count() by user_id, u.name
| join kind=leftouter (
    graph-match (u:User)-[r2:ACCESSED_SENSITIVE]->(file)
    | project u.user_id, u.name
    | summarize sensitive_access = count() by u.user_id, u.name
  ) on user_id
| join kind=leftouter (
    graph-match (u:User)-[r3:EXECUTED]->(process)
    | project u.user_id, u.name
    | summarize process_execs = count() by u.user_id, u.name
  ) on user_id
| extend risk_score = (coalesce(failed_logins, 0) * 10
                       + coalesce(sensitive_access, 0) * 5
                       + coalesce(process_execs, 0) * 2)
| sort by risk_score desc
| limit 20
```

### Example 3: Temporal Attack Path Analysis

```cypher
-- Goal: Find attack paths that occurred within time window
CYPHER:
MATCH (attacker:User)-[r1:INITIAL_COMPROMISE]->(first_device:Device)
      -[r2:LATERAL_MOVE*1..5]->(target_device:Device)
WHERE r1.timestamp < r2.timestamp
  AND r2.timestamp < r1.timestamp + duration('PT1H')
RETURN attacker.name, first_device.name, target_device.name,
       COUNT(DISTINCT r2) as move_count

KQL:
graph-match (attacker:User)-[r1:INITIAL_COMPROMISE]->(first_device:Device)
| where r1.timestamp > now(-1d)
| project attacker_id = attacker.user_id, attacker.name, first_device_id = first_device.device_id,
          first_device.name, initial_time = r1.timestamp
| join kind=inner (
    graph-match (first_device:Device)-[r2:LATERAL_MOVE*1..5]->(target_device:Device)
    | project from_device_id = first_device.device_id, target_device_id = target_device.device_id,
              target_device.name, move_time = r2.timestamp
  ) on first_device_id == from_device_id
| where move_time > initial_time and move_time < initial_time + 1h
| distinct attacker_id, attacker_name, first_device_name, target_device_name
| summarize move_count = count() by attacker_name, first_device_name, target_device_name
```

### Example 4: Network Pivot Analysis

```cypher
-- Goal: Find potential network pivots from external to internal
CYPHER:
MATCH (ext:IP {is_external: true})
      -[r1:INITIATED_CONNECTION*1..3]->
      (int:IP {is_external: false})
WHERE r1.connection_time > now() - duration('P7D')
RETURN DISTINCT ext.ip_address, int.ip_address, COUNT(*) as connection_count

KQL:
graph-match (ext:IP)-[r1:INITIATED_CONNECTION*1..3]->(int:IP)
| where ext.is_external == true
        and int.is_external == false
        and r1.connection_time > now(-7d)
| project external_ip = ext.ip_address, internal_ip = int.ip_address
| summarize connection_count = count() by external_ip, internal_ip
| sort by connection_count desc
```

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and design
- [SCHEMA_GUIDE.md](./SCHEMA_GUIDE.md) - Schema mapping configuration
- [openCypher Specification](https://opencypher.org) - Official Cypher reference
- [KQL Documentation](https://learn.microsoft.com/en-us/kusto/query/) - Kusto Query Language reference
