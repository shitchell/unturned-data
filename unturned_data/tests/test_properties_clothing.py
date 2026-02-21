"""Tests for clothing property models: ClothingProperties, BagProperties, GearProperties."""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models.properties.clothing import (
    BagProperties,
    ClothingProperties,
    GearProperties,
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
# ClothingProperties (base)
# ---------------------------------------------------------------------------


class TestClothingBaseDefaults:
    """ClothingProperties defaults with empty raw."""

    def test_clothing_base_defaults(self):
        props = ClothingProperties.from_raw({})

        assert props.armor is None
        assert props.armor_explosion is None
        assert props.proof_water is None
        assert props.proof_fire is None
        assert props.proof_radiation is None
        assert props.movement_speed_multiplier is None
        assert props.visible_on_ragdoll is None
        assert props.hair_visible is None
        assert props.beard_visible is None


# ---------------------------------------------------------------------------
# BagProperties
# ---------------------------------------------------------------------------


class TestBagProperties:
    """BagProperties.from_raw parsing."""

    def test_bag_properties_from_fixture(self):
        raw, _ = _load_fixture("backpack_alice")
        props = BagProperties.from_raw(raw)

        assert props.width > 0
        assert props.height > 0
        assert props.width == 8
        assert props.height == 7

    def test_bag_properties_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = BagProperties.from_raw({})

        assert props.width is None
        assert props.height is None
        # Inherits clothing defaults
        assert props.armor is None
        assert props.proof_water is None
        assert props.movement_speed_multiplier is None

    def test_bag_properties_serializes(self):
        raw, _ = _load_fixture("backpack_alice")
        props = BagProperties.from_raw(raw)
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        assert "width" in dumped
        assert "height" in dumped
        assert "armor" in dumped
        assert "proof_water" in dumped
        # All top-level keys, no nesting
        for key, val in dumped.items():
            assert not isinstance(val, dict), f"{key} should not be a dict"

    def test_bag_properties_with_armor(self):
        """Test bag with armor and proof fields set."""
        raw = {
            "Width": "5",
            "Height": "4",
            "Armor": "0.85",
            "Armor_Explosion": "0.5",
            "Proof_Water": "True",
            "Movement_Speed_Multiplier": "0.9",
        }
        props = BagProperties.from_raw(raw)

        assert props.width == 5
        assert props.height == 4
        assert props.armor == pytest.approx(0.85)
        assert props.armor_explosion == pytest.approx(0.5)
        assert props.proof_water is True
        assert props.movement_speed_multiplier == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# GearProperties
# ---------------------------------------------------------------------------


class TestGearProperties:
    """GearProperties.from_raw parsing."""

    def test_gear_properties_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = GearProperties.from_raw({})

        assert props.hair is None
        assert props.beard is None
        assert props.hair_override is None
        assert props.vision is None
        assert props.nightvision_color_r is None
        assert props.nightvision_color_g is None
        assert props.nightvision_color_b is None
        assert props.nightvision_fog_intensity is None
        assert props.blindfold is None
        assert props.earpiece is None
        # Inherits clothing defaults
        assert props.armor is None
        assert props.proof_water is None

    def test_gear_properties_nightvision(self):
        """Test gear with nightvision properties."""
        raw = {
            "Vision": "Military",
            "Nightvision_Color_R": "0",
            "Nightvision_Color_G": "200",
            "Nightvision_Color_B": "0",
            "Nightvision_Fog_Intensity": "0.25",
            "Armor": "0.9",
        }
        props = GearProperties.from_raw(raw)

        assert props.vision == "Military"
        assert props.nightvision_color_r == 0
        assert props.nightvision_color_g == 200
        assert props.nightvision_color_b == 0
        assert props.nightvision_fog_intensity == pytest.approx(0.25)
        assert props.armor == pytest.approx(0.9)

    def test_gear_properties_blindfold_earpiece(self):
        """Test blindfold and earpiece flags."""
        raw = {
            "Blindfold": "True",
            "Earpiece": "True",
        }
        props = GearProperties.from_raw(raw)

        assert props.blindfold is True
        assert props.earpiece is True

    def test_gear_properties_hair_beard(self):
        """Test hair/beard override fields."""
        raw = {
            "Hair": "True",
            "Beard": "True",
            "Hair_Override": "some_override",
            "Hair_Visible": "False",
            "Beard_Visible": "False",
        }
        props = GearProperties.from_raw(raw)

        assert props.hair is True
        assert props.beard is True
        assert props.hair_override == "some_override"
        assert props.hair_visible is False
        assert props.beard_visible is False

    def test_gear_properties_serializes(self):
        props = GearProperties.from_raw({})
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        assert "vision" in dumped
        assert "blindfold" in dumped
        assert "earpiece" in dumped
        assert "nightvision_color_r" in dumped
        assert "armor" in dumped
