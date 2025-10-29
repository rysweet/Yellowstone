# Integration Patterns for Agentic AI Translation Layer

## Overview

This document describes how the Agentic AI Translation Layer integrates with the overall Cypher-Sentinel architecture, including routing decisions, fallback strategies, and coordination with other translation tiers.

## System Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  Cypher Query Interface (API, CLI, Web UI)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   QUERY ROUTER & CLASSIFIER                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Pattern Analyzer:                                         │ │
│  │  - Parse Cypher AST                                        │ │
│  │  - Extract complexity metrics                              │ │
│  │  - Classify into execution tier                            │ │
│  │  - Route to appropriate translator                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────┬───────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬─────────────────┐
        │            │            │                 │
        ▼            ▼            ▼                 ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐
│  FAST PATH   │ │  AI PATH   │ │ FALLBACK     │ │ REJECT PATH  │
│              │ │            │ │              │ │              │
│  85%         │ │  10%       │ │  5%          │ │ <1%          │
│              │ │            │ │              │ │              │
│  Direct      │ │  AGENTIC   │ │  Manual      │ │  Error +     │
│  Graph Ops   │ │  AI LAYER  │ │  Join-Based  │ │  Guidance    │
│  Translation │ │  (Claude)  │ │  Translation │ │              │
└──────┬───────┘ └─────┬──────┘ └──────┬───────┘ └──────┬───────┘
       │               │               │                │
       └───────────────┴───────────────┴────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXECUTION LAYER                                │
│  KQL Query Executor (Microsoft Sentinel)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Pattern Classification and Routing

### Classification Decision Tree

```python
class QueryClassifier:
    """
    Classifies Cypher queries into execution tiers.

    Classification factors:
    - Pattern complexity (hops, variable-length, algorithms)
    - Query features (aggregations, subqueries, unions)
    - Data characteristics (cardinality, density)
    - Performance requirements (latency, accuracy)
    """

    def classify(
        self,
        cypher: str,
        context: QueryContext
    ) -> ExecutionTier:
        """
        Main classification logic.

        Decision tree:
        1. Check for intractable patterns → REJECT
        2. Check for complex AI-suitable patterns → AI_PATH
        3. Check for direct graph operator mappings → FAST_PATH
        4. Default to fallback → FALLBACK
        """

        ast = self.parser.parse(cypher)
        metrics = self._compute_complexity_metrics(ast)

        # Check for intractable patterns
        if self._is_intractable(ast, metrics):
            return ExecutionTier.REJECT

        # Check for AI-suitable patterns
        if self._needs_ai_translation(ast, metrics, context):
            return ExecutionTier.AI_PATH

        # Check for direct translation
        if self._can_direct_translate(ast, metrics):
            return ExecutionTier.FAST_PATH

        # Fallback to join-based
        return ExecutionTier.FALLBACK

    def _needs_ai_translation(
        self,
        ast: CypherAST,
        metrics: ComplexityMetrics,
        context: QueryContext
    ) -> bool:
        """
        Determine if query needs AI translation.

        AI translation is beneficial when:
        1. Multiple relationship types in variable-length path
        2. Complex negation or existence patterns
        3. Semantic optimization opportunities
        4. Ambiguous query intent
        5. Pattern not in direct translation rules
        """

        # Multiple relationship types in single pattern
        if metrics.multi_relationship_patterns > 0:
            return True

        # Complex WHERE EXISTS or NOT EXISTS
        if metrics.complex_existence_checks > 0:
            return True

        # Variable-length with constraints on path properties
        if metrics.has_path_property_filters:
            return True

        # Semantic optimization beneficial (high cardinality)
        if context.estimated_cardinality > 100_000:
            # AI can choose better strategy
            return True

        # Pattern not in direct translation cache
        if not self.direct_translator.can_translate(ast):
            return True

        return False

    def _compute_complexity_metrics(
        self,
        ast: CypherAST
    ) -> ComplexityMetrics:
        """
        Extract complexity metrics from AST.
        """

        return ComplexityMetrics(
            hop_count=self._count_hops(ast),
            has_variable_length=self._has_variable_length_path(ast),
            max_variable_depth=self._extract_max_depth(ast),
            relationship_type_count=self._count_relationship_types(ast),
            multi_relationship_patterns=self._count_multi_rel_patterns(ast),
            has_shortest_path=self._has_shortest_path(ast),
            complex_existence_checks=self._count_complex_exists(ast),
            has_path_property_filters=self._has_path_filters(ast),
            aggregation_complexity=self._compute_aggregation_complexity(ast),
            subquery_count=self._count_subqueries(ast)
        )
```

### Routing Examples

#### Example 1: Direct Translation (Fast Path)

**Query**:
```cypher
MATCH (u:User)-[:OWNS]->(d:Device)
WHERE u.department = "IT" AND d.os = "Windows"
RETURN u.name, d.hostname
```

**Classification**:
- Hop count: 1
- No variable-length
- Single relationship type
- Simple WHERE clause
- **Tier**: FAST_PATH

**Routing**:
```python
# Direct translation to graph operators
kql = DirectTranslator().translate(cypher)
# Result: 2-3ms translation time
```

#### Example 2: AI Translation (AI Path)

**Query**:
```cypher
MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*1..4]->(r:Resource)
WHERE r.classification = "secret"
  AND NOT (u)-[:DIRECT_PERMISSION]->(r)
RETURN u.name, length(path) as indirection_depth
ORDER BY indirection_depth
```

**Classification**:
- Hop count: variable (1-4)
- Multiple relationship types (PERMISSION, GROUP_MEMBER)
- Complex negation (NOT EXISTS pattern)
- **Tier**: AI_PATH

**Routing**:
```python
# Route to agentic AI translator
kql = await AgenticTranslator().translate(cypher, context)
# Result: 200-500ms translation time, high quality
```

#### Example 3: Fallback Translation

**Query**:
```cypher
MATCH (u:User)-[:LOGGED_INTO]->(d:Device)-[:CONNECTED_TO]->(n:Network)
WHERE u.suspicious = true
RETURN u.name, d.hostname, n.name
```

**Classification**:
- Hop count: 2 (fixed)
- No variable-length
- Simple pattern but no graph operator optimization benefit
- **Tier**: FALLBACK

**Routing**:
```python
# Use join-based fallback
kql = JoinBasedTranslator().translate(cypher)
# Result: Verbose but reliable
```

## Integration with Fast Path (Direct Translation)

### Coordination Pattern

The AI layer can **enhance** fast path translations:

```python
class HybridTranslationStrategy:
    """
    Combines fast path with AI optimization.

    Strategy:
    1. Fast path generates baseline translation
    2. AI layer optimizes if beneficial
    3. Compare and select best
    """

    async def translate(
        self,
        cypher: str,
        context: TranslationContext
    ) -> TranslationResponse:
        """
        Hybrid translation with optimization.
        """

        # Get baseline from fast path
        baseline = self.direct_translator.translate(cypher)

        # Check if AI optimization is worthwhile
        if not self._should_optimize(baseline, context):
            return TranslationResponse(
                kql_query=baseline,
                strategy="direct",
                confidence=0.95
            )

        # Get AI-optimized version
        optimized = await self.ai_translator.optimize(
            kql=baseline,
            cypher=cypher,
            context=context
        )

        # Compare performance estimates
        if optimized.estimated_speedup > 1.5:
            return optimized
        else:
            return TranslationResponse(
                kql_query=baseline,
                strategy="direct",
                confidence=0.95
            )

    def _should_optimize(
        self,
        baseline: str,
        context: TranslationContext
    ) -> bool:
        """
        Determine if AI optimization is worth the latency.
        """

        # Only optimize for large result sets
        if context.estimated_cardinality < 10_000:
            return False

        # Only optimize for repeated queries
        if context.query_frequency < 5:
            return False

        # Only optimize if fast path used many joins
        if self._count_joins(baseline) < 4:
            return False

        return True
```

## Integration with Fallback (Join-Based Translation)

### Fallback Chain Pattern

```python
class TranslationPipeline:
    """
    Translation pipeline with fallback chain.

    Chain: AI → Pattern Cache → Join-Based → Error
    """

    async def translate(
        self,
        cypher: str,
        context: TranslationContext,
        options: TranslationOptions
    ) -> TranslationResponse:
        """
        Execute translation with fallback chain.
        """

        # Attempt 1: AI translation
        try:
            result = await self.ai_translator.translate(
                cypher, context, options
            )

            if result.confidence >= options.confidence_threshold:
                return result

            # Low confidence, try fallback
            logger.warning(
                f"AI translation low confidence: {result.confidence}"
            )

        except TranslationTimeout:
            logger.warning("AI translation timeout, falling back")

        except ClaudeAPIError as e:
            logger.error(f"Claude API error: {e}, falling back")

        # Attempt 2: Pattern cache lookup
        cached = await self.pattern_cache.find_similar(cypher, context)
        if cached and cached.confidence >= 0.8:
            logger.info("Using cached similar pattern")
            return cached

        # Attempt 3: Join-based translation
        try:
            result = self.join_translator.translate(cypher, context)
            logger.info("Using join-based fallback")
            return TranslationResponse(
                kql_query=result,
                strategy="join_based_fallback",
                confidence=0.75,
                warnings=["Using fallback strategy, may be suboptimal"]
            )

        except UntranslatableError as e:
            # Attempt 4: Return error with guidance
            logger.error(f"Translation failed: {e}")
            return TranslationFailure(
                error="untranslatable",
                reason=str(e),
                suggested_alternative=self._suggest_rewrite(cypher),
                fallback_translation=None
            )
```

## Context Sharing Between Layers

### Schema Context

Shared schema metadata across all translation layers:

```python
class SchemaContextProvider:
    """
    Centralized schema context for all translation layers.

    Provides:
    - Node/edge type mappings
    - Cardinality statistics
    - Index information
    - Performance hints
    """

    def __init__(self, sentinel_client: SentinelClient):
        self.sentinel = sentinel_client
        self.cache = SchemaCache(ttl=3600)  # 1 hour cache

    async def get_context(
        self,
        query_ast: CypherAST
    ) -> SchemaContext:
        """
        Get schema context relevant to query.
        """

        # Extract entity types from query
        entity_types = self._extract_entity_types(query_ast)

        # Fetch metadata (cached)
        metadata = await self._fetch_metadata(entity_types)

        # Fetch statistics
        statistics = await self._fetch_statistics(entity_types)

        return SchemaContext(
            schema_version=await self._get_schema_version(),
            entity_metadata=metadata,
            statistics=statistics,
            indexes=await self._get_index_info(entity_types)
        )

    async def _fetch_statistics(
        self,
        entity_types: List[str]
    ) -> Dict[str, EntityStatistics]:
        """
        Fetch cardinality and performance statistics.
        """

        cache_key = f"stats:{','.join(sorted(entity_types))}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Query Sentinel for statistics
        stats = {}
        for entity_type in entity_types:
            table_name = self._map_entity_to_table(entity_type)

            # Get row count
            row_count = await self.sentinel.execute_scalar(
                f"{table_name} | count"
            )

            # Get average fan-out for relationships
            avg_fanout = await self._compute_avg_fanout(table_name)

            stats[entity_type] = EntityStatistics(
                cardinality=row_count,
                average_degree=avg_fanout,
                density=self._compute_density(row_count, avg_fanout)
            )

        await self.cache.set(cache_key, stats, ttl=3600)
        return stats
```

### Query History Context

Share query execution history for optimization:

```python
class QueryHistoryProvider:
    """
    Provides query execution history for optimization.

    Used by AI layer to:
    - Learn from successful patterns
    - Estimate performance
    - Choose strategies
    """

    async def get_similar_queries(
        self,
        cypher: str,
        limit: int = 10
    ) -> List[HistoricalQuery]:
        """
        Find similar queries from history.
        """

        # Compute query fingerprint
        fingerprint = self._compute_fingerprint(cypher)

        # Find similar fingerprints
        similar = await self.db.query(
            """
            SELECT cypher, kql, execution_time_ms, result_count
            FROM query_history
            WHERE fingerprint = $1
               OR similarity(fingerprint, $1) > 0.8
            ORDER BY timestamp DESC
            LIMIT $2
            """,
            fingerprint, limit
        )

        return [
            HistoricalQuery(
                cypher=row['cypher'],
                kql=row['kql'],
                execution_time_ms=row['execution_time_ms'],
                result_count=row['result_count']
            )
            for row in similar
        ]
```

## Parallel Execution Pattern

For independent query components, execute translations in parallel:

```python
class ParallelTranslationCoordinator:
    """
    Coordinates parallel translation of independent query components.

    Use case: Query with UNION or multiple independent MATCH clauses
    """

    async def translate_parallel(
        self,
        query_components: List[CypherAST],
        context: TranslationContext
    ) -> List[TranslationResponse]:
        """
        Translate multiple independent components in parallel.
        """

        # Create translation tasks
        tasks = [
            self.translator.translate(component, context)
            for component in query_components
        ]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle failures
        translations = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Component {i} translation failed: {result}"
                )
                # Use fallback for failed component
                fallback = await self.fallback_translator.translate(
                    query_components[i], context
                )
                translations.append(fallback)
            else:
                translations.append(result)

        return translations

    async def combine_translations(
        self,
        translations: List[TranslationResponse],
        combinator: str  # "union", "join", etc.
    ) -> str:
        """
        Combine parallel translations into single KQL query.
        """

        if combinator == "union":
            # Combine with KQL union
            kql_queries = [t.kql_query for t in translations]
            return "\n| union\n".join(kql_queries)

        elif combinator == "join":
            # Combine with KQL join
            # (More complex logic)
            return self._combine_with_join(translations)

        else:
            raise ValueError(f"Unknown combinator: {combinator}")
```

## Error Handling and Recovery

### Circuit Breaker Pattern

Protect against cascading failures:

```python
class CircuitBreaker:
    """
    Circuit breaker for AI translation layer.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, skip AI translation
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.last_failure_time = None

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Call function with circuit breaker protection.
        """

        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if (
                self.last_failure_time and
                time.time() - self.last_failure_time > self.timeout
            ):
                # Try half-open
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                # Still open, fail fast
                raise CircuitOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)

            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    # Recovered, close circuit
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

            return result

        except Exception as e:
            # Failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                # Open circuit
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

            raise e
```

### Graceful Degradation

Degrade service quality instead of failing:

```python
class GracefulDegradationStrategy:
    """
    Gracefully degrade AI translation service.

    Degradation levels:
    1. Normal: Full AI translation with refinement
    2. Fast: Single-shot AI translation (no refinement)
    3. Cache-only: Only use pattern cache
    4. Fallback: Use join-based translator
    """

    def __init__(self):
        self.current_level = DegradationLevel.NORMAL

    async def translate_with_degradation(
        self,
        cypher: str,
        context: TranslationContext
    ) -> TranslationResponse:
        """
        Translate with current degradation level.
        """

        if self.current_level == DegradationLevel.NORMAL:
            # Full AI translation
            return await self.ai_translator.translate(
                cypher, context,
                options=TranslationOptions(max_iterations=3)
            )

        elif self.current_level == DegradationLevel.FAST:
            # Single-shot AI (no refinement)
            return await self.ai_translator.translate(
                cypher, context,
                options=TranslationOptions(max_iterations=1)
            )

        elif self.current_level == DegradationLevel.CACHE_ONLY:
            # Cache lookup only
            cached = await self.cache.find_similar(cypher, context)
            if cached:
                return cached
            else:
                # Fall back to join-based
                return await self.fallback_translator.translate(
                    cypher, context
                )

        else:  # FALLBACK
            # Direct to join-based translator
            return await self.fallback_translator.translate(
                cypher, context
            )

    def adjust_degradation_level(
        self,
        metrics: SystemMetrics
    ):
        """
        Adjust degradation level based on system health.
        """

        # Check Claude API health
        if metrics.claude_error_rate > 0.1:  # >10% errors
            self.current_level = max(
                self.current_level,
                DegradationLevel.CACHE_ONLY
            )

        # Check latency
        elif metrics.ai_translation_p95_latency > 5000:  # >5s
            self.current_level = max(
                self.current_level,
                DegradationLevel.FAST
            )

        # Check load
        elif metrics.concurrent_translations > 80:  # >80% capacity
            self.current_level = max(
                self.current_level,
                DegradationLevel.FAST
            )

        # Recover if healthy
        elif (
            metrics.claude_error_rate < 0.01 and
            metrics.ai_translation_p95_latency < 2000 and
            metrics.concurrent_translations < 50
        ):
            self.current_level = DegradationLevel.NORMAL
```

## Request/Response Flow Examples

### Example 1: Successful AI Translation

```
Client Request:
POST /translate/agentic
{
  "cypher": "MATCH path = (u:User)-[:PERMISSION*1..3]->(r:Resource) ...",
  "context": {
    "schema_version": "1.2.0",
    "performance_profile": "interactive"
  },
  "options": {
    "optimization_goal": "latency",
    "confidence_threshold": 0.85
  }
}

↓

Query Router:
- Parses Cypher AST
- Classifies as AI_PATH (multiple relationship types)
- Routes to AgenticTranslationService

↓

AgenticTranslationService:
1. Cache lookup: MISS
2. Build agent context: 50ms
3. Claude Agent SDK translation: 1200ms
   - Agent reasoning: 600ms
   - Tool calls (validation): 400ms
   - Refinement iteration: 200ms
4. Semantic validation: 200ms
5. Cache update: 20ms

↓

Response:
{
  "translation_id": "tr_abc123",
  "status": "success",
  "kql_query": "let G = ... | graph-match ...",
  "confidence": 0.92,
  "strategy": "graph_operators",
  "estimated_performance": {
    "execution_time_ms": 1500,
    "result_cardinality": 250
  },
  "validation": {
    "syntax_valid": true,
    "semantically_equivalent": true,
    "safety_checks_passed": true
  },
  "explanation": "Translated using graph operators...",
  "metadata": {
    "agent_iterations": 2,
    "translation_time_ms": 1470
  }
}

Total time: 1470ms
```

### Example 2: Low Confidence with Fallback

```
Client Request:
POST /translate/agentic
{
  "cypher": "MATCH (a)-[:REL*]->(b) WHERE ... RETURN ..."
}

↓

AgenticTranslationService:
1. Cache lookup: MISS
2. Claude Agent translation: 800ms
3. Result confidence: 0.65 (below threshold of 0.85)
4. Trigger fallback chain

↓

Fallback Chain:
1. Pattern cache lookup: MISS
2. Join-based translator: 150ms
3. Success with lower confidence

↓

Response:
{
  "translation_id": "tr_xyz789",
  "status": "success",
  "kql_query": "/* Join-based translation */...",
  "confidence": 0.75,
  "strategy": "join_based_fallback",
  "warnings": [
    "AI translation had low confidence (0.65)",
    "Using join-based fallback, may be suboptimal"
  ],
  "metadata": {
    "fallback_reason": "low_confidence",
    "translation_time_ms": 950
  }
}

Total time: 950ms
```

### Example 3: Circuit Breaker Open

```
Client Request:
POST /translate/agentic
{
  "cypher": "MATCH (u:User)...",
}

↓

Circuit Breaker Check:
- State: OPEN (Claude API experiencing issues)
- Skip AI translation
- Direct to fallback

↓

Fallback Translator:
- Join-based translation: 100ms

↓

Response:
{
  "translation_id": "tr_fallback456",
  "status": "success",
  "kql_query": "/* Join-based translation */...",
  "confidence": 0.70,
  "strategy": "fallback_circuit_open",
  "warnings": [
    "AI translation temporarily unavailable",
    "Using fallback translator"
  ],
  "metadata": {
    "circuit_breaker_state": "open",
    "translation_time_ms": 100
  }
}

Total time: 100ms
```

## Coordination with Execution Layer

### Validation Query Execution

AI layer can execute validation queries:

```python
class ValidationQueryExecutor:
    """
    Executes validation queries against Sentinel.

    Used by AI layer to:
    - Validate KQL syntax
    - Test semantic equivalence with samples
    - Estimate performance
    """

    async def validate_syntax(
        self,
        kql: str
    ) -> bool:
        """
        Check if KQL is syntactically valid.
        """

        try:
            # Dry-run query with limit 0
            await self.sentinel.execute(
                f"({kql}) | take 0"
            )
            return True
        except SyntaxError:
            return False

    async def sample_execution(
        self,
        kql: str,
        sample_size: int = 10
    ) -> ExecutionResult:
        """
        Execute query with small sample for validation.
        """

        try:
            result = await self.sentinel.execute(
                f"({kql}) | take {sample_size}",
                timeout=5  # 5s timeout
            )

            return ExecutionResult(
                success=True,
                rows=result.rows,
                execution_time_ms=result.duration_ms
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e)
            )
```

## Summary

The Agentic AI Translation Layer integrates seamlessly into the Cypher-Sentinel architecture through:

1. **Intelligent Routing**: Classification-based routing to appropriate translator
2. **Fallback Chain**: Graceful degradation through multiple fallback strategies
3. **Context Sharing**: Centralized schema and query history context
4. **Parallel Execution**: Concurrent translation of independent components
5. **Error Handling**: Circuit breakers and graceful degradation
6. **Validation Integration**: Safe execution of validation queries

This integration ensures high reliability, optimal performance, and comprehensive Cypher coverage (95-98%) while maintaining acceptable latency (median 500ms for AI path).
