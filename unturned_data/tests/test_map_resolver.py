"""Tests for map_resolver module."""
import struct
import pytest
from pathlib import Path

from unturned_data.map_resolver import (
    extract_spawn_names_from_binary,
    collect_map_spawn_tables,
    resolve_spawn_table_items,
)
from unturned_data.models import SpawnTable, SpawnTableEntry

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_MAP = FIXTURES / "fake_map"


class TestExtractSpawnNames:
    def test_extracts_length_prefixed_strings(self, tmp_path):
        """Binary with length-prefixed ASCII strings are extracted."""
        # Write a binary with: \x09TestSpawn (length=9, then string)
        data = b"\x04\x00\x00\x00\x09TestSpawn\x06Police"
        path = tmp_path / "Items.dat"
        path.write_bytes(data)
        names = extract_spawn_names_from_binary(path)
        assert "TestSpawn" in names
        assert "Police" in names

    def test_empty_file(self, tmp_path):
        path = tmp_path / "Items.dat"
        path.write_bytes(b"")
        names = extract_spawn_names_from_binary(path)
        assert names == []

    def test_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.dat"
        names = extract_spawn_names_from_binary(path)
        assert names == []


class TestCollectMapSpawnTables:
    def test_finds_map_bundle_tables(self):
        """Spawn tables in the map's own Bundles/ are discovered."""
        tables = collect_map_spawn_tables(FAKE_MAP)
        assert any(t.id == 99001 for t in tables)

    def test_returns_spawn_tables(self):
        tables = collect_map_spawn_tables(FAKE_MAP)
        for t in tables:
            assert isinstance(t, SpawnTable)


class TestResolveSpawnTableItems:
    def test_resolves_asset_refs(self):
        """Asset references resolve to item IDs."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="asset", ref_id=42, weight=10),
                    SpawnTableEntry(ref_type="asset", ref_id=99, weight=5),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert 42 in items
        assert 99 in items

    def test_resolves_spawn_refs_recursively(self):
        """Spawn references are resolved through the chain."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=200, weight=10),
                ],
            ),
            200: SpawnTable(
                id=200,
                table_entries=[
                    SpawnTableEntry(ref_type="asset", ref_id=42, weight=10),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert 42 in items

    def test_handles_circular_refs(self):
        """Circular spawn references don't infinite loop."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=200, weight=10),
                ],
            ),
            200: SpawnTable(
                id=200,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=100, weight=10),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert items == set()

    def test_missing_table_id(self):
        """Missing table IDs return empty set."""
        items = resolve_spawn_table_items(999, {})
        assert items == set()
