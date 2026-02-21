"""Tests for attachment property models: Sight, Barrel, Grip, Tactical, Magazine."""

from __future__ import annotations

import pytest

from unturned_data.models.properties.attachments import (
    BarrelProperties,
    CaliberProperties,
    GripProperties,
    MagazineProperties,
    SightProperties,
    TacticalProperties,
)


# ---------------------------------------------------------------------------
# CaliberProperties (base)
# ---------------------------------------------------------------------------


class TestCaliberProperties:
    """CaliberProperties base defaults and parsing."""

    def test_caliber_defaults(self):
        """Empty raw dict produces correct defaults."""
        props = CaliberProperties.from_raw({})

        assert props.calibers == []
        assert props.recoil_x == pytest.approx(1.0)
        assert props.recoil_y == pytest.approx(1.0)
        assert props.aiming_recoil_multiplier == pytest.approx(1.0)
        assert props.spread == pytest.approx(1.0)
        assert props.sway == pytest.approx(1.0)
        assert props.shake == pytest.approx(1.0)
        assert props.damage == pytest.approx(1.0)
        assert props.firerate == 0
        assert props.ballistic_damage_multiplier == pytest.approx(0.0)
        assert props.paintable is False
        assert props.bipod is False

    def test_calibers_list_parsing(self):
        """Calibers count + Caliber_{i} entries are parsed into a list."""
        raw = {
            "Calibers": "3",
            "Caliber_0": "1",
            "Caliber_1": "7",
            "Caliber_2": "22",
        }
        props = CaliberProperties.from_raw(raw)

        assert props.calibers == [1, 7, 22]

    def test_calibers_empty_when_count_zero(self):
        raw = {"Calibers": "0"}
        props = CaliberProperties.from_raw(raw)
        assert props.calibers == []

    def test_caliber_base_fields_from_raw(self):
        raw = {
            "Recoil_X": "0.8",
            "Recoil_Y": "0.9",
            "Spread": "0.75",
            "Damage": "1.2",
            "Firerate": "-2",
            "Paintable": "true",
            "Bipod": "true",
            "Ballistic_Damage_Multiplier": "1.5",
        }
        props = CaliberProperties.from_raw(raw)

        assert props.recoil_x == pytest.approx(0.8)
        assert props.recoil_y == pytest.approx(0.9)
        assert props.spread == pytest.approx(0.75)
        assert props.damage == pytest.approx(1.2)
        assert props.firerate == -2
        assert props.paintable is True
        assert props.bipod is True
        assert props.ballistic_damage_multiplier == pytest.approx(1.5)

    def test_consumed_keys_includes_calibers(self):
        raw = {
            "Calibers": "2",
            "Caliber_0": "1",
            "Caliber_1": "5",
            "Recoil_X": "0.8",
            "Unrelated_Key": "foo",
        }
        keys = CaliberProperties.consumed_keys(raw)
        assert "Calibers" in keys
        assert "Caliber_0" in keys
        assert "Caliber_1" in keys
        assert "Recoil_X" in keys
        assert "Unrelated_Key" not in keys

    def test_caliber_pattern_ignored(self):
        assert CaliberProperties.is_ignored("Caliber_0") is True
        assert CaliberProperties.is_ignored("Caliber_99") is True
        assert CaliberProperties.is_ignored("Calibers") is False


# ---------------------------------------------------------------------------
# SightProperties
# ---------------------------------------------------------------------------


class TestSightProperties:
    """SightProperties.from_raw parsing."""

    def test_sight_properties_from_raw(self):
        raw = {
            "Calibers": "1",
            "Caliber_0": "1",
            "Recoil_X": "0.7",
            "Recoil_Y": "0.85",
            "Spread": "0.6",
            "Sway": "0.5",
            "Vision": "Military",
            "Zoom": "8.0",
            "Holographic": "true",
            "Nightvision_Color_R": "100",
            "Nightvision_Color_G": "200",
            "Nightvision_Color_B": "50",
            "Nightvision_Fog_Intensity": "0.25",
        }
        props = SightProperties.from_raw(raw)

        # Base CaliberProperties fields
        assert props.calibers == [1]
        assert props.recoil_x == pytest.approx(0.7)
        assert props.recoil_y == pytest.approx(0.85)
        assert props.spread == pytest.approx(0.6)
        assert props.sway == pytest.approx(0.5)

        # Sight-specific fields
        assert props.vision == "Military"
        assert props.zoom == pytest.approx(8.0)
        assert props.holographic is True
        assert props.nightvision_color_r == 100
        assert props.nightvision_color_g == 200
        assert props.nightvision_color_b == 50
        assert props.nightvision_fog_intensity == pytest.approx(0.25)

    def test_sight_defaults(self):
        props = SightProperties.from_raw({})

        assert props.vision == ""
        assert props.zoom == 0.0
        assert props.holographic is False
        assert props.nightvision_color_r == 0
        assert props.nightvision_color_g == 0
        assert props.nightvision_color_b == 0
        assert props.nightvision_fog_intensity == 0.0
        # Base defaults inherited
        assert props.calibers == []
        assert props.recoil_x == pytest.approx(1.0)

    def test_sight_serializes_flat(self):
        props = SightProperties.from_raw({})
        dumped = props.model_dump()
        assert isinstance(dumped, dict)
        assert "vision" in dumped
        assert "zoom" in dumped
        assert "calibers" in dumped
        for key, val in dumped.items():
            if key != "calibers":
                assert not isinstance(val, (dict, list)), f"{key} should be flat"


# ---------------------------------------------------------------------------
# BarrelProperties
# ---------------------------------------------------------------------------


class TestBarrelProperties:
    """BarrelProperties.from_raw parsing."""

    def test_barrel_properties_from_raw(self):
        raw = {
            "Recoil_X": "0.9",
            "Spread": "0.8",
            "Braked": "true",
            "Silenced": "true",
            "Volume": "0.5",
            "Durability": "100",
            "Ballistic_Drop": "1.1",
            "Gunshot_Rolloff_Distance_Multiplier": "0.6",
        }
        props = BarrelProperties.from_raw(raw)

        assert props.recoil_x == pytest.approx(0.9)
        assert props.spread == pytest.approx(0.8)
        assert props.braked is True
        assert props.silenced is True
        assert props.volume == pytest.approx(0.5)
        assert props.durability == 100
        assert props.ballistic_drop == pytest.approx(1.1)
        assert props.gunshot_rolloff_distance_multiplier == pytest.approx(0.6)

    def test_barrel_defaults(self):
        props = BarrelProperties.from_raw({})

        assert props.braked is False
        assert props.silenced is False
        assert props.volume == pytest.approx(1.0)
        assert props.durability == 0
        assert props.ballistic_drop == pytest.approx(1.0)
        assert props.gunshot_rolloff_distance_multiplier == 0.0


# ---------------------------------------------------------------------------
# GripProperties
# ---------------------------------------------------------------------------


class TestGripProperties:
    """GripProperties — no extra fields, just CaliberProperties."""

    def test_grip_properties_defaults(self):
        """Grip has no extra fields; defaults match CaliberProperties."""
        props = GripProperties.from_raw({})

        assert props.calibers == []
        assert props.recoil_x == pytest.approx(1.0)
        assert props.recoil_y == pytest.approx(1.0)
        assert props.spread == pytest.approx(1.0)
        assert props.sway == pytest.approx(1.0)
        assert props.shake == pytest.approx(1.0)

    def test_grip_from_raw_inherits_base(self):
        raw = {
            "Recoil_X": "0.6",
            "Recoil_Y": "0.7",
            "Spread": "0.5",
            "Calibers": "1",
            "Caliber_0": "3",
        }
        props = GripProperties.from_raw(raw)

        assert props.recoil_x == pytest.approx(0.6)
        assert props.recoil_y == pytest.approx(0.7)
        assert props.spread == pytest.approx(0.5)
        assert props.calibers == [3]

    def test_grip_serializes_flat(self):
        props = GripProperties.from_raw({})
        dumped = props.model_dump()
        assert isinstance(dumped, dict)
        assert "recoil_x" in dumped
        assert "calibers" in dumped


# ---------------------------------------------------------------------------
# TacticalProperties
# ---------------------------------------------------------------------------


class TestTacticalProperties:
    """TacticalProperties.from_raw parsing."""

    def test_tactical_properties_from_raw(self):
        raw = {
            "Recoil_X": "0.9",
            "Laser": "true",
            "Light": "true",
            "Rangefinder": "true",
            "Melee": "true",
            "Spotlight_Range": "128.0",
            "Spotlight_Angle": "45.0",
            "Spotlight_Intensity": "2.0",
            "Spotlight_Color_R": "255",
            "Spotlight_Color_G": "255",
            "Spotlight_Color_B": "255",
        }
        props = TacticalProperties.from_raw(raw)

        assert props.recoil_x == pytest.approx(0.9)
        assert props.laser is True
        assert props.light is True
        assert props.rangefinder is True
        assert props.melee is True
        assert props.spotlight_range == pytest.approx(128.0)
        assert props.spotlight_angle == pytest.approx(45.0)
        assert props.spotlight_intensity == pytest.approx(2.0)
        assert props.spotlight_color_r == 255
        assert props.spotlight_color_g == 255
        assert props.spotlight_color_b == 255

    def test_tactical_defaults(self):
        props = TacticalProperties.from_raw({})

        assert props.laser is False
        assert props.light is False
        assert props.rangefinder is False
        assert props.melee is False
        assert props.spotlight_range == pytest.approx(64.0)
        assert props.spotlight_angle == pytest.approx(90.0)
        assert props.spotlight_intensity == pytest.approx(1.3)
        assert props.spotlight_color_r == 245
        assert props.spotlight_color_g == 223
        assert props.spotlight_color_b == 147


# ---------------------------------------------------------------------------
# MagazineProperties
# ---------------------------------------------------------------------------


class TestMagazineProperties:
    """MagazineProperties.from_raw parsing."""

    def test_magazine_properties_from_raw(self):
        raw = {
            "Calibers": "2",
            "Caliber_0": "1",
            "Caliber_1": "5",
            "Amount": "30",
            "Count_Min": "10",
            "Count_Max": "30",
            "Pellets": "8",
            "Speed": "1.5",
            "Range": "200",
            "Player_Damage": "40",
            "Zombie_Damage": "99",
            "Animal_Damage": "40",
            "Barricade_Damage": "20",
            "Structure_Damage": "15",
            "Vehicle_Damage": "35",
            "Resource_Damage": "15",
            "Object_Damage": "25",
            "Explosive": "true",
            "Delete_Empty": "true",
            "Should_Fill_After_Detach": "true",
            "Explosion_Launch_Speed": "500",
            "Stuck": "3",
            "Projectile_Damage_Multiplier": "1.5",
            "Projectile_Blast_Radius_Multiplier": "2.0",
            "Projectile_Launch_Force_Multiplier": "1.2",
        }
        props = MagazineProperties.from_raw(raw)

        assert props.calibers == [1, 5]
        assert props.amount == 30
        assert props.count_min == 10
        assert props.count_max == 30
        assert props.pellets == 8
        assert props.speed == pytest.approx(1.5)
        assert props.range == pytest.approx(200.0)
        assert props.damage_player == pytest.approx(40.0)
        assert props.damage_zombie == pytest.approx(99.0)
        assert props.damage_animal == pytest.approx(40.0)
        assert props.damage_barricade == pytest.approx(20.0)
        assert props.damage_structure == pytest.approx(15.0)
        assert props.damage_vehicle == pytest.approx(35.0)
        assert props.damage_resource == pytest.approx(15.0)
        assert props.damage_object == pytest.approx(25.0)
        assert props.explosive is True
        assert props.delete_empty is True
        assert props.should_fill_after_detach is True
        assert props.explosion_launch_speed == pytest.approx(500.0)
        assert props.stuck == 3
        assert props.projectile_damage_multiplier == pytest.approx(1.5)
        assert props.projectile_blast_radius_multiplier == pytest.approx(2.0)
        assert props.projectile_launch_force_multiplier == pytest.approx(1.2)

    def test_magazine_defaults(self):
        props = MagazineProperties.from_raw({})

        assert props.amount == 0
        assert props.count_min == 0
        assert props.count_max == 0
        assert props.pellets == 0
        assert props.stuck == 0
        assert props.range == 0.0
        assert props.speed == 0.0
        assert props.explosive is False
        assert props.delete_empty is False
        assert props.should_fill_after_detach is False
        assert props.damage_player == 0.0
        assert props.damage_zombie == 0.0
        assert props.projectile_damage_multiplier == pytest.approx(1.0)
        assert props.projectile_blast_radius_multiplier == pytest.approx(1.0)
        assert props.projectile_launch_force_multiplier == pytest.approx(1.0)

    def test_magazine_consumed_keys_includes_damage_remaps(self):
        raw = {
            "Player_Damage": "40",
            "Zombie_Damage": "99",
            "Amount": "30",
        }
        keys = MagazineProperties.consumed_keys(raw)
        assert "Player_Damage" in keys
        assert "Zombie_Damage" in keys
        assert "Amount" in keys

    def test_magazine_ignore_known_keys(self):
        assert MagazineProperties.is_ignored("Tracer") is True
        assert MagazineProperties.is_ignored("Impact") is True
        assert MagazineProperties.is_ignored("Explosion") is True
        assert MagazineProperties.is_ignored("Spawn_Explosion_On_Dedicated_Server") is True
        assert MagazineProperties.is_ignored("Amount") is False

    def test_magazine_serializes_flat(self):
        props = MagazineProperties.from_raw({})
        dumped = props.model_dump()
        assert isinstance(dumped, dict)
        assert "amount" in dumped
        assert "damage_player" in dumped
        assert "calibers" in dumped
