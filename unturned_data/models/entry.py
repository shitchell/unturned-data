"""
Core entry models for Unturned bundle data.

Provides base BundleEntry (Pydantic BaseModel) and SpawnTable/SpawnTableEntry
models.  Type-specific data is extracted via the properties system
(see unturned_data.models.properties).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, computed_field

from .action import Action
from .blueprint import Blueprint


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
    useable: str = ""
    slot: str = ""
    can_use_underwater: bool = True
    equipable_movement_speed_multiplier: float = 1.0
    should_drop_on_death: bool = True
    allow_manual_drop: bool = True
    source_path: str = ""
    raw: dict[str, Any] = {}
    english: dict[str, str] = {}
    actions: list[Action] = []
    blueprints: list[Blueprint] = []
    properties: dict[str, Any] = {}

    @computed_field
    @property
    def category(self) -> list[str]:
        if not self.source_path:
            return []
        parts = self.source_path.split("/")
        return parts[:-1] if len(parts) > 1 else []

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
            useable=str(raw.get("Useable", "")),
            slot=str(raw.get("Slot", "")),
            can_use_underwater=bool(raw.get("Can_Use_Underwater", True)),
            equipable_movement_speed_multiplier=float(
                raw.get("Equipable_Movement_Speed_Multiplier", 1.0)
            ),
            should_drop_on_death=bool(raw.get("Should_Drop_On_Death", True)),
            allow_manual_drop=bool(raw.get("Allow_Manual_Drop", True)),
            source_path=source_path,
            raw=raw,
            english=english,
            actions=Action.list_from_raw(raw),
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
