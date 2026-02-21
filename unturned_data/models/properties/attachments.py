"""Attachment property models: Sight, Barrel, Grip, Tactical, Magazine."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from unturned_data.models.properties.base import ItemProperties, _snake_to_dat_key


def _get(raw: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from raw, returning *default* if missing."""
    val = raw.get(key)
    if val is None:
        return default
    return val


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


def _parse_calibers(raw: dict[str, Any]) -> list[int]:
    """Parse Calibers count + Caliber_{i} entries."""
    count = _get_int(raw, "Calibers", 0)
    result: list[int] = []
    for i in range(count):
        val = raw.get(f"Caliber_{i}")
        if val is not None:
            result.append(int(val))
    return result


# ---------------------------------------------------------------------------
# CaliberProperties (base for all attachments)
# ---------------------------------------------------------------------------


class CaliberProperties(ItemProperties):
    """Base for all attachment types (ItemCaliberAsset)."""

    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"^Caliber_\d+$"),
    ]

    calibers: list[int] = []
    recoil_x: float | None = None
    recoil_y: float | None = None
    aiming_recoil_multiplier: float | None = None
    spread: float | None = None
    sway: float | None = None
    shake: float | None = None
    damage: float | None = None
    firerate: int | None = None
    ballistic_damage_multiplier: float | None = None
    paintable: bool | None = None
    bipod: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> CaliberProperties:
        fields: dict[str, Any] = {}

        fields["calibers"] = _parse_calibers(raw)
        fields["recoil_x"] = _get_float(raw, "Recoil_X")
        fields["recoil_y"] = _get_float(raw, "Recoil_Y")
        fields["aiming_recoil_multiplier"] = _get_float(raw, "Aiming_Recoil_Multiplier")
        fields["spread"] = _get_float(raw, "Spread")
        fields["sway"] = _get_float(raw, "Sway")
        fields["shake"] = _get_float(raw, "Shake")
        fields["damage"] = _get_float(raw, "Damage")
        fields["firerate"] = _get_int(raw, "Firerate")
        fields["ballistic_damage_multiplier"] = _get_float(
            raw, "Ballistic_Damage_Multiplier"
        )
        fields["paintable"] = _get_bool(raw, "Paintable")
        fields["bipod"] = _get_bool(raw, "Bipod")

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        """Override to account for indexed caliber keys."""
        keys = super().consumed_keys(raw)
        # Calibers count key
        if "Calibers" in raw:
            keys.add("Calibers")
        # Caliber_{i} entries
        for key in raw:
            if re.match(r"^Caliber_\d+$", key):
                keys.add(key)
        return keys


# ---------------------------------------------------------------------------
# SightProperties
# ---------------------------------------------------------------------------


class SightProperties(CaliberProperties):
    """Properties specific to Sight attachments."""

    vision: str | None = None
    zoom: float | None = None
    holographic: bool | None = None
    nightvision_color_r: int | None = None
    nightvision_color_g: int | None = None
    nightvision_color_b: int | None = None
    nightvision_fog_intensity: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> SightProperties:
        # Get base CaliberProperties fields
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["vision"] = _get_str(raw, "Vision")
        fields["zoom"] = _get_float(raw, "Zoom")
        fields["holographic"] = _get_bool(raw, "Holographic")
        fields["nightvision_color_r"] = _get_int(raw, "Nightvision_Color_R")
        fields["nightvision_color_g"] = _get_int(raw, "Nightvision_Color_G")
        fields["nightvision_color_b"] = _get_int(raw, "Nightvision_Color_B")
        fields["nightvision_fog_intensity"] = _get_float(
            raw, "Nightvision_Fog_Intensity"
        )

        return cls(**fields)


# ---------------------------------------------------------------------------
# BarrelProperties
# ---------------------------------------------------------------------------


class BarrelProperties(CaliberProperties):
    """Properties specific to Barrel attachments."""

    braked: bool | None = None
    silenced: bool | None = None
    volume: float | None = None
    durability: int | None = None
    ballistic_drop: float | None = None
    gunshot_rolloff_distance_multiplier: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BarrelProperties:
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["braked"] = _get_bool(raw, "Braked")
        fields["silenced"] = _get_bool(raw, "Silenced")
        fields["volume"] = _get_float(raw, "Volume")
        fields["durability"] = _get_int(raw, "Durability")
        fields["ballistic_drop"] = _get_float(raw, "Ballistic_Drop")
        fields["gunshot_rolloff_distance_multiplier"] = _get_float(
            raw, "Gunshot_Rolloff_Distance_Multiplier"
        )

        return cls(**fields)


# ---------------------------------------------------------------------------
# GripProperties
# ---------------------------------------------------------------------------


class GripProperties(CaliberProperties):
    """Properties specific to Grip attachments.

    No additional fields beyond CaliberProperties.
    """

    pass  # No additional fields


# ---------------------------------------------------------------------------
# TacticalProperties
# ---------------------------------------------------------------------------


class TacticalProperties(CaliberProperties):
    """Properties specific to Tactical attachments."""

    laser: bool | None = None
    light: bool | None = None
    rangefinder: bool | None = None
    melee: bool | None = None
    spotlight_range: float | None = None
    spotlight_angle: float | None = None
    spotlight_intensity: float | None = None
    spotlight_color_r: int | None = None
    spotlight_color_g: int | None = None
    spotlight_color_b: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TacticalProperties:
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["laser"] = _get_bool(raw, "Laser")
        fields["light"] = _get_bool(raw, "Light")
        fields["rangefinder"] = _get_bool(raw, "Rangefinder")
        fields["melee"] = _get_bool(raw, "Melee")
        fields["spotlight_range"] = _get_float(raw, "Spotlight_Range")
        fields["spotlight_angle"] = _get_float(raw, "Spotlight_Angle")
        fields["spotlight_intensity"] = _get_float(raw, "Spotlight_Intensity")
        fields["spotlight_color_r"] = _get_int(raw, "Spotlight_Color_R")
        fields["spotlight_color_g"] = _get_int(raw, "Spotlight_Color_G")
        fields["spotlight_color_b"] = _get_int(raw, "Spotlight_Color_B")

        return cls(**fields)


# ---------------------------------------------------------------------------
# MagazineProperties
# ---------------------------------------------------------------------------

_MAGAZINE_DAMAGE_TARGETS = (
    "player",
    "zombie",
    "animal",
    "barricade",
    "structure",
    "vehicle",
    "resource",
    "object",
)


class MagazineProperties(CaliberProperties):
    """Properties specific to Magazine attachments."""

    IGNORE: ClassVar[set[str]] = {
        "Tracer",
        "Impact",
        "Explosion",
        "Spawn_Explosion_On_Dedicated_Server",
    }

    amount: int | None = None
    count_min: int | None = None
    count_max: int | None = None
    pellets: int | None = None
    stuck: int | None = None
    projectile_damage_multiplier: float | None = None
    projectile_blast_radius_multiplier: float | None = None
    projectile_launch_force_multiplier: float | None = None
    range: float | None = None
    damage_player: float | None = None
    damage_zombie: float | None = None
    damage_animal: float | None = None
    damage_barricade: float | None = None
    damage_structure: float | None = None
    damage_vehicle: float | None = None
    damage_resource: float | None = None
    damage_object: float | None = None
    explosion_launch_speed: float | None = None
    speed: float | None = None
    explosive: bool | None = None
    delete_empty: bool | None = None
    should_fill_after_detach: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> MagazineProperties:
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["amount"] = _get_int(raw, "Amount")
        fields["count_min"] = _get_int(raw, "Count_Min")
        fields["count_max"] = _get_int(raw, "Count_Max")
        fields["pellets"] = _get_int(raw, "Pellets")
        fields["stuck"] = _get_int(raw, "Stuck")
        fields["projectile_damage_multiplier"] = _get_float(
            raw, "Projectile_Damage_Multiplier"
        )
        fields["projectile_blast_radius_multiplier"] = _get_float(
            raw, "Projectile_Blast_Radius_Multiplier"
        )
        fields["projectile_launch_force_multiplier"] = _get_float(
            raw, "Projectile_Launch_Force_Multiplier"
        )
        fields["range"] = _get_float(raw, "Range")
        fields["explosion_launch_speed"] = _get_float(raw, "Explosion_Launch_Speed")
        fields["speed"] = _get_float(raw, "Speed")
        fields["explosive"] = _get_bool(raw, "Explosive")
        fields["delete_empty"] = _get_bool(raw, "Delete_Empty")
        fields["should_fill_after_detach"] = _get_bool(raw, "Should_Fill_After_Detach")

        # Damage fields: Player_Damage -> damage_player, etc.
        for target in _MAGAZINE_DAMAGE_TARGETS:
            dat_key = f"{target.capitalize()}_Damage"
            fields[f"damage_{target}"] = _get_float(raw, dat_key)

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        """Override to account for remapped damage keys."""
        keys = super().consumed_keys(raw)
        for target in _MAGAZINE_DAMAGE_TARGETS:
            remap_key = f"{target.capitalize()}_Damage"
            if remap_key in raw:
                keys.add(remap_key)
        return keys
