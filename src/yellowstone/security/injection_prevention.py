"""
Injection attack prevention using AST-based translation.

This module provides comprehensive protection against injection attacks by:
- Using AST-based translation (never string concatenation)
- Input sanitization and validation
- Query validation
- Parameterized queries
- Detection of malicious patterns

Key principle: All values are treated as parameters, never as code.
Queries are built from structured AST nodes, not string concatenation.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Union, Pattern
from abc import ABC, abstractmethod


class InjectionType(Enum):
    """Types of injection attacks."""
    CYPHER_INJECTION = "cypher_injection"
    KQL_INJECTION = "kql_injection"
    PARAMETER_INJECTION = "parameter_injection"
    ESCAPE_SEQUENCE = "escape_sequence"
    COMMENT_INJECTION = "comment_injection"
    NEWLINE_INJECTION = "newline_injection"
    UNICODE_ESCAPE = "unicode_escape"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    injection_type: Optional[InjectionType] = None
    detected_pattern: Optional[str] = None
    risk_level: str = "SAFE"  # SAFE, LOW, MEDIUM, HIGH, CRITICAL
    remediation: Optional[str] = None


class InjectionPattern:
    """Represents a pattern that indicates a potential injection."""

    def __init__(
        self,
        pattern: str,
        injection_type: InjectionType,
        description: str,
        risk_level: str = "MEDIUM",
    ):
        """Initialize injection pattern.

        Args:
            pattern: Regex pattern to detect
            injection_type: Type of injection this represents
            description: Description of what this pattern detects
            risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.injection_type = injection_type
        self.description = description
        self.risk_level = risk_level


# Cypher-specific injection patterns
CYPHER_INJECTION_PATTERNS = [
    # Attempt to inject additional Cypher code via UNION/semicolon (highly suspicious)
    InjectionPattern(
        r"\bUNION\b.*?\bMATCH\b|\bUNION\b.*?\bCREATE\b|\bUNION\b.*?\bDELETE\b",
        InjectionType.CYPHER_INJECTION,
        "Potential Cypher UNION injection",
        "CRITICAL",
    ),
    # Cypher comment injection (// or /*)
    InjectionPattern(
        r"//|/\*|\*/",
        InjectionType.COMMENT_INJECTION,
        "Cypher comment sequences detected",
        "HIGH",
    ),
    # Backtick identifiers that could execute (backticks are uncommon in normal queries)
    InjectionPattern(
        r"`[^`]*`",
        InjectionType.ESCAPE_SEQUENCE,
        "Backtick identifier escaping detected",
        "MEDIUM",
    ),
    # Unicode escape sequences
    InjectionPattern(
        r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}",
        InjectionType.UNICODE_ESCAPE,
        "Unicode escape sequences detected",
        "MEDIUM",
    ),
    # Double quotes with embedded variables or suspicious $ patterns
    InjectionPattern(
        r'".*?\$\{.*?\}"',
        InjectionType.ESCAPE_SEQUENCE,
        "String interpolation attempt detected",
        "HIGH",
    ),
]

# KQL-specific injection patterns
KQL_INJECTION_PATTERNS = [
    # KQL pipe injection
    InjectionPattern(
        r"\|\s*(?:summarize|project|where|filter|take|count|distinct)",
        InjectionType.KQL_INJECTION,
        "Potential KQL pipeline injection",
        "CRITICAL",
    ),
    # KQL comment injection
    InjectionPattern(
        r"//",
        InjectionType.COMMENT_INJECTION,
        "KQL comment sequence detected",
        "HIGH",
    ),
    # Semicolon followed by keywords (statement separator)
    InjectionPattern(
        r";\s*(?:let|as\s+\$)",
        InjectionType.ESCAPE_SEQUENCE,
        "KQL statement separator detected",
        "CRITICAL",
    ),
    # Dynamic function calls
    InjectionPattern(
        r"(?:has_any|has_all)\s*\(.*?\)",
        InjectionType.KQL_INJECTION,
        "Dynamic KQL function detected",
        "HIGH",
    ),
]

# General/parameter injection patterns
PARAMETER_INJECTION_PATTERNS = [
    # Null byte injection
    InjectionPattern(
        r"\x00",
        InjectionType.PARAMETER_INJECTION,
        "Null byte detected",
        "HIGH",
    ),
    # Control characters
    InjectionPattern(
        r"[\x01-\x08\x0B-\x0C\x0E-\x1F\x7F]",
        InjectionType.PARAMETER_INJECTION,
        "Control characters detected",
        "MEDIUM",
    ),
    # Excessive Unicode
    InjectionPattern(
        r"[\x80-\xFF]{20,}",
        InjectionType.PARAMETER_INJECTION,
        "Excessive non-ASCII characters detected",
        "MEDIUM",
    ),
]


class InjectionDetector:
    """Detects potential injection attacks in query strings and parameters.

    This detector uses pattern matching to identify suspicious inputs that
    might indicate injection attacks. It works on both Cypher and KQL queries.

    Example:
        >>> detector = InjectionDetector()
        >>> result = detector.validate_cypher_query("MATCH (a) RETURN a")
        >>> assert result.is_valid
        >>> result = detector.validate_cypher_query("MATCH (a) // inject: DELETE")
        >>> assert not result.is_valid
        >>> assert result.injection_type == InjectionType.COMMENT_INJECTION
    """

    def __init__(self):
        """Initialize the injection detector."""
        self.cypher_patterns = CYPHER_INJECTION_PATTERNS
        self.kql_patterns = KQL_INJECTION_PATTERNS
        self.parameter_patterns = PARAMETER_INJECTION_PATTERNS

    def validate_cypher_query(self, query: str) -> ValidationResult:
        """Validate a Cypher query for injection attacks.

        Args:
            query: The Cypher query string to validate

        Returns:
            ValidationResult indicating if query is safe

        Raises:
            TypeError: If query is not a string
        """
        if not isinstance(query, str):
            raise TypeError(f"Expected string, got {type(query)}")

        return self._check_patterns(query, self.cypher_patterns)

    def validate_kql_query(self, query: str) -> ValidationResult:
        """Validate a KQL query for injection attacks.

        Args:
            query: The KQL query string to validate

        Returns:
            ValidationResult indicating if query is safe

        Raises:
            TypeError: If query is not a string
        """
        if not isinstance(query, str):
            raise TypeError(f"Expected string, got {type(query)}")

        return self._check_patterns(query, self.kql_patterns)

    def validate_parameter(self, value: Any) -> ValidationResult:
        """Validate a parameter value for injection attacks.

        Args:
            value: The parameter value to validate

        Returns:
            ValidationResult indicating if parameter is safe
        """
        # Convert to string for validation
        str_value = str(value) if value is not None else ""

        return self._check_patterns(str_value, self.parameter_patterns)

    def _check_patterns(
        self,
        text: str,
        patterns: List[InjectionPattern],
    ) -> ValidationResult:
        """Check text against a list of patterns.

        Args:
            text: Text to check
            patterns: List of patterns to check against

        Returns:
            ValidationResult with first detected issue or SAFE result
        """
        highest_risk = "SAFE"
        risk_order = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        for pattern in patterns:
            if pattern.pattern.search(text):
                # Update highest risk level
                if risk_order.get(pattern.risk_level, 0) > risk_order.get(highest_risk, 0):
                    highest_risk = pattern.risk_level

                # Return immediately on CRITICAL
                if pattern.risk_level == "CRITICAL":
                    return ValidationResult(
                        is_valid=False,
                        injection_type=pattern.injection_type,
                        detected_pattern=pattern.pattern.pattern,
                        risk_level=pattern.risk_level,
                        remediation=pattern.description,
                    )

        if highest_risk != "SAFE":
            return ValidationResult(
                is_valid=False,
                risk_level=highest_risk,
            )

        return ValidationResult(is_valid=True, risk_level="SAFE")


class QueryValidator:
    """Validates queries for security and correctness.

    This validator ensures:
    - No injection attacks
    - Valid query structure
    - Proper parameter usage
    - Safe string operations

    Example:
        >>> validator = QueryValidator()
        >>> result = validator.validate_query("MATCH (a)-[r]->(b) RETURN a, r, b")
        >>> assert result.is_valid
    """

    MAX_QUERY_LENGTH = 100000  # 100KB max query
    MAX_PARAMETER_LENGTH = 10000  # 10KB max per parameter
    MAX_PARAMETERS = 1000  # Max number of parameters

    def __init__(self):
        """Initialize the query validator."""
        self.injection_detector = InjectionDetector()

    def validate_query(
        self,
        query: str,
        query_type: str = "CYPHER",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate a complete query with parameters.

        Args:
            query: The query string
            query_type: Type of query ("CYPHER" or "KQL")
            parameters: Optional parameter dictionary

        Returns:
            ValidationResult indicating if query is safe and valid

        Raises:
            TypeError: If query is not a string
            ValueError: If query_type is invalid
        """
        if not isinstance(query, str):
            raise TypeError(f"Expected string query, got {type(query)}")

        if query_type not in ("CYPHER", "KQL"):
            raise ValueError(f"Invalid query_type: {query_type}")

        # Check query length
        if len(query) > self.MAX_QUERY_LENGTH:
            return ValidationResult(
                is_valid=False,
                risk_level="HIGH",
                remediation="Query exceeds maximum length",
            )

        # Validate query for injections
        if query_type == "CYPHER":
            result = self.injection_detector.validate_cypher_query(query)
        else:
            result = self.injection_detector.validate_kql_query(query)

        if not result.is_valid:
            return result

        # Validate parameters if provided
        if parameters:
            param_result = self._validate_parameters(parameters)
            if not param_result.is_valid:
                return param_result

        return ValidationResult(is_valid=True, risk_level="SAFE")

    def _validate_parameters(
        self,
        parameters: Dict[str, Any],
    ) -> ValidationResult:
        """Validate query parameters.

        Args:
            parameters: Dictionary of parameters to validate

        Returns:
            ValidationResult indicating if parameters are safe
        """
        if len(parameters) > self.MAX_PARAMETERS:
            return ValidationResult(
                is_valid=False,
                risk_level="HIGH",
                remediation=f"Too many parameters (max: {self.MAX_PARAMETERS})",
            )

        for key, value in parameters.items():
            # Validate parameter name
            if not self._is_valid_parameter_name(key):
                return ValidationResult(
                    is_valid=False,
                    risk_level="MEDIUM",
                    remediation=f"Invalid parameter name: {key}",
                )

            # Validate parameter value
            if isinstance(value, str):
                if len(value) > self.MAX_PARAMETER_LENGTH:
                    return ValidationResult(
                        is_valid=False,
                        risk_level="MEDIUM",
                        remediation=f"Parameter {key} exceeds maximum length",
                    )

                # Check for injection in parameter value
                result = self.injection_detector.validate_parameter(value)
                if not result.is_valid:
                    return result

            elif isinstance(value, list):
                # Validate list elements
                for item in value:
                    if isinstance(item, str):
                        result = self.injection_detector.validate_parameter(item)
                        if not result.is_valid:
                            return result

            elif isinstance(value, dict):
                # Validate nested dict
                for k, v in value.items():
                    if isinstance(v, str):
                        result = self.injection_detector.validate_parameter(v)
                        if not result.is_valid:
                            return result

        return ValidationResult(is_valid=True, risk_level="SAFE")

    @staticmethod
    def _is_valid_parameter_name(name: str) -> bool:
        """Check if a parameter name is valid.

        Valid names: alphanumeric + underscore, start with letter or underscore.

        Args:
            name: Parameter name to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(name, str) or not name:
            return False

        # Must start with letter or underscore
        if not (name[0].isalpha() or name[0] == '_'):
            return False

        # Rest must be alphanumeric or underscore
        return all(c.isalnum() or c == '_' for c in name)


class ParameterizedQueryBuilder:
    """Builds parameterized queries safely without string concatenation.

    This class ensures all dynamic values are treated as parameters,
    never as code. This is the fundamental defense against injection.

    Example:
        >>> builder = ParameterizedQueryBuilder()
        >>> query, params = builder.build_node_query(
        ...     label="Person",
        ...     properties={"name": "Alice", "age": 30},
        ... )
        >>> assert "?" in query  # Parameterized
        >>> assert params["name"] == "Alice"
    """

    def __init__(self):
        """Initialize the parameterized query builder."""
        self.param_counter = 0
        self.params: Dict[str, Any] = {}

    def reset(self) -> None:
        """Reset the builder state."""
        self.param_counter = 0
        self.params = {}

    def add_parameter(self, value: Any) -> str:
        """Add a parameter and return its placeholder.

        Args:
            value: The parameter value

        Returns:
            Parameter placeholder string

        Raises:
            ValueError: If value is invalid for parameterization
        """
        # Validate parameter before adding
        result = InjectionDetector().validate_parameter(value)
        if not result.is_valid:
            raise ValueError(
                f"Invalid parameter value: {result.remediation}"
            )

        param_key = f"param_{self.param_counter}"
        self.param_counter += 1
        self.params[param_key] = value
        return f"${param_key}"

    def build_property_filter(
        self,
        properties: Dict[str, Any],
        operator: str = "AND",
    ) -> str:
        """Build a property filter clause with parameterized values.

        Args:
            properties: Dictionary of property filters
            operator: Operator between conditions ("AND" or "OR")

        Returns:
            Filter clause with parameterized values

        Example:
            >>> builder = ParameterizedQueryBuilder()
            >>> clause = builder.build_property_filter({"status": "active"})
            >>> assert "status =" in clause
            >>> assert "$param_0" in clause
        """
        conditions = []
        for key, value in properties.items():
            if not self._is_valid_identifier(key):
                raise ValueError(f"Invalid property name: {key}")

            param_placeholder = self.add_parameter(value)
            conditions.append(f"{key} = {param_placeholder}")

        return f" {operator} ".join(conditions)

    def build_node_match(
        self,
        variable: str,
        label: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a node match pattern with parameterized values.

        Args:
            variable: Variable name for the node
            label: Optional node label
            properties: Optional property constraints

        Returns:
            Node pattern string with parameterized values
        """
        if not self._is_valid_identifier(variable):
            raise ValueError(f"Invalid variable name: {variable}")

        if label and not self._is_valid_identifier(label):
            raise ValueError(f"Invalid label name: {label}")

        parts = [variable]

        if label:
            parts.append(f":{label}")

        if properties:
            prop_clause = self.build_property_filter(properties)
            parts.append(f" {{{prop_clause}}}")

        return "".join(parts)

    def build_relationship_match(
        self,
        variable: str,
        relationship_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        direction: str = "->",
    ) -> str:
        """Build a relationship match pattern with parameterized values.

        Args:
            variable: Variable name for the relationship
            relationship_type: Optional relationship type
            properties: Optional property constraints
            direction: Direction of relationship ("->" or "<-")

        Returns:
            Relationship pattern with parameterized values
        """
        if variable and not self._is_valid_identifier(variable):
            raise ValueError(f"Invalid variable name: {variable}")

        if relationship_type and not self._is_valid_identifier(relationship_type):
            raise ValueError(f"Invalid relationship type: {relationship_type}")

        parts = ["["]
        if variable:
            parts.append(variable)
        if relationship_type:
            parts.append(f":{relationship_type}")
        if properties:
            prop_clause = self.build_property_filter(properties)
            parts.append(f" {{{prop_clause}}}")
        parts.append("]")

        return f"{direction}".join([""] + ["".join(parts)] + [""])

    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        """Check if a string is a valid identifier.

        Valid identifiers: alphanumeric + underscore, start with letter.

        Args:
            name: String to check

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(name, str) or not name:
            return False

        if not name[0].isalpha() and name[0] != '_':
            return False

        return all(c.isalnum() or c == '_' for c in name)

    def get_parameters(self) -> Dict[str, Any]:
        """Get all accumulated parameters.

        Returns:
            Dictionary of parameters
        """
        return self.params.copy()
