# Cypher-Sentinel Implementation Plan

**Project**: Cypher Query Engine for Microsoft Sentinel
**Architecture**: KQL Native Graph Operators with Agentic AI Enhancement
**Complexity**: Medium-term project across 4 phases
**Team**: 2-3 engineers
**Target Coverage**: 95-98% of Cypher features
**Last Updated**: 2025-10-28

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Structure](#project-structure)
3. [Technology Stack](#technology-stack)
4. [Phase Breakdown](#phase-breakdown)
5. [Work Items and Dependencies](#work-items-and-dependencies)
6. [GitHub Issue Structure](#github-issue-structure)
7. [PR Strategy](#pr-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Documentation Plan](#documentation-plan)
10. [Risk Management](#risk-management)
11. [Success Metrics](#success-metrics)

---

## Executive Summary

### Project Goals

**Primary Goal**: Enable security analysts to use Cypher queries against Microsoft Sentinel data with 95-98% feature coverage and acceptable performance (2-5x overhead).

**Key Innovations**:
- KQL Native Graph Operators for 85% of queries (fast path)
- Claude Agent SDK for 10% complex patterns (intelligent path)
- Join-based fallback for 5% edge cases (safety net)

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Feature Coverage** | 95-98% | openCypher TCK test suite |
| **Performance Overhead** | 2-5x typical | Benchmark suite |
| **Translation Success Rate** | >90% | Production telemetry |
| **Query Latency (P95)** | <5s | Performance monitoring |
| **Security Compliance** | 100% | Security audit |

### Phase Summary

| Phase | Complexity | Key Deliverable | Coverage |
|-------|-----------|-----------------|----------|
| **Phase 1** | MEDIUM | Core graph operator translation | 70% |
| **Phase 2** | MEDIUM-HIGH | Performance optimization | 85% |
| **Phase 3** | HIGH | Agentic AI enhancement | 95-98% |
| **Phase 4** | MEDIUM | Production hardening | Production-ready |

---

## Project Structure

### Repository Organization

```
cypher-sentinel/
├── .github/
│   ├── workflows/                    # CI/CD pipelines
│   │   ├── ci.yml                   # Continuous integration
│   │   ├── cd.yml                   # Continuous deployment
│   │   ├── security.yml             # Security scanning
│   │   └── performance.yml          # Performance regression tests
│   ├── ISSUE_TEMPLATE/              # Issue templates
│   │   ├── epic.md
│   │   ├── story.md
│   │   ├── task.md
│   │   └── bug.md
│   └── pull_request_template.md     # PR template
│
├── modules/                          # Core modules (bricks)
│   ├── cypher_parser/               # Brick 1: Cypher AST parsing
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── lexer.py            # Token generation
│   │   │   ├── parser.py           # AST construction
│   │   │   ├── ast_nodes.py        # AST node definitions
│   │   │   └── validator.py        # Syntax validation
│   │   ├── tests/
│   │   │   ├── test_lexer.py
│   │   │   ├── test_parser.py
│   │   │   └── test_validator.py
│   │   ├── pyproject.toml          # Module dependencies
│   │   └── README.md               # Module documentation
│   │
│   ├── query_classifier/            # Brick 2: Pattern classification
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py       # Route queries to tiers
│   │   │   ├── complexity_scorer.py
│   │   │   ├── features.py         # Pattern features
│   │   │   └── rules.py            # Classification rules
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── graph_operator_translator/   # Brick 3: Direct KQL translation
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── translator.py       # Main translation logic
│   │   │   ├── match_patterns.py   # Pattern matching rules
│   │   │   ├── kql_builder.py      # KQL query construction
│   │   │   └── optimization.py     # Query optimization
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── agentic_ai_translator/       # Brick 4: Claude Agent SDK integration
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── agent_client.py     # Claude SDK wrapper
│   │   │   ├── goal_seeker.py      # Goal-seeking logic
│   │   │   ├── semantic_validator.py
│   │   │   ├── pattern_cache.py    # Learning system
│   │   │   └── feedback_loop.py
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── join_based_fallback/         # Brick 5: Join-based translation
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── join_translator.py  # Join-based logic
│   │   │   ├── query_unroller.py   # Variable-length path unrolling
│   │   │   └── optimizer.py
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── schema_mapper/               # Brick 6: Sentinel schema mapping
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── schema_loader.py    # Load Sentinel schemas
│   │   │   ├── mapper.py           # Cypher→Sentinel mapping
│   │   │   ├── versioning.py       # Schema version management
│   │   │   └── discovery.py        # Auto-discover schemas
│   │   ├── schemas/                # Schema definitions
│   │   │   ├── base_schema.yaml
│   │   │   ├── identity_graph.yaml
│   │   │   └── network_graph.yaml
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── execution_engine/            # Brick 7: KQL execution
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── executor.py         # Execute KQL queries
│   │   │   ├── graph_manager.py    # Transient/persistent graphs
│   │   │   ├── result_transformer.py
│   │   │   └── connection_pool.py  # Azure Data Explorer connections
│   │   ├── tests/
│   │   └── README.md
│   │
│   ├── security/                    # Brick 8: Security controls
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── rbac.py             # Role-based access control
│   │   │   ├── injection_guard.py  # Injection prevention
│   │   │   ├── rate_limiter.py     # Rate limiting
│   │   │   ├── complexity_limiter.py
│   │   │   └── audit_logger.py
│   │   ├── tests/
│   │   └── README.md
│   │
│   └── api/                         # Brick 9: REST API layer
│       ├── src/
│       │   ├── __init__.py
│       │   ├── app.py              # FastAPI application
│       │   ├── routes/
│       │   │   ├── query.py        # Query endpoints
│       │   │   ├── translation.py  # Translation endpoints
│       │   │   └── health.py       # Health checks
│       │   ├── models/             # API models
│       │   │   ├── request.py
│       │   │   └── response.py
│       │   └── middleware/         # API middleware
│       │       ├── auth.py
│       │       ├── logging.py
│       │       └── cors.py
│       ├── tests/
│       └── README.md
│
├── shared/                          # Shared utilities
│   ├── logging/                    # Centralized logging
│   ├── metrics/                    # Metrics and monitoring
│   ├── config/                     # Configuration management
│   └── utils/                      # Common utilities
│
├── tests/                          # Integration and E2E tests
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   ├── test_translation_pipeline.py
│   │   └── test_execution_pipeline.py
│   ├── performance/
│   │   ├── benchmarks/
│   │   │   ├── single_hop.py
│   │   │   ├── multi_hop.py
│   │   │   ├── variable_length.py
│   │   │   └── shortest_path.py
│   │   └── load_tests/
│   ├── security/
│   │   ├── test_injection.py
│   │   ├── test_rbac.py
│   │   └── test_complexity_limits.py
│   └── tck/                        # openCypher TCK compliance
│       └── run_tck.py
│
├── docs/                           # Documentation
│   ├── user_guide/
│   │   ├── getting_started.md
│   │   ├── query_examples.md
│   │   └── troubleshooting.md
│   ├── api/
│   │   ├── openapi.yaml
│   │   └── api_reference.md
│   ├── developer/
│   │   ├── architecture.md
│   │   ├── contributing.md
│   │   ├── testing.md
│   │   └── deployment.md
│   └── deployment/
│       ├── azure_setup.md
│       ├── configuration.md
│       └── monitoring.md
│
├── deploy/                         # Deployment artifacts
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── .dockerignore
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── configmap.yaml
│   │   └── secrets.yaml
│   ├── terraform/                  # Infrastructure as code
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   └── scripts/
│       ├── deploy.sh
│       └── rollback.sh
│
├── examples/                       # Usage examples
│   ├── notebooks/
│   │   ├── getting_started.ipynb
│   │   ├── lateral_movement.ipynb
│   │   └── privilege_escalation.ipynb
│   └── scripts/
│       ├── basic_query.py
│       └── batch_analysis.py
│
├── .pre-commit-config.yaml         # Pre-commit hooks
├── pyproject.toml                  # Python project config
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Dev dependencies
├── README.md                       # Project overview
├── LICENSE                         # License
└── CHANGELOG.md                    # Version history
```

### Module Philosophy

Each module follows the **brick architecture** principles:

1. **Single Responsibility**: One clear purpose per module
2. **Clear Contracts**: Defined inputs, outputs, side effects via `README.md`
3. **Regeneratable**: Can be rebuilt from specification alone
4. **Self-Contained**: All code in one directory
5. **Testable**: Comprehensive unit tests in `tests/`

---

## Technology Stack

### Core Technologies

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend Language** | Python 3.11+ | - Mature graph/parser libraries (ANTLR, pyparsing)<br>- Claude SDK support<br>- Fast development for 2-3 person team<br>- Strong Azure SDK ecosystem |
| **Parser Generator** | ANTLR4 | - Production-grade parser generator<br>- Cypher grammar available<br>- Good Python support |
| **API Framework** | FastAPI | - High performance (Starlette + Pydantic)<br>- Automatic OpenAPI generation<br>- Async support<br>- Type safety |
| **AI Integration** | Claude Agent SDK (Python) | - Goal-seeking capabilities<br>- Tool ecosystem<br>- High reasoning quality |
| **Azure Integration** | Azure SDK for Python | - Kusto (Azure Data Explorer) client<br>- Authentication (MSAL)<br>- Monitoring (Application Insights) |
| **Caching** | Redis | - Fast pattern cache<br>- Distributed session storage<br>- Circuit breaker state |
| **Database** | PostgreSQL | - Schema versioning<br>- Query history<br>- User feedback storage |
| **Containerization** | Docker + Kubernetes | - Consistent deployments<br>- Horizontal scaling<br>- Azure AKS integration |

### Development Tools

| Tool | Purpose |
|------|---------|
| **Poetry** | Dependency management and packaging |
| **Ruff** | Fast linting + formatting (replaces black, flake8, isort) |
| **Pyright** | Type checking |
| **Pytest** | Unit and integration testing |
| **Locust** | Load testing |
| **Pre-commit** | Automated quality checks |
| **GitHub Actions** | CI/CD pipelines |

### Cloud Infrastructure (Azure)

| Service | Purpose |
|---------|---------|
| **Azure Kubernetes Service (AKS)** | Container orchestration |
| **Azure Container Registry (ACR)** | Docker image storage |
| **Azure Cache for Redis** | Pattern cache and session storage |
| **Azure Database for PostgreSQL** | Metadata and feedback storage |
| **Azure Application Insights** | Monitoring and telemetry |
| **Azure Key Vault** | Secret management |
| **Azure Data Explorer (Kusto)** | Sentinel backend (query execution) |
| **Azure Log Analytics** | Query execution and logs |

---

## Phase Breakdown

### Phase 1: Core Translation

**Goal**: Implement direct Cypher → KQL graph operator translation for 70% of queries
**Complexity**: MEDIUM

#### Step 1: Foundation and Parsing (Complexity: MEDIUM)

**Focus**: Set up infrastructure and Cypher parsing

**Deliverables**:
1. Repository structure and CI/CD setup
2. Cypher parser module (ANTLR grammar)
3. AST node definitions
4. Basic query classifier (simple pattern detection)
5. Pre-commit hooks configured

**Team Assignment**:
- Engineer 1: Repository setup, CI/CD, parser integration
- Engineer 2: AST nodes, syntax validation
- Engineer 3 (if available): Documentation, CI/CD refinement

**Acceptance Criteria**:
- ✅ Parse 90% of basic Cypher queries to AST
- ✅ CI pipeline runs linting, type checking, unit tests
- ✅ Docker build succeeds
- ✅ Pre-commit hooks enforce code quality

---

#### Step 2: Graph Operator Translation (Complexity: HIGH)

**Focus**: Implement core translation to KQL graph operators

**Deliverables**:
1. Graph operator translator module
2. Pattern matching for single-hop queries
3. Pattern matching for multi-hop queries (fixed length)
4. Variable-length path translation `[*1..N]`
5. Schema mapper module (basic)

**Team Assignment**:
- Engineer 1: Single and multi-hop translation
- Engineer 2: Variable-length path translation
- Engineer 3 (if available): Schema mapper

**Acceptance Criteria**:
- ✅ Translate single-hop MATCH patterns to graph-match
- ✅ Translate multi-hop (2-5 hops) to graph-match
- ✅ Translate variable-length paths with bounds
- ✅ 80+ unit tests passing

---

#### Step 3: Execution and Basic Integration (Complexity: MEDIUM)

**Focus**: Execute translated queries and build end-to-end pipeline

**Deliverables**:
1. Execution engine module (Azure Data Explorer integration)
2. Result transformation (KQL → Cypher result format)
3. Basic API endpoints (query, translate)
4. End-to-end integration tests
5. OpenAPI specification

**Team Assignment**:
- Engineer 1: Execution engine
- Engineer 2: Result transformation and API
- Engineer 3 (if available): Integration tests

**Acceptance Criteria**:
- ✅ Execute translated KQL queries against test Sentinel workspace
- ✅ Return results in Cypher-compatible format
- ✅ API endpoints functional with authentication
- ✅ 10+ end-to-end tests passing
- ✅ **Target Coverage: 70%**

---

### Phase 2: Performance Optimization

**Goal**: Optimize performance and add persistent graphs for 85% coverage
**Complexity**: MEDIUM-HIGH

#### Step 1: Query Optimization (Complexity: HIGH)

**Focus**: Optimize generated KQL queries

**Deliverables**:
1. Query optimization layer
2. Predicate pushdown optimization
3. Join order optimization
4. Query plan analysis
5. Performance benchmarking suite

**Team Assignment**:
- Engineer 1: Optimization algorithms
- Engineer 2: Query plan analysis
- Engineer 3 (if available): Benchmarking suite

**Acceptance Criteria**:
- ✅ 30-50% reduction in query execution time for complex queries
- ✅ Automated benchmark suite (20+ query patterns)
- ✅ Performance regression detection in CI

---

#### Step 2: Persistent Graphs (Complexity: HIGH)

**Focus**: Implement persistent graph strategy for performance

**Deliverables**:
1. Graph manager (transient vs persistent)
2. Persistent graph creation automation
3. Graph refresh strategy (hourly, daily)
4. Intelligent graph selection logic
5. Graph versioning

**Team Assignment**:
- Engineer 1: Graph manager and selection logic
- Engineer 2: Persistent graph automation
- Engineer 3 (if available): Graph versioning

**Acceptance Criteria**:
- ✅ Create persistent graphs for common patterns
- ✅ 50-100x speedup for repeated queries on persistent graphs
- ✅ Automatic graph type selection based on query pattern
- ✅ Graph refresh without downtime

---

#### Step 3: Native Algorithms (Complexity: MEDIUM-HIGH)

**Focus**: Integrate KQL native graph algorithms

**Deliverables**:
1. Shortest path translation (`graph-shortest-paths`)
2. All paths translation (bounded)
3. Bidirectional pattern translation
4. Pattern existence checks
5. Advanced pattern library

**Team Assignment**:
- Engineer 1: Shortest path and all paths
- Engineer 2: Bidirectional patterns
- Engineer 3 (if available): Pattern library expansion

**Acceptance Criteria**:
- ✅ Shortest path queries functional with 1-5s execution
- ✅ Bidirectional patterns using undirected edges
- ✅ Advanced pattern coverage documented
- ✅ **Target Coverage: 85%**

---

### Phase 3: Agentic AI Enhancement

**Goal**: Add intelligent AI translation for complex patterns, achieving 95-98% coverage
**Complexity**: HIGH

#### Step 1: Claude Agent Integration (Complexity: HIGH)

**Focus**: Integrate Claude Agent SDK for complex translation

**Deliverables**:
1. Agentic AI translator module
2. Claude Agent SDK wrapper
3. Goal-seeking engine
4. Context preparation (schema, cardinality)
5. Translation validation

**Team Assignment**:
- Engineer 1: Agent SDK integration and goal-seeking
- Engineer 2: Context preparation and validation
- Engineer 3 (if available): Testing and refinement

**Acceptance Criteria**:
- ✅ Claude Agent translates complex patterns
- ✅ Goal-seeking generates 2-3 candidate translations
- ✅ Semantic validation scores translations
- ✅ 100-500ms translation latency

---

#### Step 2: Learning System and Routing (Complexity: HIGH)

**Focus**: Implement pattern cache, learning, and intelligent routing

**Deliverables**:
1. Pattern cache module (Redis)
2. Fuzzy pattern matching
3. Feedback loop and continuous learning
4. Query router with tier selection
5. Circuit breaker and fallback chain

**Team Assignment**:
- Engineer 1: Pattern cache and fuzzy matching
- Engineer 2: Learning system and feedback loop
- Engineer 3 (if available): Router and fallback chain

**Acceptance Criteria**:
- ✅ Cache hit rate >60% after 1000 queries
- ✅ Fuzzy matching finds similar patterns
- ✅ Feedback improves translation quality
- ✅ Intelligent routing to appropriate tier (graph ops, AI, fallback)
- ✅ Graceful degradation with fallback chain
- ✅ **Target Coverage: 95-98%**

---

### Phase 4: Production Hardening

**Goal**: Security, reliability, monitoring, and documentation for production readiness
**Complexity**: MEDIUM

#### Step 1: Security and Compliance (Complexity: HIGH)

**Focus**: Implement comprehensive security controls

**Deliverables**:
1. Security module (injection prevention, RBAC)
2. Query complexity limiter
3. Rate limiting per user/tenant
4. Audit logging
5. Security testing suite
6. Penetration testing results

**Team Assignment**:
- Engineer 1: Injection prevention and RBAC
- Engineer 2: Rate limiting and complexity limits
- Engineer 3 (if available): Security testing

**Acceptance Criteria**:
- ✅ AST-based translation (zero SQL injection risk)
- ✅ RBAC enforcement for all queries
- ✅ Rate limiting functional (per-user, per-tenant)
- ✅ Query complexity limits prevent DoS
- ✅ 100+ security test cases passing
- ✅ External penetration test passed

---

#### Step 2: Monitoring and Observability (Complexity: MEDIUM)

**Focus**: Production monitoring and alerting

**Deliverables**:
1. Application Insights integration
2. Custom metrics (translation success rate, latency, cache hit rate)
3. Alerting rules (critical and warning)
4. Performance dashboards
5. Log aggregation and search

**Team Assignment**:
- Engineer 1: Metrics and Application Insights
- Engineer 2: Dashboards and alerting
- Engineer 3 (if available): Log aggregation

**Acceptance Criteria**:
- ✅ All key metrics tracked (see Success Metrics)
- ✅ Critical alerts configured (translation success <90%, etc.)
- ✅ Real-time dashboards operational
- ✅ Log search functional across all components

---

#### Step 3: Documentation and Launch Prep (Complexity: LOW)

**Focus**: Complete documentation and final testing

**Deliverables**:
1. User guide (getting started, query examples)
2. API reference documentation
3. Developer guide (architecture, contributing)
4. Deployment guide (Azure setup, configuration)
5. Load testing results
6. Production readiness review

**Team Assignment**:
- Engineer 1: User guide and API reference
- Engineer 2: Developer guide and deployment guide
- Engineer 3 (if available): Load testing

**Acceptance Criteria**:
- ✅ Complete documentation published
- ✅ Load testing shows acceptable performance (100 concurrent users)
- ✅ All production checklist items complete
- ✅ Stakeholder sign-off
- ✅ **PRODUCTION READY**

---

## Work Items and Dependencies

### Dependency Graph

```
Phase 1, Step 1: Foundation
├── Repository Setup (E1)
├── Cypher Parser (E1, E2)
└── CI/CD Pipeline (E1, E3)
      ↓
Phase 1, Step 2: Translation
├── Graph Operator Translator (E1, E2) [depends: Parser]
└── Schema Mapper (E3) [depends: Parser]
      ↓
Phase 1, Step 3: Execution
├── Execution Engine (E1) [depends: Schema Mapper]
├── API Layer (E2) [depends: Translator, Execution]
└── Integration Tests (E3) [depends: API]
      ↓
Phase 2, Step 1: Optimization
├── Query Optimizer (E1) [depends: Translator]
├── Query Plan Analysis (E2) [depends: Execution]
└── Benchmark Suite (E3) [depends: all]
      ↓
Phase 2, Step 2: Persistent Graphs
├── Graph Manager (E1) [depends: Execution]
├── Persistent Graph Automation (E2) [depends: Graph Manager]
└── Graph Versioning (E3) [depends: Graph Manager]
      ↓
Phase 2, Step 3: Native Algorithms
├── Shortest Path (E1) [depends: Translator]
├── Bidirectional Patterns (E2) [depends: Translator]
└── Pattern Library (E3) [depends: all translation]
      ↓
Phase 3, Step 1: AI Integration
├── Claude Agent Integration (E1) [independent]
├── Context Preparation (E2) [depends: Schema Mapper]
└── Validation (E3) [depends: Agent]
      ↓
Phase 3, Step 2: Learning
├── Pattern Cache (E1) [depends: Agent]
├── Learning System (E2) [depends: Cache]
└── Query Router (E3) [depends: Classifier, Agent, Translator]
      ↓
Phase 4, Step 1: Security
├── Injection Prevention (E1) [depends: Translator]
├── RBAC (E2) [depends: API]
└── Security Tests (E3) [depends: all]
      ↓
Phase 4, Step 2: Monitoring
├── Metrics (E1) [depends: all modules]
├── Dashboards (E2) [depends: Metrics]
└── Alerting (E3) [depends: Metrics]
      ↓
Phase 4, Step 3: Documentation
├── User Guide (E1) [depends: API]
├── Developer Guide (E2) [depends: all]
└── Load Testing (E3) [depends: all]
```

### Parallelization Opportunities

**High Parallelism** (Phase 1):
- Parser, Schema Mapper, CI/CD can proceed independently
- Translation and Execution can be developed in parallel once interfaces defined

**Medium Parallelism** (Phase 2):
- Optimization, Persistent Graphs, Native Algorithms can largely proceed in parallel
- Require coordination on shared interfaces

**Low Parallelism** (Phases 3-4):
- AI integration requires foundational work complete
- Security, monitoring, documentation sequential on working system

---

## GitHub Issue Structure

### Issue Hierarchy

```
EPIC (Phase-level)
  ├── STORY (Feature-level)
  │     ├── TASK (Implementation unit)
  │     ├── TASK
  │     └── TASK
  ├── STORY
  └── STORY

BUG (discovered issues)
```

### Epic Template

**File**: `.github/ISSUE_TEMPLATE/epic.md`

```markdown
---
name: Epic
about: Phase-level deliverable
title: '[EPIC] Phase N: <Phase Name>'
labels: epic, phase-N
assignees: ''
---

## Epic Overview

**Phase**: N
**Complexity**: [LOW|MEDIUM|MEDIUM-HIGH|HIGH]
**Goal**: <Phase goal in one sentence>

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Target Coverage: X%

## Key Deliverables

1. Deliverable 1
2. Deliverable 2
3. Deliverable 3

## Stories

- #<story-issue-number>
- #<story-issue-number>

## Dependencies

- Depends on: #<epic-issue-number>
- Blocks: #<epic-issue-number>

## Risks

| Risk | Mitigation |
|------|------------|
| Risk 1 | Mitigation strategy |

## Sequence

| Step | Focus | Status |
|------|-------|--------|
| 1 | Deliverable 1 | Not Started |
| 2 | Deliverable 2 | Not Started |
```

### Story Template

**File**: `.github/ISSUE_TEMPLATE/story.md`

```markdown
---
name: Story
about: User-facing feature or capability
title: '[STORY] <Feature description>'
labels: story
assignees: ''
---

## User Story

As a **[user type]**,
I want to **[action]**,
So that **[benefit]**.

## Acceptance Criteria

- [ ] Given [context], when [action], then [outcome]
- [ ] Given [context], when [action], then [outcome]

## Technical Details

**Module**: `modules/<module-name>`
**Complexity**: Low | Medium | High

## Tasks

- [ ] #<task-issue-number> - Task 1
- [ ] #<task-issue-number> - Task 2

## Definition of Done

- [ ] Code complete and reviewed
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Deployed to dev environment

## Dependencies

- Depends on: #<issue-number>
- Blocks: #<issue-number>
```

### Task Template

**File**: `.github/ISSUE_TEMPLATE/task.md`

```markdown
---
name: Task
about: Specific implementation unit (1-3 days)
title: '[TASK] <Task description>'
labels: task
assignees: ''
---

## Task Description

<Clear description of what needs to be implemented>

## Module

`modules/<module-name>`

## Implementation Steps

1. Step 1
2. Step 2
3. Step 3

## Acceptance Criteria

- [ ] Specific outcome 1
- [ ] Specific outcome 2
- [ ] Tests passing

## Testing Requirements

**Unit Tests**:
- Test case 1
- Test case 2

**Integration Tests** (if applicable):
- Test scenario 1

## Complexity

[LOW|MEDIUM|HIGH]

## Dependencies

- Depends on: #<issue-number>
```

### Bug Template

**File**: `.github/ISSUE_TEMPLATE/bug.md`

```markdown
---
name: Bug Report
about: Report a bug or issue
title: '[BUG] <Bug description>'
labels: bug
assignees: ''
---

## Bug Description

<Clear, concise description of the bug>

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

<What should happen>

## Actual Behavior

<What actually happens>

## Environment

- Branch: `<branch-name>`
- Commit: `<commit-sha>`
- Python version: `<version>`
- OS: `<os>`

## Logs/Screenshots

<Paste relevant logs or attach screenshots>

## Priority

- [ ] Critical (blocks development)
- [ ] High (impacts functionality)
- [ ] Medium (workaround available)
- [ ] Low (minor issue)

## Possible Fix

<If you have suggestions for how to fix>
```

### Labels

**Priority**:
- `priority: critical` - Blocks development
- `priority: high` - Important for milestone
- `priority: medium` - Should be done
- `priority: low` - Nice to have

**Type**:
- `epic` - Phase-level work
- `story` - Feature-level work
- `task` - Implementation unit
- `bug` - Bug report

**Phase**:
- `phase-1` - Core Translation (Complexity: MEDIUM)
- `phase-2` - Performance Optimization (Complexity: MEDIUM-HIGH)
- `phase-3` - Agentic AI Enhancement (Complexity: HIGH)
- `phase-4` - Production Hardening (Complexity: MEDIUM)

**Module**:
- `module: parser`
- `module: translator`
- `module: execution`
- `module: api`
- `module: security`
- etc.

**Status**:
- `status: blocked` - Blocked by dependency
- `status: in-progress` - Currently being worked on
- `status: review` - In code review
- `status: testing` - In testing phase

### Milestones

| Milestone | Completion | Description |
|-----------|-----------|-------------|
| **M1: Core Translation** | End of Phase 1 | 70% coverage, basic translation working |
| **M2: Performance Optimized** | End of Phase 2 | 85% coverage, persistent graphs, optimized |
| **M3: AI Enhanced** | End of Phase 3 | 95-98% coverage, AI translation working |
| **M4: Production Ready** | End of Phase 4 | Security hardened, documented, monitored |

### Example Issue Structure for Phase 1

```
EPIC #1: Phase 1 - Core Translation
├── STORY #2: Parse Cypher queries to AST
│   ├── TASK #3: Integrate ANTLR Cypher grammar
│   ├── TASK #4: Define AST node classes
│   ├── TASK #5: Implement syntax validator
│   └── TASK #6: Write parser unit tests
├── STORY #7: Translate single-hop MATCH patterns
│   ├── TASK #8: Implement graph-match builder
│   ├── TASK #9: Add WHERE clause translation
│   ├── TASK #10: Add RETURN clause translation
│   └── TASK #11: Write translation unit tests
├── STORY #12: Translate multi-hop MATCH patterns
│   ├── TASK #13: Implement fixed-length multi-hop
│   ├── TASK #14: Implement variable-length paths
│   └── TASK #15: Write multi-hop tests
├── STORY #16: Execute translated queries on Sentinel
│   ├── TASK #17: Implement Azure Data Explorer client
│   ├── TASK #18: Implement result transformation
│   └── TASK #19: Write execution tests
└── STORY #20: Build REST API endpoints
    ├── TASK #21: Implement /query endpoint
    ├── TASK #22: Implement /translate endpoint
    ├── TASK #23: Add authentication middleware
    └── TASK #24: Write API integration tests
```

---

## PR Strategy

### Branch Naming Conventions

```
<type>/<issue-number>-<short-description>

Types:
- feature/  - New feature (story/task)
- fix/      - Bug fix
- refactor/ - Code refactoring
- docs/     - Documentation only
- test/     - Test additions/changes
- chore/    - Build, CI, dependencies

Examples:
feature/8-implement-graph-match-builder
fix/42-parser-null-pointer-exception
refactor/15-simplify-ast-nodes
docs/20-add-api-documentation
test/11-add-multi-hop-tests
chore/5-setup-ci-pipeline
```

### PR Title Convention

```
[<TYPE>] <Issue #> - <Description>

Examples:
[FEATURE] #8 - Implement graph-match builder
[FIX] #42 - Fix parser null pointer exception
[REFACTOR] #15 - Simplify AST node structure
[DOCS] #20 - Add API documentation
```

### PR Template

**File**: `.github/pull_request_template.md`

```markdown
## Description

<Brief description of changes>

Closes #<issue-number>

## Type of Change

- [ ] New feature (story/task)
- [ ] Bug fix
- [ ] Refactoring
- [ ] Documentation
- [ ] Test additions
- [ ] Chore (build, CI, dependencies)

## Changes Made

- Change 1
- Change 2
- Change 3

## Testing

**Unit Tests**:
- [ ] All existing tests passing
- [ ] New tests added (list below)

**New Tests Added**:
- Test 1: `test_<name>`
- Test 2: `test_<name>`

**Integration Tests** (if applicable):
- [ ] Integration tests passing
- [ ] New integration tests added

**Manual Testing**:
- [ ] Tested locally
- [ ] Steps to reproduce: <steps>

## Documentation

- [ ] Code comments updated
- [ ] Module README updated (if applicable)
- [ ] API documentation updated (if applicable)
- [ ] User guide updated (if applicable)

## Performance Impact

- [ ] No performance impact
- [ ] Performance improvement (describe below)
- [ ] Potential performance degradation (describe mitigation below)

<Details if applicable>

## Security Considerations

- [ ] No security implications
- [ ] Security review required
- [ ] Security tests added

<Details if applicable>

## Checklist

- [ ] Code follows project style guidelines (Ruff passing)
- [ ] Type checking passing (Pyright)
- [ ] All tests passing
- [ ] Pre-commit hooks passing
- [ ] CI pipeline passing
- [ ] Documentation updated
- [ ] Ready for review

## Screenshots (if applicable)

<Add screenshots for UI/API changes>

## Additional Notes

<Any additional context, trade-offs, or follow-up items>
```

### PR Review Requirements

**Minimum Requirements**:
- 1 approving review from another engineer
- All CI checks passing (linting, type checking, tests)
- Pre-commit hooks passing
- No merge conflicts

**Review Checklist for Reviewers**:

```markdown
## Code Quality
- [ ] Code is clear and maintainable
- [ ] Follows project conventions
- [ ] No unnecessary complexity
- [ ] Appropriate error handling

## Testing
- [ ] Adequate test coverage (>80% for new code)
- [ ] Tests are meaningful and thorough
- [ ] Edge cases covered

## Documentation
- [ ] Code comments where necessary
- [ ] Public APIs documented
- [ ] README updated if needed

## Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] No obvious security issues

## Performance
- [ ] No obvious performance bottlenecks
- [ ] Appropriate data structures/algorithms
```

### CI/CD Pipeline

**File**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install ruff pyright
      - name: Run Ruff
        run: ruff check .
      - name: Run Pyright
        run: pyright

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -e .
          pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest tests/ --cov=modules --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-test:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install -r requirements-dev.txt
      - name: Run integration tests
        run: pytest tests/integration/

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r modules/
      - name: Run detect-secrets
        uses: reviewdog/action-detect-secrets@master
```

### Merge Criteria

**Required for Merge**:
1. ✅ At least 1 approval from team member
2. ✅ All CI checks passing
3. ✅ Pre-commit hooks passing
4. ✅ No merge conflicts
5. ✅ Branch up-to-date with base branch
6. ✅ Issue linked in PR description
7. ✅ Documentation updated (if applicable)

**Merge Strategy**:
- **Squash and Merge** for feature branches (cleaner history)
- **Rebase and Merge** for small fixes (preserves granular history)
- **No Fast-Forward** for release branches

---

## Testing Strategy

### Testing Pyramid

```
         ┌─────────────┐
         │  E2E Tests  │  <-- 10% (Few, slow, high-level)
         │   (10%)     │
         ├─────────────┤
      ┌──┴─────────────┴──┐
      │ Integration Tests │  <-- 20% (Some, medium speed)
      │      (20%)        │
      ├───────────────────┤
   ┌──┴───────────────────┴──┐
   │     Unit Tests          │  <-- 70% (Many, fast, focused)
   │       (70%)             │
   └─────────────────────────┘
```

### 1. Unit Tests (70%)

**Scope**: Individual functions and classes

**Tools**: Pytest, pytest-mock, pytest-cov

**Coverage Target**: >80% for all modules

**Examples**:

```python
# tests/modules/cypher_parser/test_parser.py

def test_parse_simple_match():
    """Test parsing a simple MATCH query"""
    query = "MATCH (n:User) RETURN n"
    ast = parse_cypher(query)
    assert ast.type == "MatchQuery"
    assert len(ast.patterns) == 1
    assert ast.patterns[0].label == "User"

def test_parse_variable_length_path():
    """Test parsing variable-length path"""
    query = "MATCH (a)-[r*1..3]->(b) RETURN a, b"
    ast = parse_cypher(query)
    assert ast.patterns[0].relationship.min_length == 1
    assert ast.patterns[0].relationship.max_length == 3

def test_translation_single_hop():
    """Test translating single-hop pattern"""
    ast = parse_cypher("MATCH (a)-[:KNOWS]->(b) RETURN b")
    kql = translate(ast)
    assert "make-graph" in kql
    assert "graph-match" in kql
```

**Run**: `pytest tests/modules/ -v`

---

### 2. Integration Tests (20%)

**Scope**: Multiple modules working together

**Tools**: Pytest, Docker (for Redis/PostgreSQL), Azure SDK (mocked)

**Examples**:

```python
# tests/integration/test_translation_pipeline.py

def test_full_translation_pipeline():
    """Test complete translation pipeline"""
    query = "MATCH (a:User)-[:REPORTS_TO*1..3]->(b:User) WHERE b.name = 'Alice' RETURN a"

    # Parse
    ast = parse_cypher(query)

    # Classify
    tier = classify_query(ast)
    assert tier == TranslationTier.GRAPH_OPERATOR

    # Translate
    kql = translate_to_kql(ast, tier)
    assert "make-graph" in kql
    assert "graph-match" in kql
    assert "*1..3" in kql

    # Validate
    validation = validate_translation(ast, kql)
    assert validation.confidence > 0.8

def test_end_to_end_with_execution():
    """Test query from Cypher to execution"""
    query = "MATCH (n:User) WHERE n.active = true RETURN n.name LIMIT 10"

    # Full pipeline
    result = execute_cypher_query(query, test_workspace)

    # Verify result structure
    assert "results" in result
    assert len(result["results"]) <= 10
    assert all("name" in r for r in result["results"])
```

**Run**: `pytest tests/integration/ -v`

---

### 3. End-to-End Tests (10%)

**Scope**: Full system including API and execution

**Tools**: Pytest, requests (API client), Azure test workspace

**Examples**:

```python
# tests/e2e/test_api_flow.py

def test_query_endpoint_e2e():
    """Test complete API query flow"""
    response = requests.post(
        f"{API_BASE_URL}/query",
        json={
            "query": "MATCH (n:Device) WHERE n.compromised = true RETURN n LIMIT 5",
            "workspace_id": TEST_WORKSPACE_ID
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "execution_time_ms" in data
    assert "translation_tier" in data

def test_ai_translation_fallback():
    """Test AI translation with fallback"""
    # Complex query that triggers AI path
    query = """
    MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*]->(r:Resource)
    WHERE NOT (u)-[:DIRECT_PERMISSION]->(r) AND r.classification = 'secret'
    RETURN u.name, length(path)
    """

    response = requests.post(f"{API_BASE_URL}/translate", json={"query": query})

    assert response.status_code == 200
    data = response.json()
    assert data["translation_tier"] == "agentic_ai"
    assert data["confidence"] > 0.7
    assert "kql_query" in data
```

**Run**: `pytest tests/e2e/ -v`

---

### 4. openCypher TCK (Test Compatibility Kit)

**Purpose**: Validate Cypher compatibility

**Source**: https://github.com/opencypher/openCypher/tree/master/tck

**Strategy**:
1. Import TCK feature files (Cucumber/Gherkin format)
2. Implement step definitions for our system
3. Run TCK scenarios against Cypher-Sentinel
4. Track coverage percentage

**Example**:

```python
# tests/tck/run_tck.py

from pytest_bdd import scenarios, given, when, then

scenarios('features/match.feature')

@given('an empty graph')
def empty_graph():
    clear_test_workspace()

@given('having executed: <query>')
def execute_setup_query(query):
    execute_cypher_query(query)

@when('executing query: <query>')
def execute_query(query):
    global result
    result = execute_cypher_query(query)

@then('the result should be: <expected>')
def verify_result(expected):
    assert result == parse_expected(expected)
```

**Target Coverage**: 85-95% of TCK scenarios

**Run**: `pytest tests/tck/ -v`

---

### 5. Performance Benchmarks

**Purpose**: Detect performance regressions

**Tools**: Pytest-benchmark, Locust (load testing)

**Benchmark Queries**:

```python
# tests/performance/benchmarks/test_single_hop.py

def test_single_hop_performance(benchmark):
    """Benchmark single-hop query"""
    query = "MATCH (a:User)-[:KNOWS]->(b:User) WHERE a.id = 123 RETURN b"

    result = benchmark(execute_cypher_query, query)

    # Assert performance constraints
    assert benchmark.stats['mean'] < 0.2  # <200ms mean
    assert benchmark.stats['stddev'] < 0.05  # Low variance

def test_multi_hop_performance(benchmark):
    """Benchmark 3-hop query"""
    query = "MATCH (a:User)-[:KNOWS*1..3]->(b:User) WHERE a.id = 123 RETURN b"

    result = benchmark(execute_cypher_query, query)

    assert benchmark.stats['mean'] < 2.0  # <2s mean
```

**Performance Regression Detection** (in CI):

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for comparison
      - name: Run benchmarks
        run: pytest tests/performance/benchmarks/ --benchmark-json=output.json
      - name: Compare with main
        run: |
          git checkout main
          pytest tests/performance/benchmarks/ --benchmark-json=main.json
          python scripts/compare_benchmarks.py output.json main.json
```

**Run**: `pytest tests/performance/benchmarks/ --benchmark-only`

---

### 6. Load Testing

**Purpose**: Validate system under load

**Tool**: Locust

**Scenarios**:

```python
# tests/performance/load_tests/locustfile.py

from locust import HttpUser, task, between

class CypherSentinelUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)  # Weight: 3x
    def simple_query(self):
        """Simple single-hop query"""
        self.client.post("/query", json={
            "query": "MATCH (n:Device) WHERE n.id = 123 RETURN n",
            "workspace_id": WORKSPACE_ID
        })

    @task(2)  # Weight: 2x
    def multi_hop_query(self):
        """Multi-hop query"""
        self.client.post("/query", json={
            "query": "MATCH (a:User)-[:KNOWS*1..3]->(b) RETURN b",
            "workspace_id": WORKSPACE_ID
        })

    @task(1)  # Weight: 1x (least frequent)
    def complex_ai_query(self):
        """Complex query requiring AI translation"""
        self.client.post("/query", json={
            "query": "MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*]->(r:Resource) WHERE r.sensitive = true RETURN path",
            "workspace_id": WORKSPACE_ID
        })
```

**Run**: `locust -f tests/performance/load_tests/locustfile.py --host=http://localhost:8000`

**Target Load**:
- 100 concurrent users
- 1000 requests/minute sustained
- P95 latency <5s
- Error rate <1%

---

### 7. Security Testing

**Purpose**: Validate security controls

**Tools**: Pytest, Bandit (static analysis), detect-secrets

**Test Categories**:

```python
# tests/security/test_injection.py

def test_sql_injection_prevention():
    """Test SQL injection attempts are blocked"""
    malicious_queries = [
        "MATCH (n) WHERE n.id = '1 OR 1=1' RETURN n",
        "MATCH (n) RETURN n; DROP TABLE Users;--",
        "MATCH (n) WHERE n.name = '\' OR \'1\'=\'1' RETURN n"
    ]

    for query in malicious_queries:
        # Should either reject or safely escape
        result = execute_cypher_query(query)
        # Verify no SQL injection occurred by checking audit logs
        assert not check_audit_log_for_injection()

def test_rbac_enforcement():
    """Test RBAC prevents unauthorized access"""
    # User with read-only access
    token = get_token(user="readonly_user")

    # Attempt write operation (should fail)
    response = requests.post(
        f"{API_BASE_URL}/query",
        json={"query": "CREATE (n:User {name: 'Hacker'})"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403  # Forbidden

def test_complexity_limits():
    """Test query complexity limits prevent DoS"""
    # Extremely complex query
    query = "MATCH (a)-[*1..100]->(b) RETURN a, b"  # Deep traversal

    response = requests.post(
        f"{API_BASE_URL}/query",
        json={"query": query}
    )

    assert response.status_code == 400  # Bad Request
    assert "complexity limit exceeded" in response.json()["error"]
```

**Run**: `pytest tests/security/ -v`

---

### Test Automation in CI

**Pre-commit Hooks** (`.pre-commit-config.yaml`):

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.5
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: detect-private-key

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: local
    hooks:
      - id: pyright
        name: pyright
        entry: pyright
        language: system
        types: [python]

      - id: pytest-fast
        name: pytest-fast
        entry: pytest tests/ -m "not slow"
        language: system
        pass_filenames: false
        always_run: true
```

---

## Documentation Plan

### Documentation Structure

```
docs/
├── user_guide/              # For security analysts
├── api/                     # For API consumers
├── developer/               # For engineers
└── deployment/              # For DevOps/SREs
```

### 1. User Guide (For Security Analysts)

**Target Audience**: Security analysts using Cypher queries

**Files**:
- `getting_started.md` - First steps, authentication, basic queries
- `query_examples.md` - 20+ example queries for common scenarios
- `query_reference.md` - Supported Cypher syntax reference
- `performance_tips.md` - Query optimization best practices
- `troubleshooting.md` - Common issues and solutions
- `faq.md` - Frequently asked questions

**Example Content** (`query_examples.md`):

```markdown
# Cypher Query Examples for Security Analytics

## Lateral Movement Detection

### Find devices accessed from compromised hosts (3 hops)

```cypher
MATCH path = (compromised:Device)-[:LOGGED_INTO*1..3]->(target:Device)
WHERE compromised.compromised = true AND target.sensitive = true
RETURN path, length(path) as hops
ORDER BY hops
LIMIT 50
```

**KQL Equivalent**: Uses `make-graph` + `graph-match`

**Expected Performance**: 1-3s for typical environments

---

## Privilege Escalation

### Find users with indirect access to sensitive resources

```cypher
MATCH path = (u:User)-[:PERMISSION|:GROUP_MEMBER*]->(r:Resource)
WHERE NOT (u)-[:DIRECT_PERMISSION]->(r) AND r.classification = 'secret'
RETURN u.name, length(path) as indirection_depth
ORDER BY indirection_depth
```

**Translation Tier**: Agentic AI (complex pattern)

**Expected Performance**: 2-5s (includes AI translation time)
```

**Assignment**: Engineer 1

---

### 2. API Reference (For API Consumers)

**Target Audience**: Developers integrating with the API

**Files**:
- `openapi.yaml` - OpenAPI 3.0 specification
- `api_reference.md` - Endpoint documentation with examples
- `authentication.md` - Auth flows and token management
- `rate_limits.md` - Rate limiting and quotas
- `error_codes.md` - Error code reference
- `sdks.md` - Client SDK documentation

**Example Content** (`api_reference.md`):

```markdown
# API Reference

## Execute Query

**Endpoint**: `POST /api/v1/query`

**Description**: Execute a Cypher query against a Sentinel workspace

**Request**:

```json
{
  "query": "MATCH (n:Device) WHERE n.compromised = true RETURN n LIMIT 10",
  "workspace_id": "workspace-123",
  "options": {
    "optimization_goal": "balanced",
    "timeout_seconds": 30
  }
}
```

**Response** (200 OK):

```json
{
  "results": [
    {"n": {"id": "device-1", "name": "WS001", "compromised": true}},
    {"n": {"id": "device-2", "name": "WS002", "compromised": true}}
  ],
  "execution_time_ms": 450,
  "translation_tier": "graph_operator",
  "confidence": 0.95,
  "kql_query": "let G = ...",
  "metadata": {
    "result_count": 2,
    "estimated_cost": 0.02
  }
}
```

**Error Response** (400 Bad Request):

```json
{
  "error": "Invalid Cypher syntax",
  "code": "SYNTAX_ERROR",
  "details": "Unexpected token at line 1, column 15"
}
```

**Rate Limits**: 100 requests/minute per user

**Authentication**: Bearer token required
```

**Assignment**: Engineer 1

---

### 3. Developer Guide (For Engineers)

**Target Audience**: Engineers contributing to the project

**Files**:
- `architecture.md` - System architecture overview
- `contributing.md` - Contribution guidelines
- `development_setup.md` - Local development setup
- `testing.md` - Testing strategy and running tests
- `module_reference.md` - Module-by-module documentation
- `coding_standards.md` - Code style and conventions
- `debugging.md` - Debugging tips and tools

**Example Content** (`architecture.md`):

```markdown
# System Architecture

## Overview

Cypher-Sentinel is a modular query engine that translates Cypher queries to KQL for execution on Microsoft Sentinel.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     API Layer                            │
│  FastAPI + Pydantic (modules/api)                        │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│               Query Router                               │
│  Pattern Classifier (modules/query_classifier)           │
│  - 85%: Graph Operator Translation                       │
│  - 10%: Agentic AI Translation                           │
│  - 5%:  Join-Based Fallback                              │
└────────────┬────────────────────────────┬────────────────┘
             ↓                            ↓
┌────────────────────┐       ┌────────────────────────┐
│ Graph Operator     │       │ Agentic AI Translator  │
│ Translator         │       │ (Claude Agent SDK)     │
│ (modules/graph_    │       │ (modules/agentic_ai_   │
│  operator_         │       │  translator)           │
│  translator)       │       │                        │
└────────────────────┘       └────────────────────────┘
             ↓                            ↓
┌─────────────────────────────────────────────────────────┐
│              Execution Engine                            │
│  Azure Data Explorer Client (modules/execution_engine)   │
│  - Transient graphs (make-graph)                         │
│  - Persistent graphs (pre-computed)                      │
└─────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### Cypher Parser (`modules/cypher_parser`)

**Responsibility**: Parse Cypher queries into AST

**Key Classes**:
- `CypherLexer` - Tokenization
- `CypherParser` - AST construction
- `ASTValidator` - Syntax validation

**Dependencies**: ANTLR4, pyparsing (fallback)

**Contract**: Given Cypher string, produce validated AST or error

---

### Graph Operator Translator (`modules/graph_operator_translator`)

**Responsibility**: Translate AST to KQL graph operators

**Key Classes**:
- `GraphOperatorTranslator` - Main translation logic
- `MatchPatternTranslator` - MATCH clause translation
- `KQLBuilder` - KQL query construction

**Dependencies**: cypher_parser, schema_mapper

**Contract**: Given AST + schema, produce optimized KQL query
```

**Assignment**: Engineer 2

---

### 4. Deployment Guide (For DevOps/SREs)

**Target Audience**: DevOps engineers and SREs

**Files**:
- `azure_setup.md` - Azure resource provisioning
- `configuration.md` - Configuration options and env vars
- `deployment.md` - Deployment procedures (Kubernetes)
- `monitoring.md` - Monitoring and alerting setup
- `backup_restore.md` - Backup and disaster recovery
- `scaling.md` - Horizontal scaling guide
- `troubleshooting_ops.md` - Operational troubleshooting

**Example Content** (`azure_setup.md`):

```markdown
# Azure Setup Guide

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed (`az`)
- Terraform installed (for IaC)
- `kubectl` installed (for Kubernetes)

## Step 1: Provision Azure Resources

### Using Terraform

```bash
cd deploy/terraform
terraform init
terraform plan -var="environment=production"
terraform apply
```

**Resources Created**:
- Azure Kubernetes Service (AKS) cluster
- Azure Container Registry (ACR)
- Azure Cache for Redis (Premium tier)
- Azure Database for PostgreSQL (Flexible Server)
- Azure Application Insights
- Azure Key Vault
- Virtual Network with subnets

**Estimated Time**: 15-20 minutes

---

## Step 2: Configure Azure Data Explorer Access

The application needs access to Sentinel's Azure Data Explorer workspace.

### Create Service Principal

```bash
az ad sp create-for-rbac --name "cypher-sentinel-sp" \
  --role "Data Explorer Viewer" \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.Kusto/clusters/<cluster>
```

**Output** (save securely):
```json
{
  "appId": "<client-id>",
  "password": "<client-secret>",
  "tenant": "<tenant-id>"
}
```

### Store in Key Vault

```bash
az keyvault secret set --vault-name <vault-name> \
  --name "kusto-client-id" --value "<client-id>"

az keyvault secret set --vault-name <vault-name> \
  --name "kusto-client-secret" --value "<client-secret>"
```

---

## Step 3: Deploy Application to AKS

### Build and Push Docker Image

```bash
cd deploy/docker
docker build -t <acr-name>.azurecr.io/cypher-sentinel:v1.0.0 .
docker push <acr-name>.azurecr.io/cypher-sentinel:v1.0.0
```

### Deploy to Kubernetes

```bash
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl apply -f deploy/kubernetes/configmap.yaml
kubectl apply -f deploy/kubernetes/secrets.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/ingress.yaml
```

**Verify Deployment**:
```bash
kubectl get pods -n cypher-sentinel
kubectl logs -f deployment/cypher-sentinel -n cypher-sentinel
```

---

## Step 4: Configure Monitoring

Application Insights is automatically configured via environment variables.

**Verify Telemetry**:
1. Navigate to Application Insights in Azure Portal
2. Check "Live Metrics" tab for real-time data
3. Verify custom metrics appear: `translation_success_rate`, `cache_hit_rate`

**Configure Alerts**: See `monitoring.md`
```

**Assignment**: Engineer 2

---

### Documentation Standards

**All Documentation Must**:
1. Include clear examples
2. Have table of contents for pages >3 sections
3. Use consistent formatting (Markdown with standard headings)
4. Be versioned with code (in git)
5. Include "Last Updated" timestamp
6. Be reviewed alongside code changes

**Documentation Review Checklist**:
- [ ] Clear and concise
- [ ] Accurate and up-to-date
- [ ] Includes examples
- [ ] No broken links
- [ ] Screenshots current (if applicable)
- [ ] Accessible to target audience

---

## Risk Management

### Risk Assessment Framework

**Likelihood**:
- High (H): >50% probability
- Medium (M): 20-50% probability
- Low (L): <20% probability

**Impact**:
- High (H): Blocks milestone or compromises security
- Medium (M): Delays milestone or degrades performance
- Low (L): Minor inconvenience

**Priority** = Likelihood × Impact

---

### Phase 1 Risks (Complexity: MEDIUM)

| Risk | Likelihood | Impact | Priority | Mitigation |
|------|-----------|--------|----------|------------|
| **ANTLR Cypher grammar incomplete** | M | H | HIGH | - Use official openCypher grammar<br>- Fallback to pyparsing for missing patterns<br>- Start with core syntax subset |
| **Azure Data Explorer access issues** | L | H | MEDIUM | - Test ADX connectivity early in phase<br>- Have backup test environment<br>- Document auth process clearly |
| **Team member unavailability** | M | M | MEDIUM | - Cross-train on modules<br>- Document work-in-progress<br>- Use pairing for critical components |
| **Scope creep** | H | M | HIGH | - Strict adherence to 70% coverage target<br>- Defer advanced features to Phase 2+<br>- Regular scope review |

**Contingency Plan**: If mid-phase assessment shows <60% coverage, defer API layer to Phase 2 and focus on core translation quality.

---

### Phase 2 Risks (Complexity: MEDIUM-HIGH)

| Risk | Likelihood | Impact | Priority | Mitigation |
|------|-----------|--------|----------|------------|
| **Optimization doesn't improve performance** | M | M | MEDIUM | - Benchmark early in phase<br>- Focus on high-value optimizations<br>- Accept 2-5x overhead as baseline |
| **Persistent graphs slow to refresh** | M | M | MEDIUM | - Implement incremental refresh<br>- Use versioning for zero-downtime updates<br>- Cache popular graph configurations |
| **KQL graph operators less capable than expected** | L | H | MEDIUM | - Validate all graph operator features early<br>- Have join-based fallback ready<br>- Test on real Sentinel data |
| **Performance regression in CI** | M | L | LOW | - Establish baseline benchmarks early<br>- Automated regression detection<br>- Performance review in PRs |

**Contingency Plan**: If persistent graphs prove unstable, rely on transient graphs + aggressive caching as primary strategy.

---

### Phase 3 Risks (Complexity: HIGH)

| Risk | Likelihood | Impact | Priority | Mitigation |
|------|-----------|--------|----------|------------|
| **Claude Agent SDK translation quality poor** | M | H | HIGH | - Start with simple patterns, build confidence<br>- Implement robust validation layer<br>- Human-in-loop for low-confidence translations<br>- Fallback to join-based translation |
| **AI translation too slow (>2s)** | M | M | MEDIUM | - Aggressive caching of AI translations<br>- Async translation with progress tracking<br>- Pattern generalization to reduce unique queries |
| **Claude API cost exceeds budget** | L | M | LOW | - Cache aggressively (target >80% hit rate)<br>- Use smaller model for simple patterns<br>- Implement cost tracking and alerts<br>- Fallback to rule-based translation |
| **Learning system doesn't improve over time** | M | L | LOW | - Manual pattern curation as fallback<br>- Collect user feedback actively<br>- Review learning metrics regularly |

**Contingency Plan**: If AI translation quality <70% confidence consistently, reduce AI tier scope to 5% and expand join-based fallback to 15%.

---

### Phase 4 Risks (Complexity: MEDIUM)

| Risk | Likelihood | Impact | Priority | Mitigation |
|------|-----------|--------|----------|------------|
| **Security vulnerabilities discovered** | M | H | HIGH | - External penetration test in security step<br>- Security review by dedicated team<br>- Bug bounty program post-launch |
| **Production load exceeds capacity** | M | M | MEDIUM | - Load testing with 2x expected peak<br>- Horizontal scaling validated<br>- Auto-scaling configured |
| **Documentation incomplete** | H | M | HIGH | - Start documentation early (ongoing)<br>- Dedicate final step to documentation completion<br>- Technical writer review (if available) |
| **Launch readiness not achieved** | L | H | MEDIUM | - Regular production readiness checklist<br>- Go/no-go review before launch<br>- Soft launch to pilot users first |

**Contingency Plan**: If production readiness not achieved by phase end, conduct pilot with limited users before full launch.

---

### Cross-Cutting Risks (All Phases)

| Risk | Likelihood | Impact | Priority | Mitigation |
|------|-----------|--------|----------|------------|
| **Schema drift in Sentinel** | H | H | CRITICAL | - Implement schema versioning<br>- Automated schema sync tests<br>- Version compatibility matrix<br>- Schema change alerts |
| **Team turnover** | L | H | MEDIUM | - Comprehensive documentation<br>- Regular knowledge sharing sessions<br>- Modular architecture enables handoff |
| **Changing requirements** | M | M | MEDIUM | - Agile sprints with review points<br>- Regular stakeholder demos<br>- Prioritize ruthlessly (MVP mindset) |
| **Technical debt accumulation** | H | M | HIGH | - Dedicated refactoring time (20% per sprint)<br>- Pre-commit hooks enforce standards<br>- Regular code quality reviews |

**Mitigation Strategy**: Monthly risk review meetings with stakeholders to reassess and adjust.

---

## Success Metrics

### Delivery Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **On-Time Delivery** | 100% of milestones | Milestone completion dates |
| **Feature Coverage** | 95-98% | openCypher TCK test results |
| **Test Coverage** | >80% | Pytest coverage report |
| **CI/CD Pipeline** | <10 min | GitHub Actions execution time |
| **Code Quality** | 0 Ruff errors | Pre-commit + CI checks |

---

### Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Translation Success Rate** | >90% | Production telemetry |
| **Query Latency (P50)** | <500ms | Application Insights |
| **Query Latency (P95)** | <5s | Application Insights |
| **Cache Hit Rate** | >60% | Redis metrics |
| **Performance Overhead** | 2-5x vs native KQL | Benchmark suite |

---

### Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **AI Translation Confidence** | >0.85 avg | Confidence score tracking |
| **User Feedback Rating** | >4.0/5.0 | User feedback API |
| **Bug Escape Rate** | <5% to production | Issue tracking |
| **Security Vulnerabilities** | 0 critical | Security scan results |
| **API Uptime** | >99.9% | Monitoring alerts |

---

### Business Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Analyst Productivity** | 30-50% improvement | Time-to-insight surveys |
| **Query Volume** | Track growth | Query logs |
| **Adoption Rate** | >50% of team post-launch | User analytics |
| **Cost per Query** | <$0.05 | Claude API costs + infra |
| **ROI** | >1000% in year 1 | Cost savings vs analyst time |

---

## Appendix A: Phase Milestone Checklist

### Phase 1, Step 1: Foundation
- [ ] Repository created with structure
- [ ] CI/CD pipeline functional
- [ ] Pre-commit hooks configured
- [ ] ANTLR Cypher grammar integrated
- [ ] Team onboarded and accounts provisioned
- [ ] Parser generates AST for basic queries
- [ ] Syntax validator functional
- [ ] 50+ parser unit tests passing
- [ ] Documentation: Architecture overview

### Phase 1, Step 2: Translation
- [ ] Single-hop MATCH translation working
- [ ] WHERE clause translation functional
- [ ] RETURN clause translation functional
- [ ] 40+ translation unit tests passing
- [ ] Multi-hop (2-5 hops) translation working
- [ ] Variable-length path translation functional
- [ ] Schema mapper integrated
- [ ] 60+ translation tests passing

### Phase 1, Step 3: Execution
- [ ] Azure Data Explorer connection working
- [ ] Execute translated queries on Sentinel
- [ ] Result transformation functional
- [ ] 10+ end-to-end tests passing
- [ ] REST API endpoints functional
- [ ] Authentication middleware working
- [ ] OpenAPI spec generated
- [ ] **Milestone 1: 70% coverage achieved**

### Phase 2, Step 1: Optimization
- [ ] Query optimization layer implemented
- [ ] Benchmark suite (20+ queries) running
- [ ] 30-50% performance improvement demonstrated
- [ ] Performance regression detection in CI

### Phase 2, Step 2: Persistent Graphs
- [ ] Persistent graphs functional
- [ ] Graph refresh automation working
- [ ] 50-100x speedup on repeated queries
- [ ] Intelligent graph selection working

### Phase 2, Step 3: Native Algorithms
- [ ] Shortest path translation functional
- [ ] Bidirectional patterns working
- [ ] **Milestone 2: 85% coverage achieved**
- [ ] Advanced pattern library documented

### Phase 3, Step 1: AI Integration
- [ ] Claude Agent SDK integrated
- [ ] Goal-seeking engine functional
- [ ] Semantic validation working
- [ ] 100-500ms AI translation latency

### Phase 3, Step 2: Learning
- [ ] Pattern cache with fuzzy matching
- [ ] Learning system functional
- [ ] Query router with tier selection
- [ ] **Milestone 3: 95-98% coverage achieved**

### Phase 4, Step 1: Security
- [ ] Injection prevention validated
- [ ] RBAC enforcement working
- [ ] Rate limiting functional
- [ ] Security tests passing
- [ ] External penetration test completed

### Phase 4, Step 2: Monitoring
- [ ] Application Insights integrated
- [ ] Custom metrics tracked
- [ ] Alerting rules configured
- [ ] Dashboards operational

### Phase 4, Step 3: Documentation
- [ ] User guide complete
- [ ] API reference complete
- [ ] Developer guide complete
- [ ] Deployment guide complete
- [ ] Load testing passed (100 users)
- [ ] **Milestone 4: Production ready**

---

## Appendix B: Team Roles and Responsibilities

### 2-Person Team Configuration

**Engineer 1** (Full-stack, Backend focus):
- Primary: Parser, Translator, Execution Engine
- Secondary: API, Integration
- Phase 1: Lead core translation implementation
- Phase 2: Lead optimization and algorithms
- Phase 3: Lead AI integration
- Phase 4: Lead security and documentation

**Engineer 2** (Full-stack, DevOps focus):
- Primary: Schema Mapper, API, Security, Deployment
- Secondary: Testing, Documentation
- Phase 1: Support translation, build API
- Phase 2: Lead persistent graphs
- Phase 3: Lead learning system and routing
- Phase 4: Lead monitoring and deployment

### 3-Person Team Configuration

**Engineer 1** (Backend, Parser/Translation specialist):
- Primary: Parser, Graph Operator Translator
- Phase 1: Core translation
- Phase 2: Optimization and algorithms
- Phase 3: AI integration support
- Phase 4: Security implementation

**Engineer 2** (Backend, AI/ML focus):
- Primary: Agentic AI Translator, Learning System
- Phase 1: Schema Mapper
- Phase 2: Persistent graphs
- Phase 3: Lead AI integration and learning
- Phase 4: Monitoring and alerting

**Engineer 3** (Full-stack, DevOps):
- Primary: API, Execution Engine, Deployment
- Phase 1: API and execution
- Phase 2: Performance benchmarking
- Phase 3: Query router and fallback chain
- Phase 4: Lead deployment and documentation

---

## Appendix C: Key Decision Log

| # | Decision Phase | Decision | Rationale | Impact |
|---|---------------|----------|-----------|--------|
| 1 | Planning | Use Python 3.11+ | Mature libraries, Claude SDK support, team expertise | Core technology |
| 2 | Planning | ANTLR4 for parser | Production-grade, existing Cypher grammar | Faster parser dev |
| 3 | Planning | Modular monorepo | Balance simplicity and modularity for small team | Project structure |
| 4 | Planning | FastAPI for API | Performance + auto-docs + async support | API framework |
| 5 | Planning | Target 95-98% coverage | Balance ambition and realism | Scope |

**Note**: Add new decisions as project progresses

---

## Appendix D: Contact and Resources

### Team Contacts

- **Project Lead**: <project-lead@example.com>
- **Tech Lead**: <tech-lead@example.com>
- **Product Owner**: <product-owner@example.com>

### Resources

- **GitHub Repository**: https://github.com/example/cypher-sentinel
- **Project Board**: https://github.com/example/cypher-sentinel/projects/1
- **Documentation**: https://docs.cypher-sentinel.com
- **Claude Agent SDK**: https://docs.anthropic.com/agent-sdk
- **openCypher Spec**: https://opencypher.org
- **KQL Reference**: https://docs.microsoft.com/en-us/azure/data-explorer/kusto/query/

### Regular Sync

- **When**: Mondays 10:00 AM
- **Duration**: 30 minutes
- **Agenda**: Previous period review, current period planning, blockers

### Sprint Reviews

- **Cadence**: Regular intervals
- **Audience**: Team + stakeholders
- **Format**: Demo + metrics review

---

**Document Version**: 1.0
**Last Updated**: 2025-10-28
**Status**: Ready for Review
**Next Review**: After Phase 1 Milestone

---

## Summary

This implementation plan provides a **comprehensive, actionable roadmap** for building Cypher-Sentinel across 4 phases with a 2-3 person team. The plan emphasizes:

1. **Incremental delivery** - 70% → 85% → 95-98% coverage across 4 phases
2. **Risk mitigation** - Identified risks per phase with concrete mitigation strategies
3. **Modular architecture** - Brick-based modules enabling parallel development
4. **Quality assurance** - Comprehensive testing strategy (unit, integration, E2E, TCK)
5. **Production readiness** - Security, monitoring, documentation built-in

**Key Success Factors**:
- Start simple (Phase 1: direct graph operator translation)
- Optimize incrementally (Phase 2: persistent graphs, algorithms)
- Add intelligence (Phase 3: AI enhancement)
- Harden for production (Phase 4: security, monitoring, docs)

**Expected Outcome**: Production-ready Cypher query engine with 95-98% feature coverage, 2-5x performance overhead, and high reliability.
