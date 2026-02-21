"""Base properties class and field tracking infrastructure."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from pydantic import BaseModel


# Fields handled at the BundleEntry level (identity, blueprints, actions, etc.)
GLOBAL_HANDLED: set[str] = {
    "GUID",
    "ID",
    "Type",
    "Rarity",
    "Size_X",
    "Size_Y",
    "Useable",
    "Slot",
    "Can_Use_Underwater",
    "Equipable_Movement_Speed_Multiplier",
    "Should_Drop_On_Death",
    "Allow_Manual_Drop",
    "Blueprints",
    "Actions",
}

GLOBAL_HANDLED_PATTERNS: list[re.Pattern] = [
    re.compile(r"^Blueprint_\d+_"),
    re.compile(r"^Action_\d+_"),
]

GLOBAL_IGNORE: set[str] = {
    "Size_Z",
    "Size2_Z",
    "Use_Auto_Icon_Measurements",
    "Shared_Skin_Lookup_ID",
    "Econ_Icon_Use_Id",
    "Backward",
    "Procedurally_Animate_Inertia",
    "Can_Player_Equip",
    "EquipAudioClip",
    "InspectAudioDef",
    "InventoryAudio",
    "WearAudio",
    "Bypass_Hash_Verification",
    "Override_Show_Quality",
    "Should_Delete_At_Zero_Quality",
    "Pro",
    "Quality_Min",
    "Quality_Max",
}


def is_globally_handled(key: str) -> bool:
    """Check if a key is handled at the BundleEntry level."""
    if key in GLOBAL_HANDLED:
        return True
    for pattern in GLOBAL_HANDLED_PATTERNS:
        if pattern.match(key):
            return True
    return False


def _snake_to_dat_key(name: str) -> str:
    """Convert a snake_case Python field name to a .dat key.

    Example: "damage_player" -> "Damage_Player"
    """
    return "_".join(part.capitalize() for part in name.split("_"))


class ItemProperties(BaseModel):
    """Base class for type-specific item properties.

    Subclasses define Pydantic fields that map to .dat keys via
    _snake_to_dat_key(). They also declare IGNORE and IGNORE_PATTERNS
    for keys that are known but intentionally not extracted.
    """

    IGNORE: ClassVar[set[str]] = set()
    IGNORE_PATTERNS: ClassVar[list[re.Pattern]] = []

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ItemProperties:
        """Build properties from a parsed .dat dict.

        Subclasses override this to extract their specific fields.
        """
        return cls()

    @classmethod
    def consumed_keys(cls, raw: dict[str, Any]) -> set[str]:
        """Return the set of .dat keys that this model consumes from raw."""
        keys: set[str] = set()
        for field_name in cls.model_fields:
            dat_key = _snake_to_dat_key(field_name)
            if dat_key in raw:
                keys.add(dat_key)
        return keys

    @classmethod
    def is_ignored(cls, key: str) -> bool:
        """Check if a key is in this model's type-specific ignore list."""
        if key in cls.IGNORE:
            return True
        for pattern in cls.IGNORE_PATTERNS:
            if pattern.match(key):
                return True
        return False
