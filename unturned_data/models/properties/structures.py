"""Structure property models: walls, floors, pillars, roofs, etc."""

from __future__ import annotations

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


class StructureProperties(ItemProperties):
    """Properties for structure items (walls, floors, pillars, roofs, etc.)."""

    IGNORE: ClassVar[set[str]] = {
        "Has_Clip_Prefab",
        "Explosion",
        "Eligible_For_Pooling",
        "PlacementAudioClip",
    }

    construct: str = ""
    health: int = 0
    range: float = 0
    can_be_damaged: bool = True
    requires_pillars: bool = True
    vulnerable: bool = False
    unrepairable: bool = False
    proof_explosion: bool = False
    unpickupable: bool = False
    unsalvageable: bool = False
    salvage_duration_multiplier: float = 1.0
    unsaveable: bool = False
    armor_tier: str = ""
    foliage_cut_radius: float = 6.0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> StructureProperties:
        fields: dict[str, Any] = {}
        fields["construct"] = _get_str(raw, "Construct")
        fields["health"] = _get_int(raw, "Health")
        fields["range"] = _get_float(raw, "Range")
        fields["can_be_damaged"] = _get_bool(raw, "Can_Be_Damaged", True)
        fields["requires_pillars"] = _get_bool(raw, "Requires_Pillars", True)
        fields["vulnerable"] = _get_bool(raw, "Vulnerable")
        fields["unrepairable"] = _get_bool(raw, "Unrepairable")
        fields["proof_explosion"] = _get_bool(raw, "Proof_Explosion")
        fields["unpickupable"] = _get_bool(raw, "Unpickupable")
        fields["unsalvageable"] = _get_bool(raw, "Unsalvageable")
        fields["salvage_duration_multiplier"] = _get_float(
            raw, "Salvage_Duration_Multiplier", 1.0
        )
        fields["unsaveable"] = _get_bool(raw, "Unsaveable")
        fields["armor_tier"] = _get_str(raw, "Armor_Tier")
        fields["foliage_cut_radius"] = _get_float(
            raw, "Foliage_Cut_Radius", 6.0
        )
        return cls(**fields)
