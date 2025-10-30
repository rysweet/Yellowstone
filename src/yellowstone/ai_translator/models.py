"""Data models for AI translation components.

This module provides pydantic v2 models for:
- Translation requests and responses
- Query complexity scoring
- Routing decisions
- Pattern cache entries
- Semantic validation results
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class QueryComplexity(str, Enum):
    """Query complexity levels for routing decisions."""

    SIMPLE = "simple"  # Direct translation possible
    MEDIUM = "medium"  # Some complexity, might need AI
    COMPLEX = "complex"  # Requires AI translation
    UNKNOWN = "unknown"  # Cannot determine


class RouteDecision(str, Enum):
    """Query routing decision types."""

    FAST_PATH = "fast_path"  # Use direct translation (85%)
    AI_PATH = "ai_path"  # Use Claude SDK (10%)
    FALLBACK = "fallback"  # Use fallback logic (5%)


class TranslationRequest(BaseModel):
    """Request for translating natural language to KQL."""

    query: str = Field(..., description="Natural language query to translate")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context for translation"
    )
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: float = Field(default=30.0, gt=0, le=300, description="Request timeout in seconds")
    use_cache: bool = Field(default=True, description="Whether to use pattern cache")
    force_ai: bool = Field(default=False, description="Force AI translation even if simple")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class TranslationResponse(BaseModel):
    """Response from KQL translation."""

    kql: str = Field(..., description="Translated KQL query")
    complexity: QueryComplexity = Field(..., description="Query complexity score")
    route: RouteDecision = Field(..., description="Route decision taken")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Translation confidence score"
    )
    cache_hit: bool = Field(default=False, description="Whether result from cache")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Translation time in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    error: Optional[str] = Field(default=None, description="Error message if translation failed")

    @field_validator("kql")
    @classmethod
    def validate_kql(cls, v: str) -> str:
        """Validate KQL is not empty unless there's an error."""
        if not v or not v.strip():
            # KQL can be empty if there's an error, validation happens elsewhere
            return v
        return v.strip()


class ComplexityScore(BaseModel):
    """Detailed complexity scoring for a query."""

    overall: QueryComplexity = Field(..., description="Overall complexity level")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Numeric complexity score")
    factors: Dict[str, float] = Field(
        default_factory=dict, description="Individual complexity factors"
    )
    reasoning: str = Field(default="", description="Explanation of complexity score")


class RoutingDecision(BaseModel):
    """Detailed routing decision with reasoning."""

    route: RouteDecision = Field(..., description="Selected route")
    complexity: ComplexityScore = Field(..., description="Complexity analysis")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Routing decision confidence"
    )
    reasoning: str = Field(default="", description="Explanation of routing decision")
    alternatives: List[RouteDecision] = Field(
        default_factory=list, description="Alternative routes considered"
    )


class CacheEntry(BaseModel):
    """Cache entry for translation patterns."""

    query_pattern: str = Field(..., description="Normalized query pattern")
    kql_template: str = Field(..., description="KQL translation template")
    complexity: QueryComplexity = Field(..., description="Query complexity")
    hit_count: int = Field(default=0, ge=0, description="Number of cache hits")
    success_count: int = Field(default=0, ge=0, description="Number of successful uses")
    failure_count: int = Field(default=0, ge=0, description="Number of failed uses")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_used_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last usage timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this cache entry."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def age_hours(self) -> float:
        """Calculate age of cache entry in hours."""
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() / 3600


class SemanticValidationResult(BaseModel):
    """Result of semantic validation for a translation."""

    is_valid: bool = Field(..., description="Whether translation is semantically valid")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Validation confidence score"
    )
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    checks_performed: List[str] = Field(
        default_factory=list, description="List of validation checks performed"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TranslationPattern(BaseModel):
    """Pattern learned from successful translations."""

    pattern_type: str = Field(..., description="Type of pattern (e.g., 'node_query', 'path_query')")
    nl_pattern: str = Field(..., description="Natural language pattern")
    kql_pattern: str = Field(..., description="KQL pattern")
    variables: List[str] = Field(default_factory=list, description="Pattern variables")
    examples: List[Dict[str, str]] = Field(
        default_factory=list, description="Example translations"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Pattern confidence score"
    )
    usage_count: int = Field(default=0, ge=0, description="Number of times pattern used")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class ClaudeAPIRequest(BaseModel):
    """Request structure for Claude Agent SDK."""

    prompt: str = Field(..., description="Prompt for Claude")
    system: Optional[str] = Field(default=None, description="System prompt")
    max_tokens: int = Field(default=8192, gt=0, le=65536, description="Maximum tokens to generate (Sonnet 4.5: up to 64K)")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature")
    stream: bool = Field(default=False, description="Whether to stream response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    kql_docs: Optional[str] = Field(default=None, description="KQL documentation context for translation")


class ClaudeAPIResponse(BaseModel):
    """Response structure from Claude Agent SDK."""

    content: str = Field(..., description="Generated content")
    stop_reason: Optional[str] = Field(default=None, description="Why generation stopped")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    model: str = Field(default="", description="Model used for generation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CacheStatistics(BaseModel):
    """Statistics about pattern cache performance."""

    total_entries: int = Field(default=0, ge=0, description="Total cache entries")
    total_queries: int = Field(default=0, ge=0, description="Total queries processed")
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, ge=0, description="Number of cache misses")
    evictions: int = Field(default=0, ge=0, description="Number of cache evictions")
    average_hit_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average cache hit rate"
    )
    average_success_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Average translation success rate"
    )

    @property
    def hit_rate(self) -> float:
        """Calculate current hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
