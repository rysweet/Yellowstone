"""
Schema mapping module for translating Cypher to Sentinel.

Loads YAML schema definitions and provides mappings from Cypher labels
and relationships to Microsoft Sentinel tables and join conditions.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import yaml

from .models import SchemaMapping, LabelMappingCache
from .schema_validator import SchemaValidator


class SchemaMapper:
    """
    Maps Cypher graph constructs to Microsoft Sentinel tables.

    Loads schema from YAML file and provides lookups for:
    - Node label to Sentinel table mapping
    - Cypher relationship to Sentinel join condition mapping
    - Property field mappings
    """

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the schema mapper.

        Args:
            schema_path: Path to YAML schema file. If None, uses default schema.

        Example:
            >>> mapper = SchemaMapper()
            >>> table = mapper.get_sentinel_table('User')
            >>> assert table == 'IdentityInfo'
        """
        self.schema: Optional[SchemaMapping] = None
        self.cache = LabelMappingCache()
        self.validator = SchemaValidator()

        if schema_path is None:
            # Use default schema from package
            schema_path = self._get_default_schema_path()

        self.schema_path = schema_path
        self.load_schema(schema_path)

    @staticmethod
    def _get_default_schema_path() -> str:
        """Get path to default schema file."""
        current_dir = Path(__file__).parent
        return str(current_dir / "default_sentinel_schema.yaml")

    def load_schema(self, schema_path: str) -> None:
        """
        Load schema from YAML file.

        Args:
            schema_path: Path to YAML schema file

        Raises:
            FileNotFoundError: If schema file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValueError: If schema validation fails

        Example:
            >>> mapper = SchemaMapper()
            >>> mapper.load_schema('/path/to/custom_schema.yaml')
        """
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        try:
            with open(schema_path, "r") as f:
                schema_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML schema: {e}")

        # Parse and validate schema
        try:
            self.schema = SchemaMapping(**schema_dict)
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")

        # Validate schema integrity
        result = self.validator.validate(self.schema)
        if not result.is_valid:
            raise ValueError(f"Schema integrity check failed: {result.errors}")

        # Build cache
        self._build_cache()

    def _build_cache(self) -> None:
        """Build in-memory cache for fast lookups."""
        if not self.schema:
            return

        # Build label to table mapping
        for label, node_mapping in self.schema.nodes.items():
            self.cache.label_to_table[label] = node_mapping.sentinel_table

        # Build table to fields mapping
        for table_name, table_meta in self.schema.tables.items():
            self.cache.table_to_fields[table_name] = table_meta.fields or []

        # Build relationship to join mapping
        for rel_type, edge_mapping in self.schema.edges.items():
            self.cache.relationship_to_join[rel_type] = {
                "from_label": edge_mapping.from_label,
                "to_label": edge_mapping.to_label,
                "left_table": edge_mapping.sentinel_join.left_table,
                "right_table": edge_mapping.sentinel_join.right_table,
                "join_condition": edge_mapping.sentinel_join.join_condition,
                "strength": edge_mapping.strength,
            }

    def get_sentinel_table(self, cypher_label: str) -> Optional[str]:
        """
        Get the Sentinel table for a Cypher node label.

        Args:
            cypher_label: Cypher node label (e.g., 'User', 'Device')

        Returns:
            Sentinel table name or None if not found

        Example:
            >>> mapper = SchemaMapper()
            >>> table = mapper.get_sentinel_table('User')
            >>> assert table == 'IdentityInfo'
        """
        return self.cache.label_to_table.get(cypher_label)

    def get_cypher_labels(self) -> List[str]:
        """
        Get all available Cypher node labels.

        Returns:
            List of node labels defined in schema

        Example:
            >>> mapper = SchemaMapper()
            >>> labels = mapper.get_cypher_labels()
            >>> assert 'User' in labels
        """
        return list(self.cache.label_to_table.keys())

    def get_table_fields(self, table_name: str) -> List[str]:
        """
        Get available fields for a Sentinel table.

        Args:
            table_name: Sentinel table name

        Returns:
            List of field names or empty list if not found

        Example:
            >>> mapper = SchemaMapper()
            >>> fields = mapper.get_table_fields('IdentityInfo')
            >>> assert 'AccountName' in fields
        """
        return self.cache.table_to_fields.get(table_name, [])

    def get_relationship_mapping(self, rel_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the join condition for a Cypher relationship.

        Args:
            rel_type: Cypher relationship type (e.g., 'LOGGED_IN')

        Returns:
            Dict with join information or None if not found

        Example:
            >>> mapper = SchemaMapper()
            >>> mapping = mapper.get_relationship_mapping('LOGGED_IN')
            >>> assert mapping['from_label'] == 'User'
        """
        return self.cache.relationship_to_join.get(rel_type)

    def get_relationships(self) -> List[str]:
        """
        Get all available relationship types.

        Returns:
            List of relationship type names

        Example:
            >>> mapper = SchemaMapper()
            >>> rels = mapper.get_relationships()
            >>> assert 'LOGGED_IN' in rels
        """
        return list(self.cache.relationship_to_join.keys())

    def get_property_field(
        self, cypher_label: str, property_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Get the Sentinel field mapping for a Cypher property.

        Args:
            cypher_label: Cypher node label
            property_name: Property name in Cypher

        Returns:
            Dict with 'sentinel_field', 'type', and 'required' keys, or None

        Example:
            >>> mapper = SchemaMapper()
            >>> field = mapper.get_property_field('User', 'username')
            >>> assert field['sentinel_field'] == 'AccountName'
        """
        if not self.schema:
            return None

        if cypher_label not in self.schema.nodes:
            return None

        node_mapping = self.schema.nodes[cypher_label]
        if property_name not in node_mapping.properties:
            return None

        prop_mapping = node_mapping.properties[property_name]
        return {
            "sentinel_field": prop_mapping.sentinel_field,
            "type": prop_mapping.type,
            "required": prop_mapping.required,
        }

    def get_all_properties(self, cypher_label: str) -> Dict[str, Dict[str, str]]:
        """
        Get all properties for a Cypher node label.

        Args:
            cypher_label: Cypher node label

        Returns:
            Dict mapping property names to field mappings

        Example:
            >>> mapper = SchemaMapper()
            >>> props = mapper.get_all_properties('User')
            >>> assert 'username' in props
        """
        if not self.schema or cypher_label not in self.schema.nodes:
            return {}

        node_mapping = self.schema.nodes[cypher_label]
        result = {}

        for prop_name, prop_mapping in node_mapping.properties.items():
            result[prop_name] = {
                "sentinel_field": prop_mapping.sentinel_field,
                "type": prop_mapping.type,
                "required": prop_mapping.required,
            }

        return result

    def find_path_tables(
        self, start_label: str, end_label: str
    ) -> Optional[Tuple[str, str]]:
        """
        Find Sentinel tables for path traversal.

        Given two Cypher labels, return the corresponding Sentinel tables.

        Args:
            start_label: Starting Cypher label
            end_label: Ending Cypher label

        Returns:
            Tuple of (start_table, end_table) or None if labels not found

        Example:
            >>> mapper = SchemaMapper()
            >>> tables = mapper.find_path_tables('User', 'Device')
            >>> assert tables == ('IdentityInfo', 'DeviceInfo')
        """
        start_table = self.get_sentinel_table(start_label)
        end_table = self.get_sentinel_table(end_label)

        if start_table and end_table:
            return (start_table, end_table)

        return None

    def find_relationships_between(
        self, from_label: str, to_label: str
    ) -> List[str]:
        """
        Find all relationship types between two labels.

        Args:
            from_label: Source node label
            to_label: Target node label

        Returns:
            List of relationship type names

        Example:
            >>> mapper = SchemaMapper()
            >>> rels = mapper.find_relationships_between('User', 'Device')
            >>> assert 'LOGGED_IN' in rels
        """
        if not self.schema:
            return []

        results = []
        for rel_type, edge_mapping in self.schema.edges.items():
            if (
                edge_mapping.from_label == from_label
                and edge_mapping.to_label == to_label
            ):
                results.append(rel_type)

        return results

    def get_join_condition(self, rel_type: str) -> Optional[str]:
        """
        Get the SQL join condition for a relationship.

        Args:
            rel_type: Relationship type

        Returns:
            SQL join condition or None if not found

        Example:
            >>> mapper = SchemaMapper()
            >>> condition = mapper.get_join_condition('LOGGED_IN')
            >>> assert 'IdentityInfo' in condition
        """
        mapping = self.get_relationship_mapping(rel_type)
        if mapping:
            return mapping.get("join_condition")
        return None

    def validate_schema(self) -> Dict[str, Any]:
        """
        Get validation results for the current schema.

        Returns:
            Dict with validation status and details

        Example:
            >>> mapper = SchemaMapper()
            >>> result = mapper.validate_schema()
            >>> assert result['is_valid']
        """
        if not self.schema:
            return {"is_valid": False, "errors": ["No schema loaded"]}

        result = self.validator.validate(self.schema)
        return {
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "node_count": result.node_count,
            "edge_count": result.edge_count,
            "table_count": result.table_count,
        }

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded schema.

        Returns:
            Dict with schema metadata

        Example:
            >>> mapper = SchemaMapper()
            >>> info = mapper.get_schema_info()
            >>> assert 'version' in info
        """
        if not self.schema:
            return {}

        return {
            "version": self.schema.version,
            "description": self.schema.description,
            "node_labels": list(self.cache.label_to_table.keys()),
            "relationship_types": list(self.cache.relationship_to_join.keys()),
            "sentinel_tables": list(self.cache.table_to_fields.keys()),
            "node_count": len(self.schema.nodes),
            "edge_count": len(self.schema.edges),
            "table_count": len(self.schema.tables),
        }
