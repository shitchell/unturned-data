"""
Tests for the JSON formatter.
"""
from __future__ import annotations

import json

import pytest

from unturned_data.categories import Animal, Consumeable, Gun, GenericEntry
from unturned_data.formatters.json_fmt import entries_to_json


def _make_animal(name: str, id: int, guid: str = "") -> Animal:
    """Helper to build a minimal Animal entry."""
    return Animal(
        guid=guid,
        type="Animal",
        id=id,
        name=name,
        source_path=f"Animals/{name}",
    )


def _make_gun(name: str, id: int, guid: str = "") -> Gun:
    """Helper to build a minimal Gun entry."""
    return Gun(
        guid=guid,
        type="Gun",
        id=id,
        name=name,
        source_path=f"Items/Guns/{name}",
    )


def _make_consumeable(name: str, id: int, guid: str = "") -> Consumeable:
    """Helper to build a minimal Consumeable entry."""
    return Consumeable(
        guid=guid,
        type="Food",
        id=id,
        name=name,
        source_path=f"Items/Food/{name}",
    )


class TestEntriesToJson:
    """Tests for entries_to_json."""

    def test_produces_valid_json(self):
        """Output must be parseable as JSON."""
        entries = [_make_animal("Bear", 1)]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_nested_structure(self):
        """Entries are nested under their category path."""
        entries = [_make_animal("Bear", 1, guid="abc-123")]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        assert "Animals" in parsed
        assert "_entries" in parsed["Animals"]
        entry = parsed["Animals"]["_entries"][0]
        assert entry["name"] == "Bear"
        assert entry["id"] == 1
        assert entry["guid"] == "abc-123"

    def test_category_field_in_entry(self):
        """Each entry dict includes a category array."""
        entries = [_make_gun("AK-47", 10)]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        entry = parsed["Items"]["Guns"]["_entries"][0]
        assert entry["category"] == ["Items", "Guns"]

    def test_deterministic_output(self):
        """Same input always produces identical output."""
        entries = [
            _make_animal("Deer", 2),
            _make_gun("AK-47", 10),
            _make_animal("Bear", 1),
        ]
        result1 = entries_to_json(entries)
        result2 = entries_to_json(entries)
        assert result1 == result2

    def test_entries_sorted_by_name_within_node(self):
        """Entries within a node are sorted by (name, id)."""
        entries = [
            _make_animal("Deer", 2),
            _make_animal("Bear", 5),
            _make_animal("Bear", 1),
        ]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        names = [(e["name"], e["id"]) for e in parsed["Animals"]["_entries"]]
        assert names == [("Bear", 1), ("Bear", 5), ("Deer", 2)]

    def test_empty_list(self):
        """Empty input produces empty JSON object."""
        result = entries_to_json([])
        parsed = json.loads(result)
        assert parsed == {}

    def test_indent_parameter(self):
        """Custom indent is respected."""
        entries = [_make_animal("Bear", 1)]
        result_2 = entries_to_json(entries, indent=2)
        result_4 = entries_to_json(entries, indent=4)
        # Both should be valid JSON
        json.loads(result_2)
        json.loads(result_4)
        # 4-space indent should be longer
        assert len(result_4) > len(result_2)

    def test_sort_keys(self):
        """JSON keys within each entry are sorted."""
        entries = [_make_animal("Bear", 1)]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        entry = parsed["Animals"]["_entries"][0]
        keys = list(entry.keys())
        assert keys == sorted(keys)

    def test_multi_level_nesting(self):
        """Entries with deeper paths create nested structure."""
        entries = [
            _make_gun("AK-47", 10),
            _make_consumeable("Beans", 5),
        ]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        assert "Items" in parsed
        assert "Guns" in parsed["Items"]
        assert "Food" in parsed["Items"]
        assert parsed["Items"]["Guns"]["_entries"][0]["name"] == "AK-47"
        assert parsed["Items"]["Food"]["_entries"][0]["name"] == "Beans"

    def test_mixed_depth_entries(self):
        """Entries at different depths coexist in the tree."""
        # Animal at depth 1, Gun at depth 2
        entries = [
            _make_animal("Bear", 1),
            _make_gun("AK-47", 10),
        ]
        result = entries_to_json(entries)
        parsed = json.loads(result)
        assert "Animals" in parsed
        assert "Items" in parsed
        assert "_entries" in parsed["Animals"]
        assert "Guns" in parsed["Items"]
