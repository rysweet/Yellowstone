"""
Gremlin-to-Cypher Bridge Module

Translates Gremlin AST (from gremlin.ast_nodes) to Cypher AST (from parser.ast_nodes).

This module provides the core translation logic from Gremlin graph traversals to
equivalent Cypher queries, enabling Gremlin clients to work with Neptune Analytics.

Translation Strategy:
1. Collect Information - Scan all steps to understand query intent
2. Build MATCH Clause - Convert traversal patterns to Cypher path patterns
3. Build WHERE Clause - Convert filter steps to Cypher predicates
4. Build RETURN Clause - Convert projection steps to Cypher return items

Example:
    >>> from yellowstone.gremlin.parser import parse_gremlin
    >>> from yellowstone.gremlin.cypher_bridge import translate_gremlin_to_cypher
    >>>
    >>> # g.V().hasLabel('User').has('age', 30)
    >>> traversal = parse_gremlin("g.V().hasLabel('User').has('age',30)")
    >>>
    >>> query = translate_gremlin_to_cypher(traversal)
    >>> # Returns: MATCH (v:User) WHERE v.age = 30 RETURN v
"""

from typing import Any, Optional

from yellowstone.gremlin.ast import (
    GremlinTraversal,
    Step,
    VertexStep,
    EdgeStep,
    FilterStep,
    TraversalStep,
    ProjectionStep,
    LimitStep,
    OrderStep,
)

from yellowstone.parser.ast_nodes import (
    Query,
    MatchClause,
    WhereClause,
    ReturnClause,
    PathExpression,
    NodePattern,
    RelationshipPattern,
    Identifier,
    Literal,
    Property,
)


class TranslationError(Exception):
    """Raised when Gremlin traversal cannot be translated to Cypher."""
    pass


class UnsupportedPatternError(TranslationError):
    """Raised when encountering unsupported Gremlin patterns."""
    pass


class TranslationContext:
    """
    Maintains state during translation from Gremlin to Cypher.

    Tracks variables, labels, filters, and other elements needed to build
    the Cypher query AST.

    Attributes:
        node_counter: Counter for generating unique node variable names (v0, v1, v2, ...)
        current_variable: The currently active node variable
        node_labels: Dictionary mapping variables to their labels
        filters: List of filter conditions to become WHERE clause
        traversal_chain: List of nodes and relationships for MATCH pattern
        projection: Projection step (values, project, select) if present
        limit: Limit value if present
        order_by: Order specification if present
    """

    def __init__(self):
        self.node_counter = 0
        self.current_variable: Optional[str] = None
        self.node_labels: dict[str, str] = {}
        self.filters: list[dict[str, Any]] = []
        self.traversal_chain: list[Any] = []  # Nodes and relationships
        self.projection: Optional[ProjectionStep] = None
        self.limit: Optional[int] = None
        self.order_by: Optional[OrderStep] = None

    def new_variable(self) -> str:
        """Generate a new unique node variable name."""
        var = f"v{self.node_counter}"
        self.node_counter += 1
        self.current_variable = var
        return var

    def get_current_variable(self) -> str:
        """Get the current active variable, creating one if needed."""
        if self.current_variable is None:
            return self.new_variable()
        return self.current_variable


def translate_gremlin_to_cypher(traversal: GremlinTraversal) -> Query:
    """
    Translate a Gremlin traversal to a Cypher query AST.

    Args:
        traversal: The Gremlin traversal to translate

    Returns:
        A Query object representing the equivalent Cypher query

    Raises:
        TranslationError: If the traversal cannot be translated
        UnsupportedPatternError: If the traversal uses unsupported patterns

    Example:
        >>> traversal = GremlinTraversal(steps=[
        ...     VertexStep(),
        ...     FilterStep(predicate='hasLabel', args=['Person']),
        ...     FilterStep(predicate='has', args=['name', 'John'])
        ... ])
        >>> query = translate_gremlin_to_cypher(traversal)
    """
    if not traversal.steps:
        raise TranslationError("Empty traversal - no steps to translate")

    # Validate starting step
    first_step = traversal.steps[0]
    if not isinstance(first_step, (VertexStep, EdgeStep)):
        raise TranslationError(
            f"Traversal must start with V() or E(), got {type(first_step).__name__}"
        )

    if isinstance(first_step, EdgeStep):
        raise UnsupportedPatternError(
            "Edge starting point E() not yet supported - start with V() instead"
        )

    # Create translation context
    ctx = TranslationContext()

    # Process all steps to collect information
    _collect_information(traversal.steps, ctx)

    # Build AST components
    match_clause = _build_match_clause(ctx)
    where_clause = _build_where_clause(ctx)
    return_clause = _build_return_clause(ctx)

    # Construct final query
    query = Query(
        match_clause=match_clause,
        where_clause=where_clause,
        return_clause=return_clause
    )

    return query


def _collect_information(steps: list[Step], ctx: TranslationContext) -> None:
    """
    Scan all steps to understand query intent and collect information.

    This first pass identifies:
    - Starting point (VertexStep/EdgeStep)
    - Labels from hasLabel filters
    - Property filters from has() steps
    - Traversal patterns from out/in/both steps
    - Projections from values/project/select
    - Modifiers like limit and order

    Args:
        steps: List of Gremlin steps
        ctx: Translation context to populate
    """
    # Start with initial vertex
    initial_var = ctx.new_variable()

    for i, step in enumerate(steps):
        if isinstance(step, VertexStep):
            # Initial vertex step - already handled
            if i > 0:
                raise UnsupportedPatternError(
                    "Multiple V() steps not supported - use single starting point"
                )
            continue

        elif isinstance(step, FilterStep):
            _process_filter_step(step, ctx)

        elif isinstance(step, TraversalStep):
            _process_traversal_step(step, ctx)

        elif isinstance(step, ProjectionStep):
            if ctx.projection is not None:
                raise UnsupportedPatternError(
                    "Multiple projection steps not supported"
                )
            ctx.projection = step

        elif isinstance(step, LimitStep):
            if ctx.limit is not None:
                raise UnsupportedPatternError(
                    "Multiple limit steps not supported"
                )
            ctx.limit = step.count

        elif isinstance(step, OrderStep):
            if ctx.order_by is not None:
                raise UnsupportedPatternError(
                    "Multiple order steps not supported"
                )
            ctx.order_by = step

        else:
            raise UnsupportedPatternError(
                f"Unsupported step type: {type(step).__name__}"
            )


def _process_filter_step(step: FilterStep, ctx: TranslationContext) -> None:
    """
    Process a FilterStep and update context.

    Handles:
    - hasLabel('Label') -> adds label to current node
    - has('property', value) -> adds filter condition

    Args:
        step: The FilterStep to process
        ctx: Translation context
    """
    current_var = ctx.get_current_variable()

    if step.filter_type == 'hasLabel':
        label = step.value.value if step.value else None
        if not label:
            raise TranslationError("hasLabel requires a label argument")
        if not isinstance(label, str):
            raise TranslationError(f"hasLabel argument must be string, got {type(label)}")

        # Store label for current variable
        if current_var in ctx.node_labels:
            raise UnsupportedPatternError(
                f"Multiple labels on same node not yet supported (variable: {current_var})"
            )
        ctx.node_labels[current_var] = label

    elif step.filter_type == 'has':
        if not step.property_name:
            raise TranslationError("has requires a property name")
        property_name = step.property_name
        value = step.value.value if step.value else None
        if not isinstance(property_name, str):
            raise TranslationError(
                f"has property name must be string, got {type(property_name)}"
            )

        # Create filter condition
        filter_condition = {
            'type': 'comparison',
            'operator': '=',
            'left': {
                'type': 'property',
                'variable': current_var,
                'property': property_name
            },
            'right': _value_to_literal_dict(value)
        }
        ctx.filters.append(filter_condition)

    else:
        raise UnsupportedPatternError(
            f"Filter predicate '{step.filter_type}' not yet supported. "
            f"Supported: hasLabel, has"
        )


def _process_traversal_step(step: TraversalStep, ctx: TranslationContext) -> None:
    """
    Process a TraversalStep and update context.

    Handles:
    - out('LABEL') -> creates outgoing relationship pattern
    - in('LABEL') -> creates incoming relationship pattern
    - both('LABEL') -> creates undirected relationship pattern

    Args:
        step: The TraversalStep to process
        ctx: Translation context
    """
    if step.direction not in ['out', 'in', 'both']:
        raise UnsupportedPatternError(
            f"Traversal direction '{step.direction}' not yet supported. "
            f"Supported: out, in, both"
        )

    # Save current node before creating relationship
    source_var = ctx.get_current_variable()

    # Create relationship pattern
    rel_type = step.edge_label
    direction_map = {
        'out': 'out',
        'in': 'in',
        'both': 'both'
    }

    relationship = RelationshipPattern(
        variable=None,  # Don't bind relationship to variable for now
        relationship_type=Identifier(name=rel_type) if rel_type else None,
        directed=(step.direction != 'both'),
        direction=direction_map[step.direction]
    )

    # Create new target node
    target_var = ctx.new_variable()

    # Store pattern for later MATCH construction
    ctx.traversal_chain.append({
        'source': source_var,
        'relationship': relationship,
        'target': target_var
    })


def _value_to_literal_dict(value: Any) -> dict[str, Any]:
    """
    Convert a Python value to a literal dictionary representation.

    Args:
        value: Python value to convert

    Returns:
        Dictionary with 'type', 'value', and 'value_type' keys
    """
    if isinstance(value, str):
        return {
            'type': 'literal',
            'value': value,
            'value_type': 'string'
        }
    elif isinstance(value, bool):
        return {
            'type': 'literal',
            'value': value,
            'value_type': 'boolean'
        }
    elif isinstance(value, (int, float)):
        return {
            'type': 'literal',
            'value': value,
            'value_type': 'number'
        }
    elif value is None:
        return {
            'type': 'literal',
            'value': None,
            'value_type': 'null'
        }
    else:
        raise TranslationError(
            f"Unsupported value type: {type(value).__name__}"
        )


def _build_match_clause(ctx: TranslationContext) -> MatchClause:
    """
    Build the MATCH clause from collected information.

    Creates path expressions from traversal chains, including node patterns
    with labels and relationship patterns.

    Args:
        ctx: Translation context with collected information

    Returns:
        MatchClause containing the path patterns
    """
    if not ctx.traversal_chain:
        # Simple case: single node with optional label
        var = ctx.get_current_variable()
        label = ctx.node_labels.get(var)

        node = NodePattern(
            variable=Identifier(name=var),
            labels=[Identifier(name=label)] if label else []
        )

        path = PathExpression(
            nodes=[node],
            relationships=[]
        )

        return MatchClause(paths=[path], optional=False)

    # Complex case: traversal chain with relationships
    nodes = []
    relationships = []

    # Add first node
    first_var = f"v0"
    first_label = ctx.node_labels.get(first_var)
    nodes.append(NodePattern(
        variable=Identifier(name=first_var),
        labels=[Identifier(name=first_label)] if first_label else []
    ))

    # Add relationships and subsequent nodes
    for chain_item in ctx.traversal_chain:
        relationships.append(chain_item['relationship'])

        target_var = chain_item['target']
        target_label = ctx.node_labels.get(target_var)
        nodes.append(NodePattern(
            variable=Identifier(name=target_var),
            labels=[Identifier(name=target_label)] if target_label else []
        ))

    path = PathExpression(
        nodes=nodes,
        relationships=relationships
    )

    # Validate path structure
    path.validate_structure()

    return MatchClause(paths=[path], optional=False)


def _build_where_clause(ctx: TranslationContext) -> Optional[WhereClause]:
    """
    Build the WHERE clause from collected filter conditions.

    Args:
        ctx: Translation context with collected filters

    Returns:
        WhereClause if filters exist, None otherwise
    """
    if not ctx.filters:
        return None

    if len(ctx.filters) == 1:
        # Single condition
        return WhereClause(conditions=ctx.filters[0])

    # Multiple conditions - combine with AND
    conditions = {
        'type': 'logical',
        'operator': 'AND',
        'operands': ctx.filters
    }

    return WhereClause(conditions=conditions)


def _build_return_clause(ctx: TranslationContext) -> ReturnClause:
    """
    Build the RETURN clause from projection step or default to returning current variable.

    Args:
        ctx: Translation context with optional projection

    Returns:
        ReturnClause with appropriate return items
    """
    return_items = []

    if ctx.projection:
        current_var = ctx.get_current_variable()

        if ctx.projection.projection_type == 'values':
            # values('prop1', 'prop2') -> RETURN v.prop1, v.prop2
            for prop_name in ctx.projection.property_names:
                return_items.append(Property(
                    variable=Identifier(name=current_var),
                    property_name=Identifier(name=prop_name)
                ))
        else:
            raise UnsupportedPatternError(
                f"Projection type '{ctx.projection.projection_type}' not yet supported. "
                f"Supported: values"
            )
    else:
        # No projection - return current variable
        current_var = ctx.get_current_variable()
        return_items.append(Identifier(name=current_var))

    # Build order_by if present
    order_by_spec = None
    if ctx.order_by:
        current_var = ctx.get_current_variable()
        order_by_spec = [{
            'expression': {
                'type': 'property',
                'variable': current_var,
                'property': ctx.order_by.order_by
            },
            'direction': 'ASC' if ctx.order_by.order == 'asc' else 'DESC'
        }]

    return ReturnClause(
        items=return_items,
        distinct=False,
        order_by=order_by_spec,
        limit=ctx.limit
    )
