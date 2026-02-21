"""
Tests for the Markdown formatter.
"""

from __future__ import annotations

import pytest

from unturned_data.categories import Animal, GenericEntry
from unturned_data.models import BundleEntry
from unturned_data.formatters.markdown_fmt import build_guid_map, entries_to_markdown


def _make_animal(name: str, id: int, guid: str = "") -> Animal:
    """Helper to build a minimal Animal entry."""
    return Animal(
        guid=guid,
        type="Animal",
        id=id,
        name=name,
        source_path=f"Animals/{name}",
    )


def _make_gun(name: str, id: int, guid: str = "") -> BundleEntry:
    """Helper to build a minimal Gun-type BundleEntry."""
    return BundleEntry(
        guid=guid,
        type="Gun",
        id=id,
        name=name,
        source_path=f"Items/Guns/{name}",
    )


def _make_consumeable(name: str, id: int, guid: str = "") -> BundleEntry:
    """Helper to build a minimal Food-type BundleEntry."""
    return BundleEntry(
        guid=guid,
        type="Food",
        id=id,
        name=name,
        source_path=f"Items/Food/{name}",
    )


def _make_generic(name: str, id: int, guid: str = "") -> GenericEntry:
    """Helper to build a minimal GenericEntry."""
    return GenericEntry(
        guid=guid,
        type="UnknownType",
        id=id,
        name=name,
        source_path=f"Other/{name}",
    )


class TestBuildGuidMap:
    """Tests for build_guid_map."""

    def test_maps_guid_to_name(self):
        entries = [
            _make_animal("Bear", 1, guid="guid-bear"),
            _make_gun("AK-47", 10, guid="guid-ak"),
        ]
        guid_map = build_guid_map(entries)
        assert guid_map["guid-bear"] == "Bear"
        assert guid_map["guid-ak"] == "AK-47"

    def test_skips_empty_guid(self):
        entries = [_make_animal("Bear", 1, guid="")]
        guid_map = build_guid_map(entries)
        assert "" not in guid_map

    def test_empty_list(self):
        guid_map = build_guid_map([])
        assert guid_map == {}


class TestEntriesToMarkdown:
    """Tests for entries_to_markdown."""

    def test_produces_table_headers(self):
        """Output contains markdown table header row."""
        entries = [_make_animal("Bear", 1)]
        result = entries_to_markdown(entries)
        assert "| Name |" in result

    def test_directory_based_headings(self):
        """Entries are organized under directory-based headings."""
        entries = [
            _make_gun("AK-47", 10),
            _make_animal("Bear", 1),
            _make_consumeable("Beans", 5),
        ]
        result = entries_to_markdown(entries)
        assert "## Animals" in result
        assert "## Items" in result
        # Subdirectories get deeper headings
        assert "### Guns" in result
        assert "### Food" in result

    def test_heading_depth(self):
        """Deeper directories get deeper heading levels."""
        entries = [_make_gun("AK-47", 10)]
        result = entries_to_markdown(entries)
        # Items is ## (depth 0), Guns is ### (depth 1)
        assert "## Items" in result
        assert "### Guns" in result

    def test_entries_sorted_within_group(self):
        """Entries within a group are sorted by (name, id)."""
        entries = [
            _make_animal("Deer", 2),
            _make_animal("Bear", 1),
            _make_animal("Bear", 3),
        ]
        result = entries_to_markdown(entries)
        # Find the table rows (lines starting with |)
        lines = result.split("\n")
        data_rows = [
            l
            for l in lines
            if l.startswith("| ") and "---" not in l and "Name" not in l
        ]
        # Bear (id=1) should come before Bear (id=3) which should come before Deer
        assert len(data_rows) == 3
        assert "Bear" in data_rows[0]
        assert "Bear" in data_rows[1]
        assert "Deer" in data_rows[2]

    def test_deterministic_output(self):
        """Same input always produces identical output."""
        entries = [
            _make_gun("AK-47", 10),
            _make_animal("Deer", 2),
            _make_animal("Bear", 1),
        ]
        result1 = entries_to_markdown(entries)
        result2 = entries_to_markdown(entries)
        assert result1 == result2

    def test_underscore_replaced_in_headings(self):
        """Directory names with underscores become spaces in headings."""
        entry = GenericEntry(
            type="UnknownType",
            id=1,
            name="Test",
            source_path="Items/Oil_Pump/Test",
        )
        result = entries_to_markdown([entry])
        assert "Oil Pump" in result

    def test_pipe_chars_escaped(self):
        """Pipe characters in cell values are escaped."""
        animal = _make_animal("Bear | Grizzly", 1)
        result = entries_to_markdown([animal])
        # The pipe in the name should be escaped
        assert "Bear \\| Grizzly" in result

    def test_empty_list(self):
        """Empty input produces empty string."""
        result = entries_to_markdown([])
        assert result == ""

    def test_separator_row_present(self):
        """Each table has a separator row with dashes."""
        entries = [_make_animal("Bear", 1)]
        result = entries_to_markdown(entries)
        lines = result.split("\n")
        separator_lines = [l for l in lines if "---" in l]
        assert len(separator_lines) >= 1

    def test_sections_sorted_alphabetically(self):
        """Top-level directory sections are sorted alphabetically."""
        entries = [
            _make_gun("AK-47", 10),
            _make_animal("Bear", 1),
        ]
        result = entries_to_markdown(entries)
        animals_pos = result.index("## Animals")
        items_pos = result.index("## Items")
        assert animals_pos < items_pos
