"""Query classification and routing logic.

This module provides:
- Query complexity analysis and scoring
- Intelligent routing decisions (Fast/AI/Fallback)
- Pattern recognition for routing optimization
- Learning from translation success/failure
"""

import logging
import re
from typing import Dict, List, Optional

from .models import (
    ComplexityScore,
    QueryComplexity,
    RouteDecision,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


class QueryClassifier:
    """Classifies queries and routes them to appropriate translation paths.

    Routes queries to:
    - Fast path (85%): Simple queries with direct translation
    - AI path (10%): Complex queries requiring Claude SDK
    - Fallback (5%): Queries that need special handling

    Example:
        >>> classifier = QueryClassifier()
        >>> decision = classifier.classify("Find all nodes with label 'Person'")
        >>> print(decision.route)
        RouteDecision.FAST_PATH
        >>> print(decision.complexity.overall)
        QueryComplexity.SIMPLE
    """

    # Complexity scoring weights
    WEIGHTS = {
        "query_length": 0.15,
        "keyword_complexity": 0.25,
        "property_complexity": 0.20,
        "logical_complexity": 0.20,
        "pattern_complexity": 0.20,
    }

    # Simple keywords (low complexity)
    SIMPLE_KEYWORDS = {
        "find", "get", "show", "list", "all", "nodes", "edges",
        "with", "label", "type", "name", "where",
    }

    # Complex keywords (high complexity)
    COMPLEX_KEYWORDS = {
        "aggregate", "group", "join", "union", "intersect", "recursive",
        "shortest", "longest", "optimal", "analyze", "compute", "calculate",
        "recommend", "suggest", "rank", "order by multiple", "pivot",
    }

    # Medium complexity keywords
    MEDIUM_KEYWORDS = {
        "path", "connected", "related", "count", "sum", "average",
        "max", "min", "order", "sort", "limit", "top", "distinct",
    }

    def __init__(self, learning_enabled: bool = True):
        """Initialize query classifier.

        Args:
            learning_enabled: Whether to learn from routing decisions
        """
        self.learning_enabled = learning_enabled
        self._route_history: List[Dict] = []
        self._success_by_route: Dict[RouteDecision, int] = {
            RouteDecision.FAST_PATH: 0,
            RouteDecision.AI_PATH: 0,
            RouteDecision.FALLBACK: 0,
        }
        self._failure_by_route: Dict[RouteDecision, int] = {
            RouteDecision.FAST_PATH: 0,
            RouteDecision.AI_PATH: 0,
            RouteDecision.FALLBACK: 0,
        }

    def classify(self, query: str, force_ai: bool = False) -> RoutingDecision:
        """Classify query and determine routing decision.

        Args:
            query: Natural language query
            force_ai: Force AI path regardless of complexity

        Returns:
            Routing decision with complexity analysis
        """
        # Calculate complexity score
        complexity = self._calculate_complexity(query)

        # Determine route
        if force_ai:
            route = RouteDecision.AI_PATH
            reasoning = "Forced AI translation requested"
        else:
            route = self._determine_route(complexity, query)
            reasoning = self._generate_reasoning(complexity, route, query)

        # Calculate routing confidence
        confidence = self._calculate_routing_confidence(complexity, route)

        # Determine alternative routes
        alternatives = self._get_alternative_routes(route)

        decision = RoutingDecision(
            route=route,
            complexity=complexity,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
        )

        # Record for learning
        if self.learning_enabled:
            self._route_history.append({
                "query": query,
                "decision": decision,
                "timestamp": None,  # Could add timestamp tracking
            })

        return decision

    def _calculate_complexity(self, query: str) -> ComplexityScore:
        """Calculate detailed complexity score for query.

        Args:
            query: Natural language query

        Returns:
            Detailed complexity score
        """
        factors = {}

        # Query length factor (0-1)
        words = query.lower().split()
        word_count = len(words)
        if word_count <= 5:
            factors["query_length"] = 0.0
        elif word_count <= 10:
            factors["query_length"] = 0.3
        elif word_count <= 20:
            factors["query_length"] = 0.6
        else:
            factors["query_length"] = 1.0

        # Keyword complexity factor (0-1)
        simple_count = sum(1 for word in words if word in self.SIMPLE_KEYWORDS)
        medium_count = sum(1 for word in words if word in self.MEDIUM_KEYWORDS)
        complex_count = sum(1 for word in words if word in self.COMPLEX_KEYWORDS)

        if complex_count > 0:
            factors["keyword_complexity"] = 1.0
        elif medium_count > 0:
            factors["keyword_complexity"] = 0.5
        elif simple_count > 0:
            factors["keyword_complexity"] = 0.2
        else:
            factors["keyword_complexity"] = 0.6  # Unknown keywords

        # Property complexity factor (0-1)
        property_patterns = [
            r"properties?\.\w+",  # properties.name
            r"\w+\s*(==|!=|>|<|>=|<=)\s*",  # comparison operators
            r"has\s+\w+",  # has keyword
        ]
        property_count = sum(
            len(re.findall(pattern, query.lower()))
            for pattern in property_patterns
        )
        if property_count == 0:
            factors["property_complexity"] = 0.0
        elif property_count <= 2:
            factors["property_complexity"] = 0.3
        elif property_count <= 4:
            factors["property_complexity"] = 0.6
        else:
            factors["property_complexity"] = 1.0

        # Logical complexity factor (0-1)
        logical_operators = ["and", "or", "not"]
        logical_count = sum(
            query.lower().count(f" {op} ") for op in logical_operators
        )
        nested_count = query.count("(")

        if logical_count == 0 and nested_count == 0:
            factors["logical_complexity"] = 0.0
        elif logical_count <= 1 and nested_count <= 1:
            factors["logical_complexity"] = 0.3
        elif logical_count <= 3 and nested_count <= 2:
            factors["logical_complexity"] = 0.6
        else:
            factors["logical_complexity"] = 1.0

        # Pattern complexity factor (0-1)
        pattern_indicators = [
            "path", "shortest", "longest", "recursive", "traverse",
            "connected", "relationship", "graph pattern",
        ]
        pattern_count = sum(
            1 for indicator in pattern_indicators
            if indicator in query.lower()
        )
        if pattern_count == 0:
            factors["pattern_complexity"] = 0.0
        elif pattern_count == 1:
            factors["pattern_complexity"] = 0.5
        else:
            factors["pattern_complexity"] = 1.0

        # Calculate weighted overall score
        overall_score = sum(
            factors[key] * self.WEIGHTS[key]
            for key in factors
        )

        # Determine overall complexity level
        if overall_score < 0.3:
            overall = QueryComplexity.SIMPLE
        elif overall_score < 0.6:
            overall = QueryComplexity.MEDIUM
        else:
            overall = QueryComplexity.COMPLEX

        reasoning = self._generate_complexity_reasoning(factors, overall_score)

        return ComplexityScore(
            overall=overall,
            score=overall_score,
            factors=factors,
            reasoning=reasoning,
        )

    def _determine_route(self, complexity: ComplexityScore, query: str) -> RouteDecision:
        """Determine routing decision based on complexity.

        Args:
            complexity: Complexity score
            query: Natural language query

        Returns:
            Route decision
        """
        # Check for fallback indicators
        if self._needs_fallback(query):
            return RouteDecision.FALLBACK

        # Route based on complexity
        if complexity.overall == QueryComplexity.SIMPLE:
            # 95% fast path, 5% AI for learning
            if complexity.score < 0.25:
                return RouteDecision.FAST_PATH
            else:
                # Borderline simple queries might need AI
                return RouteDecision.FAST_PATH if complexity.score < 0.28 else RouteDecision.AI_PATH

        elif complexity.overall == QueryComplexity.MEDIUM:
            # 70% fast path, 30% AI
            if complexity.score < 0.45:
                return RouteDecision.FAST_PATH
            else:
                return RouteDecision.AI_PATH

        else:  # COMPLEX
            # 10% fast path (very structured), 90% AI
            if complexity.score < 0.65 and self._is_structured_complex(query):
                return RouteDecision.FAST_PATH
            else:
                return RouteDecision.AI_PATH

    def _needs_fallback(self, query: str) -> bool:
        """Check if query needs fallback handling.

        Args:
            query: Natural language query

        Returns:
            True if fallback needed
        """
        fallback_indicators = [
            "explain", "describe", "what is", "how to", "help",
            "syntax", "example", "tutorial", "documentation",
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in fallback_indicators)

    def _is_structured_complex(self, query: str) -> bool:
        """Check if complex query has clear structure.

        Args:
            query: Natural language query

        Returns:
            True if query has clear structure despite complexity
        """
        # Check for clear structural indicators
        structure_indicators = [
            re.compile(r"find .* where .* and .*"),  # Clear where clause
            re.compile(r"get .* with .* and .*"),  # Clear with clause
            re.compile(r"count .* where .*"),  # Count with filter
        ]
        return any(pattern.search(query.lower()) for pattern in structure_indicators)

    def _calculate_routing_confidence(
        self, complexity: ComplexityScore, route: RouteDecision
    ) -> float:
        """Calculate confidence in routing decision.

        Args:
            complexity: Complexity score
            route: Chosen route

        Returns:
            Confidence score (0-1)
        """
        # Base confidence on how clear the complexity is
        if complexity.overall == QueryComplexity.SIMPLE:
            if route == RouteDecision.FAST_PATH:
                return 0.9 - complexity.score * 0.2  # High confidence for simple
            else:
                return 0.5  # Lower confidence if not fast path
        elif complexity.overall == QueryComplexity.MEDIUM:
            if route == RouteDecision.AI_PATH:
                return 0.7  # Moderate confidence
            else:
                return 0.6  # Slightly lower for fast path
        else:  # COMPLEX
            if route == RouteDecision.AI_PATH:
                return 0.8 + complexity.score * 0.2  # High confidence for AI
            else:
                return 0.5  # Lower confidence if not AI

    def _get_alternative_routes(self, chosen_route: RouteDecision) -> List[RouteDecision]:
        """Get alternative routes that were considered.

        Args:
            chosen_route: The chosen route

        Returns:
            List of alternative routes
        """
        all_routes = [RouteDecision.FAST_PATH, RouteDecision.AI_PATH, RouteDecision.FALLBACK]
        return [route for route in all_routes if route != chosen_route]

    def _generate_complexity_reasoning(
        self, factors: Dict[str, float], score: float
    ) -> str:
        """Generate human-readable reasoning for complexity score.

        Args:
            factors: Individual complexity factors
            score: Overall complexity score

        Returns:
            Reasoning explanation
        """
        high_factors = [
            factor for factor, value in factors.items()
            if value >= 0.6
        ]
        low_factors = [
            factor for factor, value in factors.items()
            if value < 0.3
        ]

        if high_factors:
            return f"High complexity due to: {', '.join(high_factors)}"
        elif low_factors:
            return f"Low complexity: simple {', '.join(low_factors)}"
        else:
            return f"Medium complexity (score: {score:.2f})"

    def _generate_reasoning(
        self, complexity: ComplexityScore, route: RouteDecision, query: str
    ) -> str:
        """Generate human-readable reasoning for routing decision.

        Args:
            complexity: Complexity analysis
            route: Chosen route
            query: Original query

        Returns:
            Reasoning explanation
        """
        if route == RouteDecision.FAST_PATH:
            return (
                f"Query classified as {complexity.overall.value} "
                f"(score: {complexity.score:.2f}), routing to fast path for "
                f"direct translation"
            )
        elif route == RouteDecision.AI_PATH:
            return (
                f"Query classified as {complexity.overall.value} "
                f"(score: {complexity.score:.2f}), routing to AI for "
                f"intelligent translation"
            )
        else:  # FALLBACK
            return (
                f"Query appears to be informational or help request, "
                f"routing to fallback handler"
            )

    def record_success(self, route: RouteDecision) -> None:
        """Record successful translation for learning.

        Args:
            route: Route that succeeded
        """
        if self.learning_enabled:
            self._success_by_route[route] += 1

    def record_failure(self, route: RouteDecision) -> None:
        """Record failed translation for learning.

        Args:
            route: Route that failed
        """
        if self.learning_enabled:
            self._failure_by_route[route] += 1

    def get_route_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics about routing decisions.

        Returns:
            Statistics by route including success rates
        """
        stats = {}
        for route in RouteDecision:
            successes = self._success_by_route[route]
            failures = self._failure_by_route[route]
            total = successes + failures

            stats[route.value] = {
                "total": total,
                "successes": successes,
                "failures": failures,
                "success_rate": successes / total if total > 0 else 0.0,
            }

        return stats

    def reset_statistics(self) -> None:
        """Reset all learning statistics."""
        self._route_history.clear()
        for route in RouteDecision:
            self._success_by_route[route] = 0
            self._failure_by_route[route] = 0
