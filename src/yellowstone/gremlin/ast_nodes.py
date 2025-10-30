"""
Gremlin AST Node Classes

Data structures representing Gremlin traversal steps as an Abstract Syntax Tree.
These classes model the structure of Gremlin queries for translation purposes.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Step:
    """Base class for all Gremlin traversal steps."""

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}()"


@dataclass
class VertexStep(Step):
    """
    Represents g.V() or g.V(id1, id2, ...).

    Starting point for vertex-based traversals.
    """
    ids: list[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.ids:
            ids_str = ", ".join(str(i) for i in self.ids)
            return f"VertexStep(ids=[{ids_str}])"
        return "VertexStep()"


@dataclass
class EdgeStep(Step):
    """
    Represents g.E() or g.E(id1, id2, ...).

    Starting point for edge-based traversals.
    """
    ids: list[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.ids:
            ids_str = ", ".join(str(i) for i in self.ids)
            return f"EdgeStep(ids=[{ids_str}])"
        return "EdgeStep()"


@dataclass
class FilterStep(Step):
    """
    Represents filtering operations: has(), hasLabel(), is(), where().

    Filters elements in the traversal based on predicates.
    """
    predicate: str  # "has", "hasLabel", "is", "where"
    args: list[Any] = field(default_factory=list)

    def __post_init__(self):
        """Validate predicate type."""
        valid_predicates = {"has", "hasLabel", "is", "where"}
        if self.predicate not in valid_predicates:
            raise ValueError(
                f"Invalid predicate '{self.predicate}'. "
                f"Must be one of: {valid_predicates}"
            )

    def __repr__(self) -> str:
        args_str = ", ".join(repr(a) for a in self.args)
        return f"FilterStep(predicate='{self.predicate}', args=[{args_str}])"


@dataclass
class TraversalStep(Step):
    """
    Represents graph navigation steps: out(), in(), both(), outE(), inE(), bothE(), inV(), outV().

    Moves the traverser from current elements to adjacent vertices or edges.
    """
    direction: str  # "out", "in", "both", "outE", "inE", "bothE", "inV", "outV"
    edge_label: Optional[str] = None

    def __post_init__(self):
        """Validate direction."""
        valid_directions = {"out", "in", "both", "outE", "inE", "bothE", "inV", "outV"}
        if self.direction not in valid_directions:
            raise ValueError(
                f"Invalid direction '{self.direction}'. "
                f"Must be one of: {valid_directions}"
            )

    def __repr__(self) -> str:
        if self.edge_label:
            return f"TraversalStep(direction='{self.direction}', edge_label='{self.edge_label}')"
        return f"TraversalStep(direction='{self.direction}')"


@dataclass
class ProjectionStep(Step):
    """
    Represents data extraction: values(), project(), select().

    Projects or selects specific properties from graph elements.
    """
    type: str  # "values", "project", "select"
    properties: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate projection type."""
        valid_types = {"values", "project", "select"}
        if self.type not in valid_types:
            raise ValueError(
                f"Invalid projection type '{self.type}'. "
                f"Must be one of: {valid_types}"
            )

    def __repr__(self) -> str:
        props_str = ", ".join(f"'{p}'" for p in self.properties)
        return f"ProjectionStep(type='{self.type}', properties=[{props_str}])"


@dataclass
class LimitStep(Step):
    """
    Represents limit(n).

    Limits the number of results returned.
    """
    count: int

    def __post_init__(self):
        """Validate count is positive."""
        if self.count < 0:
            raise ValueError(f"Limit count must be non-negative, got {self.count}")

    def __repr__(self) -> str:
        return f"LimitStep(count={self.count})"


@dataclass
class OrderStep(Step):
    """
    Represents order().by(property).

    Orders results by specified property.
    """
    property: str
    ascending: bool = True

    def __repr__(self) -> str:
        direction = "asc" if self.ascending else "desc"
        return f"OrderStep(property='{self.property}', {direction})"


@dataclass
class GremlinTraversal:
    """
    Container for a complete Gremlin traversal.

    Represents a sequence of steps that form a complete query.
    """
    steps: list[Step] = field(default_factory=list)

    def __repr__(self) -> str:
        if not self.steps:
            return "GremlinTraversal(steps=[])"

        steps_str = ",\n    ".join(repr(step) for step in self.steps)
        return f"GremlinTraversal(steps=[\n    {steps_str}\n])"

    def add_step(self, step: Step) -> None:
        """Add a step to the traversal."""
        if not isinstance(step, Step):
            raise TypeError(f"Expected Step instance, got {type(step)}")
        self.steps.append(step)

    def to_gremlin_string(self) -> str:
        """
        Convert traversal to Gremlin query string.

        Returns a readable Gremlin query representation.
        """
        if not self.steps:
            return "g"

        parts = ["g"]

        for step in self.steps:
            if isinstance(step, VertexStep):
                if step.ids:
                    ids_str = ", ".join(str(i) for i in step.ids)
                    parts.append(f"V({ids_str})")
                else:
                    parts.append("V()")

            elif isinstance(step, EdgeStep):
                if step.ids:
                    ids_str = ", ".join(str(i) for i in step.ids)
                    parts.append(f"E({ids_str})")
                else:
                    parts.append("E()")

            elif isinstance(step, FilterStep):
                args_str = ", ".join(repr(a) for a in step.args)
                parts.append(f"{step.predicate}({args_str})")

            elif isinstance(step, TraversalStep):
                if step.edge_label:
                    parts.append(f"{step.direction}('{step.edge_label}')")
                else:
                    parts.append(f"{step.direction}()")

            elif isinstance(step, ProjectionStep):
                props_str = ", ".join(f"'{p}'" for p in step.properties)
                parts.append(f"{step.type}({props_str})")

            elif isinstance(step, LimitStep):
                parts.append(f"limit({step.count})")

            elif isinstance(step, OrderStep):
                order_str = "order().by('" + step.property + "'"
                if not step.ascending:
                    order_str += ", desc"
                order_str += ")"
                parts.append(order_str)

        return ".".join(parts)
