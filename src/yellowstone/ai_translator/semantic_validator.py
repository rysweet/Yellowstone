"""Semantic validation for KQL translations.

This module provides:
- Semantic correctness validation for translated KQL
- Result equivalence checking
- Graph pattern validation
- Error detection and recovery suggestions
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from .models import SemanticValidationResult

logger = logging.getLogger(__name__)


class SemanticValidator:
    """Validates semantic correctness of KQL translations.

    Performs multiple validation checks to ensure translations
    are semantically correct and will produce expected results.

    Example:
        >>> validator = SemanticValidator()
        >>> result = validator.validate(
        ...     query="find all nodes with label 'Person'",
        ...     kql="graph.nodes | where labels has 'Person'"
        ... )
        >>> print(result.is_valid)
        True
    """

    # Valid KQL table sources
    VALID_TABLES = {"graph.nodes", "graph.edges", "graph.paths"}

    # Valid KQL operators
    VALID_OPERATORS = {
        "where", "project", "extend", "summarize", "join", "union",
        "count", "take", "limit", "sort", "order", "top", "distinct",
        "mv-expand", "parse", "parse-where", "sample",
    }

    # Valid comparison operators
    VALID_COMPARISONS = {
        "==", "!=", ">", "<", ">=", "<=", "=~", "!~",
        "contains", "has", "startswith", "endswith", "matches",
    }

    # Valid logical operators
    VALID_LOGICAL = {"and", "or", "not"}

    # Valid property prefixes
    VALID_PROPERTIES = {"properties.", "labels", "type", "source.", "target."}

    def __init__(self, strict_mode: bool = False):
        """Initialize semantic validator.

        Args:
            strict_mode: If True, apply stricter validation rules
        """
        self.strict_mode = strict_mode
        self._validation_count = 0
        self._error_count = 0

    def validate(
        self,
        query: str,
        kql: str,
        expected_result_type: Optional[str] = None,
    ) -> SemanticValidationResult:
        """Validate semantic correctness of KQL translation.

        Args:
            query: Original natural language query
            kql: Translated KQL query
            expected_result_type: Expected type of results (nodes/edges/paths/count)

        Returns:
            Validation result with errors and warnings
        """
        self._validation_count += 1

        errors: List[str] = []
        warnings: List[str] = []
        checks: List[str] = []

        # Basic syntax validation
        syntax_errors = self._validate_syntax(kql)
        errors.extend(syntax_errors)
        checks.append("syntax_check")

        # Table source validation
        table_errors, table_warnings = self._validate_tables(kql)
        errors.extend(table_errors)
        warnings.extend(table_warnings)
        checks.append("table_validation")

        # Operator validation
        op_errors, op_warnings = self._validate_operators(kql)
        errors.extend(op_errors)
        warnings.extend(op_warnings)
        checks.append("operator_validation")

        # Property validation
        prop_errors, prop_warnings = self._validate_properties(kql)
        errors.extend(prop_errors)
        warnings.extend(prop_warnings)
        checks.append("property_validation")

        # Query-KQL alignment validation
        align_errors, align_warnings = self._validate_alignment(query, kql)
        errors.extend(align_errors)
        warnings.extend(align_warnings)
        checks.append("alignment_validation")

        # Result type validation
        if expected_result_type:
            type_errors = self._validate_result_type(kql, expected_result_type)
            errors.extend(type_errors)
            checks.append("result_type_validation")

        # Graph pattern validation
        pattern_errors, pattern_warnings = self._validate_graph_patterns(kql)
        errors.extend(pattern_errors)
        warnings.extend(pattern_warnings)
        checks.append("graph_pattern_validation")

        # Calculate confidence
        is_valid = len(errors) == 0
        confidence = self._calculate_confidence(errors, warnings)

        if not is_valid:
            self._error_count += 1

        return SemanticValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            errors=errors,
            warnings=warnings,
            checks_performed=checks,
            metadata={
                "query": query,
                "kql": kql,
                "strict_mode": self.strict_mode,
            },
        )

    def _validate_syntax(self, kql: str) -> List[str]:
        """Validate basic KQL syntax.

        Args:
            kql: KQL query

        Returns:
            List of syntax errors
        """
        errors = []

        if not kql or not kql.strip():
            errors.append("KQL query is empty")
            return errors

        # Check for balanced parentheses
        if kql.count("(") != kql.count(")"):
            errors.append("Unbalanced parentheses in KQL")

        # Check for balanced quotes
        single_quotes = kql.count("'") - kql.count("\\'")
        double_quotes = kql.count('"') - kql.count('\\"')
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes in KQL")
        if double_quotes % 2 != 0:
            errors.append("Unbalanced double quotes in KQL")

        # Check for pipe operator consistency
        if "|" in kql:
            parts = kql.split("|")
            for part in parts:
                if not part.strip():
                    errors.append("Empty pipe operator segment in KQL")
                    break

        return errors

    def _validate_tables(self, kql: str) -> Tuple[List[str], List[str]]:
        """Validate table sources in KQL.

        Args:
            kql: KQL query

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Extract table references
        table_pattern = r"\b(graph\.\w+|\w+)\s*(\||$)"
        matches = re.finditer(table_pattern, kql.lower())

        found_tables = set()
        for match in matches:
            table = match.group(1)
            found_tables.add(table)

            if table.startswith("graph."):
                if table not in self.VALID_TABLES:
                    errors.append(f"Invalid table reference: {table}")
            elif self.strict_mode:
                warnings.append(f"Non-graph table reference: {table}")

        if not found_tables:
            errors.append("No table source found in KQL")

        return errors, warnings

    def _validate_operators(self, kql: str) -> Tuple[List[str], List[str]]:
        """Validate KQL operators.

        Args:
            kql: KQL query

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Extract operators (words after pipes)
        operator_pattern = r"\|\s*(\w+[\w-]*)"
        matches = re.finditer(operator_pattern, kql.lower())

        for match in matches:
            operator = match.group(1)
            if operator not in self.VALID_OPERATORS:
                if self.strict_mode:
                    errors.append(f"Unknown operator: {operator}")
                else:
                    warnings.append(f"Unknown operator (may be valid): {operator}")

        # Check for comparison operators
        for comp in self.VALID_COMPARISONS:
            if comp in kql.lower():
                # Verify comparison has both left and right operands
                comp_pattern = rf"\S+\s*{re.escape(comp)}\s*\S+"
                if not re.search(comp_pattern, kql, re.IGNORECASE):
                    warnings.append(f"Incomplete comparison with operator: {comp}")

        return errors, warnings

    def _validate_properties(self, kql: str) -> Tuple[List[str], List[str]]:
        """Validate property references in KQL.

        Args:
            kql: KQL query

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Find property references
        property_pattern = r"\b(properties\.\w+|labels|type|source\.\w+|target\.\w+)\b"
        matches = re.finditer(property_pattern, kql.lower())

        for match in matches:
            prop = match.group(1)

            # Check if property is properly prefixed
            has_valid_prefix = any(prop.startswith(prefix) for prefix in self.VALID_PROPERTIES)

            if not has_valid_prefix:
                if self.strict_mode:
                    errors.append(f"Invalid property reference: {prop}")
                else:
                    warnings.append(f"Property may need prefix: {prop}")

        # Check for 'labels has' pattern (common for node filtering)
        if "labels" in kql.lower():
            if "has" not in kql.lower() and "==" not in kql.lower():
                warnings.append("Labels property should typically use 'has' operator")

        return errors, warnings

    def _validate_alignment(self, query: str, kql: str) -> Tuple[List[str], List[str]]:
        """Validate query-KQL semantic alignment.

        Args:
            query: Natural language query
            kql: KQL query

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        query_lower = query.lower()
        kql_lower = kql.lower()

        # Check for node/edge/path alignment
        if "node" in query_lower and "graph.nodes" not in kql_lower:
            warnings.append("Query mentions 'nodes' but KQL doesn't use graph.nodes")
        if "edge" in query_lower and "graph.edges" not in kql_lower:
            warnings.append("Query mentions 'edges' but KQL doesn't use graph.edges")
        if "path" in query_lower and "graph.paths" not in kql_lower:
            warnings.append("Query mentions 'paths' but KQL doesn't use graph.paths")

        # Check for count alignment
        if any(word in query_lower for word in ["count", "how many", "number of"]):
            if "count" not in kql_lower and "summarize" not in kql_lower:
                warnings.append("Query asks for count but KQL doesn't include count operation")

        # Check for filtering alignment
        filter_keywords = ["with", "where", "having", "that have"]
        if any(keyword in query_lower for keyword in filter_keywords):
            if "where" not in kql_lower:
                warnings.append("Query suggests filtering but KQL doesn't include where clause")

        # Check for label/type alignment
        label_pattern = r"label\s+['\"](\w+)['\"]|type\s+['\"](\w+)['\"]"
        label_matches = re.finditer(label_pattern, query_lower)
        for match in label_matches:
            label = match.group(1) or match.group(2)
            if label.lower() not in kql_lower:
                warnings.append(f"Query mentions label/type '{label}' not found in KQL")

        # Check for name/property alignment
        name_pattern = r"named?\s+['\"](\w+)['\"]"
        name_matches = re.finditer(name_pattern, query_lower)
        for match in name_matches:
            name = match.group(1)
            if name.lower() not in kql_lower:
                warnings.append(f"Query mentions name '{name}' not found in KQL")

        return errors, warnings

    def _validate_result_type(self, kql: str, expected_type: str) -> List[str]:
        """Validate expected result type matches KQL.

        Args:
            kql: KQL query
            expected_type: Expected result type

        Returns:
            List of errors
        """
        errors = []
        kql_lower = kql.lower()

        if expected_type == "nodes" and "graph.nodes" not in kql_lower:
            errors.append(f"Expected nodes but KQL doesn't query graph.nodes")
        elif expected_type == "edges" and "graph.edges" not in kql_lower:
            errors.append(f"Expected edges but KQL doesn't query graph.edges")
        elif expected_type == "paths" and "graph.paths" not in kql_lower:
            errors.append(f"Expected paths but KQL doesn't query graph.paths")
        elif expected_type == "count" and "count" not in kql_lower:
            errors.append(f"Expected count but KQL doesn't include count operation")

        return errors

    def _validate_graph_patterns(self, kql: str) -> Tuple[List[str], List[str]]:
        """Validate graph-specific patterns in KQL.

        Args:
            kql: KQL query

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        kql_lower = kql.lower()

        # Check for common graph pattern mistakes
        if "graph.nodes" in kql_lower:
            # Nodes should typically filter by labels or properties
            if "where" not in kql_lower and "take" not in kql_lower:
                warnings.append("Node query without filtering may return too many results")

        if "graph.edges" in kql_lower:
            # Edges should typically filter by type
            if "where" not in kql_lower and "take" not in kql_lower:
                warnings.append("Edge query without filtering may return too many results")

        if "graph.paths" in kql_lower:
            # Paths should specify source and/or target
            if "source" not in kql_lower and "target" not in kql_lower:
                warnings.append("Path query should typically specify source or target")

        # Check for proper label syntax
        if "labels" in kql_lower:
            # Labels should use 'has' not '=='
            if "labels ==" in kql_lower:
                errors.append("Labels should use 'has' operator, not '=='")

        # Check for proper property access
        if "properties" in kql_lower:
            # Should be properties.field not properties['field']
            if "properties[" in kql_lower and self.strict_mode:
                warnings.append("Consider using properties.field instead of properties['field']")

        return errors, warnings

    def _calculate_confidence(self, errors: List[str], warnings: List[str]) -> float:
        """Calculate confidence score for validation.

        Args:
            errors: List of validation errors
            warnings: List of validation warnings

        Returns:
            Confidence score (0-1)
        """
        if errors:
            # Errors drastically reduce confidence
            return max(0.0, 0.3 - (len(errors) * 0.1))

        if warnings:
            # Warnings moderately reduce confidence
            return max(0.5, 1.0 - (len(warnings) * 0.1))

        # No errors or warnings = high confidence
        return 0.95

    def suggest_fix(self, validation_result: SemanticValidationResult) -> Optional[str]:
        """Suggest a fix for validation errors.

        Args:
            validation_result: Validation result with errors

        Returns:
            Suggested fix description or None
        """
        if validation_result.is_valid:
            return None

        errors = validation_result.errors
        kql = validation_result.metadata.get("kql", "")

        suggestions = []

        for error in errors:
            if "empty" in error.lower():
                suggestions.append("Generate a non-empty KQL query")
            elif "unbalanced" in error.lower():
                suggestions.append("Fix unbalanced quotes or parentheses")
            elif "invalid table" in error.lower():
                suggestions.append("Use valid table: graph.nodes, graph.edges, or graph.paths")
            elif "labels" in error.lower() and "==" in error:
                suggestions.append("Change 'labels ==' to 'labels has'")
            elif "no table source" in error.lower():
                suggestions.append("Add a table source (e.g., graph.nodes)")

        if suggestions:
            return "; ".join(suggestions)

        return "Review KQL syntax and semantic correctness"

    def get_statistics(self) -> Dict[str, int]:
        """Get validation statistics.

        Returns:
            Dictionary with validation counts
        """
        return {
            "total_validations": self._validation_count,
            "total_errors": self._error_count,
            "success_rate": (
                (self._validation_count - self._error_count) / self._validation_count
                if self._validation_count > 0
                else 0.0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset validation statistics."""
        self._validation_count = 0
        self._error_count = 0
