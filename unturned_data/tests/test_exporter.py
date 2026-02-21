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


class TestBuildGuidIndexByIdFormat:
    def test_by_id_namespace_source_grouped(self):
        """by_id should group by namespace and source."""
        from unturned_data.exporter import _build_guid_index
        from unturned_data.models import BundleEntry

        entries = [
            BundleEntry(
                guid="aaa",
                type="Gun",
                id=100,
                name="Eaglefire",
                source_path="Items/Guns/Eaglefire",
            ),
            BundleEntry(
                guid="bbb",
                type="Spawn",
                id=100,
                name="Spawn 100",
                source_path="Spawns/Spawn_100",
            ),
            BundleEntry(
                guid="ccc",
                type="Vehicle",
                id=100,
                name="Tank",
                source_path="Vehicles/Tank",
            ),
        ]
        gi = _build_guid_index(entries, [], {}, "2026-01-01")

        assert gi.by_id["100"]["items"]["base"] == "aaa"
        assert gi.by_id["100"]["spawns"]["base"] == "bbb"
        assert gi.by_id["100"]["vehicles"]["base"] == "ccc"

    def test_by_id_map_source(self):
        """Map entries should use map safe name as source."""
        from unturned_data.exporter import _build_guid_index
        from unturned_data.models import BundleEntry

        base = [
            BundleEntry(
                guid="aaa",
                type="Gun",
                id=100,
                name="Eaglefire",
                source_path="Items/Guns/Eaglefire",
            )
        ]
        map_entries = [
            BundleEntry(
                guid="bbb",
                type="Food",
                id=100,
                name="Bread",
                source_path="Items/Edible/Bread",
            )
        ]
        gi = _build_guid_index(
            base, [], {"a6_polaris": (map_entries, [])}, "2026-01-01"
        )

        assert gi.by_id["100"]["items"]["base"] == "aaa"
        assert gi.by_id["100"]["items"]["a6_polaris"] == "bbb"

    def test_by_id_skips_id_zero(self):
        """ID 0 is a cosmetics dumping ground and should be excluded from by_id."""
        from unturned_data.exporter import _build_guid_index
        from unturned_data.models import BundleEntry

        entries = [
            BundleEntry(
                guid="aaa",
                type="Hat",
                id=0,
                name="Cool Hat",
                source_path="Items/Hats/Cool_Hat",
            )
        ]
        gi = _build_guid_index(entries, [], {}, "2026-01-01")
        assert "0" not in gi.by_id


class TestSyntheticGuids:
    def test_generates_synthetic_for_guidless_entry(self):
        from unturned_data.exporter import _ensure_guids
        from unturned_data.models import BundleEntry

        entries = [
            BundleEntry(
                guid="",
                type="Gun",
                id=42,
                name="No GUID Gun",
                source_path="Items/Guns/NoGuid",
            )
        ]
        _ensure_guids(entries, "base")
        assert entries[0].guid.startswith("00000")
        assert len(entries[0].guid) == 32

    def test_synthetic_guid_is_deterministic(self):
        from unturned_data.exporter import _ensure_guids
        from unturned_data.models import BundleEntry

        e1 = [
            BundleEntry(
                guid="", type="Gun", id=42, name="X", source_path="Items/Guns/X"
            )
        ]
        e2 = [
            BundleEntry(
                guid="", type="Gun", id=42, name="X", source_path="Items/Guns/X"
            )
        ]
        _ensure_guids(e1, "base")
        _ensure_guids(e2, "base")
        assert e1[0].guid == e2[0].guid

    def test_does_not_overwrite_existing_guid(self):
        from unturned_data.exporter import _ensure_guids
        from unturned_data.models import BundleEntry

        entries = [
            BundleEntry(
                guid="realguid123",
                type="Gun",
                id=42,
                name="Has GUID",
                source_path="Items/Guns/X",
            )
        ]
        _ensure_guids(entries, "base")
        assert entries[0].guid == "realguid123"


class TestResolveBlueprintIds:
    def test_resolves_numeric_id_to_guid(self):
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        bread = BundleEntry(guid="bread-guid", type="Food", id=36033,
                            name="Bread", source_path="Items/Edible/Bread")
        sandwich = BundleEntry(
            guid="sandwich-guid", type="Food", id=36079,
            name="Sandwich", source_path="Items/Edible/Sandwich",
            blueprints=[Blueprint(name="Craft", inputs=["36033"], outputs=["this"])],
        )
        _resolve_blueprint_ids([bread, sandwich], "base")
        assert sandwich.blueprints[0].inputs == ["bread-guid"]
        assert sandwich.blueprints[0].outputs == ["this"]

    def test_resolves_numeric_id_with_quantity(self):
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        berry = BundleEntry(guid="berry-guid", type="Water", id=36022,
                            name="Berry", source_path="Items/Edible/Berry")
        sandwich = BundleEntry(
            guid="sandwich-guid", type="Food", id=36079,
            name="Sandwich", source_path="Items/Edible/Sandwich",
            blueprints=[Blueprint(name="Craft", inputs=["36022 x 5"],
                                  outputs=["this"])],
        )
        _resolve_blueprint_ids([berry, sandwich], "base")
        assert sandwich.blueprints[0].inputs == ["berry-guid x 5"]

    def test_leaves_guid_unchanged(self):
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="X",
            source_path="Items/Guns/X",
            blueprints=[Blueprint(name="Craft",
                                  inputs=["abcdef1234567890abcdef1234567890"],
                                  outputs=["this"])],
        )
        _resolve_blueprint_ids([entry], "base")
        assert entry.blueprints[0].inputs == ["abcdef1234567890abcdef1234567890"]

    def test_leaves_this_unchanged(self):
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="X",
            source_path="Items/Guns/X",
            blueprints=[Blueprint(name="Craft", inputs=["100"],
                                  outputs=["this"])],
        )
        item = BundleEntry(guid="bbb", type="Melee", id=100, name="Y",
                           source_path="Items/Melee/Y")
        _resolve_blueprint_ids([entry, item], "base")
        assert entry.blueprints[0].outputs == ["this"]

    def test_prefers_items_namespace(self):
        """When a numeric ID collides across namespaces, items should win."""
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        item = BundleEntry(guid="item-guid", type="Food", id=100,
                           name="Food Item", source_path="Items/Edible/Food")
        spawn = BundleEntry(guid="spawn-guid", type="Spawn", id=100,
                            name="Spawn 100", source_path="Spawns/Spawn_100")
        recipe = BundleEntry(
            guid="recipe-guid", type="Food", id=200,
            name="Recipe", source_path="Items/Edible/Recipe",
            blueprints=[Blueprint(name="Craft", inputs=["100"],
                                  outputs=["this"])],
        )
        _resolve_blueprint_ids([item, spawn, recipe], "base")
        assert recipe.blueprints[0].inputs == ["item-guid"]

    def test_warns_on_unresolvable_id(self, caplog):
        """Unresolvable IDs should log a warning and stay as-is."""
        import logging
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="X",
            source_path="Items/Guns/X",
            blueprints=[Blueprint(name="Craft", inputs=["99999"],
                                  outputs=["this"])],
        )
        with caplog.at_level(logging.WARNING):
            _resolve_blueprint_ids([entry], "base")
        assert entry.blueprints[0].inputs == ["99999"]
        assert "99999" in caplog.text

    def test_resolves_tool_dict_input(self):
        """Tool inputs are dicts with ID key -- should also be resolved."""
        from unturned_data.exporter import _resolve_blueprint_ids
        from unturned_data.models import Blueprint, BundleEntry

        tool = BundleEntry(guid="tool-guid", type="Melee", id=76,
                           name="Saw", source_path="Items/Melee/Saw")
        entry = BundleEntry(
            guid="aaa", type="Structure", id=1, name="X",
            source_path="Items/Structures/X",
            blueprints=[Blueprint(name="Craft",
                                  inputs=[{"ID": "76", "Amount": 1,
                                           "Delete": False}],
                                  outputs=["this"])],
        )
        _resolve_blueprint_ids([tool, entry], "base")
        assert entry.blueprints[0].inputs[0]["ID"] == "tool-guid"
