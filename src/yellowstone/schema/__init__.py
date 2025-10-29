"""
Schema module for Yellowstone.

Provides Cypher to Microsoft Sentinel schema mapping and validation.
Maps Cypher graph constructs to Sentinel tables and provides join conditions.
"""

from .schema_mapper import SchemaMapper
from .schema_validator import SchemaValidator
from .models import (
    SchemaMapping,
    NodeMapping,
    EdgeMapping,
    PropertyMapping,
    SchemaValidationResult,
    LabelMappingCache,
)

__all__ = [
    "SchemaMapper",
    "SchemaValidator",
    "SchemaMapping",
    "NodeMapping",
    "EdgeMapping",
    "PropertyMapping",
    "SchemaValidationResult",
    "LabelMappingCache",
]
