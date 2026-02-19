"""Tests for stub node enrichment in crafting graph builder."""
import json
import pytest

from unturned_data.formatters.crafting_fmt import entries_to_crafting_json
from unturned_data.models import BundleEntry, Blueprint, CraftingBlacklist


class TestStubNodeEnrichment:
    def _make_entry(self, guid, name, type_, source, maps=None, blueprints=None):
        entry = BundleEntry(
            guid=guid, type=type_, id=0, name=name,
            source_path=source, blueprints=blueprints or [],
        )
        if maps:
            entry._map_spawnable = set(maps)
        return entry

    def test_stub_inherits_maps_from_real_entry(self):
        """Stub nodes should inherit maps/type/rarity from the real entry."""
        cloth = self._make_entry(
            "aaa00000000000000000000000000001", "Cloth", "Supply",
            "Items/Supplies/Cloth", maps=["PEI", "Washington"],
        )
        cloth.rarity = "Common"

        bow = self._make_entry(
            "bbb00000000000000000000000000002", "Birch Bow", "Bow",
            "Items/Weapons/Birch_Bow",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["aaa00000000000000000000000000001 x 3"],
                outputs=["this"],
            )],
        )
        bow._map_spawnable = {"PEI"}

        output = entries_to_crafting_json([cloth, bow])
        data = json.loads(output)

        cloth_node = next(
            (n for n in data["nodes"] if n["name"] == "Cloth"), None
        )
        assert cloth_node is not None, "Cloth node should exist"
        assert cloth_node["type"] == "Supply", "Stub should inherit type"
        assert cloth_node["rarity"] == "Common", "Stub should inherit rarity"
        assert "PEI" in cloth_node["maps"], "Stub should inherit maps"
        assert "Washington" in cloth_node["maps"], "Stub should inherit maps"

    def test_unknown_stub_gets_empty_data(self):
        """Items not in the entries list should still get empty stub data."""
        bow = self._make_entry(
            "bbb00000000000000000000000000002", "Birch Bow", "Bow",
            "Items/Weapons/Birch_Bow",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ccc00000000000000000000000000003 x 2"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([bow])
        data = json.loads(output)

        unknown = next(
            (n for n in data["nodes"]
             if n["id"] == "ccc00000000000000000000000000003"),
            None,
        )
        assert unknown is not None
        assert unknown["maps"] == []
        assert unknown["type"] == ""

    def test_stub_gets_category_parts(self):
        """Stub nodes should inherit category_parts from real entries."""
        metal = self._make_entry(
            "ddd00000000000000000000000000004", "Metal Scrap", "Supply",
            "Items/Supplies/Scrap_Metal",
        )
        plate = self._make_entry(
            "eee00000000000000000000000000005", "Metal Plate", "Supply",
            "Items/Supplies/Metal_Plate",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ddd00000000000000000000000000004 x 3"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([metal, plate])
        data = json.loads(output)

        metal_node = next(
            (n for n in data["nodes"] if n["name"] == "Metal Scrap"), None
        )
        assert metal_node is not None
        assert metal_node["category"] == ["Items", "Supplies"]


class TestBlacklistFiltering:
    def _make_entry(self, guid, name, type_, source, maps=None, blueprints=None):
        entry = BundleEntry(
            guid=guid, type=type_, id=0, name=name,
            source_path=source, blueprints=blueprints or [],
        )
        if maps:
            entry._map_spawnable = set(maps)
        return entry

    def test_core_blueprints_excluded_when_blacklisted(self):
        """When allow_core_blueprints=False, base-game item blueprints are excluded."""
        # Base-game item (source_path starts with "Items/")
        tomato = self._make_entry(
            "aaa00000000000000000000000000001", "Tomato", "Food",
            "Items/Edible/Tomato",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["bbb00000000000000000000000000002 x 2"],
                outputs=["this"],
            )],
        )

        # Workshop map item (source_path starts with map-specific prefix)
        snowberry = self._make_entry(
            "ccc00000000000000000000000000003", "Snowberry", "Food",
            "Polaris/Items/Edible/Snowberry",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ddd00000000000000000000000000004 x 1"],
                outputs=["this"],
            )],
        )

        blacklists = {
            "A6 Polaris": CraftingBlacklist(allow_core_blueprints=False),
        }
        map_source_prefixes = {
            "A6 Polaris": ["Polaris/"],
        }

        output = entries_to_crafting_json(
            [tomato, snowberry],
            crafting_blacklists=blacklists,
            map_source_prefixes=map_source_prefixes,
        )
        data = json.loads(output)

        # Tomato blueprint edges should be excluded (core blueprint on blacklisted map)
        node_names = {n["name"] for n in data["nodes"]}
        edge_sources_targets = [(e["source"], e["target"]) for e in data["edges"]]
        assert "Snowberry" in node_names, "Workshop item should be present"
        # Find Tomato's guid in edges - should NOT be a target of any crafting edge
        tomato_edges = [e for e in data["edges"] if e["target"] == "aaa00000000000000000000000000001"]
        assert len(tomato_edges) == 0, "Core blueprint should be excluded"

    def test_no_blacklist_keeps_all_blueprints(self):
        """Without blacklists, all blueprints are included."""
        tomato = self._make_entry(
            "aaa00000000000000000000000000001", "Tomato", "Food",
            "Items/Edible/Tomato",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["bbb00000000000000000000000000002 x 2"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([tomato])
        data = json.loads(output)

        assert any(n["name"] == "Tomato" for n in data["nodes"])
        assert len(data["edges"]) > 0
