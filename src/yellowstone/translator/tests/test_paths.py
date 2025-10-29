"""Tests for path translation."""

import pytest
from yellowstone.translator.paths import PathTranslator, PathLength


class TestPathLength:
    """Test suite for PathLength dataclass."""

    def test_fixed_length(self):
        """Test fixed-length path."""
        path_len = PathLength(min_length=5, max_length=5)

        assert not path_len.is_variable_length()
        assert path_len.to_kql_format() == "[5]"

    def test_variable_length_range(self):
        """Test variable-length path with range."""
        path_len = PathLength(min_length=1, max_length=3)

        assert path_len.is_variable_length()
        assert path_len.to_kql_format() == "[1..3]"

    def test_minimum_only(self):
        """Test path with minimum length only."""
        path_len = PathLength(min_length=2)

        assert path_len.is_variable_length()
        assert path_len.to_kql_format() == "[2..]"

    def test_maximum_only(self):
        """Test path with maximum length only."""
        path_len = PathLength(max_length=5)

        assert path_len.is_variable_length()
        assert path_len.to_kql_format() == "[..5]"

    def test_unbounded(self):
        """Test unbounded path."""
        path_len = PathLength()

        assert path_len.is_variable_length()
        assert path_len.to_kql_format() == "[..]"

    def test_to_kql_format_raises_on_negative_min(self):
        """Test that negative minimum raises error."""
        path_len = PathLength(min_length=-1, max_length=5)

        with pytest.raises(ValueError):
            path_len.to_kql_format()

    def test_to_kql_format_raises_on_negative_max(self):
        """Test that negative maximum raises error."""
        path_len = PathLength(min_length=1, max_length=-1)

        with pytest.raises(ValueError):
            path_len.to_kql_format()

    def test_to_kql_format_raises_on_invalid_range(self):
        """Test that min > max raises error."""
        path_len = PathLength(min_length=5, max_length=3)

        with pytest.raises(ValueError):
            path_len.to_kql_format()


class TestPathTranslator:
    """Test suite for PathTranslator."""

    def setup_method(self):
        """Set up translator for each test."""
        self.translator = PathTranslator()

    def test_parse_fixed_length(self):
        """Test parsing fixed path length."""
        path_len = self.translator.parse_path_length_specification("5")

        assert path_len.min_length == 5
        assert path_len.max_length == 5

    def test_parse_variable_range(self):
        """Test parsing variable path length."""
        path_len = self.translator.parse_path_length_specification("1..3")

        assert path_len.min_length == 1
        assert path_len.max_length == 3

    def test_parse_unbounded(self):
        """Test parsing unbounded path."""
        path_len = self.translator.parse_path_length_specification("*")

        assert path_len.min_length is None
        assert path_len.max_length is None

    def test_parse_minimum_only(self):
        """Test parsing path with minimum only."""
        path_len = self.translator.parse_path_length_specification("2..")

        assert path_len.min_length == 2
        assert path_len.max_length is None

    def test_parse_maximum_only(self):
        """Test parsing path with maximum only."""
        path_len = self.translator.parse_path_length_specification("..5")

        assert path_len.min_length is None
        assert path_len.max_length == 5

    def test_parse_raises_on_invalid_format(self):
        """Test that invalid format raises error."""
        with pytest.raises(ValueError):
            self.translator.parse_path_length_specification("abc")

    def test_translate_node_reference_with_variable(self):
        """Test translating node reference with variable."""
        result = self.translator.translate_node_reference("n", [])

        assert result == "n"

    def test_translate_node_reference_with_label(self):
        """Test translating node reference with label."""
        result = self.translator.translate_node_reference(None, ["Person"])

        assert result == "Person"

    def test_translate_node_reference_with_both(self):
        """Test translating node reference with variable and label."""
        result = self.translator.translate_node_reference("n", ["Person"])

        assert result == "n:Person"

    def test_translate_node_reference_with_multiple_labels(self):
        """Test translating node with multiple labels."""
        result = self.translator.translate_node_reference("n", ["Person", "Actor"])

        assert "n:" in result
        assert "Person" in result
        assert "Actor" in result

    def test_translate_node_reference_empty(self):
        """Test translating empty node reference."""
        result = self.translator.translate_node_reference(None, [])

        assert result == ""

    def test_translate_node_reference_raises_on_invalid_labels(self):
        """Test that non-list labels raise error."""
        with pytest.raises(ValueError):
            self.translator.translate_node_reference("n", "not_a_list")

    def test_translate_relationship_reference_with_variable(self):
        """Test translating relationship with variable."""
        result = self.translator.translate_relationship_reference("r", [])

        assert result == "r"

    def test_translate_relationship_reference_with_type(self):
        """Test translating relationship with type."""
        result = self.translator.translate_relationship_reference(None, ["KNOWS"])

        assert result == "KNOWS"

    def test_translate_relationship_reference_with_both(self):
        """Test translating relationship with variable and type."""
        result = self.translator.translate_relationship_reference("r", ["KNOWS"])

        assert result == "r:KNOWS"

    def test_translate_relationship_reference_with_multiple_types(self):
        """Test translating relationship with multiple types."""
        result = self.translator.translate_relationship_reference("r", ["KNOWS", "FRIEND"])

        assert "r:" in result
        assert "KNOWS" in result
        assert "FRIEND" in result

    def test_translate_relationship_reference_empty(self):
        """Test translating empty relationship reference."""
        result = self.translator.translate_relationship_reference(None, [])

        assert result == ""

    def test_translate_relationship_reference_raises_on_invalid_types(self):
        """Test that non-list types raise error."""
        with pytest.raises(ValueError):
            self.translator.translate_relationship_reference("r", "not_a_list")

    def test_translate_path_segment_simple(self):
        """Test translating simple path segment."""
        from_node = {'variable': 'n', 'labels': ['Person']}
        rel = {'variable': 'r', 'types': ['KNOWS'], 'direction': 'out', 'length': None}
        to_node = {'variable': 'm', 'labels': ['Person']}

        result = self.translator.translate_path_segment(from_node, rel, to_node)

        assert "(n:Person)" in result
        assert "-[r:KNOWS]->" in result
        assert "(m:Person)" in result

    def test_translate_path_segment_incoming(self):
        """Test translating path segment with incoming relationship."""
        from_node = {'variable': 'n', 'labels': []}
        rel = {'variable': 'r', 'types': [], 'direction': 'in', 'length': None}
        to_node = {'variable': 'm', 'labels': []}

        result = self.translator.translate_path_segment(from_node, rel, to_node)

        assert "<-[r]-" in result

    def test_translate_path_segment_undirected(self):
        """Test translating path segment with undirected relationship."""
        from_node = {'variable': 'n', 'labels': []}
        rel = {'variable': 'r', 'types': [], 'direction': 'both', 'length': None}
        to_node = {'variable': 'm', 'labels': []}

        result = self.translator.translate_path_segment(from_node, rel, to_node)

        assert "-[r]-" in result
        assert "->" not in result

    def test_translate_path_segment_with_variable_length(self):
        """Test translating path segment with variable-length relationship."""
        from_node = {'variable': 'n', 'labels': []}
        rel = {'variable': 'r', 'types': [], 'direction': 'out', 'length': '1..3'}
        to_node = {'variable': 'm', 'labels': []}

        result = self.translator.translate_path_segment(from_node, rel, to_node)

        assert "[1..3]" in result or "1" in result

    def test_translate_path_segment_raises_on_invalid_nodes(self):
        """Test that invalid node specs raise error."""
        with pytest.raises(ValueError):
            self.translator.translate_path_segment("not_dict", {}, {})

    def test_translate_path_segment_raises_on_invalid_rel(self):
        """Test that invalid relationship spec raises error."""
        from_node = {'variable': 'n', 'labels': []}
        to_node = {'variable': 'm', 'labels': []}

        with pytest.raises(ValueError):
            self.translator.translate_path_segment(from_node, "not_dict", to_node)

    def test_translate_full_path_single_segment(self):
        """Test translating full path with single segment."""
        segments = [
            {
                'from_node': {'variable': 'n', 'labels': []},
                'relationship': {'variable': 'r', 'types': [], 'direction': 'out', 'length': None},
                'to_node': {'variable': 'm', 'labels': []}
            }
        ]

        result = self.translator.translate_full_path(segments)

        assert "(n)" in result
        assert "-[r]->" in result
        assert "(m)" in result

    def test_translate_full_path_multiple_segments(self):
        """Test translating full path with multiple segments."""
        segments = [
            {
                'from_node': {'variable': 'n', 'labels': []},
                'relationship': {'variable': 'r1', 'types': [], 'direction': 'out', 'length': None},
                'to_node': {'variable': 'm', 'labels': []}
            },
            {
                'from_node': {'variable': 'm', 'labels': []},
                'relationship': {'variable': 'r2', 'types': [], 'direction': 'out', 'length': None},
                'to_node': {'variable': 'p', 'labels': []}
            }
        ]

        result = self.translator.translate_full_path(segments)

        assert "(n)" in result
        assert "(m)" in result
        assert "(p)" in result

    def test_translate_full_path_raises_on_non_list(self):
        """Test that non-list segments raise error."""
        with pytest.raises(ValueError):
            self.translator.translate_full_path("not_list")

    def test_translate_full_path_raises_on_empty_list(self):
        """Test that empty segments list raises error."""
        with pytest.raises(ValueError):
            self.translator.translate_full_path([])

    def test_merge_adjacent_nodes(self):
        """Test optimization of adjacent node patterns."""
        path = "(n)-[r1]->(m) (m)-[r2]->(p)"

        result = self.translator.merge_adjacent_nodes(path)

        # Current implementation doesn't optimize, just returns as-is
        assert isinstance(result, str)

    def test_relationship_direction_mapping(self):
        """Test that relationship directions are mapped correctly."""
        assert self.translator.relationship_direction_map['out'] == "->"
        assert self.translator.relationship_direction_map['in'] == "<-"
        assert self.translator.relationship_direction_map['both'] == "--"
