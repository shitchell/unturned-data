"""Tests for Schema C exporter."""

import json
from pathlib import Path

import pytest

from unturned_data.exporter import (
    SCHEMA_C_FIELDS,
    _serialize_entry,
    export_schema_c,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestSerializeEntry:
    def test_schema_c_fields_only(self):
        """Subclass-specific fields should NOT appear at top level."""
        from unturned_data.categories.items import Gun
        from unturned_data.dat_parser import parse_dat_file
        from unturned_data.loader import load_english_dat

        fix = FIXTURES / "gun_maplestrike"
        raw = parse_dat_file(list(fix.glob("*.dat"))[0])
        eng = load_english_dat(fix / "English.dat")
        gun = Gun.from_raw(raw, eng, "Items/Guns/Maplestrike")
        d = _serialize_entry(gun)

        # Should have Schema C fields
        assert "parsed" in d
        assert "english" in d
        assert "raw" in d

        # Should NOT have subclass fields at top level
        assert "slot" not in d
        assert "caliber" not in d
        assert "damage" not in d
        assert "firerate" not in d

        # parsed should have them
        assert "slot" in d["parsed"]
        assert "firerate" in d["parsed"]

    def test_all_schema_c_fields_present(self):
        from unturned_data.models import BundleEntry

        e = BundleEntry(
            guid="abc",
            type="Gun",
            id=42,
            name="Test",
            source_path="Items/Guns/Test",
            english={"Name": "Test"},
            raw={"Type": "Gun"},
        )
        d = _serialize_entry(e)
        for field in SCHEMA_C_FIELDS:
            assert field in d, f"Missing field: {field}"


class TestExportSchemaC:
    def test_creates_directory_structure(self, tmp_path):
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=tmp_path)
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "base" / "entries.json").exists()
        assert (tmp_path / "base" / "assets.json").exists()
        assert (tmp_path / "guid_index.json").exists()

    def test_entries_have_schema_c_shape(self, tmp_path):
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=tmp_path)
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        assert isinstance(entries, list)
        if entries:
            e = entries[0]
            assert "guid" in e
            assert "parsed" in e
            assert "english" in e
            assert "raw" in e
            assert "blueprints" in e
            assert "category" in e
            # No subclass-specific top-level fields
            for key in e:
                assert key in SCHEMA_C_FIELDS, f"Unexpected top-level key: {key}"

    def test_manifest_has_counts(self, tmp_path):
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=tmp_path)
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest["base_entry_count"] > 0
        assert manifest["version"] == "1.0.0"

    def test_guid_index_covers_entries(self, tmp_path):
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=tmp_path)
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        index = json.loads((tmp_path / "guid_index.json").read_text())
        for e in entries:
            if e["guid"]:
                assert e["guid"] in index["entries"], f"Missing GUID: {e['guid']}"

    def test_entries_sorted_by_name(self, tmp_path):
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=tmp_path)
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        names = [e["name"] for e in entries]
        assert names == sorted(names)

    def test_map_creates_map_json(self, tmp_path):
        fake_map = FIXTURES / "fake_map"
        export_schema_c(
            base_bundles=FIXTURES,
            map_dirs=[fake_map],
            output_dir=tmp_path,
        )
        safe = "fake_map"
        map_json_path = tmp_path / "maps" / safe / "map.json"
        assert map_json_path.exists()
        map_data = json.loads(map_json_path.read_text())
        assert map_data["name"] == "fake_map"
        assert "spawn_resolution" in map_data

    def test_map_entries_exported(self, tmp_path):
        fake_map = FIXTURES / "fake_map"
        export_schema_c(
            base_bundles=FIXTURES,
            map_dirs=[fake_map],
            output_dir=tmp_path,
        )
        safe = "fake_map"
        entries_path = tmp_path / "maps" / safe / "entries.json"
        # fake_map has a spawn table in Bundles/, which is an entry
        if entries_path.exists():
            entries = json.loads(entries_path.read_text())
            assert isinstance(entries, list)
            for e in entries:
                for key in e:
                    assert key in SCHEMA_C_FIELDS, f"Unexpected key in map entry: {key}"

    def test_guid_index_includes_map_entries(self, tmp_path):
        fake_map = FIXTURES / "fake_map"
        export_schema_c(
            base_bundles=FIXTURES,
            map_dirs=[fake_map],
            output_dir=tmp_path,
        )
        index = json.loads((tmp_path / "guid_index.json").read_text())
        # Check that by_id has entries
        assert isinstance(index["by_id"], dict)
        assert index["total_entries"] > 0

    def test_manifest_includes_map_info(self, tmp_path):
        fake_map = FIXTURES / "fake_map"
        export_schema_c(
            base_bundles=FIXTURES,
            map_dirs=[fake_map],
            output_dir=tmp_path,
        )
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert "fake_map" in manifest["maps"]
        map_info = manifest["maps"]["fake_map"]
        assert map_info["map_file"] == "maps/fake_map/map.json"
