"""Tests for consumable property models: Food, Medical, Water."""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models.properties.consumables import ConsumableProperties

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
# Food
# ---------------------------------------------------------------------------


class TestFoodProperties:
    """ConsumableProperties.from_raw for Food items."""

    def test_food_properties_from_fixture(self):
        raw, _ = _load_fixture("food_beans")
        props = ConsumableProperties.from_raw(raw)

        assert props.health == 10
        assert props.food == 55
        # Beans don't have water/virus/vision
        assert props.water is None
        assert props.virus is None
        assert props.vision is None

    def test_food_defaults_correct(self):
        raw, _ = _load_fixture("food_beans")
        props = ConsumableProperties.from_raw(raw)

        # Beans have no combat or status effect properties
        assert props.bleeding is None
        assert props.broken is None
        assert props.aid is None
        assert props.should_delete_after_use is None
        assert props.damage_player is None
        assert props.range is None


# ---------------------------------------------------------------------------
# Medical
# ---------------------------------------------------------------------------


class TestMedicalProperties:
    """ConsumableProperties.from_raw for Medical items."""

    def test_medical_properties_from_fixture(self):
        raw, _ = _load_fixture("medical_bandage")
        props = ConsumableProperties.from_raw(raw)

        assert props.health == 15
        assert props.aid is True
        assert props.bleeding_modifier == "Heal"

    def test_medical_no_food_water(self):
        raw, _ = _load_fixture("medical_bandage")
        props = ConsumableProperties.from_raw(raw)

        assert props.food is None
        assert props.water is None


# ---------------------------------------------------------------------------
# Water
# ---------------------------------------------------------------------------


class TestWaterProperties:
    """ConsumableProperties.from_raw for Water items."""

    def test_water_properties_from_fixture(self):
        raw, _ = _load_fixture("water_berries")
        props = ConsumableProperties.from_raw(raw)

        assert props.health == 10
        assert props.food == 5
        assert props.water == 10
        assert props.virus == 5
        assert props.vision == 20

    def test_water_defaults(self):
        raw, _ = _load_fixture("water_berries")
        props = ConsumableProperties.from_raw(raw)

        assert props.aid is None
        assert props.bleeding is None
        assert props.should_delete_after_use is None


# ---------------------------------------------------------------------------
# Defaults & Serialization
# ---------------------------------------------------------------------------


class TestConsumableGeneral:
    """General ConsumableProperties tests."""

    def test_consumable_defaults(self):
        """Empty raw dict produces None for all scalar fields."""
        props = ConsumableProperties.from_raw({})

        assert props.health is None
        assert props.food is None
        assert props.water is None
        assert props.virus is None
        assert props.disinfectant is None
        assert props.energy is None
        assert props.vision is None
        assert props.oxygen is None
        assert props.warmth is None
        assert props.experience is None

        assert props.damage_player is None
        assert props.damage_zombie is None
        assert props.damage_animal is None
        assert props.damage_barricade is None
        assert props.damage_structure is None
        assert props.damage_vehicle is None
        assert props.damage_resource is None
        assert props.damage_object is None

        assert props.range is None
        assert props.durability is None
        assert props.wear is None
        assert props.invulnerable is None

        assert props.bleeding is None
        assert props.bleeding_modifier is None
        assert props.broken is None
        assert props.bones_modifier is None
        assert props.aid is None
        assert props.should_delete_after_use is None

        assert props.item_reward_spawn_id is None
        assert props.min_item_rewards is None
        assert props.max_item_rewards is None

    def test_consumable_serializes(self):
        """model_dump works and produces flat dict."""
        raw, _ = _load_fixture("food_beans")
        props = ConsumableProperties.from_raw(raw)
        dumped = props.model_dump()

        assert isinstance(dumped, dict)
        for key, val in dumped.items():
            assert not isinstance(val, dict), f"{key} should not be a dict"
        # Spot check keys exist
        assert "health" in dumped
        assert "food" in dumped
        assert "aid" in dumped
        assert "bleeding_modifier" in dumped
        assert "should_delete_after_use" in dumped

    def test_consumable_from_synthetic_raw(self):
        """Test with synthetic raw data covering more fields."""
        raw = {
            "Health": 25,
            "Food": -10,
            "Water": 30,
            "Virus": -5,
            "Disinfectant": 10,
            "Energy": 5,
            "Vision": 15,
            "Oxygen": 0,
            "Warmth": 20,
            "Experience": 3,
            "Player_Damage": 10,
            "Range": 5.0,
            "Durability": 0.5,
            "Wear": 2,
            "Bleeding": True,
            "Bleeding_Modifier": "Heal",
            "Broken": True,
            "Bones_Modifier": "Heal",
            "Aid": True,
            "Should_Delete_After_Use": False,
            "Item_Reward_Spawn_ID": 42,
            "Min_Item_Rewards": 1,
            "Max_Item_Rewards": 3,
        }
        props = ConsumableProperties.from_raw(raw)

        assert props.health == 25
        assert props.food == -10
        assert props.water == 30
        assert props.virus == -5
        assert props.disinfectant == 10
        assert props.energy == 5
        assert props.vision == 15
        assert props.warmth == 20
        assert props.experience == 3
        assert props.damage_player == 10.0
        assert props.range == pytest.approx(5.0)
        assert props.durability == pytest.approx(0.5)
        assert props.wear == 2
        assert props.bleeding is True
        assert props.bleeding_modifier == "Heal"
        assert props.broken is True
        assert props.bones_modifier == "Heal"
        assert props.aid is True
        assert props.should_delete_after_use is False
        assert props.item_reward_spawn_id == 42
        assert props.min_item_rewards == 1
        assert props.max_item_rewards == 3
