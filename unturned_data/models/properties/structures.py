"""Structure property models: walls, floors, pillars, roofs, etc."""

from __future__ import annotations

from typing import Any, ClassVar

from unturned_data.models.properties.base import ItemProperties


def _get_int(raw: dict[str, Any], key: str, default: int | None = None) -> int | None:
    val = raw.get(key)
    if val is None:
        return default
    return int(val)


def _get_float(
    raw: dict[str, Any], key: str, default: float | None = None
) -> float | None:
    val = raw.get(key)
    if val is None:
        return default
    return float(val)


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


class StructureProperties(ItemProperties):
    """Properties for structure items (walls, floors, pillars, roofs, etc.)."""

    IGNORE: ClassVar[set[str]] = {
        "Has_Clip_Prefab",
        "Explosion",
        "Eligible_For_Pooling",
        "PlacementAudioClip",
    }

    construct: str | None = None
    health: int | None = None
    range: float | None = None
    can_be_damaged: bool | None = None
    requires_pillars: bool | None = None
    vulnerable: bool | None = None
    unrepairable: bool | None = None
    proof_explosion: bool | None = None
    unpickupable: bool | None = None
    unsalvageable: bool | None = None
    salvage_duration_multiplier: float | None = None
    unsaveable: bool | None = None
    armor_tier: str | None = None
    foliage_cut_radius: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> StructureProperties:
        fields: dict[str, Any] = {}
        fields["construct"] = _get_str(raw, "Construct")
        fields["health"] = _get_int(raw, "Health")
        fields["range"] = _get_float(raw, "Range")
        fields["can_be_damaged"] = _get_bool(raw, "Can_Be_Damaged")
        fields["requires_pillars"] = _get_bool(raw, "Requires_Pillars")
        fields["vulnerable"] = _get_bool(raw, "Vulnerable")
        fields["unrepairable"] = _get_bool(raw, "Unrepairable")
        fields["proof_explosion"] = _get_bool(raw, "Proof_Explosion")
        fields["unpickupable"] = _get_bool(raw, "Unpickupable")
        fields["unsalvageable"] = _get_bool(raw, "Unsalvageable")
        fields["salvage_duration_multiplier"] = _get_float(
            raw, "Salvage_Duration_Multiplier"
        )
        fields["unsaveable"] = _get_bool(raw, "Unsaveable")
        fields["armor_tier"] = _get_str(raw, "Armor_Tier")
        fields["foliage_cut_radius"] = _get_float(raw, "Foliage_Cut_Radius")
        return cls(**fields)
