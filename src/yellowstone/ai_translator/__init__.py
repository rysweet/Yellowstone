"""AI translation layer for natural language to KQL conversion.

This package provides:
- Query classification and routing (Fast/AI/Fallback)
- Pattern-based caching for common queries
- Semantic validation of translated KQL
- Learning from successful translations
- Mock Claude SDK integration for testing

Main components:
- QueryClassifier: Routes queries based on complexity (85%/10%/5% split)
- PatternCache: Caches translations with pattern learning (target >60% hit rate)
- SemanticValidator: Validates KQL syntax and semantics
- ClaudeSDKClient: Mock Claude API integration

Example:
    >>> from yellowstone.ai_translator import QueryClassifier, PatternCache, SemanticValidator
    >>> classifier = QueryClassifier()
    >>> cache = PatternCache(max_size=10000)
    >>> validator = SemanticValidator()
    >>>
    >>> decision = classifier.classify("Find all nodes with label Person")
    >>> print(decision.route)
    RouteDecision.FAST_PATH
    >>>
    >>> cache.put("find all nodes", "graph.nodes", QueryComplexity.SIMPLE)
    >>> cached = cache.get("find all nodes")
    >>> print(cached.kql_template if cached else "Not found")
    graph.nodes
"""

from .models import (
    CacheEntry,
    CacheStatistics,
    ClaudeAPIRequest,
    ClaudeAPIResponse,
    ComplexityScore,
    QueryComplexity,
    RoutingDecision,
    RouteDecision,
    SemanticValidationResult,
    TranslationPattern,
    TranslationRequest,
    TranslationResponse,
)
from .pattern_cache import PatternCache
from .query_classifier import QueryClassifier
from .semantic_validator import SemanticValidator

__all__ = [
    # Classifiers and Cache
    "QueryClassifier",
    "PatternCache",
    "SemanticValidator",
    # Models - Enums
    "QueryComplexity",
    "RouteDecision",
    # Models - Request/Response
    "TranslationRequest",
    "TranslationResponse",
    # Models - Internal
    "ComplexityScore",
    "RoutingDecision",
    "CacheEntry",
    "CacheStatistics",
    "SemanticValidationResult",
    "TranslationPattern",
    # Models - Claude SDK
    "ClaudeAPIRequest",
    "ClaudeAPIResponse",
]

__version__ = "0.1.0"
