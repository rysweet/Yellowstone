"""Pattern learning and caching for translation optimization.

This module provides:
- Caching of successful translation patterns
- Learning from AI translations
- Pattern matching for similar queries
- Cache hit rate optimization (target >60%)
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import (
    CacheEntry,
    CacheStatistics,
    QueryComplexity,
    TranslationPattern,
)

logger = logging.getLogger(__name__)


class PatternCache:
    """Cache for translation patterns with learning capabilities.

    Maintains a cache of successful query translations and learns
    patterns to improve hit rate over time.

    Example:
        >>> cache = PatternCache(max_size=1000)
        >>> cache.put("find all nodes", "graph.nodes", QueryComplexity.SIMPLE)
        >>> result = cache.get("find all nodes")
        >>> print(result.kql_template)
        graph.nodes
    """

    def __init__(
        self,
        max_size: int = 10000,
        ttl_hours: float = 24.0,
        min_success_rate: float = 0.7,
        learning_enabled: bool = True,
    ):
        """Initialize pattern cache.

        Args:
            max_size: Maximum number of cache entries
            ttl_hours: Time to live for cache entries in hours
            min_success_rate: Minimum success rate to keep entry
            learning_enabled: Whether to learn new patterns
        """
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.min_success_rate = min_success_rate
        self.learning_enabled = learning_enabled

        self._cache: Dict[str, CacheEntry] = {}
        self._patterns: List[TranslationPattern] = []
        self._total_queries = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._evictions = 0

    def get(self, query: str) -> Optional[CacheEntry]:
        """Retrieve cached translation for query.

        Args:
            query: Natural language query

        Returns:
            Cache entry if found and valid, None otherwise
        """
        self._total_queries += 1

        # Normalize query
        normalized = self._normalize_query(query)

        # Try exact match first
        if normalized in self._cache:
            entry = self._cache[normalized]
            if self._is_valid(entry):
                entry.hit_count += 1
                entry.last_used_at = datetime.utcnow()
                self._cache_hits += 1
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return entry
            else:
                # Entry expired or invalid
                del self._cache[normalized]

        # Try pattern matching
        pattern_entry = self._match_pattern(query)
        if pattern_entry:
            self._cache_hits += 1
            logger.debug(f"Pattern match for query: {query[:50]}...")
            return pattern_entry

        self._cache_misses += 1
        logger.debug(f"Cache miss for query: {query[:50]}...")
        return None

    def put(
        self,
        query: str,
        kql: str,
        complexity: QueryComplexity,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Store translation in cache.

        Args:
            query: Natural language query
            kql: Translated KQL query
            complexity: Query complexity level
            metadata: Optional metadata
        """
        normalized = self._normalize_query(query)

        # Check if entry exists
        if normalized in self._cache:
            entry = self._cache[normalized]
            # Update existing entry
            entry.kql_template = kql
            entry.last_used_at = datetime.utcnow()
            if metadata:
                entry.metadata.update(metadata)
        else:
            # Create new entry
            entry = CacheEntry(
                query_pattern=normalized,
                kql_template=kql,
                complexity=complexity,
                metadata=metadata or {},
            )
            self._cache[normalized] = entry

            # Check cache size and evict if needed
            if len(self._cache) > self.max_size:
                self._evict_entries()

        # Learn pattern if enabled
        if self.learning_enabled:
            self._learn_pattern(query, kql, complexity)

    def record_success(self, query: str) -> None:
        """Record successful use of cached translation.

        Args:
            query: Natural language query
        """
        normalized = self._normalize_query(query)
        if normalized in self._cache:
            self._cache[normalized].success_count += 1

    def record_failure(self, query: str) -> None:
        """Record failed use of cached translation.

        Args:
            query: Natural language query
        """
        normalized = self._normalize_query(query)
        if normalized in self._cache:
            entry = self._cache[normalized]
            entry.failure_count += 1

            # Remove entry if success rate too low
            if entry.success_rate < self.min_success_rate and entry.hit_count > 5:
                logger.info(f"Removing low success rate entry: {normalized[:50]}")
                del self._cache[normalized]

    def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics.

        Returns:
            Cache statistics including hit rate
        """
        # Calculate average success rate
        total_success = sum(e.success_count for e in self._cache.values())
        total_failure = sum(e.failure_count for e in self._cache.values())
        total_attempts = total_success + total_failure
        avg_success_rate = total_success / total_attempts if total_attempts > 0 else 0.0

        return CacheStatistics(
            total_entries=len(self._cache),
            total_queries=self._total_queries,
            cache_hits=self._cache_hits,
            cache_misses=self._cache_misses,
            evictions=self._evictions,
            average_hit_rate=self._cache_hits / self._total_queries if self._total_queries > 0 else 0.0,
            average_success_rate=avg_success_rate,
        )

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._patterns.clear()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for caching.

        Args:
            query: Natural language query

        Returns:
            Normalized query string
        """
        # Convert to lowercase
        normalized = query.lower().strip()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove punctuation at end
        normalized = normalized.rstrip(".,!?;:")

        return normalized

    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid.

        Args:
            entry: Cache entry to validate

        Returns:
            True if entry is valid
        """
        # Check TTL
        if entry.age_hours > self.ttl_hours:
            return False

        # Check success rate (after minimum usage)
        if entry.hit_count > 5 and entry.success_rate < self.min_success_rate:
            return False

        return True

    def _match_pattern(self, query: str) -> Optional[CacheEntry]:
        """Try to match query against learned patterns.

        Args:
            query: Natural language query

        Returns:
            Cache entry if pattern matches, None otherwise
        """
        normalized = self._normalize_query(query)

        # Try to find similar patterns
        for pattern in self._patterns:
            if self._matches_pattern(normalized, pattern):
                # Create synthetic cache entry from pattern
                return CacheEntry(
                    query_pattern=pattern.nl_pattern,
                    kql_template=pattern.kql_pattern,
                    complexity=QueryComplexity.SIMPLE,  # Patterns are typically simple
                    hit_count=pattern.usage_count,
                    success_count=pattern.usage_count,
                    metadata={"pattern_match": True, "pattern_type": pattern.pattern_type},
                )

        return None

    def _matches_pattern(self, query: str, pattern: TranslationPattern) -> bool:
        """Check if query matches a learned pattern.

        Args:
            query: Normalized query
            pattern: Translation pattern

        Returns:
            True if query matches pattern
        """
        # Convert pattern to regex
        pattern_regex = self._pattern_to_regex(pattern.nl_pattern)

        # Try to match
        match = re.match(pattern_regex, query, re.IGNORECASE)
        return match is not None

    def _pattern_to_regex(self, pattern: str) -> str:
        """Convert pattern with variables to regex.

        Args:
            pattern: Pattern with {var} placeholders

        Returns:
            Regex pattern string
        """
        # Escape regex special chars except {}
        escaped = re.escape(pattern)

        # Replace escaped placeholders with capture groups
        regex = escaped.replace(r"\{", "(?P<").replace(r"\}", r">\w+)")

        # Anchor to start and end
        return f"^{regex}$"

    def _learn_pattern(
        self, query: str, kql: str, complexity: QueryComplexity
    ) -> None:
        """Learn new pattern from successful translation.

        Args:
            query: Natural language query
            kql: Translated KQL
            complexity: Query complexity
        """
        # Extract pattern type
        pattern_type = self._identify_pattern_type(query, kql)

        # Try to generalize the pattern
        nl_pattern, variables = self._generalize_query(query)
        kql_pattern = self._generalize_kql(kql, variables)

        # Check if pattern already exists
        existing = next(
            (p for p in self._patterns if p.nl_pattern == nl_pattern),
            None
        )

        if existing:
            # Update existing pattern
            existing.usage_count += 1
            existing.confidence = min(1.0, existing.confidence + 0.05)
            if len(existing.examples) < 5:
                existing.examples.append({"nl": query, "kql": kql})
        else:
            # Create new pattern
            pattern = TranslationPattern(
                pattern_type=pattern_type,
                nl_pattern=nl_pattern,
                kql_pattern=kql_pattern,
                variables=variables,
                examples=[{"nl": query, "kql": kql}],
                confidence=0.6,
                usage_count=1,
            )
            self._patterns.append(pattern)

            # Keep only top patterns
            if len(self._patterns) > 100:
                self._patterns.sort(key=lambda p: p.usage_count, reverse=True)
                self._patterns = self._patterns[:100]

    def _identify_pattern_type(self, query: str, kql: str) -> str:
        """Identify the type of pattern.

        Args:
            query: Natural language query
            kql: Translated KQL

        Returns:
            Pattern type string
        """
        query_lower = query.lower()
        kql_lower = kql.lower()

        if "graph.nodes" in kql_lower:
            if "where" in kql_lower:
                return "node_filter"
            return "node_query"
        elif "graph.edges" in kql_lower:
            if "where" in kql_lower:
                return "edge_filter"
            return "edge_query"
        elif "graph.paths" in kql_lower:
            return "path_query"
        elif "count" in kql_lower:
            return "count_query"
        elif "sum" in kql_lower or "avg" in kql_lower:
            return "aggregate_query"
        else:
            return "generic_query"

    def _generalize_query(self, query: str) -> Tuple[str, List[str]]:
        """Generalize query by extracting variables.

        Args:
            query: Natural language query

        Returns:
            Tuple of (generalized pattern, list of variables)
        """
        variables = []
        pattern = query

        # Extract quoted strings as variables
        quoted_pattern = r"['\"]([^'\"]+)['\"]"
        matches = re.finditer(quoted_pattern, pattern)
        for i, match in enumerate(matches):
            var_name = f"value{i}"
            variables.append(var_name)
            pattern = pattern.replace(match.group(0), f"{{{var_name}}}", 1)

        # If no variables found, return as-is
        if not variables:
            return self._normalize_query(query), []

        return self._normalize_query(pattern), variables

    def _generalize_kql(self, kql: str, variables: List[str]) -> str:
        """Generalize KQL by replacing values with variables.

        Args:
            kql: KQL query
            variables: List of variable names

        Returns:
            Generalized KQL pattern
        """
        if not variables:
            return kql

        pattern = kql

        # Replace quoted strings with variables in order
        quoted_pattern = r"['\"]([^'\"]+)['\"]"
        matches = list(re.finditer(quoted_pattern, pattern))
        for i, match in enumerate(matches):
            if i < len(variables):
                pattern = pattern.replace(match.group(0), f"{{{variables[i]}}}", 1)

        return pattern

    def _evict_entries(self) -> None:
        """Evict least useful cache entries to maintain size limit."""
        # Calculate score for each entry (higher is better)
        scores = {}
        for key, entry in self._cache.items():
            # Score based on hit count, success rate, and recency
            recency_weight = 1.0 / (entry.age_hours + 1)
            success_weight = entry.success_rate if entry.hit_count > 0 else 0.5
            hit_weight = entry.hit_count

            scores[key] = (
                hit_weight * 0.4 +
                success_weight * 0.4 +
                recency_weight * 0.2
            )

        # Sort by score and remove bottom 10%
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k])
        remove_count = max(1, len(self._cache) // 10)

        for key in sorted_keys[:remove_count]:
            del self._cache[key]
            self._evictions += 1

        logger.info(f"Evicted {remove_count} cache entries")

    def get_patterns(self) -> List[TranslationPattern]:
        """Get all learned patterns.

        Returns:
            List of translation patterns
        """
        return self._patterns.copy()

    def get_top_patterns(self, n: int = 10) -> List[TranslationPattern]:
        """Get top N most used patterns.

        Args:
            n: Number of patterns to return

        Returns:
            List of top patterns
        """
        sorted_patterns = sorted(
            self._patterns,
            key=lambda p: p.usage_count,
            reverse=True
        )
        return sorted_patterns[:n]
