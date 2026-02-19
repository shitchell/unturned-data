"""Tests for Schema C export models."""

from unturned_data.schema import (
    AssetEntry,
    CraftingBlacklistInfo,
    GuidIndex,
    GuidIndexEntry,
    LevelAssetInfo,
    Manifest,
    ManifestMapInfo,
    MapConfig,
    SpawnResolution,
)


class TestManifest:
    def test_default_values(self):
        m = Manifest()
        assert m.version == "1.0.0"
        assert m.schema_name == "unturned-data-export"
        assert m.maps == {}

    def test_with_maps(self):
        m = Manifest(
            generated_at="2026-02-19T14:30:00Z",
            generator="unturned_data v0.6.0",
            base_bundles_path="/path/to/Bundles",
            base_entry_count=4376,
            maps={"PEI": ManifestMapInfo(map_file="maps/pei/map.json")},
        )
        d = m.model_dump()
        assert d["base_entry_count"] == 4376
        assert "PEI" in d["maps"]
        assert d["maps"]["PEI"]["map_file"] == "maps/pei/map.json"


class TestMapConfig:
    def test_minimal(self):
        mc = MapConfig(name="PEI")
        d = mc.model_dump()
        assert d["name"] == "PEI"
        assert d["spawn_resolution"]["active_table_ids"] == []

    def test_with_blacklist(self):
        mc = MapConfig(
            name="A6 Polaris",
            crafting_blacklists=[
                CraftingBlacklistInfo(
                    guid="abc123",
                    allow_core_blueprints=False,
                    blocked_input_guids=["def456"],
                )
            ],
        )
        d = mc.model_dump()
        bl = d["crafting_blacklists"][0]
        assert bl["allow_core_blueprints"] is False
        assert bl["blocked_input_guids"] == ["def456"]


class TestGuidIndex:
    def test_structure(self):
        gi = GuidIndex(
            total_entries=2,
            entries={
                "abc123": GuidIndexEntry(
                    file="base/entries.json", index=0, type="Gun", name="AK"
                ),
                "def456": GuidIndexEntry(
                    file="maps/polaris/entries.json", index=5, type="Food", name="Berry"
                ),
            },
            by_id={"42": "abc123", "36001": "def456"},
        )
        d = gi.model_dump()
        assert d["total_entries"] == 2
        assert d["entries"]["abc123"]["name"] == "AK"
        assert d["by_id"]["42"] == "abc123"


class TestAssetEntry:
    def test_basic(self):
        a = AssetEntry(
            guid="aaa", name="Frost Craft", csharp_type="CraftingBlacklistAsset"
        )
        assert a.model_dump()["csharp_type"] == "CraftingBlacklistAsset"


class TestSpawnResolution:
    def test_table_chains(self):
        sr = SpawnResolution(
            active_table_ids=[228, 229],
            table_chains={228: [1041, 1042], 229: [1043]},
        )
        d = sr.model_dump()
        assert d["table_chains"][228] == [1041, 1042]
