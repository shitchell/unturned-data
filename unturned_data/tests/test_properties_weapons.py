"""Tests for weapon property models: Gun, Melee, Throwable."""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models.properties.weapons import (
    GunProperties,
    MeleeProperties,
    ThrowableProperties,
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
# GunProperties
# ---------------------------------------------------------------------------


class TestGunProperties:
    """GunProperties.from_raw parsing."""

    def test_gun_properties_from_fixture(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.firerate == 5
        assert props.range == 200.0
        assert props.damage_player == 40.0
        assert props.action == "Trigger"
        assert props.damage_zombie == 99.0
        assert props.damage_animal == 40.0
        assert props.damage_barricade == 20.0
        assert props.damage_structure == 15.0
        assert props.damage_vehicle == 35.0
        assert props.damage_resource == 15.0
        assert props.damage_object == 25.0
        assert props.durability == pytest.approx(0.2)
        assert props.ammo_min == 10
        assert props.ammo_max == 30
        assert props.caliber == 1
        assert props.default_sight == "364"
        assert props.default_magazine == "6"

    def test_gun_properties_fire_modes(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.safety is True
        assert props.semi is True
        assert props.auto is True
        assert props.bursts is None

    def test_gun_properties_hooks(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.hook_sight is True
        assert props.hook_tactical is True
        assert props.hook_grip is True
        assert props.hook_barrel is True

    def test_gun_properties_multipliers(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.player_skull_multiplier == pytest.approx(1.1)
        assert props.zombie_skull_multiplier == pytest.approx(1.1)
        assert props.animal_skull_multiplier == pytest.approx(1.1)
        assert props.player_leg_multiplier == pytest.approx(0.6)

    def test_gun_properties_recoil(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.recoil_min_x == pytest.approx(-0.5)
        assert props.recoil_max_y == pytest.approx(5.0)
        assert props.recover_x == pytest.approx(0.6)
        assert props.recover_y == pytest.approx(0.6)

    def test_gun_properties_shake(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)

        assert props.shake_min_x == pytest.approx(-0.0025)
        assert props.shake_max_z == pytest.approx(-0.02)

    def test_gun_properties_serializes_flat(self):
        raw, _ = _load_fixture("gun_maplestrike")
        props = GunProperties.from_raw(raw)
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        # All top-level keys, no nesting (except lists)
        for key, val in dumped.items():
            assert not isinstance(val, dict), f"{key} should not be a dict"
        # Spot check some keys exist
        assert "firerate" in dumped
        assert "damage_player" in dumped
        assert "hook_sight" in dumped

    def test_gun_properties_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = GunProperties.from_raw({})

        assert props.firerate is None
        assert props.action is None
        assert props.safety is None
        assert props.range is None
        assert props.spread_sprint is None
        assert props.spread_crouch is None
        assert props.spread_prone is None
        assert props.ballistic_travel is None
        assert props.recoil_aim is None
        assert props.allow_magazine_change is None
        assert props.ammo_per_shot is None
        assert props.jam_quality_threshold is None
        assert props.jam_max_chance is None
        assert props.unjam_chamber_anim is None
        assert props.projectile_lifespan is None
        # List fields keep empty list defaults
        assert props.magazine_calibers == []
        assert props.attachment_calibers == []
        assert props.magazine_replacements == []


# ---------------------------------------------------------------------------
# MeleeProperties
# ---------------------------------------------------------------------------


class TestMeleeProperties:
    """MeleeProperties.from_raw parsing."""

    def test_melee_properties_from_fixture(self):
        raw, _ = _load_fixture("melee_katana")
        props = MeleeProperties.from_raw(raw)

        assert props.damage_player == 50.0
        assert props.damage_zombie == 50.0
        assert props.damage_animal == 50.0
        assert props.range == pytest.approx(2.25)
        assert props.strength == pytest.approx(1.5)
        assert props.stamina == 15
        assert props.durability == pytest.approx(0.15)

    def test_melee_multipliers(self):
        raw, _ = _load_fixture("melee_katana")
        props = MeleeProperties.from_raw(raw)

        assert props.player_skull_multiplier == pytest.approx(1.1)
        assert props.zombie_skull_multiplier == pytest.approx(1.1)
        assert props.animal_skull_multiplier == pytest.approx(1.1)

    def test_melee_structure_damage(self):
        raw, _ = _load_fixture("melee_katana")
        props = MeleeProperties.from_raw(raw)

        assert props.damage_barricade == 2.0
        assert props.damage_structure == 2.0
        assert props.damage_vehicle == 15.0
        assert props.damage_resource == 25.0
        assert props.damage_object == 20.0

    def test_melee_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = MeleeProperties.from_raw({})

        assert props.range is None
        assert props.strength is None
        assert props.stamina is None
        assert props.repair is None
        assert props.repeated is None
        assert props.light is None

    def test_melee_serializes_flat(self):
        raw, _ = _load_fixture("melee_katana")
        props = MeleeProperties.from_raw(raw)
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        assert "damage_player" in dumped
        assert "range" in dumped
        assert "strength" in dumped


# ---------------------------------------------------------------------------
# ThrowableProperties
# ---------------------------------------------------------------------------


class TestThrowableProperties:
    """ThrowableProperties.from_raw parsing."""

    def test_throwable_properties_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = ThrowableProperties.from_raw({})

        assert props.explosive is None
        assert props.flash is None
        assert props.sticky is None
        assert props.explode_on_impact is None
        assert props.fuse_length is None
        assert props.explosion_launch_speed is None
        assert props.strong_throw_force is None
        assert props.weak_throw_force is None
        assert props.boost_throw_force_multiplier is None
        assert props.durability is None
        assert props.wear is None
        assert props.invulnerable is None

    def test_throwable_from_raw(self):
        """Test with synthetic raw data."""
        raw = {
            "Player_Damage": 100,
            "Zombie_Damage": 200,
            "Explosive": True,
            "Fuse_Length": 2.5,
            "Sticky": True,
            "Strong_Throw_Force": 1200,
            "Weak_Throw_Force": 700,
        }
        props = ThrowableProperties.from_raw(raw)

        assert props.damage_player == 100.0
        assert props.damage_zombie == 200.0
        assert props.explosive is True
        assert props.fuse_length == pytest.approx(2.5)
        assert props.sticky is True
        assert props.strong_throw_force == pytest.approx(1200.0)
        assert props.weak_throw_force == pytest.approx(700.0)

    def test_throwable_serializes_flat(self):
        props = ThrowableProperties.from_raw({})
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        assert "explosive" in dumped
        assert "strong_throw_force" in dumped
