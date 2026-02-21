"""
Tests for category model classes and type dispatch.

Covers: Gun, MeleeWeapon, Consumeable, Clothing, Vehicle, Animal,
BarricadeItem, StructureItem, GenericEntry, and parse_entry dispatch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.categories import (
    TYPE_REGISTRY,
    parse_entry,
    Animal,
    Attachment,
    BarricadeItem,
    Clothing,
    Consumeable,
    GenericEntry,
    Gun,
    Magazine,
    MeleeWeapon,
    StructureItem,
    Throwable,
    Vehicle,
)
from unturned_data.models import SpawnTable, SpawnTableEntry

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> tuple[dict, dict]:
    """Helper: load raw + english from a fixture directory."""
    fixture_dir = FIXTURES / name
    dat_files = [f for f in fixture_dir.glob("*.dat") if f.name != "English.dat"]
    assert dat_files, f"No .dat files in {fixture_dir}"
    raw = parse_dat_file(dat_files[0])
    english = load_english_dat(fixture_dir / "English.dat")
    return raw, english


# ---------------------------------------------------------------------------
# TestGun
# ---------------------------------------------------------------------------
class TestGun:
    """Gun category model tests."""

    def test_parse_maplestrike(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert isinstance(gun, Gun)
        assert gun.name == "Maplestrike"
        assert gun.type == "Gun"
        assert gun.id == 363

    def test_damage(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert gun.damage is not None
        assert gun.damage.player == 40

    def test_firerate(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert gun.firerate == 5

    def test_range(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert gun.range == 200

    def test_fire_modes(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert "Auto" in gun.fire_modes
        assert "Semi" in gun.fire_modes
        assert "Safety" in gun.fire_modes

    def test_slot(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert gun.slot == "Primary"

    def test_blueprints(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert len(gun.blueprints) == 2

    def test_hooks(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert "Sight" in gun.hooks
        assert "Tactical" in gun.hooks
        assert "Grip" in gun.hooks
        assert "Barrel" in gun.hooks

    def test_ammo(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert gun.ammo_min == 10
        assert gun.ammo_max == 30

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        assert len(gun.markdown_row({})) == len(Gun.markdown_columns())

    def test_model_dump(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        d = gun.model_dump()
        assert d["slot"] == "Primary"
        assert d["parsed"]["firerate"] == 5
        assert d["parsed"]["range"] == 200
        assert d["parsed"]["damage"]["player"] == 40

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("gun_maplestrike")
        entry = parse_entry(raw, english, "gun_maplestrike")
        assert isinstance(entry, Gun)


# ---------------------------------------------------------------------------
# TestMeleeWeapon
# ---------------------------------------------------------------------------
class TestMeleeWeapon:
    """MeleeWeapon category model tests."""

    def test_parse_katana(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert isinstance(melee, MeleeWeapon)
        assert melee.name == "Katana"

    def test_damage(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert melee.damage is not None
        assert melee.damage.player == 50

    def test_strength(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert melee.strength == 1.5

    def test_range(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert melee.range == 2.25

    def test_stamina(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert melee.stamina == 15

    def test_blueprints(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert len(melee.blueprints) == 2

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        assert len(melee.markdown_row({})) == len(MeleeWeapon.markdown_columns())

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("melee_katana")
        entry = parse_entry(raw, english, "melee_katana")
        assert isinstance(entry, MeleeWeapon)


# ---------------------------------------------------------------------------
# TestConsumeable (food)
# ---------------------------------------------------------------------------
class TestConsumeableFood:
    """Consumeable model tests using food fixture (beans)."""

    def test_parse_beans(self):
        raw, english = _load_fixture("food_beans")
        food = Consumeable.from_raw(raw, english, "food_beans")
        assert isinstance(food, Consumeable)
        assert food.name == "Canned Beans"

    def test_consumable_food(self):
        raw, english = _load_fixture("food_beans")
        food = Consumeable.from_raw(raw, english, "food_beans")
        assert food.consumable is not None
        assert food.consumable.food == 55

    def test_consumable_health(self):
        raw, english = _load_fixture("food_beans")
        food = Consumeable.from_raw(raw, english, "food_beans")
        assert food.consumable is not None
        assert food.consumable.health == 10

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("food_beans")
        food = Consumeable.from_raw(raw, english, "food_beans")
        assert len(food.markdown_row({})) == len(Consumeable.markdown_columns())

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("food_beans")
        entry = parse_entry(raw, english, "food_beans")
        assert isinstance(entry, Consumeable)


# ---------------------------------------------------------------------------
# TestConsumeable (medical)
# ---------------------------------------------------------------------------
class TestConsumeableMedical:
    """Consumeable model tests using medical fixture (bandage)."""

    def test_parse_bandage(self):
        raw, english = _load_fixture("medical_bandage")
        med = Consumeable.from_raw(raw, english, "medical_bandage")
        assert isinstance(med, Consumeable)
        assert med.name == "Bandage"

    def test_bleeding_modifier(self):
        raw, english = _load_fixture("medical_bandage")
        med = Consumeable.from_raw(raw, english, "medical_bandage")
        assert med.consumable is not None
        assert med.consumable.bleeding_modifier == "Heal"

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("medical_bandage")
        entry = parse_entry(raw, english, "medical_bandage")
        assert isinstance(entry, Consumeable)


# ---------------------------------------------------------------------------
# TestConsumeable (water)
# ---------------------------------------------------------------------------
class TestConsumeableWater:
    """Consumeable model tests using water fixture (berries)."""

    def test_parse_berries(self):
        raw, english = _load_fixture("water_berries")
        water = Consumeable.from_raw(raw, english, "water_berries")
        assert isinstance(water, Consumeable)
        assert water.name == "Raw Amber Berries"

    def test_virus(self):
        raw, english = _load_fixture("water_berries")
        water = Consumeable.from_raw(raw, english, "water_berries")
        assert water.consumable is not None
        assert water.consumable.virus == 5

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("water_berries")
        entry = parse_entry(raw, english, "water_berries")
        assert isinstance(entry, Consumeable)


# ---------------------------------------------------------------------------
# TestClothing
# ---------------------------------------------------------------------------
class TestClothing:
    """Clothing category model tests."""

    def test_parse_backpack(self):
        raw, english = _load_fixture("backpack_alice")
        clothing = Clothing.from_raw(raw, english, "backpack_alice")
        assert isinstance(clothing, Clothing)
        assert clothing.name == "Alicepack"

    def test_storage(self):
        raw, english = _load_fixture("backpack_alice")
        clothing = Clothing.from_raw(raw, english, "backpack_alice")
        assert clothing.storage is not None
        assert clothing.storage.width == 8
        assert clothing.storage.height == 7

    def test_blueprints(self):
        raw, english = _load_fixture("backpack_alice")
        clothing = Clothing.from_raw(raw, english, "backpack_alice")
        assert len(clothing.blueprints) == 2

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("backpack_alice")
        clothing = Clothing.from_raw(raw, english, "backpack_alice")
        assert len(clothing.markdown_row({})) == len(Clothing.markdown_columns())

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("backpack_alice")
        entry = parse_entry(raw, english, "backpack_alice")
        assert isinstance(entry, Clothing)


# ---------------------------------------------------------------------------
# TestBarricadeItem
# ---------------------------------------------------------------------------
class TestBarricadeItem:
    """BarricadeItem category model tests."""

    def test_parse_barbed_wire(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        assert isinstance(barricade, BarricadeItem)
        assert barricade.name == "Barbed Wire"

    def test_health(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        assert barricade.health == 70

    def test_build(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        assert barricade.build == "Wire"

    def test_damage(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        assert barricade.damage is not None
        assert barricade.damage.player == 40

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        assert len(barricade.markdown_row({})) == len(BarricadeItem.markdown_columns())

    def test_dispatch_via_parse_entry(self):
        """Barbed wire has Type=Trap, which maps to BarricadeItem."""
        raw, english = _load_fixture("barricade_wire")
        entry = parse_entry(raw, english, "barricade_wire")
        assert isinstance(entry, BarricadeItem)


# ---------------------------------------------------------------------------
# TestStructureItem
# ---------------------------------------------------------------------------
class TestStructureItem:
    """StructureItem category model tests."""

    def test_parse_doorway(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        assert isinstance(structure, StructureItem)
        assert structure.name == "Birch Doorway"

    def test_health(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        assert structure.health == 350

    def test_construct(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        assert structure.construct == "Wall"

    def test_blueprints(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        assert len(structure.blueprints) == 2

    def test_markdown_row_length_matches_columns(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        assert len(structure.markdown_row({})) == len(StructureItem.markdown_columns())

    def test_dispatch_via_parse_entry(self):
        raw, english = _load_fixture("structure_wall")
        entry = parse_entry(raw, english, "structure_wall")
        assert isinstance(entry, StructureItem)


# ---------------------------------------------------------------------------
# TestVehicle
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
# TestAnimal
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
    """TYPE_REGISTRY completeness tests."""

    def test_all_expected_types_present(self):
        expected = {
            "Gun",
            "Melee",
            "Throwable",
            "Food",
            "Water",
            "Medical",
            "Shirt",
            "Pants",
            "Hat",
            "Vest",
            "Backpack",
            "Mask",
            "Glasses",
            "Barricade",
            "Trap",
            "Storage",
            "Sentry",
            "Generator",
            "Beacon",
            "Oil_Pump",
            "Structure",
            "Magazine",
            "Sight",
            "Grip",
            "Barrel",
            "Tactical",
            "Vehicle",
            "Animal",
            "Spawn",
        }
        assert expected == set(TYPE_REGISTRY.keys())

    def test_parse_entry_returns_bundle_entry_subclass(self):
        """Every registered class should be a BundleEntry subclass."""
        from unturned_data.models import BundleEntry

        for type_name, cls in TYPE_REGISTRY.items():
            assert issubclass(
                cls, BundleEntry
            ), f"{type_name} -> {cls} is not a BundleEntry subclass"


# ---------------------------------------------------------------------------
# TestParsedComputedField
# ---------------------------------------------------------------------------
class TestParsedComputedField:
    """Verify each category model populates parsed with expected keys."""

    def test_gun_parsed_keys(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        p = gun.parsed
        expected = {
            "caliber",
            "firerate",
            "range",
            "fire_modes",
            "hooks",
            "ammo_min",
            "ammo_max",
            "durability",
            "spread_aim",
            "spread_angle",
            "damage",
        }
        assert set(p.keys()) == expected
        assert p["damage"] is not None
        assert p["damage"]["player"] == 40

    def test_melee_parsed_keys(self):
        raw, english = _load_fixture("melee_katana")
        melee = MeleeWeapon.from_raw(raw, english, "melee_katana")
        p = melee.parsed
        expected = {"range", "strength", "stamina", "durability", "damage"}
        assert set(p.keys()) == expected
        assert p["damage"]["player"] == 50

    def test_consumeable_parsed_keys(self):
        raw, english = _load_fixture("food_beans")
        food = Consumeable.from_raw(raw, english, "food_beans")
        p = food.parsed
        assert "consumable" in p
        assert p["consumable"] is not None
        assert p["consumable"]["food"] == 55

    def test_clothing_parsed_keys(self):
        raw, english = _load_fixture("backpack_alice")
        clothing = Clothing.from_raw(raw, english, "backpack_alice")
        p = clothing.parsed
        assert "armor" in p
        assert "storage" in p
        assert p["storage"]["width"] == 8
        assert p["storage"]["height"] == 7

    def test_throwable_parsed_keys(self):
        throwable = Throwable(
            type="Throwable",
            id=1,
            name="Grenade",
            fuse=2.5,
            explosion=10.0,
        )
        p = throwable.parsed
        expected = {"fuse", "explosion", "damage"}
        assert set(p.keys()) == expected
        assert p["fuse"] == 2.5
        assert p["damage"] is None

    def test_barricade_parsed_keys(self):
        raw, english = _load_fixture("barricade_wire")
        barricade = BarricadeItem.from_raw(raw, english, "barricade_wire")
        p = barricade.parsed
        expected = {"health", "range", "build", "storage", "damage"}
        assert set(p.keys()) == expected
        assert p["damage"]["player"] == 40

    def test_structure_parsed_keys(self):
        raw, english = _load_fixture("structure_wall")
        structure = StructureItem.from_raw(raw, english, "structure_wall")
        p = structure.parsed
        expected = {"health", "range", "construct"}
        assert set(p.keys()) == expected
        assert p["health"] == 350

    def test_magazine_parsed_keys(self):
        mag = Magazine(
            type="Magazine",
            id=1,
            name="Test Mag",
            amount=30,
            count_min=5,
            count_max=10,
        )
        p = mag.parsed
        expected = {"amount", "count_min", "count_max"}
        assert set(p.keys()) == expected
        assert p["amount"] == 30

    def test_attachment_parsed_empty(self):
        attachment = Attachment(type="Sight", id=1, name="Red Dot")
        p = attachment.parsed
        assert p == {}

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

    def test_generic_parsed_empty(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        english = {"Name": "Mystery Item"}
        entry = parse_entry(raw, english, "test/path")
        assert isinstance(entry, GenericEntry)
        assert entry.parsed == {}

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

    def test_parsed_in_model_dump(self):
        """parsed field should appear in model_dump() output."""
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "gun_maplestrike")
        d = gun.model_dump()
        assert "parsed" in d
        assert d["slot"] == "Primary"
        assert d["parsed"]["firerate"] == 5
