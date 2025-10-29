# Agentic AI Translation Layer API

**Version**: 1.0.0
**Status**: Design Complete
**Target Coverage**: 10% of complex Cypher queries (contributing to 95-98% total system coverage)

## Overview

The Agentic AI Translation Layer is a critical component of the Cypher-Sentinel system, providing intelligent, AI-powered translation for complex Cypher patterns that cannot be handled by rule-based translators. It leverages **Claude Agent SDK** for semantic understanding, goal-seeking optimization, and iterative refinement.

## Key Features

- **Semantic Understanding**: AI-powered analysis of complex query patterns
- **Goal-Seeking Translation**: Iterative refinement to optimize for latency/correctness/cost
- **Multi-Strategy Support**: Graph operators, join-based, and hybrid approaches
- **Validation Pipeline**: Syntax, semantic, and performance validation
- **Pattern Learning**: Continuous improvement through feedback and caching
- **Graceful Degradation**: Fallback chain for high reliability

## Architecture Position

```
┌────────────────────────────────────────────────────────────────┐
│                     CYPHER QUERY ROUTER                         │
│                   (Pattern Classification)                      │
└────────────────┬───────────────────────────┬───────────────────┘
                 │                           │
    ┌────────────┴────────────┐   ┌─────────┴──────────┐
    │  FAST PATH (85%)        │   │  AI PATH (10%)      │
    │  Direct Translation     │   │  AGENTIC AI LAYER   │ ◄── THIS
    │  Graph Operators        │   │  Claude Agent SDK   │
    └─────────────────────────┘   └─────────────────────┘
                 │                           │
                 └───────────┬───────────────┘
                             │
                    ┌────────┴────────┐
                    │  KQL EXECUTION  │
                    │  MS Sentinel    │
                    └─────────────────┘
```

## API Documentation

### Files in This Directory

- **`openapi.yaml`**: Complete OpenAPI 3.0 specification
- **`architecture.md`**: Detailed component architecture and design decisions
- **`integration_patterns.md`**: Integration with overall system and other layers
- **`example_usage.py`**: Comprehensive usage examples and patterns
- **`README.md`**: This file

## Quick Start

### 1. Basic Translation

```python
from agentic_translator_client import AgenticTranslatorClient

client = AgenticTranslatorClient(api_key="your_api_key")

# Complex Cypher with multiple relationship types and negation
cypher = """
MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*1..4]->(r:Resource)
WHERE r.classification = "secret"
  AND NOT (u)-[:DIRECT_PERMISSION]->(r)
RETURN u.name, length(path) as indirection_depth
ORDER BY indirection_depth
"""

context = {
    "schema_version": "1.2.0",
    "max_depth": 4,
    "performance_profile": "interactive"
}

result = await client.translate(cypher, context)

print(f"Confidence: {result['confidence']}")
print(f"KQL:\n{result['kql_query']}")
```

### 2. When to Use Agentic AI Layer

The query router automatically classifies queries into tiers. Use AI translation when:

- Multiple relationship types in variable-length paths
- Complex negation or existence patterns (NOT EXISTS, WHERE EXISTS)
- Semantic optimization opportunities (high cardinality data)
- Pattern not covered by direct translation rules
- Ambiguous query intent requiring reasoning

### 3. API Endpoints

| Endpoint | Purpose | Latency |
|----------|---------|---------|
| `POST /translate/agentic` | Primary translation | 200-500ms (simple) <br> 500-2000ms (complex) |
| `POST /translate/agentic/batch` | Batch translation | Variable |
| `GET /translate/agentic/{id}` | Async job status | <50ms |
| `POST /translate/validate` | Semantic validation | 100-300ms |
| `POST /translate/optimize` | Optimize existing KQL | 200-500ms |
| `POST /learning/feedback` | Submit feedback | <20ms |
| `GET /learning/patterns` | Get cached patterns | <100ms |

## Key Concepts

### Translation Context

Provides schema metadata, statistics, and constraints:

```python
context = {
    "schema_version": "1.2.0",
    "schema_metadata": {
        "User": {
            "type": "node",
            "table_name": "Users",
            "cardinality": 50000,
            "average_degree": 4.0
        }
    },
    "max_depth": 5,
    "performance_profile": "interactive"  # or "batch", "report"
}
```

### Translation Options

Control optimization goals and behavior:

```python
options = {
    "optimization_goal": "latency",  # or "throughput", "cost", "accuracy"
    "max_iterations": 3,
    "confidence_threshold": 0.85,
    "enable_caching": True,
    "async_mode": False,
    "include_alternatives": True,
    "validation_level": "semantic"  # or "syntax_only", "full"
}
```

### Confidence Scoring

Translation confidence (0.0-1.0):

- **0.9-1.0**: High confidence - production ready
- **0.8-0.9**: Good confidence - suitable for most uses
- **0.7-0.8**: Moderate confidence - review recommended
- **<0.7**: Low confidence - triggers fallback

### Translation Strategies

The AI chooses the optimal strategy:

1. **Graph Operators**: Uses `make-graph`, `graph-match`, `graph-shortest-paths`
   - Best for: Pattern matching, variable-length paths
   - Performance: 2-5x overhead

2. **Join-Based**: Explicit joins with loop unrolling
   - Best for: Fixed-depth patterns without graph operator support
   - Performance: 5-20x overhead

3. **Hybrid**: Combines graph operators with joins
   - Best for: Complex patterns with multiple relationship types
   - Performance: 3-10x overhead

## Performance Characteristics

### Latency Budget

| Operation | Target | P95 | P99 |
|-----------|--------|-----|-----|
| Cache hit | 10ms | 20ms | 50ms |
| Simple translation | 200ms | 500ms | 1s |
| Complex translation | 500ms | 2s | 5s |
| Full pipeline (cached) | 50ms | 100ms | 200ms |
| Full pipeline (uncached) | 500ms | 2s | 5s |

### Resource Usage

- **Concurrent translations**: 50-100 (Claude API rate limit)
- **Memory per translation**: 50-100MB (context + agent state)
- **Cache hit rate target**: >60% after warm-up

## Integration Patterns

### Pattern Classification

Queries are classified and routed automatically:

```python
def classify_query(cypher: str) -> ExecutionTier:
    """
    85% -> FAST_PATH (direct graph operators)
    10% -> AI_PATH (agentic translation)
    5%  -> FALLBACK (join-based)
    <1% -> REJECT (intractable)
    """
```

### Fallback Chain

Graceful degradation with multiple fallback levels:

```
AI Translation (primary)
    ↓ (low confidence or timeout)
Pattern Cache (similar patterns)
    ↓ (cache miss)
Join-Based Translation (rule-based)
    ↓ (untranslatable)
Error with Guidance
```

### Circuit Breaker

Protection against cascading failures:

- **CLOSED**: Normal operation
- **OPEN**: Too many failures, skip AI translation
- **HALF_OPEN**: Testing recovery

## Learning and Feedback

### Pattern Cache

Successful translations are cached and generalized:

```python
# Cache lookup (fuzzy matching)
cached = await client.get_pattern_cache(
    pattern_type="graph_operators",
    min_confidence=0.9
)
```

### Feedback Loop

Submit feedback to improve translations:

```python
await client.submit_feedback(
    translation_id="tr_abc123",
    rating=5,
    correctness=True,
    actual_execution_time_ms=1250,
    actual_result_count=45,
    comments="Excellent translation"
)
```

## Error Handling

### Common Error Scenarios

1. **Untranslatable Pattern**: Query cannot be translated
   - Response: `422 Unprocessable Entity`
   - Includes: Suggested alternative or manual approach

2. **Low Confidence**: AI confidence below threshold
   - Triggers: Automatic fallback to join-based translator
   - Warning: Included in response

3. **Timeout**: Translation takes too long
   - Use: Async mode for complex queries
   - Fallback: Join-based translator

4. **AI Hallucination**: Generated KQL is invalid or incorrect
   - Mitigation: Multi-level validation (syntax + semantic)
   - Threshold: Confidence must be ≥0.8

### Example Error Handling

```python
try:
    result = await client.translate(cypher, context)

    if result['confidence'] < 0.8:
        print("Warning: Low confidence translation")

    return result

except TranslationTimeout:
    # Use async mode
    job = await client.translate(cypher, context, {"async_mode": True})
    return await poll_until_complete(job)

except UntranslatableError as e:
    print(f"Cannot translate: {e.reason}")
    print(f"Suggested: {e.suggested_alternative}")
```

## Security Considerations

### Query Injection Prevention

- AST-based translation (no string concatenation)
- KQL syntax validation before execution
- Deny-list of dangerous operators

### Resource Exhaustion

- Query complexity limits (max depth, max joins)
- Timeout enforcement (60s hard limit)
- Rate limiting per user/tenant

### AI Hallucination Detection

- Multi-level validation (syntax + semantic + sample execution)
- Confidence threshold enforcement (reject <0.8)
- Human-in-the-loop for borderline cases (0.7-0.8)

## Monitoring and Observability

### Key Metrics

**Translation Quality**:
- Translation success rate (target: >90%)
- Average confidence score (target: >0.85)
- User feedback ratings (target: >4.0/5.0)

**Performance**:
- Translation latency (P50, P95, P99)
- Cache hit rate (target: >60%)
- AI iterations per query

**Business**:
- Queries per day
- Cost per translation (Claude API)
- Fallback rate (target: <20%)

### Distributed Tracing

Full pipeline tracing with OpenTelemetry:

```
translate_request (2380ms)
├─ cache_lookup (10ms)
├─ build_agent_context (50ms)
├─ claude_agent_translate (1500ms)
│  ├─ agent_reasoning (800ms)
│  ├─ tool_syntax_validate (200ms)
│  ├─ tool_performance_estimate (300ms)
│  └─ tool_semantic_check (200ms)
├─ refinement_loop (500ms)
├─ final_validation (300ms)
└─ cache_store (20ms)
```

## Deployment

### Infrastructure Requirements

- **Container**: Docker image with Claude SDK
- **Memory**: 2-4GB per instance
- **CPU**: 2-4 cores (I/O bound)
- **Cache**: Redis Cluster (shared across instances)
- **Database**: PostgreSQL (pattern cache)
- **External**: Claude API access (Anthropic)

### Scaling Strategy

- **Horizontal**: Stateless containers (scale on CPU/latency)
- **Vertical**: Increase memory for larger context windows
- **Cache**: Redis Cluster for high availability

### High Availability

- **Multi-AZ**: Deploy across 3 availability zones
- **Health checks**: Liveness and readiness probes
- **Circuit breaker**: Automatic fallback during outages
- **Target uptime**: 99.9%

## Example Usage Scenarios

### Scenario 1: Indirect Access Investigation

Security analyst investigating users with indirect access to sensitive resources:

```cypher
MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*1..4]->(r:Resource)
WHERE r.classification = "secret"
  AND NOT (u)-[:DIRECT_PERMISSION]->(r)
RETURN u.name, length(path) as indirection_depth
ORDER BY indirection_depth
```

**AI Translation**: Uses graph operators with leftanti join for negation
**Confidence**: 0.92
**Performance**: 1.5s estimated, 1.2s actual

### Scenario 2: Lateral Movement Detection

Detecting potential lateral movement from compromised device:

```cypher
MATCH path = (compromised:Device)-[:CONNECTS_TO*1..5]->(target:Device)
WHERE compromised.compromised = true
  AND target.critical = true
RETURN path, length(path) as hop_count
```

**AI Translation**: Uses graph operators with bounded depth
**Confidence**: 0.88
**Performance**: 2.5s estimated, 2.8s actual

### Scenario 3: Attack Path Reconstruction

Reconstructing attack chain from initial access:

```cypher
MATCH path = (entry:Event)-[:CAUSED|:ENABLED*1..6]->(outcome:Event)
WHERE entry.type = "InitialAccess"
  AND outcome.severity = "Critical"
RETURN path, length(path) as chain_length
ORDER BY chain_length
```

**AI Translation**: Uses hybrid approach (graph ops + joins)
**Confidence**: 0.85
**Performance**: 3.2s estimated, 3.5s actual

## API Reference

See `openapi.yaml` for complete API specification including:
- Request/response schemas
- Error codes and messages
- Authentication requirements
- Rate limiting details

## Further Reading

- **`architecture.md`**: Deep dive into component design
- **`integration_patterns.md`**: System integration and coordination
- **`example_usage.py`**: Complete code examples

## Support

For questions or issues:
- Open GitHub issue
- Contact: cypher-sentinel-support@example.com
- Documentation: https://docs.cypher-sentinel.com

## License

[Your License Here]

---

**Last Updated**: 2025-10-28
**API Version**: 1.0.0
**OpenAPI Spec**: openapi.yaml
