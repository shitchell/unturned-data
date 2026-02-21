"""Tests for misc property models."""

from __future__ import annotations

import pytest

from unturned_data.models.properties import PROPERTIES_REGISTRY
from unturned_data.models.properties.misc import (
    ArrestEndProperties,
    ArrestStartProperties,
    BoxProperties,
    CloudProperties,
    CompassProperties,
    DetonatorProperties,
    FilterProperties,
    FisherProperties,
    FuelProperties,
    GrowerProperties,
    KeyProperties,
    MapProperties,
    OpticProperties,
    RefillProperties,
    SupplyProperties,
    TireProperties,
    ToolProperties,
    VehicleRepairToolProperties,
)


# ---------------------------------------------------------------------------
# CloudProperties
# ---------------------------------------------------------------------------


class TestCloudProperties:
    def test_defaults(self):
        props = CloudProperties()
        assert props.gravity == 0

    def test_from_raw(self):
        raw = {"Gravity": "4.5"}
        props = CloudProperties.from_raw(raw)
        assert props.gravity == 4.5

    def test_from_raw_empty(self):
        props = CloudProperties.from_raw({})
        assert props.gravity == 0


# ---------------------------------------------------------------------------
# MapProperties
# ---------------------------------------------------------------------------


class TestMapProperties:
    def test_defaults(self):
        props = MapProperties()
        assert props.enables_compass is False
        assert props.enables_chart is False
        assert props.enables_map is False

    def test_from_raw(self):
        raw = {
            "Enables_Compass": "true",
            "Enables_Chart": "true",
            "Enables_Map": "true",
        }
        props = MapProperties.from_raw(raw)
        assert props.enables_compass is True
        assert props.enables_chart is True
        assert props.enables_map is True

    def test_from_raw_partial(self):
        raw = {"Enables_Map": "true"}
        props = MapProperties.from_raw(raw)
        assert props.enables_compass is False
        assert props.enables_chart is False
        assert props.enables_map is True


# ---------------------------------------------------------------------------
# KeyProperties
# ---------------------------------------------------------------------------


class TestKeyProperties:
    def test_defaults(self):
        props = KeyProperties()
        assert props.exchange_with_target_item is False

    def test_from_raw(self):
        raw = {"Exchange_With_Target_Item": "true"}
        props = KeyProperties.from_raw(raw)
        assert props.exchange_with_target_item is True


# ---------------------------------------------------------------------------
# FisherProperties
# ---------------------------------------------------------------------------


class TestFisherProperties:
    def test_defaults(self):
        props = FisherProperties()
        assert props.reward_id == 0

    def test_from_raw(self):
        raw = {"Reward_ID": "42"}
        props = FisherProperties.from_raw(raw)
        assert props.reward_id == 42


# ---------------------------------------------------------------------------
# FuelProperties
# ---------------------------------------------------------------------------


class TestFuelProperties:
    def test_defaults(self):
        props = FuelProperties()
        assert props.fuel == 0

    def test_from_raw(self):
        raw = {"Fuel": "500"}
        props = FuelProperties.from_raw(raw)
        assert props.fuel == 500


# ---------------------------------------------------------------------------
# OpticProperties
# ---------------------------------------------------------------------------


class TestOpticProperties:
    def test_defaults(self):
        props = OpticProperties()
        assert props.zoom == 0

    def test_from_raw(self):
        raw = {"Zoom": "2.5"}
        props = OpticProperties.from_raw(raw)
        assert props.zoom == 2.5


# ---------------------------------------------------------------------------
# RefillProperties
# ---------------------------------------------------------------------------


class TestRefillProperties:
    def test_defaults(self):
        props = RefillProperties()
        assert props.water == 0
        # Verify all 18 quality/stat fields default to 0
        for quality in ("clean", "salty", "dirty"):
            for stat in ("health", "food", "water", "virus", "stamina", "oxygen"):
                assert getattr(props, f"{quality}_{stat}") == 0

    def test_from_raw_all_fields(self):
        raw = {"Water": "10"}
        # Build raw dict with all 18 quality/stat fields
        val = 1.0
        for quality in ("Clean", "Salty", "Dirty"):
            for stat in ("Health", "Food", "Water", "Virus", "Stamina", "Oxygen"):
                raw[f"{quality}_{stat}"] = str(val)
                val += 1.0

        props = RefillProperties.from_raw(raw)
        assert props.water == 10.0
        # Verify all fields parsed correctly
        expected = 1.0
        for quality in ("clean", "salty", "dirty"):
            for stat in ("health", "food", "water", "virus", "stamina", "oxygen"):
                assert getattr(props, f"{quality}_{stat}") == expected
                expected += 1.0

    def test_from_raw_partial(self):
        raw = {"Water": "5", "Clean_Health": "10", "Dirty_Virus": "3"}
        props = RefillProperties.from_raw(raw)
        assert props.water == 5.0
        assert props.clean_health == 10.0
        assert props.dirty_virus == 3.0
        assert props.salty_food == 0

    def test_field_count(self):
        """RefillProperties should have exactly 19 fields (water + 18 quality/stat)."""
        assert len(RefillProperties.model_fields) == 19


# ---------------------------------------------------------------------------
# BoxProperties
# ---------------------------------------------------------------------------


class TestBoxProperties:
    def test_defaults(self):
        props = BoxProperties()
        assert props.generate == 0
        assert props.destroy == 0
        assert props.drops == 0
        assert props.item_origin == ""
        assert props.probability_model == ""
        assert props.contains_bonus_items is False

    def test_from_raw(self):
        raw = {
            "Generate": "10",
            "Destroy": "5",
            "Drops": "3",
            "Item_Origin": "Craft",
            "Probability_Model": "Original",
            "Contains_Bonus_Items": "true",
        }
        props = BoxProperties.from_raw(raw)
        assert props.generate == 10
        assert props.destroy == 5
        assert props.drops == 3
        assert props.item_origin == "Craft"
        assert props.probability_model == "Original"
        assert props.contains_bonus_items is True

    def test_ignore_drop_pattern(self):
        assert BoxProperties.is_ignored("Drop_0")
        assert BoxProperties.is_ignored("Drop_5")
        assert BoxProperties.is_ignored("Drop_99")
        assert not BoxProperties.is_ignored("Drops")
        assert not BoxProperties.is_ignored("Generate")


# ---------------------------------------------------------------------------
# TireProperties
# ---------------------------------------------------------------------------


class TestTireProperties:
    def test_defaults(self):
        props = TireProperties()
        assert props.mode == ""

    def test_from_raw(self):
        raw = {"Mode": "Add"}
        props = TireProperties.from_raw(raw)
        assert props.mode == "Add"


# ---------------------------------------------------------------------------
# Empty types
# ---------------------------------------------------------------------------


_EMPTY_TYPES = [
    CompassProperties,
    DetonatorProperties,
    FilterProperties,
    GrowerProperties,
    SupplyProperties,
    ToolProperties,
    VehicleRepairToolProperties,
    ArrestStartProperties,
    ArrestEndProperties,
]


class TestEmptyTypes:
    @pytest.mark.parametrize("cls", _EMPTY_TYPES, ids=lambda c: c.__name__)
    def test_instantiates(self, cls):
        props = cls()
        assert props.model_dump() == {}

    @pytest.mark.parametrize("cls", _EMPTY_TYPES, ids=lambda c: c.__name__)
    def test_from_raw_empty(self, cls):
        props = cls.from_raw({})
        assert props.model_dump() == {}

    @pytest.mark.parametrize("cls", _EMPTY_TYPES, ids=lambda c: c.__name__)
    def test_from_raw_with_extra_keys(self, cls):
        """Extra keys in raw are silently ignored."""
        props = cls.from_raw({"Some_Unknown_Key": "value"})
        assert props.model_dump() == {}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_EXPECTED_REGISTRY = {
    "Cloud": CloudProperties,
    "Map": MapProperties,
    "Key": KeyProperties,
    "Fisher": FisherProperties,
    "Fuel": FuelProperties,
    "Optic": OpticProperties,
    "Refill": RefillProperties,
    "Box": BoxProperties,
    "Tire": TireProperties,
    "Compass": CompassProperties,
    "Detonator": DetonatorProperties,
    "Filter": FilterProperties,
    "Grower": GrowerProperties,
    "Supply": SupplyProperties,
    "Tool": ToolProperties,
    "Vehicle_Repair_Tool": VehicleRepairToolProperties,
    "Arrest_Start": ArrestStartProperties,
    "Arrest_End": ArrestEndProperties,
}


class TestMiscRegistry:
    @pytest.mark.parametrize(
        "type_name,expected_cls",
        _EXPECTED_REGISTRY.items(),
        ids=_EXPECTED_REGISTRY.keys(),
    )
    def test_registered(self, type_name, expected_cls):
        assert PROPERTIES_REGISTRY.get(type_name) is expected_cls

    def test_all_misc_registered(self):
        """All 18 misc types should be in the registry."""
        for type_name, cls in _EXPECTED_REGISTRY.items():
            assert (
                PROPERTIES_REGISTRY.get(type_name) is cls
            ), f"{type_name} not registered or wrong class"
