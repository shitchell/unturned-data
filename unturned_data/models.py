"""
Shared models for Unturned bundle data.

Provides base BundleEntry (Pydantic BaseModel) and composable stat blocks
(DamageStats, ConsumableStats, StorageStats, Blueprint) that category-specific
models will reuse.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, computed_field


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
        """Build from a parsed .dat dict.  Returns None if not a consumable.

        "Health" alone isn't sufficient (structures have it too).  We
        require at least one of: Food, Water, Virus, Bleeding_Modifier,
        or ``Useable == "Consumeable"``.
        """
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
# Blueprint
# ---------------------------------------------------------------------------
class Blueprint(BaseModel):
    """A single crafting blueprint."""

    name: str = ""
    category_tag: str = ""
    operation: str = ""
    inputs: list[Any] = []
    outputs: list[Any] = []
    skill: str = ""
    skill_level: int = 0
    workstation_tags: list[str] = []

    @staticmethod
    def list_from_raw(raw: dict[str, Any]) -> list[Blueprint]:
        """Parse the Blueprints array from a parsed .dat dict.

        Handles two formats:
        - Modern: ``Blueprints`` is a list of dicts with InputItems/OutputItems.
        - Legacy indexed: ``Blueprints`` is an integer count, with keys like
          ``Blueprint_0_Type``, ``Blueprint_0_Supply_0_ID``, etc.
        """
        bp_val = raw.get("Blueprints")
        if not bp_val:
            return []

        # Modern format: Blueprints is a list of dicts
        if isinstance(bp_val, list):
            results: list[Blueprint] = []
            for bp_raw in bp_val:
                if not isinstance(bp_raw, dict):
                    continue
                bp = Blueprint(
                    name=str(bp_raw.get("Name", "")),
                    category_tag=str(bp_raw.get("CategoryTag", "")),
                    operation=str(bp_raw.get("Operation", "")),
                    inputs=_parse_items(bp_raw.get("InputItems")),
                    outputs=_parse_items(bp_raw.get("OutputItems")),
                    skill=str(bp_raw.get("Skill", "")),
                    skill_level=int(bp_raw.get("Skill_Level", 0)),
                    workstation_tags=_parse_string_list(
                        bp_raw.get("RequiresNearbyCraftingTags")
                    ),
                )
                results.append(bp)
            return results

        # Legacy indexed format: Blueprints is an integer count
        if isinstance(bp_val, int):
            return Blueprint._parse_legacy_blueprints(raw)

        return []

    @staticmethod
    def _parse_legacy_blueprints(raw: dict[str, Any]) -> list[Blueprint]:
        """Parse legacy ``Blueprint_N_*`` indexed format.

        Used by many workshop/mod items and some base-game items where
        blueprints are defined via numbered keys like::

            Blueprints 2
            Blueprint_0_Type Supply
            Blueprint_0_Supply_0_ID 17
            Blueprint_0_Supply_0_Amount 9
            Blueprint_0_Tool 76
            Blueprint_1_Type Repair
            ...
        """
        count = int(raw.get("Blueprints", 0))
        results: list[Blueprint] = []

        _TYPE_TO_NAME: dict[str, str] = {
            "Supply": "Craft",
            "Repair": "Repair",
            "Ammo": "Craft",
            "Tool": "Salvage",
            "Apparel": "Craft",
            "Refill": "Craft",
        }

        for i in range(count):
            prefix = f"Blueprint_{i}_"
            bp_type = str(raw.get(f"{prefix}Type", ""))
            name = _TYPE_TO_NAME.get(bp_type, bp_type)

            # Parse supplies (inputs)
            inputs: list[Any] = []
            j = 0
            while True:
                supply_id = raw.get(f"{prefix}Supply_{j}_ID")
                if supply_id is None:
                    break
                amount = int(raw.get(f"{prefix}Supply_{j}_Amount", 1))
                if amount > 1:
                    inputs.append(f"{supply_id} x {amount}")
                else:
                    inputs.append(str(supply_id))
                j += 1

            # Parse tool (required but not consumed)
            tool_id = raw.get(f"{prefix}Tool")
            if tool_id is not None:
                inputs.append(
                    {"ID": str(tool_id), "Amount": 1, "Delete": False}
                )

            # Parse outputs
            outputs: list[Any] = []
            j = 0
            while True:
                output_id = raw.get(f"{prefix}Output_{j}_ID")
                if output_id is None:
                    break
                amount = int(raw.get(f"{prefix}Output_{j}_Amount", 1))
                if amount > 1:
                    outputs.append(f"{output_id} x {amount}")
                else:
                    outputs.append(str(output_id))
                j += 1

            # If no explicit outputs and it's a Craft type, output is the
            # item itself (implied)
            if not outputs and name == "Craft":
                outputs = ["this"]

            results.append(Blueprint(
                name=name,
                inputs=inputs,
                outputs=outputs,
            ))

        return results


def _parse_items(value: Any) -> list[Any]:
    """Normalize InputItems / OutputItems to a list.

    Can be:
    - A list of dicts (array of objects in .dat)
    - A string shorthand like ``"GUID x N"``
    - The literal string ``"this"``
    - None
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    # Bool True can appear for bare flags -- treat as empty
    if isinstance(value, bool):
        return []
    return [value]


def _parse_string_list(value: Any) -> list[str]:
    """Normalize a value to a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [value]
    return []


# ---------------------------------------------------------------------------
# Blueprint formatting helpers
# ---------------------------------------------------------------------------

# Names of blueprints to skip when showing crafting ingredients
_SKIP_BLUEPRINT_NAMES = {"Repair", "Salvage"}

# Regex to parse "GUID x N" or "GUID xN" shorthand strings
_GUID_X_RE = re.compile(r"^([0-9a-fA-F]{32})\s+x\s*(\d+)$")
# Regex to detect bare GUID strings (32 hex chars)
_BARE_GUID_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def _resolve_guid(guid: str, guid_map: dict[str, str]) -> str:
    """Resolve a GUID to a display name, or show first 8 chars."""
    guid_lower = guid.lower()
    name = guid_map.get(guid_lower)
    if name:
        return name
    return f"[{guid_lower[:8]}]"


def _format_single_input(item: Any, guid_map: dict[str, str]) -> str:
    """Format a single blueprint input item for display.

    Handles:
    - ``"GUID x N"`` → ``"Nx Name"``
    - ``"GUID"`` (bare) → ``"Name"``
    - ``"this"`` or ``"this x N"`` → ``"this"`` / ``"Nx this"``
    - ``{"ID": "GUID", "Amount": N}`` → ``"Nx Name"``
    - ``{"ID": "GUID", "Delete": false}`` → ``"Name (tool)"``
    """
    if isinstance(item, str):
        # Check for "this" or "this x N"
        if item == "this":
            return "this"
        if item.startswith("this x "):
            count = item.split("x", 1)[1].strip()
            return f"{count}x this"

        # Check for "GUID x N"
        m = _GUID_X_RE.match(item)
        if m:
            name = _resolve_guid(m.group(1), guid_map)
            return f"{m.group(2)}x {name}"

        # Check for bare GUID
        if _BARE_GUID_RE.match(item):
            return _resolve_guid(item, guid_map)

        # Unknown string -- return as-is
        return item

    if isinstance(item, dict):
        guid = str(item.get("ID", ""))
        amount = item.get("Amount")
        delete = item.get("Delete")
        name = _resolve_guid(guid, guid_map) if guid else "?"

        # Tool: Delete=false means the item is required but not consumed
        if delete is False:
            return f"{name} (tool)"

        if amount and int(amount) > 1:
            return f"{int(amount)}x {name}"
        return name

    return str(item)


def format_blueprint_ingredients(
    blueprints: list[Blueprint],
    guid_map: dict[str, str],
) -> str:
    """Format crafting blueprint inputs for markdown display.

    Filters out Repair and Salvage blueprints, then formats the
    remaining blueprints' input items.  Multiple crafting blueprints
    are separated by " | ".
    """
    crafting = [
        bp for bp in blueprints
        if bp.name not in _SKIP_BLUEPRINT_NAMES
    ]
    if not crafting:
        return ""

    parts: list[str] = []
    for bp in crafting:
        if not bp.inputs:
            continue
        items = [_format_single_input(item, guid_map) for item in bp.inputs]
        # Filter out empty strings
        items = [i for i in items if i]
        if items:
            parts.append(", ".join(items))

    return " | ".join(parts)


def format_blueprint_workstations(
    blueprints: list[Blueprint],
    guid_map: dict[str, str],
) -> str:
    """Format crafting blueprint workstation requirements for markdown display.

    Filters out Repair and Salvage blueprints, then resolves
    workstation tag GUIDs to names.
    """
    crafting = [
        bp for bp in blueprints
        if bp.name not in _SKIP_BLUEPRINT_NAMES
    ]
    if not crafting:
        return ""

    # Collect unique workstation names across all crafting blueprints
    seen: set[str] = set()
    names: list[str] = []
    for bp in crafting:
        for tag in bp.workstation_tags:
            resolved = _resolve_guid(tag, guid_map)
            if resolved not in seen:
                seen.add(resolved)
                names.append(resolved)

    return ", ".join(names)


# ---------------------------------------------------------------------------
# BundleEntry (base) -- Pydantic BaseModel
# ---------------------------------------------------------------------------
class BundleEntry(BaseModel):
    """Base entry parsed from a bundle directory."""

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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def category(self) -> list[str]:
        """Directory path segments excluding the entry's own directory.

        For ``source_path="Items/Backpacks/Alicepack"`` returns
        ``["Items", "Backpacks"]``.
        """
        if not self.source_path:
            return []
        parts = self.source_path.split("/")
        return parts[:-1] if len(parts) > 1 else []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed(self) -> dict[str, Any]:
        """Parsed category-specific data. Base returns empty dict.

        Subclasses will override to return their parsed fields.
        """
        return {}

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> BundleEntry:
        """Build a BundleEntry from parsed .dat and English.dat dicts."""
        # Fallback name: directory name with underscores -> spaces
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
    def markdown_columns() -> list[str]:
        """Column headers for markdown table output."""
        return ["Name", "Type", "ID", "Rarity", "Size"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        """Row values for markdown table output.

        ``guid_map`` maps GUIDs to display names for cross-references.
        """
        size = f"{self.size_x}x{self.size_y}" if self.size_x or self.size_y else ""
        return [
            self.name,
            self.type,
            str(self.id),
            self.rarity,
            size,
        ]


# ---------------------------------------------------------------------------
# SpawnTableEntry
# ---------------------------------------------------------------------------
class SpawnTableEntry(BaseModel):
    """A single entry in a spawn table."""

    ref_type: str = ""  # "asset", "spawn", or "guid"
    ref_id: int = 0
    ref_guid: str = ""
    weight: int = 10



# ---------------------------------------------------------------------------
# SpawnTable
# ---------------------------------------------------------------------------
class SpawnTable(BundleEntry):
    """A spawn table entry that references items or other spawn tables."""

    table_entries: list[SpawnTableEntry] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed(self) -> dict[str, Any]:
        return {"table_entries": [e.model_dump() for e in self.table_entries]}


# ---------------------------------------------------------------------------
# CraftingBlacklist
# ---------------------------------------------------------------------------
class CraftingBlacklist(BaseModel):
    """Per-map crafting restrictions parsed from CraftingBlacklistAsset."""

    allow_core_blueprints: bool = True
    blocked_inputs: set[str] = set()
    blocked_outputs: set[str] = set()

    @classmethod
    def merge(cls, blacklists: list[CraftingBlacklist]) -> CraftingBlacklist:
        """Merge multiple blacklists. Any False wins for allow_core."""
        if not blacklists:
            return cls()
        return cls(
            allow_core_blueprints=all(bl.allow_core_blueprints for bl in blacklists),
            blocked_inputs=set().union(*(bl.blocked_inputs for bl in blacklists)),
            blocked_outputs=set().union(*(bl.blocked_outputs for bl in blacklists)),
        )
