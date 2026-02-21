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
    recoil_x: float = 1.0
    recoil_y: float = 1.0
    aiming_recoil_multiplier: float = 1.0
    spread: float = 1.0
    sway: float = 1.0
    shake: float = 1.0
    damage: float = 1.0
    firerate: int = 0
    ballistic_damage_multiplier: float = 0
    paintable: bool = False
    bipod: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> CaliberProperties:
        fields: dict[str, Any] = {}

        fields["calibers"] = _parse_calibers(raw)
        fields["recoil_x"] = _get_float(raw, "Recoil_X", 1.0)
        fields["recoil_y"] = _get_float(raw, "Recoil_Y", 1.0)
        fields["aiming_recoil_multiplier"] = _get_float(
            raw, "Aiming_Recoil_Multiplier", 1.0
        )
        fields["spread"] = _get_float(raw, "Spread", 1.0)
        fields["sway"] = _get_float(raw, "Sway", 1.0)
        fields["shake"] = _get_float(raw, "Shake", 1.0)
        fields["damage"] = _get_float(raw, "Damage", 1.0)
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

    vision: str = ""
    zoom: float = 0
    holographic: bool = False
    nightvision_color_r: int = 0
    nightvision_color_g: int = 0
    nightvision_color_b: int = 0
    nightvision_fog_intensity: float = 0

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

    braked: bool = False
    silenced: bool = False
    volume: float = 1.0
    durability: int = 0
    ballistic_drop: float = 1.0
    gunshot_rolloff_distance_multiplier: float = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BarrelProperties:
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["braked"] = _get_bool(raw, "Braked")
        fields["silenced"] = _get_bool(raw, "Silenced")
        fields["volume"] = _get_float(raw, "Volume", 1.0)
        fields["durability"] = _get_int(raw, "Durability")
        fields["ballistic_drop"] = _get_float(raw, "Ballistic_Drop", 1.0)
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

    laser: bool = False
    light: bool = False
    rangefinder: bool = False
    melee: bool = False
    spotlight_range: float = 64.0
    spotlight_angle: float = 90.0
    spotlight_intensity: float = 1.3
    spotlight_color_r: int = 245
    spotlight_color_g: int = 223
    spotlight_color_b: int = 147

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TacticalProperties:
        base = CaliberProperties.from_raw(raw)
        fields = base.model_dump()

        fields["laser"] = _get_bool(raw, "Laser")
        fields["light"] = _get_bool(raw, "Light")
        fields["rangefinder"] = _get_bool(raw, "Rangefinder")
        fields["melee"] = _get_bool(raw, "Melee")
        fields["spotlight_range"] = _get_float(raw, "Spotlight_Range", 64.0)
        fields["spotlight_angle"] = _get_float(raw, "Spotlight_Angle", 90.0)
        fields["spotlight_intensity"] = _get_float(
            raw, "Spotlight_Intensity", 1.3
        )
        fields["spotlight_color_r"] = _get_int(raw, "Spotlight_Color_R", 245)
        fields["spotlight_color_g"] = _get_int(raw, "Spotlight_Color_G", 223)
        fields["spotlight_color_b"] = _get_int(raw, "Spotlight_Color_B", 147)

        return cls(**fields)


# ---------------------------------------------------------------------------
# MagazineProperties
# ---------------------------------------------------------------------------

_MAGAZINE_DAMAGE_TARGETS = (
    "player", "zombie", "animal", "barricade", "structure",
    "vehicle", "resource", "object",
)


class MagazineProperties(CaliberProperties):
    """Properties specific to Magazine attachments."""

    IGNORE: ClassVar[set[str]] = {
        "Tracer", "Impact", "Explosion",
        "Spawn_Explosion_On_Dedicated_Server",
    }

    amount: int = 0
    count_min: int = 0
    count_max: int = 0
    pellets: int = 0
    stuck: int = 0
    projectile_damage_multiplier: float = 1.0
    projectile_blast_radius_multiplier: float = 1.0
    projectile_launch_force_multiplier: float = 1.0
    range: float = 0
    damage_player: float = 0
    damage_zombie: float = 0
    damage_animal: float = 0
    damage_barricade: float = 0
    damage_structure: float = 0
    damage_vehicle: float = 0
    damage_resource: float = 0
    damage_object: float = 0
    explosion_launch_speed: float = 0
    speed: float = 0
    explosive: bool = False
    delete_empty: bool = False
    should_fill_after_detach: bool = False

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
            raw, "Projectile_Damage_Multiplier", 1.0
        )
        fields["projectile_blast_radius_multiplier"] = _get_float(
            raw, "Projectile_Blast_Radius_Multiplier", 1.0
        )
        fields["projectile_launch_force_multiplier"] = _get_float(
            raw, "Projectile_Launch_Force_Multiplier", 1.0
        )
        fields["range"] = _get_float(raw, "Range")
        fields["explosion_launch_speed"] = _get_float(
            raw, "Explosion_Launch_Speed"
        )
        fields["speed"] = _get_float(raw, "Speed")
        fields["explosive"] = _get_bool(raw, "Explosive")
        fields["delete_empty"] = _get_bool(raw, "Delete_Empty")
        fields["should_fill_after_detach"] = _get_bool(
            raw, "Should_Fill_After_Detach"
        )

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
