"""Tests for web formatter with map spawn data."""
import json
import pytest

from unturned_data.formatters.web_fmt import entries_to_web_json
from unturned_data.models import BundleEntry


class TestWebMapData:
    def test_spawnable_column_when_map_data(self):
        """When entries have _map_spawnable, output includes Maps column."""
        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Test Gun",
            source_path="Items/Guns/Test",
        )
        entry._map_spawnable = {"PEI", "Washington"}

        output = entries_to_web_json([entry])
        sections = json.loads(output)
        assert len(sections) > 0

        # Should have a "Maps" column
        cols = sections[0]["columns"]
        assert "Maps" in cols

        # The row should include the map names
        maps_idx = cols.index("Maps")
        maps_val = sections[0]["rows"][0][maps_idx]
        assert "PEI" in maps_val
        assert "Washington" in maps_val

    def test_no_map_column_when_no_map_data(self):
        """Without _map_spawnable, no Maps column appears."""
        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Test Gun",
            source_path="Items/Guns/Test",
        )
        output = entries_to_web_json([entry])
        sections = json.loads(output)
        cols = sections[0]["columns"]
        assert "Maps" not in cols

    def test_map_values_sorted(self):
        """Map names should be sorted alphabetically."""
        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Test Gun",
            source_path="Items/Guns/Test",
        )
        entry._map_spawnable = {"Washington", "PEI", "Germany"}

        output = entries_to_web_json([entry])
        sections = json.loads(output)
        maps_idx = sections[0]["columns"].index("Maps")
        maps_val = sections[0]["rows"][0][maps_idx]
        assert maps_val == "Germany, PEI, Washington"

    def test_empty_map_spawnable_set(self):
        """An entry with an empty _map_spawnable set gets empty string."""
        entry1 = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Gun A",
            source_path="Items/Guns/Test",
        )
        entry1._map_spawnable = {"PEI"}

        entry2 = BundleEntry(
            guid="bbb", type="Gun", id=2, name="Gun B",
            source_path="Items/Guns/Test",
        )
        entry2._map_spawnable = set()

        output = entries_to_web_json([entry1, entry2])
        sections = json.loads(output)
        maps_idx = sections[0]["columns"].index("Maps")

        # entry1 sorted first by name
        rows = sections[0]["rows"]
        # Gun A has PEI, Gun B has empty
        assert rows[0][maps_idx] == "PEI"
        assert rows[1][maps_idx] == ""
