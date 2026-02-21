"""Weapon property models: Gun, Melee, Throwable."""

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


def _parse_indexed_list(
    raw: dict[str, Any], count_key: str, item_prefix: str
) -> list[int]:
    """Parse indexed list like Magazine_Calibers + Magazine_Caliber_0, _1, ..."""
    count = _get_int(raw, count_key, 0)
    result: list[int] = []
    for i in range(count):
        val = raw.get(f"{item_prefix}_{i}")
        if val is not None:
            result.append(int(val))
    return result


def _parse_magazine_replacements(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Magazine_Replacements count + Magazine_Replacement_{i}_ID/Map."""
    count = _get_int(raw, "Magazine_Replacements", 0)
    result: list[dict[str, Any]] = []
    for i in range(count):
        entry: dict[str, Any] = {}
        rid = raw.get(f"Magazine_Replacement_{i}_ID")
        if rid is not None:
            entry["id"] = int(rid)
        rmap = raw.get(f"Magazine_Replacement_{i}_Map")
        if rmap is not None:
            entry["map"] = str(rmap)
        if entry:
            result.append(entry)
    return result


# ---- Shared damage extraction helpers ----

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

_PLAYER_MULTIPLIERS = ("skull", "spine", "arm", "leg")
_ZOMBIE_MULTIPLIERS = ("skull", "spine", "arm", "leg")
_ANIMAL_MULTIPLIERS = ("skull", "spine", "leg")


def _extract_damage_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract damage_* and *_multiplier fields common to guns and melee."""
    fields: dict[str, Any] = {}
    for target in _DAMAGE_TARGETS:
        key = f"{target.capitalize()}_Damage"
        fields[f"damage_{target}"] = _get_float(raw, key)

    for part in _PLAYER_MULTIPLIERS:
        key = f"Player_{part.capitalize()}_Multiplier"
        fields[f"player_{part}_multiplier"] = _get_float(raw, key)

    for part in _ZOMBIE_MULTIPLIERS:
        key = f"Zombie_{part.capitalize()}_Multiplier"
        fields[f"zombie_{part}_multiplier"] = _get_float(raw, key)

    for part in _ANIMAL_MULTIPLIERS:
        key = f"Animal_{part.capitalize()}_Multiplier"
        fields[f"animal_{part}_multiplier"] = _get_float(raw, key)

    return fields


# ---------------------------------------------------------------------------
# GunProperties
# ---------------------------------------------------------------------------


class GunProperties(ItemProperties):
    """Properties specific to Gun items."""

    IGNORE: ClassVar[set[str]] = {
        "Muzzle",
        "Shell",
        "Explosion",
        "BladeIDs",
        "BladeID",
        "Allow_Flesh_Fx",
        "Bypass_Allowed_To_Damage_Player",
        "Aim_In_Duration",
        "Spread_Angle_Degrees",
    }
    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"^Shoot_Quest_Reward_\d+"),
        re.compile(r"^Hook_"),
        re.compile(r"^BladeID_\d+"),
        re.compile(r"^Magazine_Replacement_\d+"),
        re.compile(r"^Magazine_Caliber_\d+"),
        re.compile(r"^Attachment_Caliber_\d+"),
    ]

    # Fire
    firerate: int = 0
    action: str = ""
    safety: bool = False
    semi: bool = False
    auto: bool = False
    bursts: int = 0
    turret: bool = False

    # Damage per target
    damage_player: float = 0
    damage_zombie: float = 0
    damage_animal: float = 0
    damage_barricade: float = 0
    damage_structure: float = 0
    damage_vehicle: float = 0
    damage_resource: float = 0
    damage_object: float = 0

    # Player multipliers
    player_skull_multiplier: float = 0
    player_spine_multiplier: float = 0
    player_arm_multiplier: float = 0
    player_leg_multiplier: float = 0

    # Zombie multipliers
    zombie_skull_multiplier: float = 0
    zombie_spine_multiplier: float = 0
    zombie_arm_multiplier: float = 0
    zombie_leg_multiplier: float = 0

    # Animal multipliers
    animal_skull_multiplier: float = 0
    animal_spine_multiplier: float = 0
    animal_leg_multiplier: float = 0

    # Damage mods
    player_damage_bleeding: str = ""
    player_damage_bones: str = ""
    player_damage_food: float = 0
    player_damage_water: float = 0
    player_damage_virus: float = 0
    player_damage_hallucination: float = 0

    # Accuracy
    spread_hip: float = 0
    spread_aim: float = 0
    spread_sprint: float = 1.25
    spread_crouch: float = 0.85
    spread_prone: float = 0.7

    # Range
    range: float = 0
    range_rangefinder: float = 0

    # Recoil
    recoil_min_x: float = 0
    recoil_max_x: float = 0
    recoil_min_y: float = 0
    recoil_max_y: float = 0
    recoil_aim: float = 1.0
    aiming_recoil_multiplier: float = 1.0
    recover_x: float = 0
    recover_y: float = 0
    recoil_sprint: float = 1.25
    recoil_crouch: float = 0.85
    recoil_prone: float = 0.7

    # Shake
    shake_min_x: float = 0
    shake_min_y: float = 0
    shake_min_z: float = 0
    shake_max_x: float = 0
    shake_max_y: float = 0
    shake_max_z: float = 0

    # Ballistics
    ballistic_steps: int = 0
    ballistic_travel: float = 10.0
    ballistic_drop: float = 0
    ballistic_force: float = 0
    damage_falloff_range: float = 1.0
    damage_falloff_multiplier: float = 1.0

    # Projectile
    projectile_lifespan: float = 30.0
    projectile_penetrate_buildables: bool = False
    projectile_explosion_launch_speed: float = 0

    # Magazine
    ammo_min: int = 0
    ammo_max: int = 0
    caliber: int = 0
    magazine_calibers: list[int] = []
    attachment_calibers: list[int] = []
    default_sight: str = ""
    default_tactical: str = ""
    default_grip: str = ""
    default_barrel: str = ""
    default_magazine: str = ""
    hook_sight: bool = False
    hook_tactical: bool = False
    hook_grip: bool = False
    hook_barrel: bool = False

    # Magazine handling
    delete_empty_magazines: bool = False
    should_delete_empty_magazines: bool = False
    requires_nonzero_attachment_caliber: bool = False
    allow_magazine_change: bool = True
    unplace: float = 0
    replace: float = 0
    ammo_per_shot: int = 1
    infinite_ammo: bool = False

    # Reload
    reload_time: float = 0
    hammer_timer: float = 0
    fire_delay_seconds: float = 0

    # Misc
    alert_radius: float = 0
    instakill_headshots: bool = False
    can_aim_during_sprint: bool = False
    aiming_movement_speed_multiplier: float = 0
    can_ever_jam: bool = False
    jam_quality_threshold: float = 0.4
    jam_max_chance: float = 0.1
    unjam_chamber_anim: str = "UnjamChamber"
    gunshot_rolloff_distance: float = 0
    durability: float = 0
    wear: int = 0
    invulnerable: bool = False
    stun_zombie_always: bool = False
    stun_zombie_never: bool = False

    # Complex
    magazine_replacements: list[dict[str, Any]] = []

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> GunProperties:
        fields: dict[str, Any] = {}

        # Fire
        fields["firerate"] = _get_int(raw, "Firerate")
        fields["action"] = _get_str(raw, "Action")
        fields["safety"] = _get_bool(raw, "Safety")
        fields["semi"] = _get_bool(raw, "Semi")
        fields["auto"] = _get_bool(raw, "Auto")
        fields["bursts"] = _get_int(raw, "Bursts")
        fields["turret"] = _get_bool(raw, "Turret")

        # Damage + multipliers
        fields.update(_extract_damage_fields(raw))

        # Damage mods
        fields["player_damage_bleeding"] = _get_str(raw, "Player_Damage_Bleeding")
        fields["player_damage_bones"] = _get_str(raw, "Player_Damage_Bones")
        fields["player_damage_food"] = _get_float(raw, "Player_Damage_Food")
        fields["player_damage_water"] = _get_float(raw, "Player_Damage_Water")
        fields["player_damage_virus"] = _get_float(raw, "Player_Damage_Virus")
        fields["player_damage_hallucination"] = _get_float(
            raw, "Player_Damage_Hallucination"
        )

        # Accuracy
        fields["spread_hip"] = _get_float(raw, "Spread_Hip")
        fields["spread_aim"] = _get_float(raw, "Spread_Aim")
        fields["spread_sprint"] = _get_float(raw, "Spread_Sprint", 1.25)
        fields["spread_crouch"] = _get_float(raw, "Spread_Crouch", 0.85)
        fields["spread_prone"] = _get_float(raw, "Spread_Prone", 0.7)

        # Range
        fields["range"] = _get_float(raw, "Range")
        fields["range_rangefinder"] = _get_float(raw, "Range_Rangefinder")

        # Recoil
        fields["recoil_min_x"] = _get_float(raw, "Recoil_Min_X")
        fields["recoil_max_x"] = _get_float(raw, "Recoil_Max_X")
        fields["recoil_min_y"] = _get_float(raw, "Recoil_Min_Y")
        fields["recoil_max_y"] = _get_float(raw, "Recoil_Max_Y")
        fields["recoil_aim"] = _get_float(raw, "Recoil_Aim", 1.0)
        fields["aiming_recoil_multiplier"] = _get_float(
            raw, "Aiming_Recoil_Multiplier", 1.0
        )
        fields["recover_x"] = _get_float(raw, "Recover_X")
        fields["recover_y"] = _get_float(raw, "Recover_Y")
        fields["recoil_sprint"] = _get_float(raw, "Recoil_Sprint", 1.25)
        fields["recoil_crouch"] = _get_float(raw, "Recoil_Crouch", 0.85)
        fields["recoil_prone"] = _get_float(raw, "Recoil_Prone", 0.7)

        # Shake
        fields["shake_min_x"] = _get_float(raw, "Shake_Min_X")
        fields["shake_min_y"] = _get_float(raw, "Shake_Min_Y")
        fields["shake_min_z"] = _get_float(raw, "Shake_Min_Z")
        fields["shake_max_x"] = _get_float(raw, "Shake_Max_X")
        fields["shake_max_y"] = _get_float(raw, "Shake_Max_Y")
        fields["shake_max_z"] = _get_float(raw, "Shake_Max_Z")

        # Ballistics
        fields["ballistic_steps"] = _get_int(raw, "Ballistic_Steps")
        fields["ballistic_travel"] = _get_float(raw, "Ballistic_Travel", 10.0)
        fields["ballistic_drop"] = _get_float(raw, "Ballistic_Drop")
        fields["ballistic_force"] = _get_float(raw, "Ballistic_Force")
        fields["damage_falloff_range"] = _get_float(raw, "Damage_Falloff_Range", 1.0)
        fields["damage_falloff_multiplier"] = _get_float(
            raw, "Damage_Falloff_Multiplier", 1.0
        )

        # Projectile
        fields["projectile_lifespan"] = _get_float(raw, "Projectile_Lifespan", 30.0)
        fields["projectile_penetrate_buildables"] = _get_bool(
            raw, "Projectile_Penetrate_Buildables"
        )
        fields["projectile_explosion_launch_speed"] = _get_float(
            raw, "Projectile_Explosion_Launch_Speed"
        )

        # Magazine — note key remappings
        fields["ammo_min"] = _get_int(raw, "Ammo_Min")
        fields["ammo_max"] = _get_int(raw, "Ammo_Max")
        fields["caliber"] = _get_int(raw, "Caliber")
        fields["magazine_calibers"] = _parse_indexed_list(
            raw, "Magazine_Calibers", "Magazine_Caliber"
        )
        fields["attachment_calibers"] = _parse_indexed_list(
            raw, "Attachment_Calibers", "Attachment_Caliber"
        )
        # Sight/Tactical/Grip/Barrel/Magazine -> default_*
        # These can be numeric IDs or GUIDs depending on the data format
        fields["default_sight"] = _get_str(raw, "Sight")
        fields["default_tactical"] = _get_str(raw, "Tactical")
        fields["default_grip"] = _get_str(raw, "Grip")
        fields["default_barrel"] = _get_str(raw, "Barrel")
        fields["default_magazine"] = _get_str(raw, "Magazine")
        # Hook flags
        fields["hook_sight"] = _get_bool(raw, "Hook_Sight")
        fields["hook_tactical"] = _get_bool(raw, "Hook_Tactical")
        fields["hook_grip"] = _get_bool(raw, "Hook_Grip")
        fields["hook_barrel"] = _get_bool(raw, "Hook_Barrel")

        # Magazine handling
        fields["delete_empty_magazines"] = _get_bool(raw, "Delete_Empty_Magazines")
        fields["should_delete_empty_magazines"] = _get_bool(
            raw, "Should_Delete_Empty_Magazines"
        )
        fields["requires_nonzero_attachment_caliber"] = _get_bool(
            raw, "Requires_Nonzero_Attachment_Caliber"
        )
        fields["allow_magazine_change"] = _get_bool(raw, "Allow_Magazine_Change", True)
        fields["unplace"] = _get_float(raw, "Unplace")
        fields["replace"] = _get_float(raw, "Replace")
        fields["ammo_per_shot"] = _get_int(raw, "Ammo_Per_Shot", 1)
        fields["infinite_ammo"] = _get_bool(raw, "Infinite_Ammo")

        # Reload
        fields["reload_time"] = _get_float(raw, "Reload_Time")
        fields["hammer_timer"] = _get_float(raw, "Hammer_Timer")
        fields["fire_delay_seconds"] = _get_float(raw, "Fire_Delay_Seconds")

        # Misc
        fields["alert_radius"] = _get_float(raw, "Alert_Radius")
        fields["instakill_headshots"] = _get_bool(raw, "Instakill_Headshots")
        fields["can_aim_during_sprint"] = _get_bool(raw, "Can_Aim_During_Sprint")
        fields["aiming_movement_speed_multiplier"] = _get_float(
            raw, "Aiming_Movement_Speed_Multiplier"
        )
        fields["can_ever_jam"] = _get_bool(raw, "Can_Ever_Jam")
        fields["jam_quality_threshold"] = _get_float(raw, "Jam_Quality_Threshold", 0.4)
        fields["jam_max_chance"] = _get_float(raw, "Jam_Max_Chance", 0.1)
        fields["unjam_chamber_anim"] = _get_str(
            raw, "Unjam_Chamber_Anim", "UnjamChamber"
        )
        fields["gunshot_rolloff_distance"] = _get_float(raw, "Gunshot_Rolloff_Distance")
        fields["durability"] = _get_float(raw, "Durability")
        fields["wear"] = _get_int(raw, "Wear")
        fields["invulnerable"] = _get_bool(raw, "Invulnerable")
        fields["stun_zombie_always"] = _get_bool(raw, "Stun_Zombie_Always")
        fields["stun_zombie_never"] = _get_bool(raw, "Stun_Zombie_Never")

        # Complex parsed fields
        fields["magazine_replacements"] = _parse_magazine_replacements(raw)

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        """Override to account for remapped keys."""
        keys = super().consumed_keys(raw)
        # Keys that map to differently-named fields
        for remap_key in (
            "Player_Damage",
            "Zombie_Damage",
            "Animal_Damage",
            "Barricade_Damage",
            "Structure_Damage",
            "Vehicle_Damage",
            "Resource_Damage",
            "Object_Damage",
            "Sight",
            "Tactical",
            "Grip",
            "Barrel",
            "Magazine",
            "Hook_Sight",
            "Hook_Tactical",
            "Hook_Grip",
            "Hook_Barrel",
            "Magazine_Calibers",
            "Attachment_Calibers",
            "Magazine_Replacements",
        ):
            if remap_key in raw:
                keys.add(remap_key)
        # Indexed entries
        for prefix in (
            "Magazine_Caliber",
            "Attachment_Caliber",
            "Magazine_Replacement",
        ):
            for key in raw:
                if key.startswith(prefix + "_"):
                    keys.add(key)
        # Multiplier keys
        for entity in ("Player", "Zombie", "Animal"):
            for part in ("Skull", "Spine", "Arm", "Leg"):
                k = f"{entity}_{part}_Multiplier"
                if k in raw:
                    keys.add(k)
        return keys


# ---------------------------------------------------------------------------
# MeleeProperties
# ---------------------------------------------------------------------------


class MeleeProperties(ItemProperties):
    """Properties specific to Melee items."""

    IGNORE: ClassVar[set[str]] = {
        "Explosion",
        "Allow_Flesh_Fx",
        "Bypass_Allowed_To_Damage_Player",
        "ImpactAudioDef",
        "SpotLight_Range",
        "SpotLight_Angle",
        "SpotLight_Intensity",
        "Spotlight_Color_R",
        "Spotlight_Color_G",
        "Spotlight_Color_B",
        "BladeIDs",
        "BladeID",
        "AttackAudioClip",
    }
    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"^BladeID_\d+"),
    ]

    # Damage per target
    damage_player: float = 0
    damage_zombie: float = 0
    damage_animal: float = 0
    damage_barricade: float = 0
    damage_structure: float = 0
    damage_vehicle: float = 0
    damage_resource: float = 0
    damage_object: float = 0

    # Player multipliers
    player_skull_multiplier: float = 0
    player_spine_multiplier: float = 0
    player_arm_multiplier: float = 0
    player_leg_multiplier: float = 0

    # Zombie multipliers
    zombie_skull_multiplier: float = 0
    zombie_spine_multiplier: float = 0
    zombie_arm_multiplier: float = 0
    zombie_leg_multiplier: float = 0

    # Animal multipliers
    animal_skull_multiplier: float = 0
    animal_spine_multiplier: float = 0
    animal_leg_multiplier: float = 0

    # Melee-specific
    range: float = 0
    strength: float = 0
    weak: float = 0
    strong: float = 0
    stamina: int = 0
    repair: bool = False
    repeated: bool = False
    light: bool = False
    alert_radius: float = 0
    durability: float = 0
    wear: int = 0
    invulnerable: bool = False
    stun_zombie_always: bool = False
    stun_zombie_never: bool = False

    # Damage mods (melee can have these too)
    player_damage_bleeding: str = ""
    player_damage_bones: str = ""
    player_damage_food: float = 0
    player_damage_water: float = 0
    player_damage_virus: float = 0
    player_damage_hallucination: float = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> MeleeProperties:
        fields: dict[str, Any] = {}

        # Damage + multipliers (shared)
        fields.update(_extract_damage_fields(raw))

        # Melee-specific
        fields["range"] = _get_float(raw, "Range")
        fields["strength"] = _get_float(raw, "Strength")
        fields["weak"] = _get_float(raw, "Weak")
        fields["strong"] = _get_float(raw, "Strong")
        fields["stamina"] = _get_int(raw, "Stamina")
        fields["repair"] = _get_bool(raw, "Repair")
        fields["repeated"] = _get_bool(raw, "Repeated")
        fields["light"] = _get_bool(raw, "Light")
        fields["alert_radius"] = _get_float(raw, "Alert_Radius")
        fields["durability"] = _get_float(raw, "Durability")
        fields["wear"] = _get_int(raw, "Wear")
        fields["invulnerable"] = _get_bool(raw, "Invulnerable")
        fields["stun_zombie_always"] = _get_bool(raw, "Stun_Zombie_Always")
        fields["stun_zombie_never"] = _get_bool(raw, "Stun_Zombie_Never")

        # Damage mods
        fields["player_damage_bleeding"] = _get_str(raw, "Player_Damage_Bleeding")
        fields["player_damage_bones"] = _get_str(raw, "Player_Damage_Bones")
        fields["player_damage_food"] = _get_float(raw, "Player_Damage_Food")
        fields["player_damage_water"] = _get_float(raw, "Player_Damage_Water")
        fields["player_damage_virus"] = _get_float(raw, "Player_Damage_Virus")
        fields["player_damage_hallucination"] = _get_float(
            raw, "Player_Damage_Hallucination"
        )

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        keys = super().consumed_keys(raw)
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
        for entity in ("Player", "Zombie", "Animal"):
            for part in ("Skull", "Spine", "Arm", "Leg"):
                k = f"{entity}_{part}_Multiplier"
                if k in raw:
                    keys.add(k)
        return keys


# ---------------------------------------------------------------------------
# ThrowableProperties
# ---------------------------------------------------------------------------


class ThrowableProperties(ItemProperties):
    """Properties specific to Throwable items."""

    IGNORE: ClassVar[set[str]] = {
        "Explosion",
        "Allow_Flesh_Fx",
        "Bypass_Allowed_To_Damage_Player",
    }
    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = []

    # Damage per target
    damage_player: float = 0
    damage_zombie: float = 0
    damage_animal: float = 0
    damage_barricade: float = 0
    damage_structure: float = 0
    damage_vehicle: float = 0
    damage_resource: float = 0
    damage_object: float = 0

    # Player multipliers
    player_skull_multiplier: float = 0
    player_spine_multiplier: float = 0
    player_arm_multiplier: float = 0
    player_leg_multiplier: float = 0

    # Zombie multipliers
    zombie_skull_multiplier: float = 0
    zombie_spine_multiplier: float = 0
    zombie_arm_multiplier: float = 0
    zombie_leg_multiplier: float = 0

    # Animal multipliers
    animal_skull_multiplier: float = 0
    animal_spine_multiplier: float = 0
    animal_leg_multiplier: float = 0

    # Throwable-specific
    explosive: bool = False
    flash: bool = False
    sticky: bool = False
    explode_on_impact: bool = False
    fuse_length: float = 0
    explosion_launch_speed: float = 0
    strong_throw_force: float = 1100.0
    weak_throw_force: float = 600.0
    boost_throw_force_multiplier: float = 1.4
    durability: float = 0
    wear: int = 0
    invulnerable: bool = False

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ThrowableProperties:
        fields: dict[str, Any] = {}

        # Damage + multipliers (shared)
        fields.update(_extract_damage_fields(raw))

        # Throwable-specific
        fields["explosive"] = _get_bool(raw, "Explosive")
        fields["flash"] = _get_bool(raw, "Flash")
        fields["sticky"] = _get_bool(raw, "Sticky")
        fields["explode_on_impact"] = _get_bool(raw, "Explode_On_Impact")
        fields["fuse_length"] = _get_float(raw, "Fuse_Length")
        fields["explosion_launch_speed"] = _get_float(raw, "Explosion_Launch_Speed")
        fields["strong_throw_force"] = _get_float(raw, "Strong_Throw_Force", 1100.0)
        fields["weak_throw_force"] = _get_float(raw, "Weak_Throw_Force", 600.0)
        fields["boost_throw_force_multiplier"] = _get_float(
            raw, "Boost_Throw_Force_Multiplier", 1.4
        )
        fields["durability"] = _get_float(raw, "Durability")
        fields["wear"] = _get_int(raw, "Wear")
        fields["invulnerable"] = _get_bool(raw, "Invulnerable")

        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        keys = super().consumed_keys(raw)
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
        for entity in ("Player", "Zombie", "Animal"):
            for part in ("Skull", "Spine", "Arm", "Leg"):
                k = f"{entity}_{part}_Multiplier"
                if k in raw:
                    keys.add(k)
        return keys
