"""
Core entry models for Unturned bundle data.

Provides base BundleEntry (Pydantic BaseModel) and composable stat blocks
(DamageStats, ConsumableStats, StorageStats) that category-specific
models will reuse.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, computed_field

from .blueprint import Blueprint


# ---------------------------------------------------------------------------
# DamageStats
# ---------------------------------------------------------------------------
class DamageStats(BaseModel):
    """Damage values and body-part multipliers."""

    player: float = 0
    zombie: float = 0
    animal: float = 0
    player_multipliers: dict[str, float] = {}
    zombie_multipliers: dict[str, float] = {}
    animal_multipliers: dict[str, float] = {}
    barricade: float = 0
    structure: float = 0
    vehicle: float = 0
    resource: float = 0
    object: float = 0

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> DamageStats | None:
        """Build from a parsed .dat dict.  Returns None if no damage keys."""
        has_player = "Player_Damage" in raw
        has_zombie = "Zombie_Damage" in raw
        has_animal = "Animal_Damage" in raw
        has_damage = "Damage" in raw  # animals use bare "Damage"

        if not (has_player or has_zombie or has_animal or has_damage):
            return None

        def _multipliers(prefix: str) -> dict[str, float]:
            result: dict[str, float] = {}
            for part in ("skull", "spine", "arm", "leg"):
                key = f"{prefix}_{part.capitalize()}_Multiplier"
                if key in raw:
                    result[part] = float(raw[key])
            return result

        return DamageStats(
            player=float(raw.get("Player_Damage", 0)),
            zombie=float(raw.get("Zombie_Damage", 0)),
            animal=float(raw.get("Animal_Damage", raw.get("Damage", 0))),
            player_multipliers=_multipliers("Player"),
            zombie_multipliers=_multipliers("Zombie"),
            animal_multipliers=_multipliers("Animal"),
            barricade=float(raw.get("Barricade_Damage", 0)),
            structure=float(raw.get("Structure_Damage", 0)),
            vehicle=float(raw.get("Vehicle_Damage", 0)),
            resource=float(raw.get("Resource_Damage", 0)),
            object=float(raw.get("Object_Damage", 0)),
        )


# ---------------------------------------------------------------------------
# ConsumableStats
# ---------------------------------------------------------------------------
class ConsumableStats(BaseModel):
    """Stats for consumable items (food, water, medical)."""

    health: float = 0
    food: float = 0
    water: float = 0
    virus: float = 0
    vision: float = 0
    bleeding_modifier: str = ""

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> ConsumableStats | None:
        """Build from a parsed .dat dict.  Returns None if not a consumable."""
        is_consumable = raw.get("Useable") == "Consumeable"
        has_food = "Food" in raw
        has_water = "Water" in raw
        has_virus = "Virus" in raw
        has_bleeding = "Bleeding_Modifier" in raw

        if not (is_consumable or has_food or has_water or has_virus or has_bleeding):
            return None

        return ConsumableStats(
            health=float(raw.get("Health", 0)),
            food=float(raw.get("Food", 0)),
            water=float(raw.get("Water", 0)),
            virus=float(raw.get("Virus", 0)),
            vision=float(raw.get("Vision", 0)),
            bleeding_modifier=str(raw.get("Bleeding_Modifier", "")),
        )


# ---------------------------------------------------------------------------
# StorageStats
# ---------------------------------------------------------------------------
class StorageStats(BaseModel):
    """Storage dimensions (inventory grid slots)."""

    width: int = 0
    height: int = 0

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> StorageStats | None:
        """Build from a parsed .dat dict.  Returns None if no Width/Height."""
        if "Width" not in raw and "Height" not in raw:
            return None
        return StorageStats(
            width=int(raw.get("Width", 0)),
            height=int(raw.get("Height", 0)),
        )


# ---------------------------------------------------------------------------
# BundleEntry
# ---------------------------------------------------------------------------
class BundleEntry(BaseModel):
    guid: str = ""
    type: str = ""
    id: int = 0
    name: str = ""
    description: str = ""
    rarity: str = ""
    size_x: int = 0
    size_y: int = 0
    source_path: str = ""
    raw: dict[str, Any] = {}
    english: dict[str, str] = {}
    blueprints: list[Blueprint] = []

    @computed_field
    @property
    def category(self) -> list[str]:
        if not self.source_path:
            return []
        parts = self.source_path.split("/")
        return parts[:-1] if len(parts) > 1 else []

    @computed_field
    @property
    def parsed(self) -> dict[str, Any]:
        return {}

    @classmethod
    def from_raw(cls, raw, english, source_path):
        name = english.get("Name", "")
        if not name and source_path:
            dir_name = source_path.rsplit("/", 1)[-1]
            name = dir_name.replace("_", " ")
        return cls(
            guid=str(raw.get("GUID", "")),
            type=str(raw.get("Type", "")),
            id=int(raw.get("ID", 0)),
            name=name,
            description=english.get("Description", ""),
            rarity=str(raw.get("Rarity", "")),
            size_x=int(raw.get("Size_X", 0)),
            size_y=int(raw.get("Size_Y", 0)),
            source_path=source_path,
            raw=raw,
            english=english,
            blueprints=Blueprint.list_from_raw(raw),
        )

    @staticmethod
    def markdown_columns():
        return ["Name", "Type", "ID", "Rarity", "Size"]

    def markdown_row(self, guid_map):
        size = f"{self.size_x}x{self.size_y}" if self.size_x or self.size_y else ""
        return [self.name, self.type, str(self.id), self.rarity, size]


# ---------------------------------------------------------------------------
# SpawnTableEntry
# ---------------------------------------------------------------------------
class SpawnTableEntry(BaseModel):
    ref_type: str = ""
    ref_id: int = 0
    ref_guid: str = ""
    weight: int = 10


# ---------------------------------------------------------------------------
# SpawnTable
# ---------------------------------------------------------------------------
class SpawnTable(BundleEntry):
    table_entries: list[SpawnTableEntry] = []

    @computed_field
    @property
    def parsed(self) -> dict[str, Any]:
        return {"table_entries": [e.model_dump() for e in self.table_entries]}


# ---------------------------------------------------------------------------
# CraftingBlacklist
# ---------------------------------------------------------------------------
class CraftingBlacklist(BaseModel):
    allow_core_blueprints: bool = True
    blocked_inputs: set[str] = set()
    blocked_outputs: set[str] = set()

    @classmethod
    def merge(cls, blacklists):
        if not blacklists:
            return cls()
        return cls(
            allow_core_blueprints=all(bl.allow_core_blueprints for bl in blacklists),
            blocked_inputs=set().union(*(bl.blocked_inputs for bl in blacklists)),
            blocked_outputs=set().union(*(bl.blocked_outputs for bl in blacklists)),
        )
