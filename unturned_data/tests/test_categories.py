"""
Tests for category type dispatch and properties population.

After the removal of per-type subclasses (Gun, MeleeWeapon, etc.),
all item types resolve to BundleEntry (or GenericEntry) with type-specific
data in the ``properties`` dict.  Special types (Animal, Vehicle, Spawn)
retain their own models.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.categories import (
    TYPE_REGISTRY,
    parse_entry,
    Animal,
    GenericEntry,
    Vehicle,
)
from unturned_data.models import BundleEntry, SpawnTable, SpawnTableEntry

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> tuple[dict, dict]:
    """Helper: load raw + english from a fixture directory."""
    fixture_dir = FIXTURES / name
    dat_files = [f for f in fixture_dir.glob("*.dat") if f.name != "English.dat"]
    assert dat_files, f"No .dat files in {fixture_dir}"
    from unturned_data.dat_parser import parse_dat_file
    from unturned_data.loader import load_english_dat
    raw = parse_dat_file(dat_files[0])
    english = load_english_dat(fixture_dir / "English.dat")
    return raw, english


# ---------------------------------------------------------------------------
# TestParseEntryReturnsBaseTypes
# ---------------------------------------------------------------------------
class TestParseEntryReturnsBaseTypes:
    """Item types now resolve to BundleEntry (via GenericEntry), not subclasses."""

    def test_gun_returns_bundle_entry(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = parse_entry(raw, english, "gun_maplestrike")
        # Should be a BundleEntry (GenericEntry), not a Gun subclass
        assert isinstance(entry, BundleEntry)
        assert type(entry).__name__ in ("BundleEntry", "GenericEntry")

    def test_melee_returns_bundle_entry(self):
        raw, english = _load_fixture("melee_katana")
        entry = parse_entry(raw, english, "melee_katana")
        assert isinstance(entry, BundleEntry)
        assert type(entry).__name__ in ("BundleEntry", "GenericEntry")

    def test_food_returns_bundle_entry(self):
        raw, english = _load_fixture("food_beans")
        entry = parse_entry(raw, english, "food_beans")
        assert isinstance(entry, BundleEntry)
        assert type(entry).__name__ in ("BundleEntry", "GenericEntry")

    def test_medical_returns_bundle_entry(self):
        raw, english = _load_fixture("medical_bandage")
        entry = parse_entry(raw, english, "medical_bandage")
        assert isinstance(entry, BundleEntry)

    def test_water_returns_bundle_entry(self):
        raw, english = _load_fixture("water_berries")
        entry = parse_entry(raw, english, "water_berries")
        assert isinstance(entry, BundleEntry)

    def test_backpack_returns_bundle_entry(self):
        raw, english = _load_fixture("backpack_alice")
        entry = parse_entry(raw, english, "backpack_alice")
        assert isinstance(entry, BundleEntry)

    def test_barricade_returns_bundle_entry(self):
        raw, english = _load_fixture("barricade_wire")
        entry = parse_entry(raw, english, "barricade_wire")
        assert isinstance(entry, BundleEntry)

    def test_structure_returns_bundle_entry(self):
        raw, english = _load_fixture("structure_wall")
        entry = parse_entry(raw, english, "structure_wall")
        assert isinstance(entry, BundleEntry)


# ---------------------------------------------------------------------------
# TestPropertiesPopulated
# ---------------------------------------------------------------------------
class TestPropertiesPopulated:
    """parse_entry() should populate the properties dict from PROPERTIES_REGISTRY."""

    def test_gun_properties(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = parse_entry(raw, english, "gun_maplestrike")
        assert entry.properties != {}
        assert "firerate" in entry.properties
        assert entry.properties["firerate"] == 5

    def test_melee_properties(self):
        raw, english = _load_fixture("melee_katana")
        entry = parse_entry(raw, english, "melee_katana")
        assert entry.properties != {}
        assert "range" in entry.properties

    def test_food_properties(self):
        raw, english = _load_fixture("food_beans")
        entry = parse_entry(raw, english, "food_beans")
        assert entry.properties != {}
        assert "food" in entry.properties
        assert entry.properties["food"] == 55

    def test_medical_properties(self):
        raw, english = _load_fixture("medical_bandage")
        entry = parse_entry(raw, english, "medical_bandage")
        assert entry.properties != {}
        assert "bleeding_modifier" in entry.properties

    def test_backpack_properties(self):
        raw, english = _load_fixture("backpack_alice")
        entry = parse_entry(raw, english, "backpack_alice")
        assert entry.properties != {}
        assert "width" in entry.properties
        assert entry.properties["width"] == 8

    def test_barricade_properties(self):
        raw, english = _load_fixture("barricade_wire")
        entry = parse_entry(raw, english, "barricade_wire")
        assert entry.properties != {}

    def test_structure_properties(self):
        raw, english = _load_fixture("structure_wall")
        entry = parse_entry(raw, english, "structure_wall")
        assert entry.properties != {}


# ---------------------------------------------------------------------------
# TestBaseFields
# ---------------------------------------------------------------------------
class TestBaseFieldsViaParseEntry:
    """Basic fields should still be correct on entries from parse_entry()."""

    def test_gun_base_fields(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = parse_entry(raw, english, "gun_maplestrike")
        assert entry.name == "Maplestrike"
        assert entry.type == "Gun"
        assert entry.id == 363
        assert entry.slot == "Primary"

    def test_food_base_fields(self):
        raw, english = _load_fixture("food_beans")
        entry = parse_entry(raw, english, "food_beans")
        assert entry.name == "Canned Beans"
        assert entry.type == "Food"

    def test_melee_base_fields(self):
        raw, english = _load_fixture("melee_katana")
        entry = parse_entry(raw, english, "melee_katana")
        assert entry.name == "Katana"
        assert entry.type == "Melee"

    def test_backpack_base_fields(self):
        raw, english = _load_fixture("backpack_alice")
        entry = parse_entry(raw, english, "backpack_alice")
        assert entry.name == "Alicepack"

    def test_barricade_base_fields(self):
        raw, english = _load_fixture("barricade_wire")
        entry = parse_entry(raw, english, "barricade_wire")
        assert entry.name == "Barbed Wire"

    def test_structure_base_fields(self):
        raw, english = _load_fixture("structure_wall")
        entry = parse_entry(raw, english, "structure_wall")
        assert entry.name == "Birch Doorway"


# ---------------------------------------------------------------------------
# TestBlueprintsPreserved
# ---------------------------------------------------------------------------
class TestBlueprintsPreserved:
    """Blueprint parsing should still work via parse_entry()."""

    def test_gun_blueprints(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = parse_entry(raw, english, "gun_maplestrike")
        assert len(entry.blueprints) == 2

    def test_melee_blueprints(self):
        raw, english = _load_fixture("melee_katana")
        entry = parse_entry(raw, english, "melee_katana")
        assert len(entry.blueprints) == 2

    def test_backpack_blueprints(self):
        raw, english = _load_fixture("backpack_alice")
        entry = parse_entry(raw, english, "backpack_alice")
        assert len(entry.blueprints) == 2

    def test_structure_blueprints(self):
        raw, english = _load_fixture("structure_wall")
        entry = parse_entry(raw, english, "structure_wall")
        assert len(entry.blueprints) == 2


# ---------------------------------------------------------------------------
# TestVehicle (kept as special type)
# ---------------------------------------------------------------------------
class TestVehicle:
    """Vehicle category model tests."""

    def test_parse_humvee(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert isinstance(vehicle, Vehicle)
        assert vehicle.name == "Armored Offroader"

    def test_speed_max(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert vehicle.speed_max == 14

    def test_fuel_capacity(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert vehicle.fuel_capacity == 2000

    def test_health_max(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert vehicle.health_max == 450

    def test_trunk(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert vehicle.trunk_x == 6
        assert vehicle.trunk_y == 5

    def test_speed_min(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert vehicle.speed_min == -6

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        assert len(vehicle.markdown_row({})) == len(Vehicle.markdown_columns())

    def test_model_dump(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        d = vehicle.model_dump()
        assert d["parsed"]["speed_max"] == 14
        assert d["parsed"]["fuel_capacity"] == 2000
        assert d["parsed"]["trunk_x"] == 6

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("vehicle_humvee")
        entry = parse_entry(raw, english, "vehicle_humvee")
        assert isinstance(entry, Vehicle)


# ---------------------------------------------------------------------------
# TestAnimal (kept as special type)
# ---------------------------------------------------------------------------
class TestAnimal:
    """Animal category model tests."""

    def test_parse_bear(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert isinstance(animal, Animal)
        assert animal.name == "Bear"

    def test_health(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.health == 100

    def test_speed_run(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.speed_run == 12

    def test_damage(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.damage == 20

    def test_behaviour(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.behaviour == "Offense"

    def test_regen(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.regen == 0.2

    def test_reward(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert animal.reward_id == 523
        assert animal.reward_xp == 30

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        assert len(animal.markdown_row({})) == len(Animal.markdown_columns())

    def test_model_dump(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        d = animal.model_dump()
        assert d["parsed"]["health"] == 100
        assert d["parsed"]["damage"] == 20
        assert d["parsed"]["behaviour"] == "Offense"

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("animal_bear")
        entry = parse_entry(raw, english, "animal_bear")
        assert isinstance(entry, Animal)


# ---------------------------------------------------------------------------
# TestGenericEntry
# ---------------------------------------------------------------------------
class TestGenericEntry:
    """GenericEntry fallback tests."""

    def test_unknown_type_falls_back(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item"}
        entry = parse_entry(raw, english, "test/path")
        assert isinstance(entry, GenericEntry)

    def test_unknown_type_has_empty_properties(self):
        """Unknown types should have empty properties dict."""
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item"}
        entry = parse_entry(raw, english, "test/path")
        assert entry.properties == {}

    def test_preserves_raw(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item"}
        entry = parse_entry(raw, english, "test/path")
        assert entry.raw == raw
        assert entry.raw["Foo"] == "bar"

    def test_base_fields(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item", "Description": "What is this?"}
        entry = parse_entry(raw, english, "test/path")
        assert entry.type == "SomeNewType"
        assert entry.id == 9999
        assert entry.name == "Mystery Item"
        assert entry.description == "What is this?"

    def test_model_dump_includes_raw(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item"}
        entry = parse_entry(raw, english, "test/path")
        d = entry.model_dump()
        assert "raw" in d
        assert d["raw"]["Foo"] == "bar"

    def test_markdown_row_length_matches_columns(self):
        raw = {"Type": "SomeNewType", "ID": 9999}
        english = {}
        entry = parse_entry(raw, english, "test/path")
        assert len(entry.markdown_row({})) == len(GenericEntry.markdown_columns())


# ---------------------------------------------------------------------------
# TestTypeRegistry
# ---------------------------------------------------------------------------
class TestTypeRegistry:
    """TYPE_REGISTRY should only contain special types."""

    def test_special_types_present(self):
        expected = {"Vehicle", "Animal", "Spawn"}
        assert expected == set(TYPE_REGISTRY.keys())

    def test_all_registered_are_bundle_entry_subclasses(self):
        for type_name, cls in TYPE_REGISTRY.items():
            assert issubclass(
                cls, BundleEntry
            ), f"{type_name} -> {cls} is not a BundleEntry subclass"


# ---------------------------------------------------------------------------
# TestParsedComputedField (kept types only)
# ---------------------------------------------------------------------------
class TestParsedComputedField:
    """Verify special types still populate parsed correctly."""

    def test_animal_parsed_keys(self):
        raw, english = _load_fixture("animal_bear")
        animal = Animal.from_raw(raw, english, "animal_bear")
        p = animal.parsed
        expected = {
            "health",
            "damage",
            "speed_run",
            "speed_walk",
            "behaviour",
            "regen",
            "reward_id",
            "reward_xp",
        }
        assert set(p.keys()) == expected
        assert p["health"] == 100

    def test_vehicle_parsed_keys(self):
        raw, english = _load_fixture("vehicle_humvee")
        vehicle = Vehicle.from_raw(raw, english, "vehicle_humvee")
        p = vehicle.parsed
        expected = {
            "speed_min",
            "speed_max",
            "steer_min",
            "steer_max",
            "brake",
            "fuel_min",
            "fuel_max",
            "fuel_capacity",
            "health_min",
            "health_max",
            "trunk_x",
            "trunk_y",
        }
        assert set(p.keys()) == expected
        assert p["speed_max"] == 14

    def test_spawn_table_parsed_keys(self):
        entries = [SpawnTableEntry(ref_type="asset", ref_id=42, weight=10)]
        table = SpawnTable(
            guid="abc",
            type="Spawn",
            id=1,
            name="Test",
            source_path="Spawns/Test",
            table_entries=entries,
        )
        p = table.parsed
        assert "table_entries" in p
        assert len(p["table_entries"]) == 1
        assert p["table_entries"][0]["ref_type"] == "asset"
