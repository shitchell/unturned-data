"""
Blueprint model and formatting helpers for Unturned crafting data.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel


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
    build: str = ""
    workstation_tags: list[str] = []

    @staticmethod
    def list_from_raw(raw: dict[str, Any]) -> list[Blueprint]:
        """Parse the Blueprints array from a parsed .dat dict."""
        bp_val = raw.get("Blueprints")
        if not bp_val:
            return []

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

        if isinstance(bp_val, int):
            return Blueprint._parse_legacy_blueprints(raw)

        return []

    @staticmethod
    def _parse_legacy_blueprints(raw: dict[str, Any]) -> list[Blueprint]:
        """Parse legacy Blueprint_N_* indexed format."""
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

            tool_id = raw.get(f"{prefix}Tool")
            if tool_id is not None:
                inputs.append(
                    {"ID": str(tool_id), "Amount": 1, "Delete": False}
                )

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

            if not outputs and name == "Craft":
                outputs = ["this"]

            skill = str(raw.get(f"{prefix}Skill", ""))
            skill_level = int(raw.get(f"{prefix}Level", 0))
            build = str(raw.get(f"{prefix}Build", ""))

            results.append(Blueprint(
                name=name,
                inputs=inputs,
                outputs=outputs,
                skill=skill,
                skill_level=skill_level,
                build=build,
            ))

        return results


def _parse_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    if isinstance(value, bool):
        return []
    return [value]


def _parse_string_list(value: Any) -> list[str]:
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
_SKIP_BLUEPRINT_NAMES = {"Repair", "Salvage"}
_GUID_X_RE = re.compile(r"^([0-9a-fA-F]{32})\s+x\s*(\d+)$")
_BARE_GUID_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def _resolve_guid(guid: str, guid_map: dict[str, str]) -> str:
    guid_lower = guid.lower()
    name = guid_map.get(guid_lower)
    if name:
        return name
    return f"[{guid_lower[:8]}]"


def _format_single_input(item: Any, guid_map: dict[str, str]) -> str:
    if isinstance(item, str):
        if item == "this":
            return "this"
        if item.startswith("this x "):
            count = item.split("x", 1)[1].strip()
            return f"{count}x this"
        m = _GUID_X_RE.match(item)
        if m:
            name = _resolve_guid(m.group(1), guid_map)
            return f"{m.group(2)}x {name}"
        if _BARE_GUID_RE.match(item):
            return _resolve_guid(item, guid_map)
        return item
    if isinstance(item, dict):
        guid = str(item.get("ID", ""))
        amount = item.get("Amount")
        delete = item.get("Delete")
        name = _resolve_guid(guid, guid_map) if guid else "?"
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
        items = [i for i in items if i]
        if items:
            parts.append(", ".join(items))
    return " | ".join(parts)


def format_blueprint_workstations(
    blueprints: list[Blueprint],
    guid_map: dict[str, str],
) -> str:
    crafting = [
        bp for bp in blueprints
        if bp.name not in _SKIP_BLUEPRINT_NAMES
    ]
    if not crafting:
        return ""
    seen: set[str] = set()
    names: list[str] = []
    for bp in crafting:
        for tag in bp.workstation_tags:
            resolved = _resolve_guid(tag, guid_map)
            if resolved not in seen:
                seen.add(resolved)
                names.append(resolved)
    return ", ".join(names)
