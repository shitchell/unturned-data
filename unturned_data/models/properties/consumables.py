"""Consumable property models: Food, Medical, Water."""

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


class ConsumableProperties(ItemProperties):
    """Properties shared by Food, Medical, and Water items."""

    IGNORE: ClassVar[set[str]] = {
        "Explosion",
        "Allow_Flesh_Fx",
        "Bypass_Allowed_To_Damage_Player",
        "BladeIDs",
        "BladeID",
        "Player_Skull_Multiplier",
        "Player_Spine_Multiplier",
        "Player_Arm_Multiplier",
        "Player_Leg_Multiplier",
        "Zombie_Skull_Multiplier",
        "Zombie_Spine_Multiplier",
        "Zombie_Arm_Multiplier",
        "Zombie_Leg_Multiplier",
        "Animal_Skull_Multiplier",
        "Animal_Spine_Multiplier",
        "Animal_Leg_Multiplier",
        "Player_Damage_Bleeding",
        "Player_Damage_Bones",
        "Player_Damage_Food",
        "Player_Damage_Water",
        "Player_Damage_Virus",
        "Player_Damage_Hallucination",
        "Stun_Zombie_Always",
        "Stun_Zombie_Never",
        "ConsumeAudioClip",
    }
    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"^Quest_Reward_\d+"),
        re.compile(r"^BladeID_\d+"),
    ]

    # Stat effects
    health: int = 0
    food: int = 0
    water: int = 0
    virus: int = 0
    disinfectant: int = 0
    energy: int = 0
    vision: int = 0
    oxygen: int = 0
    warmth: int = 0
    experience: int = 0

    # Damage per target
    damage_player: float = 0
    damage_zombie: float = 0
    damage_animal: float = 0
    damage_barricade: float = 0
    damage_structure: float = 0
    damage_vehicle: float = 0
    damage_resource: float = 0
    damage_object: float = 0

    # Combat stats
    range: float = 0
    durability: float = 0
    wear: int = 0
    invulnerable: bool = False

    # Status effects
    bleeding: bool = False
    bleeding_modifier: str = ""
    broken: bool = False
    bones_modifier: str = ""
    aid: bool = False
    should_delete_after_use: bool = True

    # Item rewards
    item_reward_spawn_id: int = 0
    min_item_rewards: int = 0
    max_item_rewards: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ConsumableProperties:
        fields: dict[str, Any] = {}

        # Stat effects
        fields["health"] = _get_int(raw, "Health")
        fields["food"] = _get_int(raw, "Food")
        fields["water"] = _get_int(raw, "Water")
        fields["virus"] = _get_int(raw, "Virus")
        fields["disinfectant"] = _get_int(raw, "Disinfectant")
        fields["energy"] = _get_int(raw, "Energy")
        fields["vision"] = _get_int(raw, "Vision")
        fields["oxygen"] = _get_int(raw, "Oxygen")
        fields["warmth"] = _get_int(raw, "Warmth")
        fields["experience"] = _get_int(raw, "Experience")

        # Damage per target
        _DAMAGE_TARGETS = (
            "player",
            "zombie",
            "animal",
            "barricade",
            "structure",
            "vehicle",
            "resource",
            "object",
        )
        for target in _DAMAGE_TARGETS:
            key = f"{target.capitalize()}_Damage"
            fields[f"damage_{target}"] = _get_float(raw, key)

        # Combat stats
        fields["range"] = _get_float(raw, "Range")
        fields["durability"] = _get_float(raw, "Durability")
        fields["wear"] = _get_int(raw, "Wear")
        fields["invulnerable"] = _get_bool(raw, "Invulnerable")

        # Status effects
        fields["bleeding"] = _get_bool(raw, "Bleeding")
        fields["bleeding_modifier"] = _get_str(raw, "Bleeding_Modifier")
        fields["broken"] = _get_bool(raw, "Broken")
        fields["bones_modifier"] = _get_str(raw, "Bones_Modifier")
        fields["aid"] = _get_bool(raw, "Aid")
        fields["should_delete_after_use"] = _get_bool(
            raw, "Should_Delete_After_Use", True
        )

        # Item rewards
        fields["item_reward_spawn_id"] = _get_int(raw, "Item_Reward_Spawn_ID")
        fields["min_item_rewards"] = _get_int(raw, "Min_Item_Rewards")
        fields["max_item_rewards"] = _get_int(raw, "Max_Item_Rewards")

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        """Override to account for remapped damage keys."""
        keys = super().consumed_keys(raw)
        # Damage keys use Target_Damage format, not Damage_Target
        for remap_key in (
            "Player_Damage",
            "Zombie_Damage",
            "Animal_Damage",
            "Barricade_Damage",
            "Structure_Damage",
            "Vehicle_Damage",
            "Resource_Damage",
            "Object_Damage",
        ):
            if remap_key in raw:
                keys.add(remap_key)
        return keys
