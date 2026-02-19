"""Tests for spawn table .dat parsing via the category system."""
import pytest
from pathlib import Path
from unturned_data.categories import parse_entry
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models import SpawnTable

FIXTURES = Path(__file__).parent / "fixtures"


class TestModernFormat:
    """Tests for the modern Tables [...] block format."""

    def test_parse_spawn_fixture(self):
        """Parse the existing spawn_sample fixture (modern format)."""
        raw = parse_dat_file(FIXTURES / "spawn_sample" / "Carepackage_Arena.dat")
        entry = parse_entry(raw, {}, "Spawns/Items/Carepackage_Arena")
        assert isinstance(entry, SpawnTable)
        assert entry.type == "Spawn"
        assert entry.id == 956
        # Fixture has 43 entries, all LegacyAssetId
        assert len(entry.table_entries) == 43
        assert entry.table_entries[0].ref_type == "asset"
        assert entry.table_entries[0].ref_id == 144
        assert entry.table_entries[0].weight == 200


class TestLegacyFormat:
    """Tests for the legacy Table_N_* indexed format."""

    def test_parse_legacy_spawn(self):
        """Parse a spawn table using the old indexed format."""
        # Simulate a legacy format .dat parse result
        raw = {
            "GUID": "f019fcaa2e8e4c92b17259025c80ff77",
            "Type": "Spawn",
            "ID": 228,
            "Tables": 3,
            "Table_0_Spawn_ID": 229,
            "Table_0_Weight": 31,
            "Table_1_Asset_ID": 1041,
            "Table_1_Weight": 10,
            "Table_2_Spawn_ID": 230,
            "Table_2_Weight": 52,
        }
        entry = parse_entry(raw, {}, "Spawns/Items/Militia")
        assert isinstance(entry, SpawnTable)
        assert len(entry.table_entries) == 3
        assert entry.table_entries[0].ref_type == "spawn"
        assert entry.table_entries[0].ref_id == 229
        assert entry.table_entries[1].ref_type == "asset"
        assert entry.table_entries[1].ref_id == 1041


class TestMixedModernFormat:
    """Tests for modern format with LegacySpawnId references."""

    def test_parse_mixed_refs(self):
        """Modern format can have LegacySpawnId, LegacyAssetId, and Guid."""
        raw = {
            "GUID": "dcb0974543f240b9aaddabe9d880e506",
            "Type": "Spawn",
            "ID": 551,
            "Tables": [
                {"LegacySpawnId": 646, "Weight": 175},
                {"LegacyAssetId": 1041, "Weight": 50},
                {"Guid": "e322656746a045a98eb6e5a6650a104e", "Weight": 5},
            ],
        }
        entry = parse_entry(raw, {}, "Spawns/Items/Military_Low")
        assert isinstance(entry, SpawnTable)
        assert len(entry.table_entries) == 3
        assert entry.table_entries[0].ref_type == "spawn"
        assert entry.table_entries[0].ref_id == 646
        assert entry.table_entries[1].ref_type == "asset"
        assert entry.table_entries[1].ref_id == 1041
        assert entry.table_entries[2].ref_type == "guid"
        assert entry.table_entries[2].ref_guid == "e322656746a045a98eb6e5a6650a104e"
