"""
Tests for the crafting-graph formatter.

Covers node extraction, edge direction for salvage/craft/repair,
blueprint ID grouping, "this" references, GUID x N parsing,
object-format inputs, tool detection, and stub nodes.
"""
from __future__ import annotations

import json
from typing import Any

from unturned_data.models import Blueprint, BundleEntry
from unturned_data.formatters.crafting_fmt import (
    _parse_item_ref,
    build_crafting_graph,
    entries_to_crafting_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    guid: str = "",
    name: str = "",
    entry_type: str = "",
    rarity: str = "",
    source_path: str = "",
    blueprints: list[Blueprint] | None = None,
) -> BundleEntry:
    """Create a BundleEntry with an optional blueprints attribute.

    The base BundleEntry doesn't have a ``blueprints`` field;
    category models (Gun, Clothing, etc.) do.  We dynamically
    attach it for testing.
    """
    entry = BundleEntry(
        guid=guid,
        name=name,
        type=entry_type,
        rarity=rarity,
        source_path=source_path,
    )
    if blueprints is not None:
        entry.blueprints = blueprints  # type: ignore[attr-defined]
    return entry


def _make_blueprint(
    name: str = "",
    inputs: list | None = None,
    outputs: list | None = None,
    skill: str = "",
    skill_level: int = 0,
    workstation_tags: list[str] | None = None,
) -> Blueprint:
    """Create a Blueprint with sensible defaults."""
    return Blueprint(
        name=name,
        inputs=inputs or [],
        outputs=outputs or [],
        skill=skill,
        skill_level=skill_level,
        workstation_tags=workstation_tags or [],
    )


GUID_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"
GUID_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
GUID_C = "cccccccccccccccccccccccccccccccc"
GUID_D = "dddddddddddddddddddddddddddddd"
GUID_WS = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"  # workstation tag


# ---------------------------------------------------------------------------
# _parse_item_ref
# ---------------------------------------------------------------------------
class TestParseItemRef:
    """Low-level item reference parsing."""

    def test_this_literal(self):
        guid, qty, tool = _parse_item_ref("this", GUID_A)
        assert guid == GUID_A
        assert qty == 1
        assert tool is False

    def test_this_x_n(self):
        guid, qty, tool = _parse_item_ref("this x 3", GUID_A)
        assert guid == GUID_A
        assert qty == 3
        assert tool is False

    def test_guid_x_n(self):
        guid, qty, tool = _parse_item_ref(f"{GUID_B} x 5", GUID_A)
        assert guid == GUID_B
        assert qty == 5
        assert tool is False

    def test_bare_guid(self):
        guid, qty, tool = _parse_item_ref(GUID_C, GUID_A)
        assert guid == GUID_C
        assert qty == 1
        assert tool is False

    def test_object_with_amount(self):
        guid, qty, tool = _parse_item_ref(
            {"ID": GUID_B, "Amount": 4}, GUID_A
        )
        assert guid == GUID_B
        assert qty == 4
        assert tool is False

    def test_object_tool(self):
        guid, qty, tool = _parse_item_ref(
            {"ID": GUID_B, "Delete": False}, GUID_A
        )
        assert guid == GUID_B
        assert qty == 1
        assert tool is True

    def test_object_delete_true_not_tool(self):
        """Delete: true is not a tool marker."""
        guid, qty, tool = _parse_item_ref(
            {"ID": GUID_B, "Delete": True}, GUID_A
        )
        assert guid == GUID_B
        assert tool is False

    def test_unknown_string(self):
        guid, qty, tool = _parse_item_ref("not_a_guid", GUID_A)
        assert guid == ""
        assert qty == 0

    def test_none_item(self):
        guid, qty, tool = _parse_item_ref(None, GUID_A)
        assert guid == ""

    def test_uppercase_guid_lowered(self):
        upper = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1"
        guid, qty, tool = _parse_item_ref(upper, GUID_A)
        assert guid == upper.lower()

    def test_guid_x_n_uppercase_lowered(self):
        upper = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
        guid, qty, tool = _parse_item_ref(f"{upper} x 2", GUID_A)
        assert guid == upper.lower()


# ---------------------------------------------------------------------------
# Empty / no-blueprint entries
# ---------------------------------------------------------------------------
class TestEmptyInputs:
    """Edge cases with no entries or no blueprints."""

    def test_empty_entries(self):
        result = build_crafting_graph([], {})
        assert result == {"nodes": [], "edges": []}

    def test_entries_without_blueprints_excluded(self):
        """Entries with no blueprints attribute produce no nodes/edges."""
        entry = _make_entry(guid=GUID_A, name="Plain Item")
        result = build_crafting_graph([entry], {})
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_entries_with_empty_blueprints_excluded(self):
        """Entries with an empty blueprints list produce no nodes/edges."""
        entry = _make_entry(guid=GUID_A, name="No Recipes", blueprints=[])
        result = build_crafting_graph([entry], {})
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_entry_without_guid_skipped(self):
        """Entries with no GUID are silently skipped."""
        bp = _make_blueprint(inputs=[GUID_B], outputs=["this"])
        entry = _make_entry(guid="", name="No GUID", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert result["nodes"] == []
        assert result["edges"] == []


# ---------------------------------------------------------------------------
# Node extraction
# ---------------------------------------------------------------------------
class TestNodeExtraction:
    """Nodes are created for all items participating in blueprints."""

    def test_owner_node_created(self):
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B],
        )
        entry = _make_entry(
            guid=GUID_A, name="Owner Item", entry_type="Gun",
            rarity="Rare", source_path="Items/Guns/Owner",
            blueprints=[bp],
        )
        result = build_crafting_graph([entry], {})
        owner_node = _find_node(result, GUID_A)
        assert owner_node is not None
        assert owner_node["name"] == "Owner Item"
        assert owner_node["type"] == "Gun"
        assert owner_node["category"] == ["Items", "Guns"]
        assert owner_node["rarity"] == "Rare"

    def test_referenced_item_gets_stub_node(self):
        """Items referenced by GUID but not in entries get stub nodes."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B],
        )
        entry = _make_entry(
            guid=GUID_A, name="Owner", blueprints=[bp],
        )
        result = build_crafting_graph([entry], {})
        stub = _find_node(result, GUID_B)
        assert stub is not None
        # Bracket notation: first 8 chars
        assert stub["name"] == f"[{GUID_B[:8]}]"
        assert stub["type"] == ""
        assert stub["category"] == []
        assert stub["rarity"] == ""

    def test_guid_map_resolves_stub_name(self):
        """Stub nodes use guid_map for name resolution."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B],
        )
        entry = _make_entry(guid=GUID_A, name="Owner", blueprints=[bp])
        guid_map = {GUID_A: "Owner", GUID_B: "Metal Scrap"}
        result = build_crafting_graph([entry], guid_map)
        stub = _find_node(result, GUID_B)
        assert stub["name"] == "Metal Scrap"

    def test_no_duplicate_nodes(self):
        """Same GUID referenced multiple times creates only one node."""
        bp1 = _make_blueprint(
            name="Salvage", inputs=["this"], outputs=[GUID_B],
        )
        bp2 = _make_blueprint(
            inputs=[GUID_B], outputs=["this"],
        )
        entry = _make_entry(
            guid=GUID_A, name="Owner", blueprints=[bp1, bp2],
        )
        result = build_crafting_graph([entry], {})
        guids = [n["id"] for n in result["nodes"]]
        assert guids.count(GUID_A) == 1
        assert guids.count(GUID_B) == 1

    def test_multiple_entries_share_node(self):
        """Two entries referencing the same GUID don't duplicate nodes."""
        bp1 = _make_blueprint(
            name="Salvage", inputs=["this"], outputs=[GUID_C],
        )
        bp2 = _make_blueprint(
            name="Salvage", inputs=["this"], outputs=[GUID_C],
        )
        e1 = _make_entry(guid=GUID_A, name="Item A", blueprints=[bp1])
        e2 = _make_entry(guid=GUID_B, name="Item B", blueprints=[bp2])
        result = build_crafting_graph([e1, e2], {})
        guids = [n["id"] for n in result["nodes"]]
        assert guids.count(GUID_C) == 1


# ---------------------------------------------------------------------------
# Salvage edges
# ---------------------------------------------------------------------------
class TestSalvageEdges:
    """Salvage: owner item broken down into outputs."""

    def test_salvage_direction(self):
        """Salvage edge: source=owner, target=output."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[f"{GUID_B} x 3"],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        assert edge["source"] == GUID_A
        assert edge["target"] == GUID_B
        assert edge["type"] == "salvage"
        assert edge["quantity"] == 3

    def test_salvage_multiple_outputs(self):
        """Salvage with multiple outputs creates multiple edges."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B, f"{GUID_C} x 2"],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 2
        targets = {e["target"] for e in result["edges"]}
        assert targets == {GUID_B, GUID_C}
        # Check quantities
        for edge in result["edges"]:
            if edge["target"] == GUID_B:
                assert edge["quantity"] == 1
            elif edge["target"] == GUID_C:
                assert edge["quantity"] == 2


# ---------------------------------------------------------------------------
# Repair edges
# ---------------------------------------------------------------------------
class TestRepairEdges:
    """Repair: inputs repair the owner item."""

    def test_repair_direction(self):
        """Repair edge: source=input, target=owner."""
        bp = _make_blueprint(
            name="Repair",
            inputs=[
                {"ID": GUID_B, "Amount": 4},
                {"ID": GUID_C, "Delete": False},
            ],
            skill="Repair",
            skill_level=3,
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 2

        # Material input
        mat_edge = _find_edge(result, source=GUID_B, target=GUID_A)
        assert mat_edge is not None
        assert mat_edge["type"] == "repair"
        assert mat_edge["quantity"] == 4
        assert mat_edge["tool"] is False
        assert mat_edge["skill"] == "Repair"
        assert mat_edge["skillLevel"] == 3

        # Tool input
        tool_edge = _find_edge(result, source=GUID_C, target=GUID_A)
        assert tool_edge is not None
        assert tool_edge["type"] == "repair"
        assert tool_edge["tool"] is True
        assert tool_edge["quantity"] == 1

    def test_repair_workstations(self):
        """Repair edges include resolved workstation names."""
        bp = _make_blueprint(
            name="Repair",
            inputs=[{"ID": GUID_B, "Amount": 2}],
            workstation_tags=[GUID_WS],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        guid_map = {GUID_WS: "Workbench"}
        result = build_crafting_graph([entry], guid_map)
        assert result["edges"][0]["workstations"] == ["Workbench"]

    def test_repair_workstation_unresolved(self):
        """Unresolved workstation tag uses bracket notation."""
        bp = _make_blueprint(
            name="Repair",
            inputs=[{"ID": GUID_B, "Amount": 2}],
            workstation_tags=[GUID_WS],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert result["edges"][0]["workstations"] == [f"[{GUID_WS[:8]}]"]


# ---------------------------------------------------------------------------
# Craft edges
# ---------------------------------------------------------------------------
class TestCraftEdges:
    """Craft: inputs create the output."""

    def test_craft_this_output(self):
        """Craft with output='this': inputs -> owner."""
        bp = _make_blueprint(
            inputs=[f"{GUID_B} x 2", GUID_C],
            outputs=["this"],
        )
        entry = _make_entry(guid=GUID_A, name="Bandage", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 2
        for edge in result["edges"]:
            assert edge["target"] == GUID_A
            assert edge["type"] == "craft"

        e1 = _find_edge(result, source=GUID_B, target=GUID_A)
        assert e1["quantity"] == 2

        e2 = _find_edge(result, source=GUID_C, target=GUID_A)
        assert e2["quantity"] == 1

    def test_craft_empty_output_targets_owner(self):
        """Craft with no outputs: inputs -> owner."""
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=[],
        )
        entry = _make_entry(guid=GUID_A, name="Widget", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 1
        assert result["edges"][0]["target"] == GUID_A

    def test_craft_specific_output(self):
        """Craft with a specific output GUID: inputs -> output GUID."""
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=[GUID_C],
        )
        entry = _make_entry(guid=GUID_A, name="Owner", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert len(result["edges"]) == 1
        edge = result["edges"][0]
        assert edge["source"] == GUID_B
        assert edge["target"] == GUID_C

    def test_craft_skill_fields(self):
        """Craft edges carry skill and skillLevel."""
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=["this"],
            skill="Cook",
            skill_level=2,
        )
        entry = _make_entry(guid=GUID_A, name="Sandwich", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        edge = result["edges"][0]
        assert edge["skill"] == "Cook"
        assert edge["skillLevel"] == 2

    def test_craft_object_input(self):
        """Craft with object-format inputs."""
        bp = _make_blueprint(
            inputs=[{"ID": GUID_B, "Amount": 3}],
            outputs=["this"],
        )
        entry = _make_entry(guid=GUID_A, name="Widget", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        edge = result["edges"][0]
        assert edge["source"] == GUID_B
        assert edge["quantity"] == 3
        assert edge["tool"] is False


# ---------------------------------------------------------------------------
# Blueprint ID grouping
# ---------------------------------------------------------------------------
class TestBlueprintIdGrouping:
    """Each blueprint gets a unique blueprintId; edges from the same
    blueprint share the same ID."""

    def test_same_blueprint_same_id(self):
        """Multiple inputs in one blueprint share the same blueprintId."""
        bp = _make_blueprint(
            name="Repair",
            inputs=[
                {"ID": GUID_B, "Amount": 4},
                {"ID": GUID_C, "Delete": False},
            ],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        bp_ids = {e["blueprintId"] for e in result["edges"]}
        assert len(bp_ids) == 1

    def test_different_blueprints_different_ids(self):
        """Two blueprints on the same entry get different IDs."""
        bp1 = _make_blueprint(
            name="Repair",
            inputs=[{"ID": GUID_B, "Amount": 2}],
        )
        bp2 = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_C],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp1, bp2])
        result = build_crafting_graph([entry], {})
        bp_ids = [e["blueprintId"] for e in result["edges"]]
        assert len(set(bp_ids)) == 2

    def test_blueprints_across_entries_different_ids(self):
        """Blueprints on different entries get different IDs."""
        bp1 = _make_blueprint(
            name="Salvage", inputs=["this"], outputs=[GUID_C],
        )
        bp2 = _make_blueprint(
            name="Salvage", inputs=["this"], outputs=[GUID_C],
        )
        e1 = _make_entry(guid=GUID_A, name="Gun A", blueprints=[bp1])
        e2 = _make_entry(guid=GUID_B, name="Gun B", blueprints=[bp2])
        result = build_crafting_graph([e1, e2], {})
        bp_ids = [e["blueprintId"] for e in result["edges"]]
        assert len(set(bp_ids)) == 2


# ---------------------------------------------------------------------------
# "this" reference handling
# ---------------------------------------------------------------------------
class TestThisReference:
    """The literal 'this' in inputs/outputs refers to the owning item."""

    def test_salvage_this_input_ignored_for_edges(self):
        """Salvage blueprints often have 'this' as input -- we only
        care about the outputs for edge direction."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        # Only output edges, no self-loop from "this" input
        assert len(result["edges"]) == 1
        assert result["edges"][0]["source"] == GUID_A
        assert result["edges"][0]["target"] == GUID_B

    def test_craft_this_output_resolves_to_owner(self):
        """Craft output 'this' means the crafted item is the owner."""
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=["this"],
        )
        entry = _make_entry(guid=GUID_A, name="Bandage", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert result["edges"][0]["target"] == GUID_A

    def test_this_x_n_in_output(self):
        """'this x 3' as output resolves to owner GUID."""
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=["this x 3"],
        )
        entry = _make_entry(guid=GUID_A, name="Widget", blueprints=[bp])
        result = build_crafting_graph([entry], {})
        assert result["edges"][0]["target"] == GUID_A


# ---------------------------------------------------------------------------
# entries_to_crafting_json (top-level serializer)
# ---------------------------------------------------------------------------
class TestEntriesToCraftingJson:
    """Top-level JSON serializer."""

    def test_empty_entries(self):
        result = entries_to_crafting_json([])
        parsed = json.loads(result)
        assert parsed == {"nodes": [], "edges": []}

    def test_produces_valid_json(self):
        bp = _make_blueprint(
            inputs=[GUID_B],
            outputs=["this"],
        )
        entry = _make_entry(
            guid=GUID_A, name="Widget",
            entry_type="Shirt", rarity="Uncommon",
            blueprints=[bp],
        )
        result = entries_to_crafting_json([entry])
        parsed = json.loads(result)
        assert "nodes" in parsed
        assert "edges" in parsed
        assert len(parsed["nodes"]) == 2
        assert len(parsed["edges"]) == 1

    def test_indent_parameter(self):
        bp = _make_blueprint(inputs=[GUID_B], outputs=["this"])
        entry = _make_entry(guid=GUID_A, name="Widget", blueprints=[bp])
        result = entries_to_crafting_json([entry], indent=2)
        assert "\n" in result  # indented output has newlines

    def test_supplementary_guids_resolve(self):
        """Supplementary GUIDs are used for stub node names."""
        bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[GUID_B],
        )
        entry = _make_entry(guid=GUID_A, name="Gun", blueprints=[bp])
        result = entries_to_crafting_json(
            [entry], supplementary_guids={GUID_B: "Scrap Metal"}
        )
        parsed = json.loads(result)
        stub = _find_node(parsed, GUID_B)
        assert stub["name"] == "Scrap Metal"


# ---------------------------------------------------------------------------
# Integration: fixture-like scenario
# ---------------------------------------------------------------------------
class TestIntegration:
    """Realistic multi-blueprint scenario mimicking Maplestrike data."""

    def test_maplestrike_like(self):
        """Simulates a gun with Repair + Salvage blueprints."""
        owner_guid = "38508a1f73c8417a8a68cb675460d0b6"
        scrap_guid = "21ede8ebffb14c5580e8c7ad149e335e"
        tool_guid = "5830b84bf8074caa91cf3f4dde0dd19e"
        ws_guid = "7b82c125a5a54984b8bb26576b59e977"

        repair_bp = _make_blueprint(
            name="Repair",
            inputs=[
                {"ID": scrap_guid, "Amount": 4},
                {"ID": tool_guid, "Delete": False},
            ],
            skill="Repair",
            skill_level=3,
            workstation_tags=[ws_guid],
        )
        salvage_bp = _make_blueprint(
            name="Salvage",
            inputs=["this"],
            outputs=[f"{scrap_guid} x 3"],
        )

        entry = _make_entry(
            guid=owner_guid,
            name="Maplestrike",
            entry_type="Gun",
            rarity="Epic",
            source_path="Items/Guns/Maplestrike",
            blueprints=[repair_bp, salvage_bp],
        )

        guid_map = {
            owner_guid: "Maplestrike",
            scrap_guid: "Military Scrap",
            tool_guid: "Blowtorch",
            ws_guid: "Workshop",
        }

        result = build_crafting_graph([entry], guid_map)

        # Nodes: owner + scrap + tool = 3 unique
        assert len(result["nodes"]) == 3
        owner_node = _find_node(result, owner_guid)
        assert owner_node["name"] == "Maplestrike"
        assert owner_node["type"] == "Gun"

        scrap_node = _find_node(result, scrap_guid)
        assert scrap_node["name"] == "Military Scrap"

        tool_node = _find_node(result, tool_guid)
        assert tool_node["name"] == "Blowtorch"

        # Edges: 2 repair inputs + 1 salvage output = 3
        assert len(result["edges"]) == 3

        # Repair edges: input -> owner
        repair_edges = [e for e in result["edges"] if e["type"] == "repair"]
        assert len(repair_edges) == 2
        for re_edge in repair_edges:
            assert re_edge["target"] == owner_guid
            assert re_edge["workstations"] == ["Workshop"]

        scrap_repair = _find_edge(result, source=scrap_guid, target=owner_guid)
        assert scrap_repair["quantity"] == 4
        assert scrap_repair["tool"] is False

        tool_repair = _find_edge(result, source=tool_guid, target=owner_guid)
        assert tool_repair["tool"] is True

        # Salvage edge: owner -> scrap
        salvage_edges = [e for e in result["edges"] if e["type"] == "salvage"]
        assert len(salvage_edges) == 1
        assert salvage_edges[0]["source"] == owner_guid
        assert salvage_edges[0]["target"] == scrap_guid
        assert salvage_edges[0]["quantity"] == 3

        # Blueprint IDs: 2 blueprints = 2 unique IDs
        bp_ids = {e["blueprintId"] for e in result["edges"]}
        assert len(bp_ids) == 2

    def test_sandwich_like(self):
        """Simulates a food item with a Craft blueprint."""
        owner_guid = "34c726fe3bcf48c4add440627e3d6507"
        bread_guid = "4880f590a948465891188c5f96559340"
        meat_guid = "8592e8b68b334972b4a8b7acb8db7da1"
        ws_guid = "68816064e2ce44839c3f35da55033cba"

        bp = _make_blueprint(
            inputs=[
                f"{bread_guid} x 2",
                meat_guid,
            ],
            outputs=["this"],
            skill="Cook",
            skill_level=2,
            workstation_tags=[ws_guid],
        )

        entry = _make_entry(
            guid=owner_guid,
            name="Beef Sandwich",
            entry_type="Food",
            rarity="Common",
            source_path="Items/Food/Sandwich_Beef",
            blueprints=[bp],
        )

        guid_map = {
            owner_guid: "Beef Sandwich",
            bread_guid: "Bread",
            meat_guid: "Cooked Beef",
            ws_guid: "Campfire",
        }

        result = build_crafting_graph([entry], guid_map)

        # Nodes: owner + bread + meat = 3
        assert len(result["nodes"]) == 3

        # Edges: 2 inputs -> owner
        assert len(result["edges"]) == 2
        for edge in result["edges"]:
            assert edge["target"] == owner_guid
            assert edge["type"] == "craft"
            assert edge["skill"] == "Cook"
            assert edge["skillLevel"] == 2
            assert edge["workstations"] == ["Campfire"]

        bread_edge = _find_edge(result, source=bread_guid, target=owner_guid)
        assert bread_edge["quantity"] == 2

        meat_edge = _find_edge(result, source=meat_guid, target=owner_guid)
        assert meat_edge["quantity"] == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_node(
    result: dict[str, Any],
    guid: str,
) -> dict[str, Any] | None:
    """Find a node by GUID in the result dict."""
    for node in result["nodes"]:
        if node["id"] == guid:
            return node
    return None


def _find_edge(
    result: dict[str, Any],
    source: str,
    target: str,
) -> dict[str, Any] | None:
    """Find an edge by source and target in the result dict."""
    for edge in result["edges"]:
        if edge["source"] == source and edge["target"] == target:
            return edge
    return None
