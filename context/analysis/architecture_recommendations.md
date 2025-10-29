# Cypher-on-Sentinel: Architecture Recommendations & Decision Matrix

## Executive Summary

This document provides architectural recommendations for implementing a production-grade Cypher query engine on Microsoft Sentinel, with specific guidance on when to use Cypher vs native KQL, and architectural patterns to maximize performance.

---

## 1. Architectural Decision Matrix

### Use Cypher When:

| Scenario | Benefit | Performance Impact |
|----------|---------|-------------------|
| Interactive threat investigations | Intuitive graph patterns | Acceptable (2-5x) |
| Dashboard queries (cached) | Better readability | Minimal (cached) |
| 1-2 hop relationship queries | Declarative patterns | Low (2-3x) |
| Developer training cost matters | Standard query language | N/A |
| Query portability needed | Works across graph DBs | N/A |
| Schema-driven development | Type safety, validation | N/A |

### Use Native KQL When:

| Scenario | Benefit | Performance Impact |
|----------|---------|-------------------|
| Performance-critical queries | Direct optimization | Baseline (1x) |
| Deep traversals (3+ hops) | Custom optimization | Avoid 10-50x penalty |
| Variable-length paths *4+ | Impossible in Cypher | N/A |
| Complex aggregations | KQL operators optimized | Baseline (1x) |
| Time-series analytics | Native support | Baseline (1x) |
| Custom algorithms | Full control | Baseline (1x) |

### Hybrid Approach (RECOMMENDED):

```
┌────────────────────────────────────────────────────────┐
│  Use Case Layer                                        │
├────────────────────────────────────────────────────────┤
│  80%: Cypher for common patterns                       │
│  - Single/2-hop queries                                │
│  - Interactive investigations                          │
│  - Dashboard visualizations                            │
├────────────────────────────────────────────────────────┤
│  20%: Native KQL for specialized needs                 │
│  - Performance-critical paths                          │
│  - Complex analytics                                   │
│  - Custom algorithms                                   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Reference Architecture

### 2.1 Three-Tier Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Tier 1: API Gateway                       │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │ Authentication │  │Rate Limiting │  │Request Routing │   │
│  └────────────────┘  └──────────────┘  └────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  Cypher Engine  │ │  KQL Engine  │ │  Hybrid Engine  │
│   (Translation) │ │   (Direct)   │ │ (Smart Routing) │
└─────────────────┘ └──────────────┘ └─────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                  Tier 2: Query Processing                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Cypher Query Processor                     │  │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────────────┐   │  │
│  │  │  Parser  │→ │ Validator  │→ │   Translator     │   │  │
│  │  │ (ANTLR)  │  │ (Schema)   │  │ (Cypher→KQL)     │   │  │
│  │  └──────────┘  └────────────┘  └──────────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Query Optimizer                            │  │
│  │  - Complexity scoring                                   │  │
│  │  - Join order optimization                              │  │
│  │  - Time injection                                       │  │
│  │  - Cardinality estimation                               │  │
│  └────────────────────────────────────────────────────────┘  │
│                            │                                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Execution Planner                          │  │
│  │  - Query routing (Cypher vs KQL)                        │  │
│  │  - Result size estimation                               │  │
│  │  - Timeout prediction                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                 Tier 3: Data & Caching Layer                  │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │Translation Cache│ │ Result Cache │  │Metadata Store  │   │
│  │  (Query→KQL)   │  │(Sentinel ADX)│  │(Cardinality)   │   │
│  └────────────────┘  └──────────────┘  └────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         Microsoft Sentinel (ADX Backend)                │  │
│  │  - Time-based partitioning                              │  │
│  │  - Columnar storage                                     │  │
│  │  - Query execution engine                               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

### 2.2 Component Specifications

#### A. Cypher Parser
- **Technology**: ANTLR4 grammar for openCypher
- **Latency**: 1-2ms for typical queries
- **Features**:
  - Syntax validation
  - AST generation
  - Error reporting with line numbers

**Example Grammar Fragment**:
```antlr
grammar Cypher;

query
    : matchClause whereClause? returnClause
    ;

matchClause
    : MATCH pattern (COMMA pattern)*
    ;

pattern
    : node (relationship node)*
    ;

node
    : LPAREN variable? label? properties? RPAREN
    ;

relationship
    : DASH LBRACKET variable? type? variableLength? properties? RBRACKET ARROW
    ;

variableLength
    : STAR (NUMBER (DOTDOT NUMBER?)?)?
    ;
```

#### B. Schema Validator
- **Purpose**: Validate Cypher queries against Sentinel schema
- **Latency**: 0.5-1ms
- **Features**:
  - Label validation (User, System, File, etc.)
  - Relationship type validation (LOGIN, ACCESS, etc.)
  - Property validation (name, timestamp, etc.)

**Schema Definition Format**:
```yaml
labels:
  User:
    properties:
      - name: id, type: string, required: true
      - name: username, type: string, required: true
      - name: risk_score, type: int, required: false
      - name: department, type: string, required: false

  System:
    properties:
      - name: id, type: string, required: true
      - name: hostname, type: string, required: true
      - name: criticality, type: string, required: false

relationships:
  LOGIN:
    from: User
    to: System
    properties:
      - name: timestamp, type: datetime, required: true
      - name: success, type: bool, required: false

  ACCESS:
    from: User
    to: File
    properties:
      - name: timestamp, type: datetime, required: true
      - name: permission, type: string, required: false
```

#### C. Query Translator
- **Purpose**: Transform Cypher AST to optimized KQL
- **Latency**: 2-3ms
- **Architecture**: Template-based code generation

**Translation Rules**:
```python
class CypherToKQLTranslator:
    """Translates Cypher AST to KQL"""

    def __init__(self, schema, cardinality_stats):
        self.schema = schema
        self.cardinality = cardinality_stats

    def translate(self, ast: CypherAST) -> str:
        """Main translation entry point"""
        kql_parts = []

        # 1. Extract time constraints (critical for performance)
        time_filter = self._extract_or_inject_time_filter(ast)

        # 2. Translate MATCH patterns
        for pattern in ast.match_patterns:
            kql_parts.append(self._translate_pattern(pattern, time_filter))

        # 3. Translate WHERE clauses
        if ast.where_clause:
            kql_parts.append(self._translate_where(ast.where_clause))

        # 4. Translate RETURN clause
        kql_parts.append(self._translate_return(ast.return_clause))

        return '\n'.join(kql_parts)

    def _translate_pattern(self, pattern, time_filter):
        """Translate graph pattern to KQL joins"""
        if pattern.is_single_hop():
            return self._translate_single_hop(pattern, time_filter)
        elif pattern.is_multi_hop():
            return self._translate_multi_hop(pattern, time_filter)
        elif pattern.is_variable_length():
            return self._translate_variable_length(pattern, time_filter)

    def _translate_single_hop(self, pattern, time_filter):
        """
        MATCH (a:Label1)-[:REL]->(b:Label2)
        →
        SecurityEvent
        | where EventType == "REL"
        | where TimeGenerated >= ago(24h)
        """
        source_label = pattern.source.label
        target_label = pattern.target.label
        rel_type = pattern.relationship.type

        kql = f"""
        SecurityEvent
        | where EntityType == "{rel_type}"
        | where TimeGenerated >= {time_filter}
        | where SourceLabel == "{source_label}"
        | where TargetLabel == "{target_label}"
        """
        return textwrap.dedent(kql)

    def _translate_multi_hop(self, pattern, time_filter):
        """
        MATCH (a)-[:R1]->(b)-[:R2]->(c)
        →
        Multiple joins with optimal ordering
        """
        # Order joins by cardinality
        joins = self._optimize_join_order(pattern.hops)

        kql_parts = []
        for i, hop in enumerate(joins):
            if i == 0:
                kql_parts.append(self._first_join(hop, time_filter))
            else:
                kql_parts.append(self._subsequent_join(hop, time_filter))

        return '\n'.join(kql_parts)
```

#### D. Query Optimizer
- **Purpose**: Optimize generated KQL before execution
- **Latency**: 2-5ms
- **Techniques**:

**1. Complexity Scoring**:
```python
def calculate_complexity(ast: CypherAST) -> float:
    """Calculate query complexity score"""
    score = 0

    # Depth scoring
    max_depth = ast.max_pattern_depth()
    score += (max_depth ** 2) * 10

    # Variable-length scoring
    for pattern in ast.patterns:
        if pattern.is_variable_length():
            max_var = pattern.variable_length_max
            score += (max_var ** 3) * 100

    # Pattern count
    score += len(ast.patterns) * 5

    # Time window (larger = more expensive)
    time_window_hours = ast.get_time_window_hours()
    score += time_window_hours * 0.5

    # Filters (reduce complexity)
    score -= len(ast.where_filters) * 10

    return max(0, score)
```

**2. Join Order Optimization**:
```python
def optimize_join_order(patterns: List[Pattern]) -> List[Pattern]:
    """Order patterns by selectivity (smallest first)"""

    # Estimate cardinality for each pattern
    estimates = []
    for pattern in patterns:
        cardinality = estimate_pattern_cardinality(
            pattern.label,
            pattern.filters
        )
        estimates.append((pattern, cardinality))

    # Sort by cardinality (ascending)
    optimized = sorted(estimates, key=lambda x: x[1])

    return [pattern for pattern, _ in optimized]
```

**3. Time Constraint Injection**:
```python
def inject_time_constraint(ast: CypherAST, default_window='24h'):
    """Ensure all queries have time constraints"""

    if not ast.has_time_filter():
        # Inject default time window
        time_filter = TimeFilter(
            field='timestamp',
            operator='>=',
            value=f'ago({default_window})'
        )
        ast.where_clause.add_filter(time_filter)

    return ast
```

#### E. Execution Planner
- **Purpose**: Decide execution strategy and predict performance
- **Latency**: 1-2ms

**Decision Logic**:
```python
class ExecutionPlanner:
    """Decide how to execute query based on complexity"""

    def plan(self, ast: CypherAST, kql: str) -> ExecutionPlan:
        """Create execution plan"""

        complexity = calculate_complexity(ast)

        # Estimate execution time
        estimated_time = self._estimate_execution_time(complexity, ast)

        # Choose execution strategy
        if complexity < 50:
            strategy = "direct"  # Execute immediately
        elif complexity < 100:
            strategy = "monitored"  # Execute with timeout
        elif complexity < 200:
            strategy = "warned"  # Warn user, require confirmation
        else:
            strategy = "rejected"  # Too complex, reject

        return ExecutionPlan(
            kql=kql,
            complexity=complexity,
            estimated_time=estimated_time,
            strategy=strategy,
            warnings=self._generate_warnings(complexity, ast)
        )

    def _estimate_execution_time(self, complexity: float, ast: CypherAST) -> float:
        """Estimate query execution time in seconds"""

        # Base time (overhead)
        base_time = 0.1  # 100ms

        # Complexity factor
        complexity_time = (complexity / 100) * 2  # 2s per 100 points

        # Time window factor
        time_window_hours = ast.get_time_window_hours()
        window_factor = (time_window_hours / 24) * 0.5  # 0.5s per day

        # Join count factor
        num_joins = len(ast.patterns) - 1
        join_time = num_joins * 0.5  # 0.5s per join

        total = base_time + complexity_time + window_factor + join_time

        return total
```

---

## 3. Performance Optimization Strategies

### 3.1 Materialized View Strategy

**Purpose**: Pre-compute common graph projections for fast access

**Example 1: User-Group Membership**
```kql
.create materialized-view UserGroupMembership on table SecurityEvent
{
    SecurityEvent
    | where EventType == "GroupMembership"
    | where TimeGenerated >= ago(30d)
    | summarize Groups = make_set(GroupId), LastUpdated = max(TimeGenerated) by UserId
}
```

**Usage in Cypher**:
```cypher
// Original (slow)
MATCH (u:User)-[:MEMBER_OF]->(g:Group)
WHERE u.id = 'X'
RETURN g

// Translated to use materialized view (fast)
UserGroupMembership
| where UserId == 'X'
| mv-expand Groups to typeof(string)
```

**Performance Improvement**: 10-50x faster

**Example 2: Node Degree Statistics**
```kql
.create materialized-view NodeDegrees on table SecurityEvent
{
    let outbound = SecurityEvent
        | summarize OutDegree = dcount(TargetId) by NodeId = SourceId;

    let inbound = SecurityEvent
        | summarize InDegree = dcount(SourceId) by NodeId = TargetId;

    outbound
    | join kind=fullouter (inbound) on NodeId
    | project NodeId = coalesce(NodeId, NodeId1),
              InDegree = coalesce(InDegree, 0),
              OutDegree = coalesce(OutDegree, 0)
}
```

**Usage**: Query planner uses this for join ordering decisions

---

### 3.2 Incremental Query Execution

**Problem**: Large queries may timeout or OOM

**Solution**: Break into smaller chunks and combine results

```python
class IncrementalExecutor:
    """Execute large queries incrementally"""

    async def execute_incremental(self,
                                  kql: str,
                                  time_window_hours: int,
                                  chunk_size_hours: int = 6):
        """
        Break query into time-based chunks and execute incrementally

        Args:
            kql: KQL query to execute
            time_window_hours: Total time window
            chunk_size_hours: Size of each chunk
        """
        chunks = []
        current_offset = 0

        while current_offset < time_window_hours:
            # Create time-bounded chunk
            chunk_start = datetime.now() - timedelta(hours=current_offset + chunk_size_hours)
            chunk_end = datetime.now() - timedelta(hours=current_offset)

            # Execute chunk
            chunk_kql = self._add_time_bounds(kql, chunk_start, chunk_end)
            result = await self.execute(chunk_kql)

            chunks.append(result)
            current_offset += chunk_size_hours

        # Combine results
        return self._combine_results(chunks)

# Example usage
executor = IncrementalExecutor()
result = await executor.execute_incremental(
    kql="SecurityEvent | where EventType == 'Login'",
    time_window_hours=168,  # 7 days
    chunk_size_hours=6      # 6-hour chunks
)
```

**Performance**: Avoids timeouts, reduces memory pressure

---

### 3.3 Adaptive Query Execution

**Concept**: Adjust execution strategy based on intermediate results

```python
class AdaptiveExecutor:
    """Execute queries adaptively based on intermediate results"""

    async def execute_adaptive(self, ast: CypherAST):
        """Execute with adaptive strategy"""

        # Execute first hop
        first_hop_result = await self._execute_first_hop(ast)

        # Check intermediate result size
        intermediate_size = len(first_hop_result)

        if intermediate_size > 100000:
            # Too many intermediate results, warn user
            raise QueryComplexityError(
                f"First hop returned {intermediate_size} results. "
                "Add more filters or reduce time window."
            )
        elif intermediate_size > 10000:
            # Large but manageable, use materialization
            return await self._execute_with_materialization(ast, first_hop_result)
        else:
            # Small result set, proceed normally
            return await self._execute_remaining_hops(ast, first_hop_result)
```

---

### 3.4 Query Result Caching Strategy

**Cache Layers**:

**Layer 1: Translation Cache** (Redis/In-Memory)
- Key: Cypher query hash
- Value: KQL translation
- TTL: Indefinite (deterministic)
- Hit rate: 60-80%

**Layer 2: Execution Result Cache** (Sentinel Native)
- Key: KQL query + time parameters
- Value: Result set
- TTL: 5-15 minutes
- Hit rate: 30-50%

**Layer 3: Materialized View Cache** (ADX Tables)
- Key: Common patterns (user-group, etc.)
- Value: Pre-computed relationships
- TTL: 1-24 hours
- Hit rate: 20-40%

**Combined Cache Hit Rate**: ~70-85% (dramatic performance improvement)

---

## 4. Scalability Architecture

### 4.1 Horizontal Scaling

```
┌──────────────────────────────────────────────────────────┐
│                   Load Balancer                           │
│         (Azure Front Door / App Gateway)                  │
└──────────────────────────────────────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Instance 1 │ │   Instance 2 │ │   Instance N │
│              │ │              │ │              │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │  Parser  │ │ │ │  Parser  │ │ │ │  Parser  │ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │Translator│ │ │ │Translator│ │ │ │Translator│ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
└──────────────┘ └──────────────┘ └──────────────┘
          │             │             │
          └─────────────┼─────────────┘
                        ▼
          ┌──────────────────────────┐
          │   Shared Cache (Redis)   │
          │  - Translation cache     │
          │  - Cardinality stats     │
          └──────────────────────────┘
                        │
                        ▼
          ┌──────────────────────────┐
          │  Microsoft Sentinel ADX  │
          │  (Handles own scaling)   │
          └──────────────────────────┘
```

**Scaling Characteristics**:
- Translation layer: Stateless, scales linearly
- Cache layer: Redis cluster, 100K+ ops/sec
- Sentinel layer: Auto-scales based on ingestion rate

---

### 4.2 Query Routing Strategy

**Problem**: Not all queries need translation

**Solution**: Route based on query type

```python
class QueryRouter:
    """Route queries to optimal execution path"""

    def route(self, query: str) -> str:
        """Determine execution path"""

        # Detect query language
        if self._is_kql(query):
            return "kql_direct"  # Execute directly
        elif self._is_cypher(query):
            if self._is_simple_cypher(query):
                return "cypher_fast"  # Fast translation path
            else:
                return "cypher_full"  # Full optimization path
        else:
            raise ValueError("Unknown query language")

    def _is_simple_cypher(self, query: str) -> bool:
        """Check if Cypher query is simple enough for fast path"""
        ast = parse_cypher(query)

        # Simple = 1 pattern, no variable-length, < 3 filters
        return (
            len(ast.patterns) == 1
            and not ast.has_variable_length()
            and len(ast.where_filters) <= 3
        )
```

**Fast Path** (simple queries):
- Skip full optimization
- Use template-based translation
- Latency: 1-2ms (vs 5-10ms full path)

---

## 5. Monitoring and Observability

### 5.1 Key Metrics

**Translation Metrics**:
```python
# Prometheus-style metrics
translation_duration_seconds = Histogram(
    'cypher_translation_duration_seconds',
    'Time to translate Cypher to KQL',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)

translation_cache_hit_rate = Gauge(
    'cypher_translation_cache_hit_rate',
    'Translation cache hit rate'
)

query_complexity_score = Histogram(
    'cypher_query_complexity_score',
    'Query complexity distribution',
    buckets=[0, 50, 100, 150, 200, 300, 500]
)
```

**Execution Metrics**:
```python
execution_duration_seconds = Histogram(
    'cypher_execution_duration_seconds',
    'Time to execute translated query',
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60]
)

execution_timeout_rate = Counter(
    'cypher_execution_timeouts_total',
    'Number of queries that timed out'
)

result_size_bytes = Histogram(
    'cypher_result_size_bytes',
    'Size of query results',
    buckets=[1e3, 1e4, 1e5, 1e6, 1e7]
)
```

---

### 5.2 Alerting Rules

**Critical Alerts**:
```yaml
- alert: HighTranslationLatency
  expr: histogram_quantile(0.95, translation_duration_seconds) > 0.01
  for: 5m
  annotations:
    summary: "P95 translation latency > 10ms"

- alert: HighTimeoutRate
  expr: rate(execution_timeouts_total[5m]) > 0.05
  annotations:
    summary: "More than 5% of queries timing out"

- alert: LowCacheHitRate
  expr: translation_cache_hit_rate < 0.5
  for: 10m
  annotations:
    summary: "Cache hit rate below 50%"
```

---

## 6. Migration Strategy

### Phase 1: Limited Alpha (Complexity: LOW-MEDIUM)
- Deploy translation layer (read-only)
- Support simple patterns only (1-hop, basic filters)
- Internal testing with security team
- **Success Criteria**: 90% of simple queries translate correctly

### Phase 2: Expanded Beta (Complexity: MEDIUM)
- Add 2-hop pattern support
- Add aggregation support
- Limited external users (opt-in)
- Performance monitoring and tuning
- **Success Criteria**: P95 latency < 5s for 90% of queries

### Phase 3: General Availability (Complexity: LOW)
- Full feature set (3-hop, variable-length *1..3)
- Production-grade monitoring
- Documentation and training
- **Success Criteria**: 80% of queries perform acceptably

### Phase 4: Optimization (Ongoing)
- Materialized views for common patterns
- Advanced query optimization
- Cost-based query planning
- **Success Criteria**: Reduce P95 latency by 50%

---

## 7. Risk Mitigation

### Risk 1: Query Explosion (Variable-Length Paths)

**Mitigation**:
1. Hard limit: *1..3 (reject *4+)
2. Require time window < 24h for variable-length
3. Pre-execution cardinality checks
4. Adaptive execution (abort if intermediate results too large)

### Risk 2: Poor Performance User Experience

**Mitigation**:
1. Show estimated execution time before running
2. Provide query complexity score
3. Suggest optimizations (add filters, reduce time window)
4. Allow "explain" mode to see translated KQL

### Risk 3: Cache Invalidation

**Mitigation**:
1. Translation cache: Never invalidate (deterministic)
2. Result cache: TTL-based (5-15 min)
3. Materialized views: Scheduled refresh (hourly/daily)

### Risk 4: Schema Evolution

**Mitigation**:
1. Version schema definitions
2. Support multiple schema versions concurrently
3. Graceful degradation if label/property not found
4. Schema migration tools

---

## 8. Cost Analysis

### Translation Layer Cost (Per 1M Queries)

| Component | Cost | Notes |
|-----------|------|-------|
| Compute (translation) | $50-100 | 3-5ms @ $0.10/hour compute |
| Cache (Redis) | $100-200 | High hit rate reduces load |
| Storage (metadata) | $10 | Minimal storage needs |
| **Total** | **$160-310** | ~$0.0003 per query |

### Sentinel Execution Cost (Per 1M Queries)

| Component | Cost | Notes |
|-----------|------|-------|
| Data ingestion | $2,000-5,000 | Based on data volume |
| Query execution | $500-2,000 | Based on data scanned |
| Data retention | $1,000-3,000 | Based on retention period |
| **Total** | **$3,500-10,000** | ~$0.004-0.01 per query |

**Key Insight**: Translation cost is < 5% of total cost. Execution dominates.

---

## 9. Final Recommendations

### DO Implement:
1. Simple pattern matching (1-2 hops) - High value, low risk
2. Time-based query optimization - Critical for performance
3. Query complexity limits - Prevents catastrophic failures
4. Translation caching - Easy wins
5. Hybrid Cypher/KQL support - Flexibility for users

### DON'T Implement (Initially):
1. Variable-length paths *4+ - Too risky
2. Graph algorithms (shortest path, etc.) - Not feasible
3. Unbounded recursion - Impossible
4. Real-time streaming queries - Wrong tool
5. OLTP-style workloads - Wrong architecture

### MAYBE Implement (Later):
1. Limited variable-length *1..3 - With heavy constraints
2. Materialized view hints - Advanced optimization
3. Cost-based query planner - Long-term improvement
4. Query federation - If multi-source support needed

---

## 10. Success Metrics (6 Months Post-Launch)

### Performance Metrics
- P95 query latency < 5 seconds: **Target 80% of queries**
- Cache hit rate > 60%: **Target 70%**
- Timeout rate < 5%: **Target 3%**

### Adoption Metrics
- 50% of security analysts use Cypher regularly
- 1000+ queries per day
- 80% user satisfaction score

### Business Metrics
- 30% reduction in query development time
- 50% reduction in incorrect query bugs
- 20% improvement in investigation speed

### Technical Metrics
- 99.9% uptime
- < 0.1% error rate
- Horizontal scaling to 10K queries/minute

---

## Conclusion

Implementing Cypher on Sentinel is **technically feasible and strategically valuable** for 80% of security analytics workloads. The 2-5x performance tax for common queries is acceptable given the developer productivity gains.

**Key Success Factors**:
1. Focus on simple patterns initially
2. Implement strong performance guardrails
3. Provide escape hatch to native KQL
4. Invest in caching and optimization
5. Set clear performance expectations

**Expected Outcome**: A production-grade Cypher interface that significantly improves developer experience while maintaining acceptable performance for interactive security investigations.
