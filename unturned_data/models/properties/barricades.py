"""Barricade property models: Storage, Farm, Generator, Trap, Beacon, etc."""

from __future__ import annotations

from typing import Any, ClassVar

from unturned_data.models.properties.base import ItemProperties, _snake_to_dat_key


def _get(raw: dict[str, Any], key: str, default: Any = None) -> Any:
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


# Damage targets shared by Trap and Charge
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


def _extract_damage_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract damage_* fields (Player_Damage -> damage_player, etc.)."""
    fields: dict[str, Any] = {}
    for target in _DAMAGE_TARGETS:
        key = f"{target.capitalize()}_Damage"
        fields[f"damage_{target}"] = _get_float(raw, key)
    return fields


_DAMAGE_REMAP_KEYS = tuple(f"{t.capitalize()}_Damage" for t in _DAMAGE_TARGETS)


# ---------------------------------------------------------------------------
# BarricadeProperties (base)
# ---------------------------------------------------------------------------


class BarricadeProperties(ItemProperties):
    """Base properties for all barricade items."""

    IGNORE: ClassVar[set[str]] = {
        "Explosion",
        "Has_Clip_Prefab",
        "PlacementPreviewPrefab",
        "Eligible_For_Pooling",
        "Use_Water_Height_Transparent_Sort",
        "PlacementAudioClip",
        "Should_Close_When_Outside_Range",
        "Items_Recovered_On_Salvage",
        "SalvageItem",
        "Items_Dropped_On_Destroy",
        "Item_Dropped_On_Destroy",
    }

    health: int | None = None
    range: float | None = None
    radius: float | None = None
    offset: float | None = None
    can_be_damaged: bool | None = None
    locked: bool | None = None
    vulnerable: bool | None = None
    bypass_claim: bool | None = None
    allow_placement_on_vehicle: bool | None = None
    unrepairable: bool | None = None
    proof_explosion: bool | None = None
    unpickupable: bool | None = None
    bypass_pickup_ownership: bool | None = None
    allow_placement_inside_clip_volumes: bool | None = None
    unsalvageable: bool | None = None
    salvage_duration_multiplier: float | None = None
    unsaveable: bool | None = None
    allow_collision_while_animating: bool | None = None
    armor_tier: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BarricadeProperties:
        fields: dict[str, Any] = {}
        fields["health"] = _get_int(raw, "Health")
        fields["range"] = _get_float(raw, "Range")
        fields["radius"] = _get_float(raw, "Radius")
        fields["offset"] = _get_float(raw, "Offset")
        fields["can_be_damaged"] = _get_bool(raw, "Can_Be_Damaged")
        fields["locked"] = _get_bool(raw, "Locked")
        fields["vulnerable"] = _get_bool(raw, "Vulnerable")
        fields["bypass_claim"] = _get_bool(raw, "Bypass_Claim")
        fields["allow_placement_on_vehicle"] = _get_bool(
            raw, "Allow_Placement_On_Vehicle"
        )
        fields["unrepairable"] = _get_bool(raw, "Unrepairable")
        fields["proof_explosion"] = _get_bool(raw, "Proof_Explosion")
        fields["unpickupable"] = _get_bool(raw, "Unpickupable")
        fields["bypass_pickup_ownership"] = _get_bool(raw, "Bypass_Pickup_Ownership")
        fields["allow_placement_inside_clip_volumes"] = _get_bool(
            raw, "Allow_Placement_Inside_Clip_Volumes"
        )
        fields["unsalvageable"] = _get_bool(raw, "Unsalvageable")
        fields["salvage_duration_multiplier"] = _get_float(
            raw, "Salvage_Duration_Multiplier"
        )
        fields["unsaveable"] = _get_bool(raw, "Unsaveable")
        fields["allow_collision_while_animating"] = _get_bool(
            raw, "Allow_Collision_While_Animating"
        )
        fields["armor_tier"] = _get_str(raw, "Armor_Tier")
        return cls(**fields)


# ---------------------------------------------------------------------------
# StorageProperties
# ---------------------------------------------------------------------------


class StorageProperties(BarricadeProperties):
    """Properties for Storage barricades (crates, lockers, etc.)."""

    storage_x: int | None = None
    storage_y: int | None = None
    display: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> StorageProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["storage_x"] = _get_int(raw, "Storage_X")
        fields["storage_y"] = _get_int(raw, "Storage_Y")
        fields["display"] = _get_bool(raw, "Display")
        return cls(**fields)


# ---------------------------------------------------------------------------
# SentryProperties
# ---------------------------------------------------------------------------


class SentryProperties(StorageProperties):
    """Properties for Sentry barricades."""

    IGNORE: ClassVar[set[str]] = {
        *StorageProperties.IGNORE,
        "Target_Acquired_Effect",
        "Target_Lost_Effect",
    }

    mode: str | None = None
    requires_power: bool | None = None
    infinite_ammo: bool | None = None
    infinite_quality: bool | None = None
    detection_radius: float | None = None
    target_loss_radius: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> SentryProperties:
        base = StorageProperties.from_raw(raw)
        fields = base.model_dump()
        fields["mode"] = _get_str(raw, "Mode")
        fields["requires_power"] = _get_bool(raw, "Requires_Power")
        fields["infinite_ammo"] = _get_bool(raw, "Infinite_Ammo")
        fields["infinite_quality"] = _get_bool(raw, "Infinite_Quality")
        fields["detection_radius"] = _get_float(raw, "Detection_Radius")
        fields["target_loss_radius"] = _get_float(raw, "Target_Loss_Radius")
        return cls(**fields)


# ---------------------------------------------------------------------------
# FarmProperties
# ---------------------------------------------------------------------------


class FarmProperties(BarricadeProperties):
    """Properties for Farm barricades (planter boxes, etc.)."""

    IGNORE: ClassVar[set[str]] = {
        *BarricadeProperties.IGNORE,
        "Grow_SpawnTable",
        "Ignore_Soil_Restrictions",
    }

    growth: int | None = None
    grow: int | None = None
    allow_fertilizer: bool | None = None
    harvest_reward_experience: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> FarmProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["growth"] = _get_int(raw, "Growth")
        fields["grow"] = _get_int(raw, "Grow")
        fields["allow_fertilizer"] = _get_bool(raw, "Allow_Fertilizer")
        fields["harvest_reward_experience"] = _get_int(raw, "Harvest_Reward_Experience")
        return cls(**fields)


# ---------------------------------------------------------------------------
# GeneratorProperties
# ---------------------------------------------------------------------------


class GeneratorProperties(BarricadeProperties):
    """Properties for Generator barricades."""

    capacity: int | None = None
    wirerange: float | None = None
    burn: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> GeneratorProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["capacity"] = _get_int(raw, "Capacity")
        fields["wirerange"] = _get_float(raw, "Wirerange")
        fields["burn"] = _get_float(raw, "Burn")
        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        keys = super().consumed_keys(raw)
        # Wirerange doesn't follow PascalCase convention
        if "Wirerange" in raw:
            keys.add("Wirerange")
        return keys


# ---------------------------------------------------------------------------
# TrapProperties
# ---------------------------------------------------------------------------


class TrapProperties(BarricadeProperties):
    """Properties for Trap barricades (barbed wire, landmines, etc.)."""

    IGNORE: ClassVar[set[str]] = {
        *BarricadeProperties.IGNORE,
        "Explosion2",
    }

    range2: float | None = None
    damage_player: float | None = None
    damage_zombie: float | None = None
    damage_animal: float | None = None
    damage_barricade: float | None = None
    damage_structure: float | None = None
    damage_vehicle: float | None = None
    damage_resource: float | None = None
    damage_object: float | None = None
    trap_setup_delay: float | None = None
    trap_cooldown: float | None = None
    explosion_launch_speed: float | None = None
    broken: bool | None = None
    explosive: bool | None = None
    damage_tires: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TrapProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["range2"] = _get_float(raw, "Range2")
        fields.update(_extract_damage_fields(raw))
        fields["trap_setup_delay"] = _get_float(raw, "Trap_Setup_Delay")
        fields["trap_cooldown"] = _get_float(raw, "Trap_Cooldown")
        fields["explosion_launch_speed"] = _get_float(raw, "Explosion_Launch_Speed")
        fields["broken"] = _get_bool(raw, "Broken")
        fields["explosive"] = _get_bool(raw, "Explosive")
        fields["damage_tires"] = _get_bool(raw, "Damage_Tires")
        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        keys = super().consumed_keys(raw)
        for remap_key in _DAMAGE_REMAP_KEYS:
            if remap_key in raw:
                keys.add(remap_key)
        return keys


# ---------------------------------------------------------------------------
# BeaconProperties
# ---------------------------------------------------------------------------


class BeaconProperties(BarricadeProperties):
    """Properties for Beacon barricades (horde beacons)."""

    wave: int | None = None
    rewards: int | None = None
    reward_id: int | None = None
    enable_participant_scaling: bool | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> BeaconProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["wave"] = _get_int(raw, "Wave")
        fields["rewards"] = _get_int(raw, "Rewards")
        fields["reward_id"] = _get_int(raw, "Reward_ID")
        fields["enable_participant_scaling"] = _get_bool(
            raw, "Enable_Participant_Scaling"
        )
        return cls(**fields)


# ---------------------------------------------------------------------------
# TankProperties
# ---------------------------------------------------------------------------


class TankProperties(BarricadeProperties):
    """Properties for Tank barricades (water/fuel tanks)."""

    source: str | None = None
    resource: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> TankProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["source"] = _get_str(raw, "Source")
        fields["resource"] = _get_int(raw, "Resource")
        return cls(**fields)


# ---------------------------------------------------------------------------
# ChargeProperties
# ---------------------------------------------------------------------------


class ChargeProperties(BarricadeProperties):
    """Properties for Charge barricades (remote detonators)."""

    IGNORE: ClassVar[set[str]] = {
        *BarricadeProperties.IGNORE,
        "Explosion2",
    }

    range2: float | None = None
    damage_player: float | None = None
    damage_zombie: float | None = None
    damage_animal: float | None = None
    damage_barricade: float | None = None
    damage_structure: float | None = None
    damage_vehicle: float | None = None
    damage_resource: float | None = None
    damage_object: float | None = None
    explosion_launch_speed: float | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ChargeProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["range2"] = _get_float(raw, "Range2")
        fields.update(_extract_damage_fields(raw))
        fields["explosion_launch_speed"] = _get_float(raw, "Explosion_Launch_Speed")
        return cls(**fields)

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        keys = super().consumed_keys(raw)
        for remap_key in _DAMAGE_REMAP_KEYS:
            if remap_key in raw:
                keys.add(remap_key)
        return keys


# ---------------------------------------------------------------------------
# LibraryProperties
# ---------------------------------------------------------------------------


class LibraryProperties(BarricadeProperties):
    """Properties for Library barricades."""

    capacity: int | None = None
    tax: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> LibraryProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["capacity"] = _get_int(raw, "Capacity")
        fields["tax"] = _get_int(raw, "Tax")
        return cls(**fields)


# ---------------------------------------------------------------------------
# OilPumpProperties
# ---------------------------------------------------------------------------


class OilPumpProperties(BarricadeProperties):
    """Properties for Oil Pump barricades."""

    fuel_capacity: int | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> OilPumpProperties:
        base = BarricadeProperties.from_raw(raw)
        fields = base.model_dump()
        fields["fuel_capacity"] = _get_int(raw, "Fuel_Capacity")
        return cls(**fields)
