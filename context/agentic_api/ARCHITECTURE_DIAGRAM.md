# Agentic AI Translation Layer - Architecture Diagrams

## System Context Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                         CYPHER-SENTINEL SYSTEM                          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    CLIENT APPLICATIONS                            │  │
│  │  • Security Analyst Dashboard                                     │  │
│  │  • Investigation Tools                                            │  │
│  │  • Automated Threat Detection                                     │  │
│  │  • Compliance Reporting                                           │  │
│  └────────────────────────┬─────────────────────────────────────────┘  │
│                           │                                             │
│                           │ Cypher Queries                              │
│                           ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    QUERY ROUTER                                   │  │
│  │  • Pattern Analysis                                               │  │
│  │  • Complexity Classification                                      │  │
│  │  • Tier Selection                                                 │  │
│  └───┬───────────────────────┬────────────────────────┬─────────────┘  │
│      │                       │                        │                 │
│      │ 85%                   │ 10%                    │ 5%              │
│      ▼                       ▼                        ▼                 │
│  ┌──────────┐    ┌────────────────────────┐    ┌──────────────┐       │
│  │ FAST     │    │  AGENTIC AI LAYER      │    │  FALLBACK    │       │
│  │ PATH     │    │  ═════════════════════ │    │  PATH        │       │
│  │          │    │                        │    │              │       │
│  │ Direct   │    │  Claude Agent SDK      │    │  Join-Based  │       │
│  │ Graph    │    │  Goal-Seeking          │    │  Translation │       │
│  │ Operators│    │  Validation            │    │              │       │
│  │          │    │  Learning              │    │              │       │
│  └────┬─────┘    └────────────┬───────────┘    └──────┬───────┘       │
│       │                       │                       │                │
│       │                       │ KQL Queries           │                │
│       └───────────────────────┴───────────────────────┘                │
│                               │                                         │
│                               ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    MICROSOFT SENTINEL                             │  │
│  │  • KQL Query Execution                                            │  │
│  │  • Security Data Lake                                             │  │
│  │  • Graph Operators (make-graph, graph-match)                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

## Agentic AI Layer - Component Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       AGENTIC AI TRANSLATION LAYER                        │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                          API GATEWAY                                 │ │
│  │  • Authentication (API Keys)                                         │ │
│  │  • Rate Limiting                                                     │ │
│  │  • Request Validation                                                │ │
│  │  • Distributed Tracing                                               │ │
│  └────────────────────────────┬────────────────────────────────────────┘ │
│                                │                                          │
│                                ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                  TRANSLATION SERVICE (Orchestrator)                  │ │
│  │                                                                      │ │
│  │  async def translate(cypher, context, options):                     │ │
│  │      1. Check Pattern Cache                                         │ │
│  │      2. Build Agent Context                                         │ │
│  │      3. Invoke Claude Agent (Goal-Seeking)                          │ │
│  │      4. Iterative Refinement                                        │ │
│  │      5. Semantic Validation                                         │ │
│  │      6. Update Cache                                                │ │
│  │      7. Return TranslationResponse                                  │ │
│  └──┬────────────────┬─────────────────┬──────────────────┬───────────┘ │
│     │                │                 │                  │              │
│     ▼                ▼                 ▼                  ▼              │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ PATTERN  │  │ CLAUDE    │  │ GOAL-SEEKING │  │ SEMANTIC        │   │
│  │ CACHE    │  │ AGENT SDK │  │ ENGINE       │  │ VALIDATOR       │   │
│  │          │  │           │  │              │  │                 │   │
│  │ • Fuzzy  │  │ • Reasoning│ │ • Iterative  │  │ • Syntax Check  │   │
│  │   Match  │  │ • Tools   │  │   Refinement │  │ • Structure     │   │
│  │ • Success│  │ • MCP     │  │ • Feedback   │  │   Analysis      │   │
│  │   Rates  │  │ • Context │  │   Loop       │  │ • AI Reasoning  │   │
│  │ • Learning│  │   Mgmt    │  │ • Progress   │  │ • Sample Exec   │   │
│  └──────────┘  └───────────┘  │   Tracking   │  └─────────────────┘   │
│       │              │         └──────────────┘           │             │
│       │              │                                    │             │
│       ▼              ▼                                    ▼             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    SUPPORT COMPONENTS                             │  │
│  │                                                                   │  │
│  │  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐   │  │
│  │  │ Performance   │  │ Schema       │  │ Query History      │   │  │
│  │  │ Estimator     │  │ Provider     │  │ Provider           │   │  │
│  │  │               │  │              │  │                    │   │  │
│  │  │ • Cardinality │  │ • Metadata   │  │ • Similar Queries  │   │  │
│  │  │ • Complexity  │  │ • Statistics │  │ • Performance Data │   │  │
│  │  │ • Time Est    │  │ • Indexes    │  │ • Success Patterns │   │  │
│  │  └───────────────┘  └──────────────┘  └────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    RELIABILITY LAYER                              │  │
│  │                                                                   │  │
│  │  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐   │  │
│  │  │ Circuit      │  │ Graceful        │  │ Fallback         │   │  │
│  │  │ Breaker      │  │ Degradation     │  │ Coordinator      │   │  │
│  │  │              │  │                 │  │                  │   │  │
│  │  │ • OPEN       │  │ • Normal        │  │ • AI → Cache     │   │  │
│  │  │ • CLOSED     │  │ • Fast          │  │ • Cache → Join   │   │  │
│  │  │ • HALF_OPEN  │  │ • Cache-Only    │  │ • Join → Error   │   │  │
│  │  └──────────────┘  │ • Fallback      │  └──────────────────┘   │  │
│  │                    └─────────────────┘                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Redis Cache  │    │ PostgreSQL      │    │ Claude API      │
│ (Patterns)   │    │ (Learning DB)   │    │ (Anthropic)     │
└──────────────┘    └─────────────────┘    └─────────────────┘
```

## Request Flow - Successful Translation

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /translate/agentic
     │ {cypher, context, options}
     ▼
┌─────────────────────┐
│ API Gateway         │ ◄─── Authentication, Rate Limiting
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Translation Service                         │
│                                             │
│ 1. Parse Request (10ms)                     │
├─────────────────────────────────────────────┤
          │
          ▼
┌─────────────────────────────────────────────┐
│ Pattern Cache Lookup (10ms)                 │
│ • Compute fingerprint                       │
│ • Search similar patterns                   │
│ • [MISS] → Continue                         │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Build Agent Context (50ms)                  │
│ • Load schema metadata                      │
│ • Get cardinality statistics                │
│ • Fetch query history                       │
│ • Prepare constraints                       │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Claude Agent SDK Translation (1200ms)       │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Agent Reasoning (600ms)                 │ │
│ │ • Analyze query semantics               │ │
│ │ • Identify patterns                     │ │
│ │ • Choose translation strategy           │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Tool Invocations (400ms)                │ │
│ │ • KQL Syntax Validator (100ms)          │ │
│ │ • Performance Estimator (150ms)         │ │
│ │ • Semantic Equivalence Check (150ms)    │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Refinement Iteration (200ms)            │ │
│ │ • Apply optimization hints              │ │
│ │ • Regenerate improved version           │ │
│ │ • Validate improvement                  │ │
│ └─────────────────────────────────────────┘ │
└─────────┬───────────────────────────────────┘
          │ Generated KQL + confidence
          ▼
┌─────────────────────────────────────────────┐
│ Semantic Validation (200ms)                 │
│ • Syntax validation                         │
│ • Structural comparison                     │
│ • AI equivalence reasoning                  │
│ • Confidence scoring                        │
│ • [PASS] confidence=0.92                    │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Cache Update (20ms)                         │
│ • Store translation pattern                 │
│ • Update statistics                         │
│ • Index for future lookups                  │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Response Builder                            │
│ • Package KQL query                         │
│ • Include confidence & strategy             │
│ • Add performance estimates                 │
│ • Generate explanation                      │
│ • Include alternatives                      │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ TranslationResponse                         │
│ {                                           │
│   translation_id: "tr_abc123",              │
│   status: "success",                        │
│   kql_query: "...",                         │
│   confidence: 0.92,                         │
│   strategy: "graph_operators",              │
│   estimated_performance: {...},             │
│   validation: {...},                        │
│   explanation: "..."                        │
│ }                                           │
└─────────┬───────────────────────────────────┘
          │
          ▼
     ┌──────────┐
     │  Client  │
     └──────────┘

Total Time: 1480ms
```

## Request Flow - With Fallback

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /translate/agentic
     ▼
┌─────────────────────┐
│ Translation Service │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Claude Agent Translation                    │
│ • Result: confidence=0.65                   │
│ • [BELOW THRESHOLD] → Trigger Fallback      │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Fallback Chain                              │
│                                             │
│ Step 1: Pattern Cache Lookup               │
│ • Search similar high-confidence patterns   │
│ • [MISS] → Continue                         │
│                                             │
│ Step 2: Join-Based Translator               │
│ • Apply rule-based translation              │
│ • Generate verbose but reliable KQL         │
│ • [SUCCESS] confidence=0.75                 │
└─────────┬───────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ TranslationResponse                         │
│ {                                           │
│   status: "success",                        │
│   kql_query: "/* Join-based */...",         │
│   confidence: 0.75,                         │
│   strategy: "join_based_fallback",          │
│   warnings: [                               │
│     "AI translation had low confidence",    │
│     "Using fallback, may be suboptimal"     │
│   ]                                         │
│ }                                           │
└─────────┬───────────────────────────────────┘
          │
          ▼
     ┌──────────┐
     │  Client  │
     └──────────┘

Total Time: 950ms
```

## Learning Feedback Loop

```
┌──────────────────────────────────────────────────────────────┐
│                    TRANSLATION LIFECYCLE                      │
└──────────────────────────────────────────────────────────────┘

     1. TRANSLATE
     ┌──────────┐
     │  Client  │ ──────► Cypher Query
     └──────────┘              │
                               ▼
                     ┌────────────────────┐
                     │ AI Translation     │
                     │ translation_id:    │
                     │   "tr_abc123"      │
                     └─────────┬──────────┘
                               │ KQL Query
                               │
     2. EXECUTE                ▼
                     ┌────────────────────┐
                     │ Microsoft Sentinel │
                     │ • Execute KQL      │
                     │ • Measure time     │
                     │ • Count results    │
                     └─────────┬──────────┘
                               │ Execution Metrics
                               │
     3. FEEDBACK               ▼
     ┌──────────┐       ┌──────────────────┐
     │  Client  │ ────► │ Submit Feedback  │
     └──────────┘       │ • translation_id │
                        │ • rating: 5/5    │
                        │ • correctness    │
                        │ • actual_time    │
                        │ • actual_count   │
                        └─────────┬────────┘
                                  │
     4. LEARN                     ▼
                        ┌──────────────────────┐
                        │ Pattern Cache Update │
                        │ • Update confidence  │
                        │ • Update success rate│
                        │ • Update perf stats  │
                        │ • Refine pattern     │
                        └─────────┬────────────┘
                                  │
     5. IMPROVE                   ▼
                        ┌──────────────────────┐
                        │ Future Translations  │
                        │ • Better estimates   │
                        │ • Higher confidence  │
                        │ • Faster lookups     │
                        └──────────────────────┘
```

## Circuit Breaker State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                      CIRCUIT BREAKER                             │
└─────────────────────────────────────────────────────────────────┘

       ┌────────────────┐
       │    CLOSED      │◄─────────────────────────┐
       │  (Normal Ops)  │                          │
       └────────┬───────┘                          │
                │                                  │
                │ failure_count > threshold        │ success_count >
                │                                  │ threshold
                ▼                                  │
       ┌────────────────┐                 ┌────────────────┐
       │     OPEN       │                 │   HALF_OPEN    │
       │  (Skip AI)     │                 │  (Testing)     │
       │  Use Fallback  │                 │                │
       └────────┬───────┘                 └────────▲───────┘
                │                                  │
                │ timeout elapsed                  │
                └──────────────────────────────────┘


State Transitions:

CLOSED → OPEN:
  • Trigger: 5 consecutive failures
  • Action: Skip AI translation, use fallback immediately

OPEN → HALF_OPEN:
  • Trigger: 60 seconds elapsed since last failure
  • Action: Allow 1 AI translation attempt

HALF_OPEN → CLOSED:
  • Trigger: 2 consecutive successes
  • Action: Resume normal AI translation

HALF_OPEN → OPEN:
  • Trigger: Any failure
  • Action: Return to open state
```

## Graceful Degradation Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                   DEGRADATION LEVELS                             │
└─────────────────────────────────────────────────────────────────┘

Level 1: NORMAL                     (Healthy System)
┌────────────────────────────────────────────────────────┐
│ • Full AI translation with refinement                  │
│ • max_iterations = 3                                   │
│ • All validation levels enabled                        │
│ • Latency: 500-2000ms                                  │
└────────────────────────────────────────────────────────┘
         │
         │ Claude API latency > 3s
         ▼
Level 2: FAST                       (Degraded Performance)
┌────────────────────────────────────────────────────────┐
│ • Single-shot AI translation (no refinement)           │
│ • max_iterations = 1                                   │
│ • Syntax validation only                               │
│ • Latency: 200-500ms                                   │
└────────────────────────────────────────────────────────┘
         │
         │ Claude API error_rate > 10%
         ▼
Level 3: CACHE_ONLY                 (Degraded Functionality)
┌────────────────────────────────────────────────────────┐
│ • Pattern cache lookup only                            │
│ • No AI translation                                    │
│ • Fallback to join-based if cache miss                 │
│ • Latency: 10-300ms                                    │
└────────────────────────────────────────────────────────┘
         │
         │ Claude API unavailable
         ▼
Level 4: FALLBACK                   (Minimal Functionality)
┌────────────────────────────────────────────────────────┐
│ • Direct to join-based translator                      │
│ • No AI, no cache                                      │
│ • Guaranteed translation (limited quality)             │
│ • Latency: 100-300ms                                   │
└────────────────────────────────────────────────────────┘
```

## Data Flow - Pattern Learning

```
┌─────────────────────────────────────────────────────────────────┐
│                     PATTERN LEARNING SYSTEM                      │
└─────────────────────────────────────────────────────────────────┘

Translation Request
       │
       ▼
┌──────────────────┐
│ Compute          │
│ Fingerprint      │ ───► Pattern Signature
│ • AST features   │      "MATCH-VAR_LENGTH-MULTI_REL-NEGATION"
│ • Pattern type   │
│ • Constraints    │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Lookup Similar   │
│ Patterns         │ ───► Cache Hit/Miss
│ • Fuzzy match    │
│ • Similarity     │
│   threshold=0.85 │
└──────────────────┘
       │
       │ [Cache Miss]
       ▼
┌──────────────────┐
│ Perform          │
│ AI Translation   │ ───► New Translation
│                  │      {cypher, kql, confidence, strategy}
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Generalize       │
│ Pattern          │ ───► Pattern Template
│ • Replace values │      "MATCH (u:$NODE_TYPE)-[:$REL_TYPE*$MIN..$MAX]..."
│ • Parameterize   │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Store in Cache   │
│                  │ ───► Pattern Cache Entry
│ • Pattern        │      {fingerprint, template, confidence,
│ • Metrics        │       usage_count, success_rate, avg_time}
│ • Statistics     │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Build Index      │
│                  │ ───► Fast Lookup Index
│ • Fingerprint    │      B-tree: fingerprint → pattern_id
│ • Similarity     │      LSH: features → similar_patterns
└──────────────────┘
       │
       │ [Future Request]
       ▼
┌──────────────────┐
│ Fast Lookup      │
│ (Cache Hit)      │ ───► Instant Translation
│ • 10-50ms        │      95% confidence
│ • No AI call     │
└──────────────────┘
       │
       │ [Feedback Received]
       ▼
┌──────────────────┐
│ Update Pattern   │
│ Statistics       │ ───► Refined Pattern
│ • Success rate   │      Higher confidence
│ • Performance    │      Better estimates
│ • Confidence     │
└──────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AZURE CLOUD                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Azure Load Balancer                            │ │
│  │              (Round-robin with health checks)               │ │
│  └─────────────────────────┬──────────────────────────────────┘ │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│  │ API Node 1 │    │ API Node 2 │    │ API Node 3 │            │
│  │ (Container)│    │ (Container)│    │ (Container)│            │
│  │            │    │            │    │            │            │
│  │ • 4GB RAM  │    │ • 4GB RAM  │    │ • 4GB RAM  │            │
│  │ • 2 vCPU   │    │ • 2 vCPU   │    │ • 2 vCPU   │            │
│  │ • Stateless│    │ • Stateless│    │ • Stateless│            │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘            │
│        │                 │                 │                    │
│        └─────────────────┴─────────────────┘                    │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌────────────┐   ┌─────────────┐   ┌────────────┐             │
│  │ Redis      │   │ PostgreSQL  │   │ Monitoring │             │
│  │ Cluster    │   │ (Patterns)  │   │ (Grafana)  │             │
│  │            │   │             │   │            │             │
│  │ • Cache    │   │ • Learning  │   │ • Metrics  │             │
│  │ • Sessions │   │ • History   │   │ • Tracing  │             │
│  │ • 3 nodes  │   │ • Replicas  │   │ • Alerts   │             │
│  └────────────┘   └─────────────┘   └────────────┘             │
│                                                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               │ HTTPS
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Claude API         │
                    │   (Anthropic)        │
                    │                      │
                    │ • Rate Limited       │
                    │ • Authenticated      │
                    │ • Monitored          │
                    └──────────────────────┘
```

---

**Note**: These diagrams provide visual representations of the architecture described in the detailed documentation. For implementation details, refer to the complete design documents.

