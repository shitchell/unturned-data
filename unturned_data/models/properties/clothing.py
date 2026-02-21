"""Clothing property models: ClothingProperties, BagProperties, GearProperties."""

from __future__ import annotations

from typing import Any, ClassVar

from unturned_data.models.properties.base import ItemProperties


def _get_float(
    raw: dict[str, Any], key: str, default: float | None = None
) -> float | None:
    val = raw.get(key)
    if val is None:
        return default
    return float(val)


def _get_int(raw: dict[str, Any], key: str, default: int | None = None) -> int | None:
    val = raw.get(key)
    if val is None:
        return default
    return int(val)


def _get_bool(
    raw: dict[str, Any], key: str, default: bool | None = None
) -> bool | None:
    val = raw.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "y")
    return bool(val)


def _get_str(raw: dict[str, Any], key: str, default: str | None = None) -> str | None:
    val = raw.get(key)
    if val is None:
        return default
    return str(val)


class ClothingProperties(ItemProperties):
    """Base clothing properties shared by all clothing types."""

    IGNORE: ClassVar[set[str]] = {
        "Mirror_Left_Handed_Model",
        "Has_1P_Character_Mesh_Override",
        "Character_Mesh_3P_Override_LODs",
        "Has_Character_Material_Override",
        "Ignore_Hand",
    }

    armor: float | None = None
    armor_explosion: float | None = None
    proof_water: bool | None = None
    proof_fire: bool | None = None
    proof_radiation: bool | None = None
    movement_speed_multiplier: float | None = None
    visible_on_ragdoll: bool | None = None
    hair_visible: bool | None = None
    beard_visible: bool | None = None

    @classmethod
    def _extract_clothing_fields(cls, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract fields common to all clothing types."""
        fields: dict[str, Any] = {}
        fields["armor"] = _get_float(raw, "Armor")
        fields["armor_explosion"] = _get_float(raw, "Armor_Explosion")
        fields["proof_water"] = _get_bool(raw, "Proof_Water")
        fields["proof_fire"] = _get_bool(raw, "Proof_Fire")
        fields["proof_radiation"] = _get_bool(raw, "Proof_Radiation")
        fields["movement_speed_multiplier"] = _get_float(
            raw, "Movement_Speed_Multiplier"
        )
        fields["visible_on_ragdoll"] = _get_bool(raw, "Visible_On_Ragdoll")
        fields["hair_visible"] = _get_bool(raw, "Hair_Visible")
        fields["beard_visible"] = _get_bool(raw, "Beard_Visible")
        return fields

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ClothingProperties:
        fields = cls._extract_clothing_fields(raw)
        return cls(**fields)


class BagProperties(ClothingProperties):
    """Properties for Backpack, Pants, Shirt, Vest (have storage)."""

    width: int | None = None
    height: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BagProperties:
        fields = cls._extract_clothing_fields(raw)
        fields["width"] = _get_int(raw, "Width")
        fields["height"] = _get_int(raw, "Height")
        return cls(**fields)


class GearProperties(ClothingProperties):
    """Properties for Hat, Mask, Glasses."""

    hair: bool | None = None
    beard: bool | None = None
    hair_override: str | None = None
    vision: str | None = None
    nightvision_color_r: int | None = None
    nightvision_color_g: int | None = None
    nightvision_color_b: int | None = None
    nightvision_fog_intensity: float | None = None
    blindfold: bool | None = None
    earpiece: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> GearProperties:
        fields = cls._extract_clothing_fields(raw)
        fields["hair"] = _get_bool(raw, "Hair")
        fields["beard"] = _get_bool(raw, "Beard")
        fields["hair_override"] = _get_str(raw, "Hair_Override")
        fields["vision"] = _get_str(raw, "Vision")
        fields["nightvision_color_r"] = _get_int(raw, "Nightvision_Color_R")
        fields["nightvision_color_g"] = _get_int(raw, "Nightvision_Color_G")
        fields["nightvision_color_b"] = _get_int(raw, "Nightvision_Color_B")
        fields["nightvision_fog_intensity"] = _get_float(
            raw, "Nightvision_Fog_Intensity"
        )
        fields["blindfold"] = _get_bool(raw, "Blindfold")
        fields["earpiece"] = _get_bool(raw, "Earpiece")
        return cls(**fields)
