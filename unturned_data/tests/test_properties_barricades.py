"""Tests for barricade property models."""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models.properties.barricades import (
    BarricadeProperties,
    BeaconProperties,
    ChargeProperties,
    FarmProperties,
    GeneratorProperties,
    LibraryProperties,
    OilPumpProperties,
    SentryProperties,
    StorageProperties,
    TankProperties,
    TrapProperties,
)

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
# BarricadeProperties (base)
# ---------------------------------------------------------------------------


class TestBarricadeDefaults:
    """BarricadeProperties default values."""

    def test_barricade_defaults(self):
        props = BarricadeProperties()
        assert props.health == 0
        assert props.range == 0
        assert props.radius == 0
        assert props.offset == 0
        assert props.can_be_damaged is True
        assert props.locked is False
        assert props.vulnerable is False
        assert props.bypass_claim is False
        assert props.allow_placement_on_vehicle is False
        assert props.unrepairable is False
        assert props.proof_explosion is False
        assert props.unpickupable is False
        assert props.bypass_pickup_ownership is False
        assert props.allow_placement_inside_clip_volumes is False
        assert props.unsalvageable is False
        assert props.salvage_duration_multiplier == 1.0
        assert props.unsaveable is False
        assert props.allow_collision_while_animating is False
        assert props.armor_tier == ""


# ---------------------------------------------------------------------------
# TrapProperties (from fixture)
# ---------------------------------------------------------------------------


class TestTrapProperties:
    """TrapProperties.from_raw parsing using barricade_wire fixture."""

    def test_trap_from_fixture(self):
        raw, _ = _load_fixture("barricade_wire")
        props = TrapProperties.from_raw(raw)

        # Base barricade fields
        assert props.health == 70
        assert props.range == 4.0
        assert props.radius == pytest.approx(0.15)
        assert props.offset == pytest.approx(0.2)
        assert props.vulnerable is True
        assert props.unrepairable is True

        # Trap damage fields (Player_Damage -> damage_player)
        assert props.damage_player == 40.0
        assert props.damage_zombie == 80.0
        assert props.damage_animal == 80.0
        assert props.damage_barricade == 0.0
        assert props.damage_structure == 0.0
        assert props.damage_vehicle == 0.0

        # Trap-specific defaults
        assert props.trap_setup_delay == 0.25
        assert props.trap_cooldown == 0.0
        assert props.broken is False
        assert props.explosive is False
        assert props.damage_tires is False

    def test_trap_consumed_keys(self):
        raw = {
            "Player_Damage": "40",
            "Zombie_Damage": "80",
            "Health": "70",
            "Range": "4",
        }
        keys = TrapProperties.consumed_keys(raw)
        assert "Player_Damage" in keys
        assert "Zombie_Damage" in keys
        assert "Health" in keys
        assert "Range" in keys

    def test_trap_ignored_keys(self):
        assert TrapProperties.is_ignored("Explosion2")
        assert TrapProperties.is_ignored("Explosion")
        assert TrapProperties.is_ignored("Has_Clip_Prefab")
        assert not TrapProperties.is_ignored("Health")


# ---------------------------------------------------------------------------
# StorageProperties
# ---------------------------------------------------------------------------


class TestStorageProperties:
    """StorageProperties.from_raw parsing."""

    def test_storage_properties(self):
        raw = {
            "Health": "500",
            "Range": "4",
            "Storage_X": "6",
            "Storage_Y": "4",
            "Display": "true",
        }
        props = StorageProperties.from_raw(raw)
        assert props.health == 500
        assert props.storage_x == 6
        assert props.storage_y == 4
        assert props.display is True

    def test_storage_defaults(self):
        props = StorageProperties()
        assert props.storage_x == 0
        assert props.storage_y == 0
        assert props.display is False


# ---------------------------------------------------------------------------
# FarmProperties
# ---------------------------------------------------------------------------


class TestFarmProperties:
    """FarmProperties.from_raw parsing."""

    def test_farm_properties(self):
        raw = {
            "Health": "300",
            "Range": "4",
            "Growth": "5",
            "Grow": "10",
            "Allow_Fertilizer": "false",
            "Harvest_Reward_Experience": "3",
        }
        props = FarmProperties.from_raw(raw)
        assert props.health == 300
        assert props.growth == 5
        assert props.grow == 10
        assert props.allow_fertilizer is False
        assert props.harvest_reward_experience == 3

    def test_farm_defaults(self):
        props = FarmProperties()
        assert props.growth == 0
        assert props.grow == 0
        assert props.allow_fertilizer is True
        assert props.harvest_reward_experience == 1

    def test_farm_ignored_keys(self):
        assert FarmProperties.is_ignored("Grow_SpawnTable")
        assert FarmProperties.is_ignored("Ignore_Soil_Restrictions")


# ---------------------------------------------------------------------------
# GeneratorProperties
# ---------------------------------------------------------------------------


class TestGeneratorProperties:
    """GeneratorProperties.from_raw parsing."""

    def test_generator_properties(self):
        raw = {
            "Health": "750",
            "Range": "4",
            "Capacity": "500",
            "Wirerange": "32",
            "Burn": "2.5",
        }
        props = GeneratorProperties.from_raw(raw)
        assert props.health == 750
        assert props.capacity == 500
        assert props.wirerange == 32.0
        assert props.burn == pytest.approx(2.5)

    def test_generator_consumed_keys_includes_wirerange(self):
        raw = {"Wirerange": "32", "Health": "750"}
        keys = GeneratorProperties.consumed_keys(raw)
        assert "Wirerange" in keys
        assert "Health" in keys


# ---------------------------------------------------------------------------
# SentryProperties
# ---------------------------------------------------------------------------


class TestSentryProperties:
    """SentryProperties.from_raw parsing."""

    def test_sentry_properties(self):
        raw = {
            "Health": "600",
            "Range": "4",
            "Storage_X": "3",
            "Storage_Y": "3",
            "Mode": "Neutral",
            "Requires_Power": "true",
            "Infinite_Ammo": "false",
            "Infinite_Quality": "true",
            "Detection_Radius": "64",
            "Target_Loss_Radius": "72",
        }
        props = SentryProperties.from_raw(raw)
        assert props.health == 600
        assert props.storage_x == 3
        assert props.storage_y == 3
        assert props.mode == "Neutral"
        assert props.requires_power is True
        assert props.infinite_ammo is False
        assert props.infinite_quality is True
        assert props.detection_radius == 64.0
        assert props.target_loss_radius == 72.0

    def test_sentry_defaults(self):
        props = SentryProperties()
        assert props.detection_radius == 48.0
        assert props.target_loss_radius == 0
        assert props.mode == ""

    def test_sentry_ignored_keys(self):
        assert SentryProperties.is_ignored("Target_Acquired_Effect")
        assert SentryProperties.is_ignored("Target_Lost_Effect")
        # Inherits parent ignores
        assert SentryProperties.is_ignored("Explosion")


# ---------------------------------------------------------------------------
# TankProperties
# ---------------------------------------------------------------------------


class TestTankProperties:
    """TankProperties.from_raw parsing."""

    def test_tank_properties(self):
        raw = {
            "Health": "400",
            "Range": "4",
            "Source": "Water",
            "Resource": "10",
        }
        props = TankProperties.from_raw(raw)
        assert props.health == 400
        assert props.source == "Water"
        assert props.resource == 10


# ---------------------------------------------------------------------------
# ChargeProperties
# ---------------------------------------------------------------------------


class TestChargeProperties:
    """ChargeProperties.from_raw parsing."""

    def test_charge_properties(self):
        raw = {
            "Health": "100",
            "Range": "4",
            "Range2": "12",
            "Player_Damage": "200",
            "Zombie_Damage": "500",
            "Animal_Damage": "500",
            "Barricade_Damage": "400",
            "Structure_Damage": "300",
            "Vehicle_Damage": "250",
            "Resource_Damage": "100",
            "Object_Damage": "100",
            "Explosion_Launch_Speed": "15",
        }
        props = ChargeProperties.from_raw(raw)
        assert props.health == 100
        assert props.range2 == 12.0
        assert props.damage_player == 200.0
        assert props.damage_zombie == 500.0
        assert props.damage_barricade == 400.0
        assert props.damage_structure == 300.0
        assert props.damage_vehicle == 250.0
        assert props.explosion_launch_speed == 15.0

    def test_charge_consumed_keys(self):
        raw = {
            "Player_Damage": "200",
            "Zombie_Damage": "500",
            "Range2": "12",
        }
        keys = ChargeProperties.consumed_keys(raw)
        assert "Player_Damage" in keys
        assert "Zombie_Damage" in keys
        assert "Range2" in keys

    def test_charge_ignored_keys(self):
        assert ChargeProperties.is_ignored("Explosion2")


# ---------------------------------------------------------------------------
# LibraryProperties
# ---------------------------------------------------------------------------


class TestLibraryProperties:
    """LibraryProperties.from_raw parsing."""

    def test_library_properties(self):
        raw = {
            "Health": "500",
            "Range": "4",
            "Capacity": "10",
            "Tax": "3",
        }
        props = LibraryProperties.from_raw(raw)
        assert props.health == 500
        assert props.capacity == 10
        assert props.tax == 3


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestBarricadeSerializes:
    """Barricade properties serialize to/from dict."""

    def test_barricade_serializes(self):
        raw = {
            "Health": "70",
            "Range": "4",
            "Radius": "0.15",
            "Offset": "0.2",
            "Vulnerable": "",
            "Unrepairable": "",
        }
        props = BarricadeProperties.from_raw(raw)
        data = props.model_dump()
        restored = BarricadeProperties(**data)
        assert restored.health == props.health
        assert restored.range == props.range
        assert restored.radius == props.radius
        assert restored.offset == props.offset
        assert restored.vulnerable == props.vulnerable
        assert restored.unrepairable == props.unrepairable

    def test_trap_serializes_roundtrip(self):
        raw, _ = _load_fixture("barricade_wire")
        props = TrapProperties.from_raw(raw)
        data = props.model_dump()
        restored = TrapProperties(**data)
        assert restored.damage_player == props.damage_player
        assert restored.damage_zombie == props.damage_zombie
        assert restored.health == props.health
