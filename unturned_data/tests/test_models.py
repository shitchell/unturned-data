"""
Tests for shared stat dataclasses and base BundleEntry model.

Covers: DamageStats, ConsumableStats, StorageStats, Blueprint, BundleEntry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models import (
    Blueprint,
    BlueprintCondition,
    BlueprintReward,
    BundleEntry,
    ConsumableStats,
    CraftingBlacklist,
    DamageStats,
    SpawnTable,
    SpawnTableEntry,
    StorageStats,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> tuple[dict, dict]:
    """Helper: load raw + english from a fixture directory."""
    fixture_dir = FIXTURES / name
    # Find the main .dat file (not English.dat)
    dat_files = [f for f in fixture_dir.glob("*.dat") if f.name != "English.dat"]
    assert dat_files, f"No .dat files in {fixture_dir}"
    raw = parse_dat_file(dat_files[0])
    english = load_english_dat(fixture_dir / "English.dat")
    return raw, english


# ---------------------------------------------------------------------------
# TestDamageStats
# ---------------------------------------------------------------------------
class TestDamageStats:
    """DamageStats.from_raw parsing."""

    def test_gun_fixture(self):
        raw, _ = _load_fixture("gun_maplestrike")
        ds = DamageStats.from_raw(raw)
        assert ds is not None
        assert ds.player == 40
        assert ds.zombie == 99
        assert ds.animal == 40
        # Multipliers
        assert ds.player_multipliers["skull"] == 1.1
        assert ds.player_multipliers["spine"] == 0.8
        assert ds.player_multipliers["arm"] == 0.6
        assert ds.player_multipliers["leg"] == 0.6
        assert ds.zombie_multipliers["skull"] == 1.1
        assert ds.zombie_multipliers["spine"] == 0.6
        assert ds.zombie_multipliers["arm"] == 0.3
        assert ds.zombie_multipliers["leg"] == 0.3
        assert ds.animal_multipliers["skull"] == 1.1
        assert ds.animal_multipliers["spine"] == 0.8
        assert ds.animal_multipliers["leg"] == 0.6
        # Environmental damage
        assert ds.barricade == 20
        assert ds.structure == 15
        assert ds.vehicle == 35
        assert ds.resource == 15
        assert ds.object == 25

    def test_food_returns_none(self):
        raw, _ = _load_fixture("food_beans")
        ds = DamageStats.from_raw(raw)
        assert ds is None

    def test_melee_fixture(self):
        raw, _ = _load_fixture("melee_katana")
        ds = DamageStats.from_raw(raw)
        assert ds is not None
        assert ds.player == 50
        assert ds.zombie == 50
        assert ds.animal == 50
        assert ds.barricade == 2
        assert ds.structure == 2
        assert ds.vehicle == 15
        assert ds.resource == 25
        assert ds.object == 20
        # Multipliers
        assert ds.player_multipliers["skull"] == 1.1
        assert ds.animal_multipliers["spine"] == 0.6

    def test_barricade_with_damage(self):
        """Barbed wire has Player/Zombie/Animal_Damage but no multipliers."""
        raw, _ = _load_fixture("barricade_wire")
        ds = DamageStats.from_raw(raw)
        assert ds is not None
        assert ds.player == 40
        assert ds.zombie == 80
        assert ds.animal == 80
        # No multiplier keys in barbed wire -- should default to empty dicts
        assert ds.player_multipliers == {}
        assert ds.zombie_multipliers == {}
        assert ds.animal_multipliers == {}

    def test_animal_uses_damage_key(self):
        """Bear uses 'Damage' key for its attack damage, not Player_Damage etc."""
        raw, _ = _load_fixture("animal_bear")
        ds = DamageStats.from_raw(raw)
        # Bear has Damage 20 but no Player_Damage/Zombie_Damage/Animal_Damage
        # The spec says animals use just "Damage" -- from_raw should detect this
        assert ds is not None
        assert ds.animal == 20


# ---------------------------------------------------------------------------
# TestConsumableStats
# ---------------------------------------------------------------------------
class TestConsumableStats:
    """ConsumableStats.from_raw parsing."""

    def test_food_fixture(self):
        raw, _ = _load_fixture("food_beans")
        cs = ConsumableStats.from_raw(raw)
        assert cs is not None
        assert cs.food == 55
        assert cs.health == 10
        assert cs.water == 0
        assert cs.virus == 0
        assert cs.vision == 0

    def test_water_berries(self):
        raw, _ = _load_fixture("water_berries")
        cs = ConsumableStats.from_raw(raw)
        assert cs is not None
        assert cs.virus == 5
        assert cs.vision == 20
        assert cs.food == 5
        assert cs.water == 10
        assert cs.health == 10

    def test_gun_returns_none(self):
        raw, _ = _load_fixture("gun_maplestrike")
        cs = ConsumableStats.from_raw(raw)
        assert cs is None

    def test_bandage_with_bleeding_modifier(self):
        raw, _ = _load_fixture("medical_bandage")
        cs = ConsumableStats.from_raw(raw)
        assert cs is not None
        assert cs.bleeding_modifier == "Heal"
        assert cs.health == 15

    def test_structure_with_health_returns_none(self):
        """Structures have Health but aren't consumables."""
        raw, _ = _load_fixture("structure_wall")
        cs = ConsumableStats.from_raw(raw)
        assert cs is None


# ---------------------------------------------------------------------------
# TestStorageStats
# ---------------------------------------------------------------------------
class TestStorageStats:
    """StorageStats.from_raw parsing."""

    def test_backpack(self):
        raw, _ = _load_fixture("backpack_alice")
        ss = StorageStats.from_raw(raw)
        assert ss is not None
        assert ss.width == 8
        assert ss.height == 7

    def test_food_returns_none(self):
        raw, _ = _load_fixture("food_beans")
        ss = StorageStats.from_raw(raw)
        assert ss is None


# ---------------------------------------------------------------------------
# TestBlueprint
# ---------------------------------------------------------------------------
class TestBlueprint:
    """Blueprint.list_from_raw parsing."""

    def test_bandage(self):
        raw, _ = _load_fixture("medical_bandage")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        # Bandage blueprint has no name, has InputItems and OutputItems
        assert isinstance(bp.inputs, list)
        assert isinstance(bp.outputs, list)

    def test_maplestrike(self):
        raw, _ = _load_fixture("gun_maplestrike")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 2
        names = [bp.name for bp in bps]
        assert "Repair" in names
        assert "Salvage" in names

    def test_sandwich(self):
        raw, _ = _load_fixture("food_sandwich")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        assert bp.skill == "Cook"
        assert bp.skill_level == 2
        assert len(bp.workstation_tags) == 1

    def test_bear_empty_list(self):
        raw, _ = _load_fixture("animal_bear")
        bps = Blueprint.list_from_raw(raw)
        assert bps == []

    def test_ace_blueprints(self):
        raw, _ = _load_fixture("gun_ace")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 2
        repair = [bp for bp in bps if bp.name == "Repair"][0]
        assert repair.operation == "RepairTargetItem"
        assert len(repair.inputs) > 0
        assert len(repair.workstation_tags) == 1

    def test_legacy_single_blueprint(self):
        """Legacy indexed format with one Supply blueprint."""
        raw, _ = _load_fixture("legacy_blueprint_single")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        assert bp.name == "Craft"
        assert bp.inputs == ["36021"]
        # No explicit products -> output is "this"
        assert bp.outputs == ["this"]

    def test_legacy_multi_blueprint(self):
        """Legacy indexed format with two blueprints, tool, and products."""
        raw, _ = _load_fixture("legacy_blueprint_multi")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 2

        bp0 = bps[0]
        assert bp0.name == "Craft"
        # Two supplies + a tool
        assert "17 x 9" in bp0.inputs
        assert "67 x 3" in bp0.inputs
        # Tool should be a dict with Delete=False
        tools = [i for i in bp0.inputs if isinstance(i, dict)]
        assert len(tools) == 1
        assert tools[0]["ID"] == "76"
        assert tools[0]["Delete"] is False
        # No explicit products -> "this"
        assert bp0.outputs == ["this"]

        bp1 = bps[1]
        assert bp1.name == "Craft"
        assert bp1.inputs == ["363"]
        assert bp1.outputs == ["17 x 5"]

    def test_legacy_repair_blueprint(self):
        """Legacy Repair type gets name='Repair' and no implied output."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Repair",
            "Blueprint_0_Supply_0_ID": 67,
            "Blueprint_0_Supply_0_Amount": 2,
        }
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        assert bp.name == "Repair"
        assert bp.inputs == ["67 x 2"]
        # Repair type should NOT get "this" as output
        assert bp.outputs == []

    def test_legacy_output_key_parsed(self):
        """Legacy blueprints use Output_N_ID, not Product_N_ID."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Tool",
            "Blueprint_0_Output_0_ID": 36011,
            "Blueprint_0_Output_0_Amount": 3,
        }
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        assert bps[0].outputs == ["36011 x 3"]

    def test_legacy_single_output(self):
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Output_0_ID": 100,
            "Blueprint_0_Output_0_Amount": 1,
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].outputs == ["100"]

    def test_legacy_no_outputs_defaults_to_this(self):
        """Craft blueprints with no outputs should still default to 'this'."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Supply_0_ID": 50,
            "Blueprint_0_Supply_0_Amount": 2,
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].outputs == ["this"]

    def test_legacy_tool_type_is_salvage(self):
        """Type Tool blueprints should be classified as Salvage."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Tool",
            "Blueprint_0_Output_0_ID": 36011,
            "Blueprint_0_Output_0_Amount": 3,
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].name == "Salvage"

    def test_legacy_integer_zero_returns_empty(self):
        """Blueprints 0 should return empty list."""
        raw = {"Blueprints": 0}
        bps = Blueprint.list_from_raw(raw)
        assert bps == []


class TestBlueprintLegacySkillBuild:
    def test_extracts_skill(self):
        from unturned_data.models import Blueprint

        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Skill": "Cook",
            "Blueprint_0_Level": "2",
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].skill == "Cook"
        assert bps[0].skill_level == 2

    def test_extracts_build(self):
        from unturned_data.models import Blueprint

        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Build": "Torch",
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].build == "Torch"

    def test_defaults_when_missing(self):
        from unturned_data.models import Blueprint

        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].skill == ""
        assert bps[0].skill_level == 0
        assert bps[0].build == ""


# ---------------------------------------------------------------------------
# TestBlueprintConditionsRewards
# ---------------------------------------------------------------------------
class TestBlueprintConditionsRewards:
    """Tests for Blueprint conditions, rewards, and new fields."""

    def test_legacy_blueprint_conditions(self):
        raw, _ = _load_fixture("legacy_blueprint_conditions")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        assert len(bp.conditions) == 1
        cond = bp.conditions[0]
        assert cond.type == "Holiday"
        assert cond.value == "Christmas"

    def test_legacy_blueprint_state_transfer(self):
        raw, _ = _load_fixture("legacy_blueprint_conditions")
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].state_transfer is True

    def test_legacy_blueprint_tool_critical(self):
        raw, _ = _load_fixture("legacy_blueprint_conditions")
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].tool_critical is True

    def test_legacy_blueprint_map(self):
        raw, _ = _load_fixture("legacy_blueprint_conditions")
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].map == "PEI"

    def test_legacy_blueprint_rewards(self):
        raw, _ = _load_fixture("legacy_blueprint_conditions")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        bp = bps[0]
        assert len(bp.rewards) == 1
        rew = bp.rewards[0]
        assert rew.type == "Experience"
        assert rew.value == 5

    def test_blueprint_condition_serializes(self):
        cond = BlueprintCondition(
            type="Holiday", value="Christmas", logic="Equal", id="cond1"
        )
        d = cond.model_dump()
        assert d == {
            "type": "Holiday",
            "value": "Christmas",
            "logic": "Equal",
            "id": "cond1",
        }

    def test_blueprint_reward_serializes(self):
        rew = BlueprintReward(
            type="Experience", id="rew1", value=10, modification="Add"
        )
        d = rew.model_dump()
        assert d == {
            "type": "Experience",
            "id": "rew1",
            "value": 10,
            "modification": "Add",
        }

    def test_new_fields_default_values(self):
        """New fields should default correctly when not present."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Supply_0_ID": 50,
            "Blueprint_0_Supply_0_Amount": 1,
        }
        bps = Blueprint.list_from_raw(raw)
        bp = bps[0]
        assert bp.state_transfer is False
        assert bp.tool_critical is False
        assert bp.map == ""
        assert bp.level == 0
        assert bp.conditions == []
        assert bp.rewards == []

    def test_legacy_blueprint_level_synced(self):
        """level field should match skill_level for legacy blueprints."""
        raw = {
            "Blueprints": 1,
            "Blueprint_0_Type": "Supply",
            "Blueprint_0_Skill": "Cook",
            "Blueprint_0_Level": "3",
        }
        bps = Blueprint.list_from_raw(raw)
        assert bps[0].skill_level == 3
        assert bps[0].level == 3


# ---------------------------------------------------------------------------
# TestBundleEntry
# ---------------------------------------------------------------------------
class TestBundleEntry:
    """BundleEntry.from_raw basic test."""

    def test_from_raw_basic(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = BundleEntry.from_raw(raw, english, "gun_maplestrike")
        assert entry.guid == "38508a1f73c8417a8a68cb675460d0b6"
        assert entry.type == "Gun"
        assert entry.id == 363
        assert entry.name == "Maplestrike"
        assert (
            entry.description
            == "Canadian assault rifle chambered in Military ammunition."
        )
        assert entry.rarity == "Epic"
        assert entry.size_x == 4
        assert entry.size_y == 2
        assert entry.source_path == "gun_maplestrike"

    def test_model_dump(self):
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        assert isinstance(d, dict)
        assert d["guid"] == "78fefdd23def4ab6ac8301adfcc3b2d4"
        assert d["name"] == "Canned Beans"
        assert d["type"] == "Food"
        assert d["category"] == ["Items", "Food"]

    def test_markdown_columns(self):
        cols = BundleEntry.markdown_columns()
        assert isinstance(cols, list)
        assert len(cols) > 0
        assert "Name" in cols

    def test_markdown_row(self):
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "food_beans")
        row = entry.markdown_row({})
        assert isinstance(row, list)
        assert len(row) == len(BundleEntry.markdown_columns())

    def test_from_raw_missing_fields(self):
        """Entry with minimal fields should still work."""
        raw, english = _load_fixture("animal_bear")
        entry = BundleEntry.from_raw(raw, english, "animal_bear")
        assert entry.guid == "b1db3548447c4cde9f92d274e22f57a2"
        assert entry.type == "Animal"
        assert entry.name == "Bear"
        assert entry.rarity == ""
        assert entry.description == ""


# ---------------------------------------------------------------------------
# TestCraftingBlacklist
# ---------------------------------------------------------------------------
class TestCraftingBlacklist:
    def test_default_allows_core(self):
        bl = CraftingBlacklist()
        assert bl.allow_core_blueprints is True
        assert bl.blocked_inputs == set()
        assert bl.blocked_outputs == set()

    def test_blocks_core(self):
        bl = CraftingBlacklist(allow_core_blueprints=False)
        assert bl.allow_core_blueprints is False

    def test_merge_combines_blocks(self):
        a = CraftingBlacklist(
            allow_core_blueprints=True,
            blocked_inputs={"guid-a"},
        )
        b = CraftingBlacklist(
            allow_core_blueprints=False,
            blocked_outputs={"guid-b"},
        )
        merged = CraftingBlacklist.merge([a, b])
        assert merged.allow_core_blueprints is False
        assert merged.blocked_inputs == {"guid-a"}
        assert merged.blocked_outputs == {"guid-b"}

    def test_merge_empty_list(self):
        merged = CraftingBlacklist.merge([])
        assert merged.allow_core_blueprints is True


# ---------------------------------------------------------------------------
# TestBundleEntrySchemaC
# ---------------------------------------------------------------------------
class TestBundleEntrySchemaC:
    """Tests for Schema C output shape from model_dump()."""

    def test_schema_c_keys_present(self):
        """model_dump() should include all Schema C top-level keys."""
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        expected_keys = {
            "guid",
            "type",
            "id",
            "name",
            "description",
            "rarity",
            "size_x",
            "size_y",
            "source_path",
            "english",
            "raw",
            "blueprints",
            "category",
            "parsed",
        }
        assert expected_keys == set(d.keys())

    def test_schema_c_category_computed(self):
        """category computed_field should appear in model_dump()."""
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        assert d["category"] == ["Items", "Food"]

    def test_schema_c_parsed_empty_for_base(self):
        """Base BundleEntry parsed should be empty dict."""
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        assert d["parsed"] == {}

    def test_schema_c_english_stored(self):
        """english field should contain the full English.dat dict."""
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        assert d["english"]["Name"] == "Canned Beans"

    def test_schema_c_raw_stored(self):
        """raw field should contain the full .dat dict."""
        raw, english = _load_fixture("food_beans")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/food_beans")
        d = entry.model_dump()
        assert d["raw"]["Type"] == "Food"

    def test_schema_c_blueprints_serialized(self):
        """blueprints should serialize to list in model_dump()."""
        raw, english = _load_fixture("gun_maplestrike")
        entry = BundleEntry.from_raw(raw, english, "gun_maplestrike")
        d = entry.model_dump()
        assert isinstance(d["blueprints"], list)
        assert len(d["blueprints"]) == 2

    def test_schema_c_empty_source_path(self):
        """Empty source_path should produce empty category."""
        entry = BundleEntry(guid="abc", type="Test", source_path="")
        d = entry.model_dump()
        assert d["category"] == []

    def test_schema_c_single_segment_path(self):
        """Single segment source_path should produce empty category."""
        entry = BundleEntry(guid="abc", type="Test", source_path="Animals")
        d = entry.model_dump()
        assert d["category"] == []


# ---------------------------------------------------------------------------
# TestSpawnTableSchemaC
# ---------------------------------------------------------------------------
class TestSpawnTableSchemaC:
    """Tests for SpawnTable and SpawnTableEntry Pydantic models."""

    def test_spawn_table_entry_model_dump(self):
        e = SpawnTableEntry(ref_type="asset", ref_id=42, weight=10)
        d = e.model_dump()
        assert d == {"ref_type": "asset", "ref_id": 42, "ref_guid": "", "weight": 10}

    def test_spawn_table_model_dump(self):
        from unturned_data.models import SpawnTable, SpawnTableEntry

        entries = [SpawnTableEntry(ref_type="asset", ref_id=42, weight=10)]
        table = SpawnTable(
            guid="abc",
            type="Spawn",
            id=1,
            name="Test",
            source_path="Spawns/Test",
            table_entries=entries,
        )
        d = table.model_dump()
        assert "table_entries" in d
        assert d["table_entries"][0]["ref_type"] == "asset"
        assert "category" in d
        assert d["category"] == ["Spawns"]


# ---------------------------------------------------------------------------
# TestCraftingBlacklistPydantic
# ---------------------------------------------------------------------------
class TestCraftingBlacklistPydantic:
    """Tests for CraftingBlacklist as Pydantic BaseModel."""

    def test_model_dump_preserves_sets(self):
        """model_dump() preserves sets; model_dump(mode='json') converts to lists."""
        bl = CraftingBlacklist(
            blocked_inputs={"guid-a", "guid-b"},
            blocked_outputs={"guid-c"},
        )
        d = bl.model_dump()
        assert d["blocked_inputs"] == {"guid-a", "guid-b"}
        assert d["blocked_outputs"] == {"guid-c"}

        # JSON mode converts sets to lists (for JSON serialization)
        dj = bl.model_dump(mode="json")
        assert isinstance(dj["blocked_inputs"], list)
        assert set(dj["blocked_inputs"]) == {"guid-a", "guid-b"}
