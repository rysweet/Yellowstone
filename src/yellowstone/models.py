"""
Core data models for Yellowstone.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class TranslationStrategy(Enum):
    """Translation strategy for routing queries."""
    FAST_PATH = "fast_path"  # Direct graph operator translation (85%)
    AI_PATH = "ai_path"  # Agentic AI translation (10%)
    FALLBACK = "fallback"  # Join-based fallback (5%)


@dataclass
class CypherQuery:
    """Represents a Cypher query input."""
    query: str
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class KQLQuery:
    """Represents a translated KQL query."""
    query: str
    strategy: TranslationStrategy
    confidence: float  # 0.0-1.0
    estimated_execution_time_ms: Optional[int] = None


@dataclass
class TranslationContext:
    """Context for query translation."""
    user_id: str
    tenant_id: str
    permissions: list[str]
    max_execution_time_ms: int = 60000
    enable_ai_translation: bool = True
