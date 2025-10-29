"""
Schema validation module for Cypher to Sentinel mappings.

Validates schema structure, consistency, and integrity.
"""

from typing import Dict, List, Set, Tuple
from .models import SchemaMapping, SchemaValidationResult


class SchemaValidator:
    """Validates schema mappings for correctness and completeness."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, schema: SchemaMapping) -> SchemaValidationResult:
        """
        Validate a complete schema mapping.

        Args:
            schema: SchemaMapping to validate

        Returns:
            SchemaValidationResult with validation status and any errors/warnings

        Example:
            >>> validator = SchemaValidator()
            >>> result = validator.validate(schema)
            >>> assert result.is_valid
        """
        self.errors = []
        self.warnings = []

        # Run all validation checks
        self._validate_basic_structure(schema)
        self._validate_node_mappings(schema)
        self._validate_edge_mappings(schema)
        self._validate_table_consistency(schema)
        self._validate_referential_integrity(schema)

        is_valid = len(self.errors) == 0

        return SchemaValidationResult(
            is_valid=is_valid,
            errors=self.errors,
            warnings=self.warnings,
            node_count=len(schema.nodes),
            edge_count=len(schema.edges),
            table_count=len(schema.tables),
        )

    def _validate_basic_structure(self, schema: SchemaMapping) -> None:
        """Validate basic schema structure."""
        if not schema.version:
            self.errors.append("Schema must have a version")

        if not schema.description:
            self.errors.append("Schema must have a description")

        if not schema.nodes:
            self.warnings.append("Schema has no node mappings")

        if not schema.edges:
            self.warnings.append("Schema has no edge mappings")

        if not schema.tables:
            self.warnings.append("Schema has no table metadata")

    def _validate_node_mappings(self, schema: SchemaMapping) -> None:
        """Validate node mapping definitions."""
        if not schema.nodes:
            return

        for label, mapping in schema.nodes.items():
            # Check for required fields
            if not mapping.sentinel_table:
                self.errors.append(f"Node '{label}' missing sentinel_table")

            # Validate property mappings
            if mapping.properties:
                for prop_name, prop_mapping in mapping.properties.items():
                    if not prop_mapping.sentinel_field:
                        self.errors.append(
                            f"Node '{label}' property '{prop_name}' missing sentinel_field"
                        )
                    if not prop_mapping.type:
                        self.errors.append(
                            f"Node '{label}' property '{prop_name}' missing type"
                        )

    def _validate_edge_mappings(self, schema: SchemaMapping) -> None:
        """Validate edge/relationship mapping definitions."""
        if not schema.edges:
            return

        for rel_type, mapping in schema.edges.items():
            # Check for required fields
            if not mapping.description:
                self.errors.append(f"Edge '{rel_type}' missing description")

            # Validate join conditions (except for generic ASSOCIATED_WITH)
            if rel_type != "ASSOCIATED_WITH":
                if not mapping.from_label:
                    self.errors.append(f"Edge '{rel_type}' missing from_label")
                if not mapping.to_label:
                    self.errors.append(f"Edge '{rel_type}' missing to_label")

            if mapping.sentinel_join:
                if (
                    mapping.from_label
                    and mapping.to_label
                    and not mapping.sentinel_join.join_condition
                ):
                    self.errors.append(
                        f"Edge '{rel_type}' has labels but missing join_condition"
                    )

    def _validate_table_consistency(self, schema: SchemaMapping) -> None:
        """Validate consistency between node mappings and table metadata."""
        if not schema.nodes or not schema.tables:
            return

        # Get all referenced tables
        referenced_tables: Set[str] = set()
        for node_mapping in schema.nodes.values():
            referenced_tables.add(node_mapping.sentinel_table)

        # Check for missing metadata
        for table_name in referenced_tables:
            if table_name not in schema.tables:
                self.warnings.append(
                    f"Table '{table_name}' referenced by nodes but missing from tables metadata"
                )

        # Check for unreferenced table metadata
        for table_name in schema.tables.keys():
            if table_name not in referenced_tables:
                self.warnings.append(
                    f"Table '{table_name}' defined in metadata but not referenced by any node"
                )

    def _validate_referential_integrity(self, schema: SchemaMapping) -> None:
        """Validate that edges reference existing node labels."""
        if not schema.edges or not schema.nodes:
            return

        node_labels = set(schema.nodes.keys())

        for rel_type, edge_mapping in schema.edges.items():
            # Skip validation for ASSOCIATED_WITH (generic relationship)
            if rel_type == "ASSOCIATED_WITH":
                continue

            if edge_mapping.from_label and edge_mapping.from_label not in node_labels:
                self.errors.append(
                    f"Edge '{rel_type}' references unknown from_label '{edge_mapping.from_label}'"
                )

            if edge_mapping.to_label and edge_mapping.to_label not in node_labels:
                self.errors.append(
                    f"Edge '{rel_type}' references unknown to_label '{edge_mapping.to_label}'"
                )

            # Validate join table references
            if edge_mapping.sentinel_join:
                join = edge_mapping.sentinel_join
                if join.left_table and join.left_table not in schema.tables:
                    self.warnings.append(
                        f"Edge '{rel_type}' references unknown table '{join.left_table}'"
                    )
                if join.right_table and join.right_table not in schema.tables:
                    self.warnings.append(
                        f"Edge '{rel_type}' references unknown table '{join.right_table}'"
                    )

    def validate_property_access(
        self, schema: SchemaMapping, label: str, property_name: str
    ) -> Tuple[bool, str]:
        """
        Validate that a property can be accessed for a given label.

        Args:
            schema: SchemaMapping to check against
            label: Cypher node label
            property_name: Property name to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, msg = validator.validate_property_access(schema, 'User', 'username')
            >>> assert is_valid
        """
        if label not in schema.nodes:
            return False, f"Unknown node label '{label}'"

        node_mapping = schema.nodes[label]
        if property_name not in node_mapping.properties:
            return False, f"Unknown property '{property_name}' for node '{label}'"

        return True, ""

    def validate_relationship(
        self, schema: SchemaMapping, rel_type: str, from_label: str, to_label: str
    ) -> Tuple[bool, str]:
        """
        Validate that a relationship exists and connects correct labels.

        Args:
            schema: SchemaMapping to check against
            rel_type: Relationship type (e.g., 'LOGGED_IN')
            from_label: Source node label
            to_label: Target node label

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, msg = validator.validate_relationship(schema, 'LOGGED_IN', 'User', 'Device')
            >>> assert is_valid
        """
        if rel_type not in schema.edges:
            return False, f"Unknown relationship type '{rel_type}'"

        edge_mapping = schema.edges[rel_type]

        # For generic ASSOCIATED_WITH, accept any labels
        if rel_type == "ASSOCIATED_WITH":
            return True, ""

        if edge_mapping.from_label and edge_mapping.from_label != from_label:
            return (
                False,
                f"Relationship '{rel_type}' expects from_label '{edge_mapping.from_label}', got '{from_label}'",
            )

        if edge_mapping.to_label and edge_mapping.to_label != to_label:
            return (
                False,
                f"Relationship '{rel_type}' expects to_label '{edge_mapping.to_label}', got '{to_label}'",
            )

        return True, ""

    def get_field_mapping(
        self, schema: SchemaMapping, label: str, property_name: str
    ) -> Dict[str, str]:
        """
        Get the sentinel field mapping for a property.

        Args:
            schema: SchemaMapping to check
            label: Cypher node label
            property_name: Property name

        Returns:
            Dict with 'sentinel_field' and 'type' keys

        Example:
            >>> mapping = validator.get_field_mapping(schema, 'User', 'username')
            >>> assert mapping['sentinel_field'] == 'AccountName'
        """
        if label not in schema.nodes:
            return {}

        node_mapping = schema.nodes[label]
        if property_name not in node_mapping.properties:
            return {}

        prop_mapping = node_mapping.properties[property_name]
        return {
            "sentinel_field": prop_mapping.sentinel_field,
            "type": prop_mapping.type,
            "required": prop_mapping.required,
        }
