"""Tests for SpawnTable and SpawnTableEntry models."""
import pytest
from unturned_data.models import SpawnTable, SpawnTableEntry


class TestSpawnTableEntry:
    def test_asset_entry(self):
        e = SpawnTableEntry(ref_type="asset", ref_id=1041, weight=10)
        assert e.ref_type == "asset"
        assert e.ref_id == 1041
        assert e.weight == 10
        assert e.ref_guid == ""

    def test_spawn_entry(self):
        e = SpawnTableEntry(ref_type="spawn", ref_id=229, weight=31)
        assert e.ref_type == "spawn"
        assert e.ref_id == 229

    def test_guid_entry(self):
        e = SpawnTableEntry(
            ref_type="guid",
            ref_guid="e322656746a045a98eb6e5a6650a104e",
            weight=5,
        )
        assert e.ref_type == "guid"
        assert e.ref_guid == "e322656746a045a98eb6e5a6650a104e"
        assert e.ref_id == 0


class TestSpawnTable:
    def test_basic_construction(self):
        entries = [
            SpawnTableEntry(ref_type="asset", ref_id=1041, weight=10),
            SpawnTableEntry(ref_type="spawn", ref_id=229, weight=31),
        ]
        table = SpawnTable(
            guid="907024f5c5b94642ae5f4123e0026f06",
            type="Spawn",
            id=654,
            name="Military_Low_Guns",
            source_path="Spawns/Items/Military_Low_Guns",
            table_entries=entries,
        )
        assert table.id == 654
        assert len(table.table_entries) == 2
        assert table.table_entries[0].ref_type == "asset"

    def test_model_dump(self):
        entries = [SpawnTableEntry(ref_type="asset", ref_id=42, weight=10)]
        table = SpawnTable(
            guid="abc", type="Spawn", id=1, name="Test",
            source_path="Spawns/Test", table_entries=entries,
        )
        d = table.model_dump()
        assert d["parsed"]["table_entries"] == [
            {"ref_type": "asset", "ref_id": 42, "ref_guid": "", "weight": 10}
        ]
