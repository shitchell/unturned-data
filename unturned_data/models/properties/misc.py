"""Misc property models: Cloud, Map, Key, Fisher, Fuel, Optic, Refill, Box, etc."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from unturned_data.models.properties.base import ItemProperties


def _get_int(raw: dict[str, Any], key: str, default: int = 0) -> int:
    val = raw.get(key)
    if val is None:
        return default
    return int(val)


def _get_float(raw: dict[str, Any], key: str, default: float = 0.0) -> float:
    val = raw.get(key)
    if val is None:
        return default
    return float(val)


def _get_bool(raw: dict[str, Any], key: str, default: bool = False) -> bool:
    val = raw.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "y")
    return bool(val)


def _get_str(raw: dict[str, Any], key: str, default: str = "") -> str:
    val = raw.get(key)
    if val is None:
        return default
    return str(val)


# ---------------------------------------------------------------------------
# CloudProperties
# ---------------------------------------------------------------------------

class CloudProperties(ItemProperties):
    """Properties for Cloud items (smoke grenades, etc.)."""

    gravity: float = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> CloudProperties:
        return cls(gravity=_get_float(raw, "Gravity"))


# ---------------------------------------------------------------------------
# MapProperties
# ---------------------------------------------------------------------------

class MapProperties(ItemProperties):
    """Properties for Map items."""

    enables_compass: bool = False
    enables_chart: bool = False
    enables_map: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> MapProperties:
        return cls(
            enables_compass=_get_bool(raw, "Enables_Compass"),
            enables_chart=_get_bool(raw, "Enables_Chart"),
            enables_map=_get_bool(raw, "Enables_Map"),
        )


# ---------------------------------------------------------------------------
# KeyProperties
# ---------------------------------------------------------------------------

class KeyProperties(ItemProperties):
    """Properties for Key items."""

    exchange_with_target_item: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> KeyProperties:
        return cls(
            exchange_with_target_item=_get_bool(raw, "Exchange_With_Target_Item"),
        )


# ---------------------------------------------------------------------------
# FisherProperties
# ---------------------------------------------------------------------------

class FisherProperties(ItemProperties):
    """Properties for Fisher items (fishing rods)."""

    reward_id: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> FisherProperties:
        return cls(reward_id=_get_int(raw, "Reward_ID"))


# ---------------------------------------------------------------------------
# FuelProperties
# ---------------------------------------------------------------------------

class FuelProperties(ItemProperties):
    """Properties for Fuel items (gas cans, etc.)."""

    fuel: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> FuelProperties:
        return cls(fuel=_get_int(raw, "Fuel"))


# ---------------------------------------------------------------------------
# OpticProperties
# ---------------------------------------------------------------------------

class OpticProperties(ItemProperties):
    """Properties for Optic items (binoculars, etc.)."""

    zoom: float = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> OpticProperties:
        return cls(zoom=_get_float(raw, "Zoom"))


# ---------------------------------------------------------------------------
# RefillProperties
# ---------------------------------------------------------------------------

# Water quality prefixes and stat suffixes for RefillProperties
_WATER_QUALITIES = ("clean", "salty", "dirty")
_WATER_STATS = ("health", "food", "water", "virus", "stamina", "oxygen")


class RefillProperties(ItemProperties):
    """Properties for Refill items (water containers)."""

    water: float = 0
    clean_health: float = 0
    salty_health: float = 0
    dirty_health: float = 0
    clean_food: float = 0
    salty_food: float = 0
    dirty_food: float = 0
    clean_water: float = 0
    salty_water: float = 0
    dirty_water: float = 0
    clean_virus: float = 0
    salty_virus: float = 0
    dirty_virus: float = 0
    clean_stamina: float = 0
    salty_stamina: float = 0
    dirty_stamina: float = 0
    clean_oxygen: float = 0
    salty_oxygen: float = 0
    dirty_oxygen: float = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> RefillProperties:
        fields: dict[str, Any] = {}
        fields["water"] = _get_float(raw, "Water")
        for quality in _WATER_QUALITIES:
            for stat in _WATER_STATS:
                dat_key = f"{quality.capitalize()}_{stat.capitalize()}"
                field_name = f"{quality}_{stat}"
                fields[field_name] = _get_float(raw, dat_key)
        return cls(**fields)


# ---------------------------------------------------------------------------
# BoxProperties
# ---------------------------------------------------------------------------

class BoxProperties(ItemProperties):
    """Properties for Box items (mystery boxes, etc.)."""

    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = [re.compile(r"^Drop_\d+$")]

    generate: int = 0
    destroy: int = 0
    drops: int = 0
    item_origin: str = ""
    probability_model: str = ""
    contains_bonus_items: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BoxProperties:
        return cls(
            generate=_get_int(raw, "Generate"),
            destroy=_get_int(raw, "Destroy"),
            drops=_get_int(raw, "Drops"),
            item_origin=_get_str(raw, "Item_Origin"),
            probability_model=_get_str(raw, "Probability_Model"),
            contains_bonus_items=_get_bool(raw, "Contains_Bonus_Items"),
        )


# ---------------------------------------------------------------------------
# TireProperties
# ---------------------------------------------------------------------------

class TireProperties(ItemProperties):
    """Properties for Tire items."""

    mode: str = ""

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TireProperties:
        return cls(mode=_get_str(raw, "Mode"))


# ---------------------------------------------------------------------------
# Empty property types (no type-specific fields)
# ---------------------------------------------------------------------------

class CompassProperties(ItemProperties):
    """Properties for Compass items."""
    pass


class DetonatorProperties(ItemProperties):
    """Properties for Detonator items."""
    pass


class FilterProperties(ItemProperties):
    """Properties for Filter items."""
    pass


class GrowerProperties(ItemProperties):
    """Properties for Grower items."""
    pass


class SupplyProperties(ItemProperties):
    """Properties for Supply items."""
    pass


class ToolProperties(ItemProperties):
    """Properties for Tool items."""
    pass


class VehicleRepairToolProperties(ItemProperties):
    """Properties for Vehicle_Repair_Tool items."""
    pass


class ArrestStartProperties(ItemProperties):
    """Properties for Arrest_Start items (handcuffs)."""
    pass


class ArrestEndProperties(ItemProperties):
    """Properties for Arrest_End items (handcuff keys)."""
    pass
