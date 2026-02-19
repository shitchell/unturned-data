"""Integration tests for map-aware parsing against real server data."""
import pytest
from pathlib import Path

from unturned_data.map_resolver import (
    collect_map_spawn_tables,
    determine_active_tables,
    resolve_spawn_table_items,
)
from unturned_data.categories import parse_entry
from unturned_data.loader import walk_bundle_dir
from unturned_data.models import SpawnTable

# These paths are on localAI — skip if not available
BUNDLES = Path.home() / "unturned-bundles"
PEI_MAP = Path.home() / "unturned-server" / "Maps" / "PEI"

pytestmark = pytest.mark.skipif(
    not BUNDLES.exists() or not PEI_MAP.exists(),
    reason="Full server data not available",
)


class TestPEIMap:
    @pytest.fixture(scope="class")
    def all_tables(self):
        tables_by_id = {}
        name_to_id = {}
        for raw, english, rel_path in walk_bundle_dir(BUNDLES):
            if raw.get("Type") != "Spawn":
                continue
            entry = parse_entry(raw, english, rel_path)
            if isinstance(entry, SpawnTable):
                tables_by_id[entry.id] = entry
                name_to_id[entry.name] = entry.id
        return tables_by_id, name_to_id

    def test_finds_spawn_tables(self, all_tables):
        tables_by_id, _ = all_tables
        assert len(tables_by_id) > 100

    def test_determines_active_tables(self, all_tables):
        tables_by_id, name_to_id = all_tables
        active = determine_active_tables(PEI_MAP, tables_by_id, name_to_id)
        assert len(active) > 10

    def test_resolves_items(self, all_tables):
        tables_by_id, name_to_id = all_tables
        active = determine_active_tables(PEI_MAP, tables_by_id, name_to_id)
        all_items = set()
        for tid in active:
            all_items |= resolve_spawn_table_items(tid, tables_by_id)
        assert len(all_items) > 100
