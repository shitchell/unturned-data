"""Integration tests for the complete export pipeline.

Tests are split into two groups:
1. Fixture-based tests that always run (using test fixtures).
2. Full-server tests that only run when real server data is available.
"""

import json
import pytest
from pathlib import Path

from unturned_data.categories import parse_entry
from unturned_data.dat_parser import parse_dat_file
from unturned_data.exporter import (
    SCHEMA_C_FIELDS,
    SCHEMA_C_FIELDS_WITH_RAW,
    _serialize_entry,
    export_schema_c,
)
from unturned_data.loader import load_english_dat

FIXTURES = Path(__file__).parent / "fixtures"
SERVER_ROOT = Path("/home/guy/unturned-server")
SERVER_BUNDLES = SERVER_ROOT / "Bundles"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(name: str):
    """Load a fixture by name, returning (raw_dict, english_dict)."""
    fixture_dir = FIXTURES / name
    dat_files = [f for f in fixture_dir.glob("*.dat") if f.name != "English.dat"]
    assert dat_files, f"No .dat file found in fixture {name}"
    raw = parse_dat_file(dat_files[0])
    english_path = fixture_dir / "English.dat"
    english = load_english_dat(english_path) if english_path.exists() else {}
    return raw, english


# A representative set of fixtures covering different item types
FIXTURE_NAMES = [
    "gun_maplestrike",
    "melee_katana",
    "food_beans",
    "food_sandwich",
    "backpack_alice",
    "barricade_wire",
    "medical_bandage",
    "structure_wall",
    "vehicle_humvee",
    "water_berries",
    "animal_bear",
    "gun_ace",
]

# Source paths that match how the real game data is structured
_FIXTURE_SOURCE_PATHS = {
    "gun_maplestrike": "Items/Guns/Maplestrike",
    "melee_katana": "Items/Melee/Katana",
    "food_beans": "Items/Edible/Canned_Beans",
    "food_sandwich": "Items/Edible/Sandwich_Beef",
    "backpack_alice": "Items/Bags/Alicepack",
    "barricade_wire": "Items/Barricades/Barbedwire",
    "medical_bandage": "Items/Edible/Bandage",
    "structure_wall": "Items/Structures/Doorway_Birch",
    "vehicle_humvee": "Vehicles/Humvee",
    "water_berries": "Items/Edible/Raw_Amber_Berries",
    "animal_bear": "Animals/Bear",
    "gun_ace": "Items/Guns/Ace",
}


# ---------------------------------------------------------------------------
# Fixture-based tests (always run)
# ---------------------------------------------------------------------------


class TestFixtureRoundTrip:
    """Parse fixtures through the full pipeline and validate output structure."""

    @pytest.fixture(params=FIXTURE_NAMES)
    def parsed_entry(self, request):
        name = request.param
        raw, english = _load_fixture(name)
        source_path = _FIXTURE_SOURCE_PATHS.get(name, f"Items/{name}")
        return parse_entry(raw, english, source_path)

    def test_entry_has_properties(self, parsed_entry):
        """Every entry should have a properties dict."""
        assert hasattr(parsed_entry, "properties")
        assert parsed_entry.properties is not None

    def test_entry_has_actions(self, parsed_entry):
        """Every entry should have an actions list."""
        assert hasattr(parsed_entry, "actions")
        assert isinstance(parsed_entry.actions, list)

    def test_serialized_has_properties(self, parsed_entry):
        """Serialized entry should have a properties dict."""
        d = _serialize_entry(parsed_entry)
        assert "properties" in d
        assert isinstance(d["properties"], dict)

    def test_serialized_has_actions(self, parsed_entry):
        """Serialized entry should have an actions list."""
        d = _serialize_entry(parsed_entry)
        assert "actions" in d
        assert isinstance(d["actions"], list)

    def test_serialized_no_raw_by_default(self, parsed_entry):
        """raw should not appear in default serialization."""
        d = _serialize_entry(parsed_entry)
        assert "raw" not in d

    def test_serialized_no_parsed_field(self, parsed_entry):
        """The old 'parsed' field should not appear."""
        d = _serialize_entry(parsed_entry)
        assert "parsed" not in d

    def test_serialized_only_schema_c_fields(self, parsed_entry):
        """Only Schema C fields should appear at top level."""
        d = _serialize_entry(parsed_entry)
        for key in d:
            assert key in SCHEMA_C_FIELDS, f"Unexpected top-level key: {key}"

    def test_serialized_all_schema_c_fields_present(self, parsed_entry):
        """All Schema C fields should be present."""
        d = _serialize_entry(parsed_entry)
        for field in SCHEMA_C_FIELDS:
            assert field in d, f"Missing field: {field}"

    def test_serialized_with_raw(self, parsed_entry):
        """include_raw=True should add the raw dict."""
        d = _serialize_entry(parsed_entry, include_raw=True)
        assert "raw" in d
        assert isinstance(d["raw"], dict)
        for key in d:
            assert key in SCHEMA_C_FIELDS_WITH_RAW, f"Unexpected key: {key}"


class TestFixtureExport:
    """Run the export pipeline against fixture data."""

    @pytest.fixture(scope="class")
    def export_result(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("fixture_export")
        export_schema_c(base_bundles=FIXTURES, map_dirs=[], output_dir=out)
        return out

    def test_creates_expected_files(self, export_result):
        assert (export_result / "manifest.json").exists()
        assert (export_result / "base" / "entries.json").exists()
        assert (export_result / "base" / "assets.json").exists()
        assert (export_result / "guid_index.json").exists()

    def test_all_entries_have_properties(self, export_result):
        entries = json.loads(
            (export_result / "base" / "entries.json").read_text()
        )
        for entry in entries:
            assert "properties" in entry, f"Missing properties in {entry.get('name')}"
            assert isinstance(entry["properties"], dict)

    def test_all_entries_have_actions(self, export_result):
        entries = json.loads(
            (export_result / "base" / "entries.json").read_text()
        )
        for entry in entries:
            assert "actions" in entry, f"Missing actions in {entry.get('name')}"
            assert isinstance(entry["actions"], list)

    def test_no_raw_in_default_export(self, export_result):
        entries = json.loads(
            (export_result / "base" / "entries.json").read_text()
        )
        for entry in entries:
            assert "raw" not in entry, f"raw found in {entry.get('name')}"

    def test_no_parsed_field(self, export_result):
        entries = json.loads(
            (export_result / "base" / "entries.json").read_text()
        )
        for entry in entries:
            assert "parsed" not in entry, f"parsed found in {entry.get('name')}"

    def test_only_schema_c_fields(self, export_result):
        entries = json.loads(
            (export_result / "base" / "entries.json").read_text()
        )
        for entry in entries:
            for key in entry:
                assert key in SCHEMA_C_FIELDS, (
                    f"Unexpected key '{key}' in {entry.get('name')}"
                )

    def test_include_raw_export(self, tmp_path):
        """Export with include_raw=True should add raw to every entry."""
        export_schema_c(
            base_bundles=FIXTURES,
            map_dirs=[],
            output_dir=tmp_path,
            include_raw=True,
        )
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        assert len(entries) > 0
        for entry in entries:
            assert "raw" in entry, f"raw missing in {entry.get('name')}"
            assert isinstance(entry["raw"], dict)
            for key in entry:
                assert key in SCHEMA_C_FIELDS_WITH_RAW, (
                    f"Unexpected key '{key}' in {entry.get('name')}"
                )


# ---------------------------------------------------------------------------
# Full server data tests (skipped if server data not available)
# ---------------------------------------------------------------------------

server_data_available = pytest.mark.skipif(
    not SERVER_BUNDLES.is_dir(),
    reason="Server data not available at /home/guy/unturned-server/Bundles",
)


@server_data_available
class TestFullServerExport:
    """Integration tests that run the full export against real game data."""

    @pytest.fixture(scope="class")
    def export_dir(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("server_export")
        export_schema_c(
            base_bundles=SERVER_BUNDLES, map_dirs=[], output_dir=out
        )
        return out

    @pytest.fixture(scope="class")
    def entries(self, export_dir):
        return json.loads(
            (export_dir / "base" / "entries.json").read_text()
        )

    def test_manifest_exists(self, export_dir):
        assert (export_dir / "manifest.json").exists()

    def test_significant_entry_count(self, entries):
        """Real game data should have >1000 entries."""
        assert len(entries) > 1000, f"Only {len(entries)} entries found"

    def test_all_entries_have_properties(self, entries):
        """Every entry should have a properties dict."""
        for entry in entries:
            assert "properties" in entry, (
                f"Missing properties in {entry.get('name')} (type={entry.get('type')})"
            )
            assert isinstance(entry["properties"], dict)

    def test_all_entries_have_actions(self, entries):
        """Every entry should have an actions list."""
        for entry in entries:
            assert "actions" in entry, (
                f"Missing actions in {entry.get('name')} (type={entry.get('type')})"
            )
            assert isinstance(entry["actions"], list)

    def test_no_raw_in_default_export(self, entries):
        """raw should be excluded from default export."""
        for entry in entries:
            assert "raw" not in entry, (
                f"raw found in {entry.get('name')} (type={entry.get('type')})"
            )

    def test_no_parsed_field(self, entries):
        """The old 'parsed' field should not appear."""
        for entry in entries:
            assert "parsed" not in entry, (
                f"parsed found in {entry.get('name')} (type={entry.get('type')})"
            )

    def test_only_schema_c_fields(self, entries):
        """Only Schema C fields should appear at top level."""
        for entry in entries:
            for key in entry:
                assert key in SCHEMA_C_FIELDS, (
                    f"Unexpected key '{key}' in {entry.get('name')} "
                    f"(type={entry.get('type')})"
                )

    def test_has_expected_types(self, entries):
        """Real data should contain common item types."""
        types_found = {e["type"] for e in entries}
        for expected in ["Gun", "Food", "Vehicle", "Animal", "Melee"]:
            assert expected in types_found, f"Missing type: {expected}"

    def test_guid_index_covers_entries(self, export_dir, entries):
        index = json.loads(
            (export_dir / "guid_index.json").read_text()
        )
        guids_with_values = [e["guid"] for e in entries if e["guid"]]
        # Spot-check first 100 entries
        for guid in guids_with_values[:100]:
            assert guid in index["entries"], f"GUID {guid} missing from index"

    def test_assets_json_exists(self, export_dir):
        assert (export_dir / "base" / "assets.json").exists()
        assets = json.loads(
            (export_dir / "base" / "assets.json").read_text()
        )
        assert len(assets) > 0

    def test_entries_sorted_by_name(self, entries):
        names = [(e["name"], e["id"]) for e in entries]
        assert names == sorted(names)


@server_data_available
class TestFullServerExportWithRaw:
    """Test the --include-raw flag against real game data."""

    @pytest.fixture(scope="class")
    def export_dir(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("server_export_raw")
        export_schema_c(
            base_bundles=SERVER_BUNDLES,
            map_dirs=[],
            output_dir=out,
            include_raw=True,
        )
        return out

    @pytest.fixture(scope="class")
    def entries(self, export_dir):
        return json.loads(
            (export_dir / "base" / "entries.json").read_text()
        )

    def test_all_entries_have_raw(self, entries):
        """Every entry should have raw when include_raw=True."""
        for entry in entries:
            assert "raw" in entry, (
                f"raw missing in {entry.get('name')} (type={entry.get('type')})"
            )
            assert isinstance(entry["raw"], dict)

    def test_only_extended_schema_c_fields(self, entries):
        """Only Schema C + raw fields should appear."""
        for entry in entries:
            for key in entry:
                assert key in SCHEMA_C_FIELDS_WITH_RAW, (
                    f"Unexpected key '{key}' in {entry.get('name')} "
                    f"(type={entry.get('type')})"
                )

    def test_raw_contains_type_key(self, entries):
        """The raw dict should at minimum contain a Type key."""
        for entry in entries[:100]:
            assert "Type" in entry["raw"], (
                f"raw dict missing 'Type' in {entry.get('name')}"
            )
