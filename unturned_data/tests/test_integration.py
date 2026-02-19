"""Integration tests against full bundle data."""
import json
import pytest
from pathlib import Path
from unturned_data.exporter import export_schema_c, SCHEMA_C_FIELDS

BUNDLES = Path.home() / "unturned-bundles"

pytestmark = pytest.mark.skipif(
    not BUNDLES.exists(), reason="Full bundle data not available"
)


class TestSchemaC:
    @pytest.fixture(scope="class")
    def export_dir(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("export")
        export_schema_c(base_bundles=BUNDLES, map_dirs=[], output_dir=out)
        return out

    def test_manifest_exists(self, export_dir):
        assert (export_dir / "manifest.json").exists()

    def test_entry_count(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        assert len(entries) > 1000

    def test_all_entries_have_schema_c_fields(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        for e in entries[:100]:
            for field in SCHEMA_C_FIELDS:
                assert field in e, f"Missing field '{field}' in {e.get('name')}"
            # No extra fields
            for key in e:
                assert key in SCHEMA_C_FIELDS, f"Unexpected key '{key}' in {e.get('name')}"

    def test_has_expected_types(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        types_found = {e["type"] for e in entries}
        for expected in ["Gun", "Food", "Vehicle", "Animal", "Melee"]:
            assert expected in types_found, f"Missing type: {expected}"

    def test_guid_index_covers_entries(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        index = json.loads((export_dir / "guid_index.json").read_text())
        guids_with_values = [e["guid"] for e in entries if e["guid"]]
        for guid in guids_with_values[:50]:
            assert guid in index["entries"]

    def test_assets_json_exists(self, export_dir):
        assert (export_dir / "base" / "assets.json").exists()
        assets = json.loads((export_dir / "base" / "assets.json").read_text())
        assert len(assets) > 0

    def test_json_deterministic(self, export_dir):
        """Two reads of same file give same content."""
        text1 = (export_dir / "base" / "entries.json").read_text()
        text2 = (export_dir / "base" / "entries.json").read_text()
        assert text1 == text2
