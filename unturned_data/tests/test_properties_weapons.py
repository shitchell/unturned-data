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
        assert props.bursts == 0

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
        """Empty raw dict produces correct defaults."""
        props = GunProperties.from_raw({})

        assert props.firerate == 0
        assert props.action == ""
        assert props.safety is False
        assert props.range == 0.0
        assert props.spread_sprint == pytest.approx(1.25)
        assert props.spread_crouch == pytest.approx(0.85)
        assert props.spread_prone == pytest.approx(0.7)
        assert props.ballistic_travel == pytest.approx(10.0)
        assert props.recoil_aim == pytest.approx(1.0)
        assert props.allow_magazine_change is True
        assert props.ammo_per_shot == 1
        assert props.jam_quality_threshold == pytest.approx(0.4)
        assert props.jam_max_chance == pytest.approx(0.1)
        assert props.unjam_chamber_anim == "UnjamChamber"
        assert props.projectile_lifespan == pytest.approx(30.0)
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
        """Empty raw dict produces correct defaults."""
        props = MeleeProperties.from_raw({})

        assert props.range == 0.0
        assert props.strength == 0.0
        assert props.stamina == 0
        assert props.repair is False
        assert props.repeated is False
        assert props.light is False

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
        """Empty raw dict produces correct defaults."""
        props = ThrowableProperties.from_raw({})

        assert props.explosive is False
        assert props.flash is False
        assert props.sticky is False
        assert props.explode_on_impact is False
        assert props.fuse_length == 0.0
        assert props.explosion_launch_speed == 0.0
        assert props.strong_throw_force == pytest.approx(1100.0)
        assert props.weak_throw_force == pytest.approx(600.0)
        assert props.boost_throw_force_multiplier == pytest.approx(1.4)
        assert props.durability == 0.0
        assert props.wear == 0
        assert props.invulnerable is False

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
