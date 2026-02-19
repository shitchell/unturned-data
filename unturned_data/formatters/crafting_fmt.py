"""
Crafting-graph formatter for Unturned bundle entries.

Produces a JSON object with ``nodes`` and ``edges`` arrays suitable
for rendering as an interactive graph with Cytoscape.js.

Nodes represent unique items that participate in any blueprint.
Edges represent input/output relationships between items.
"""
from __future__ import annotations

import re
import json
from typing import Any, TYPE_CHECKING

from unturned_data.models import Blueprint, BundleEntry, _GUID_X_RE, _BARE_GUID_RE

if TYPE_CHECKING:
    from unturned_data.models import CraftingBlacklist

# Regex for numeric item ID references (e.g. "68 x 2", "1297")
_ID_X_RE = re.compile(r"^(\d+)\s+x\s*(\d+)$")
_BARE_ID_RE = re.compile(r"^\d+$")
from unturned_data.formatters.markdown_fmt import build_guid_map


def _parse_item_ref(
    item: Any,
    owner_guid: str,
    id_to_guid: dict[int, str] | None = None,
) -> tuple[str, int, bool]:
    """Parse a single blueprint item reference.

    Returns ``(guid, quantity, is_tool)`` where *guid* is lowercase.

    Handles:
    - ``"this"`` or ``"this x N"`` -- returns owner_guid
    - ``"GUID x N"`` -- 32 hex chars + quantity
    - ``"GUID"`` -- bare 32-char hex string (quantity = 1)
    - ``"ID x N"`` -- numeric item ID + quantity (resolved via id_to_guid)
    - ``"ID"`` -- bare numeric item ID
    - ``{"ID": "GUID", "Amount": N}`` -- object form
    - ``{"ID": "GUID", "Delete": false}`` -- tool
    - ``{"ID": "this", ...}`` -- object form referencing owner
    """
    if isinstance(item, str):
        # "this" or "this x N"
        if item == "this":
            return (owner_guid.lower(), 1, False)
        if item.startswith("this x "):
            count_str = item.split("x", 1)[1].strip()
            return (owner_guid.lower(), int(count_str), False)

        # "GUID x N"
        m = _GUID_X_RE.match(item)
        if m:
            return (m.group(1).lower(), int(m.group(2)), False)

        # bare GUID
        if _BARE_GUID_RE.match(item):
            return (item.lower(), 1, False)

        # "ID x N" (numeric item ID)
        m = _ID_X_RE.match(item)
        if m and id_to_guid:
            guid = id_to_guid.get(int(m.group(1)), "")
            if guid:
                return (guid, int(m.group(2)), False)

        # bare numeric ID
        if _BARE_ID_RE.match(item) and id_to_guid:
            guid = id_to_guid.get(int(item), "")
            if guid:
                return (guid, 1, False)

        # Unknown string -- skip
        return ("", 0, False)

    if isinstance(item, dict):
        raw_id = str(item.get("ID", ""))
        amount = int(item.get("Amount", 1))
        delete = item.get("Delete")
        is_tool = delete is False

        # Handle "this" in dict form
        if raw_id.lower() == "this":
            return (owner_guid.lower(), amount, is_tool)

        guid = raw_id.lower()
        return (guid, amount, is_tool)

    return ("", 0, False)


def _resolve_name(guid: str, guid_map: dict[str, str]) -> str:
    """Resolve a GUID to a display name, or bracket notation."""
    guid_lower = guid.lower()
    name = guid_map.get(guid_lower)
    if name:
        return name
    return f"[{guid_lower[:8]}]"


def _is_entry_core(entry: BundleEntry, map_source_prefixes: dict[str, list[str]] | None) -> bool:
    """Check if an entry is from the core/base game (not a map-specific item)."""
    if not map_source_prefixes:
        return True
    for prefixes in map_source_prefixes.values():
        for prefix in prefixes:
            if entry.source_path.startswith(prefix):
                return False
    return True


def build_crafting_graph(
    entries: list[BundleEntry],
    guid_map: dict[str, str],
    crafting_blacklists: dict[str, CraftingBlacklist] | None = None,
    map_source_prefixes: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build a crafting graph from entries.

    Returns a dict with ``nodes`` (list of node dicts) and ``edges``
    (list of edge dicts).

    Only entries that have a ``blueprints`` attribute with at least
    one blueprint are included.
    """
    nodes: dict[str, dict[str, Any]] = {}  # guid -> node dict
    edges: list[dict[str, Any]] = []
    blueprint_counter = 0

    # Build numeric ID -> GUID map for legacy blueprint references.
    # Only include Items (not Effects, Objects, Spawns, etc.) since
    # numeric IDs are not unique across entry types.
    id_to_guid: dict[int, str] = {}
    for entry in entries:
        if entry.id and entry.guid and entry.source_path.startswith("Items/"):
            id_to_guid[entry.id] = entry.guid.lower()

    # Build GUID -> entry lookup for enriching stub nodes
    entries_by_guid: dict[str, BundleEntry] = {}
    for entry in entries:
        if entry.guid:
            entries_by_guid[entry.guid.lower()] = entry

    for entry in entries:
        blueprints: list[Blueprint] = getattr(entry, "blueprints", [])
        if not blueprints:
            continue

        # Check crafting blacklists: only skip core blueprints if ALL
        # maps with blacklists disallow them.  Maps without a blacklist
        # entry implicitly allow core blueprints.
        if crafting_blacklists and _is_entry_core(entry, map_source_prefixes):
            # Maps not in the blacklist dict implicitly allow core blueprints
            all_maps = set(map_source_prefixes.keys()) if map_source_prefixes else set()
            maps_with_blacklist = set(crafting_blacklists.keys())
            maps_without_blacklist = all_maps - maps_with_blacklist
            any_allows_core = bool(maps_without_blacklist)
            if not any_allows_core:
                for map_name, bl in crafting_blacklists.items():
                    if bl is None or bl.allow_core_blueprints:
                        any_allows_core = True
                        break
            if not any_allows_core:
                continue

        owner_guid = entry.guid.lower()
        if not owner_guid:
            continue

        # Add owner node
        if owner_guid not in nodes:
            nodes[owner_guid] = {
                "id": owner_guid,
                "name": entry.name or _resolve_name(owner_guid, guid_map),
                "type": entry.type,
                "category": entry.category_parts,
                "rarity": entry.rarity,
                "maps": sorted(getattr(entry, "_map_spawnable", None) or []),
            }

        for bp in blueprints:
            blueprint_counter += 1
            bp_id = f"bp-{blueprint_counter}"

            # Determine edge type
            if bp.name == "Salvage":
                edge_type = "salvage"
            elif bp.name == "Repair":
                edge_type = "repair"
            else:
                edge_type = "craft"

            # Resolve workstation names
            workstation_names = [
                _resolve_name(tag, guid_map) for tag in bp.workstation_tags
            ]

            if edge_type == "salvage":
                # Salvage: owner is broken down into outputs
                # Edge: source=owner -> target=each output
                for out_item in bp.outputs:
                    out_guid, out_qty, out_tool = _parse_item_ref(
                        out_item, owner_guid, id_to_guid
                    )
                    if not out_guid:
                        continue
                    _ensure_stub_node(out_guid, guid_map, nodes, entries_by_guid)
                    edges.append({
                        "source": owner_guid,
                        "target": out_guid,
                        "type": edge_type,
                        "quantity": out_qty,
                        "tool": out_tool,
                        "workstations": workstation_names,
                        "skill": bp.skill,
                        "skillLevel": bp.skill_level,
                        "blueprintId": bp_id,
                        "byproduct": False,
                    })

            elif edge_type == "repair":
                # Repair: inputs repair the owner
                # Edge: source=input -> target=owner
                for in_item in bp.inputs:
                    in_guid, in_qty, in_tool = _parse_item_ref(
                        in_item, owner_guid, id_to_guid
                    )
                    if not in_guid:
                        continue
                    _ensure_stub_node(in_guid, guid_map, nodes, entries_by_guid)
                    edges.append({
                        "source": in_guid,
                        "target": owner_guid,
                        "type": edge_type,
                        "quantity": in_qty,
                        "tool": in_tool,
                        "workstations": workstation_names,
                        "skill": bp.skill,
                        "skillLevel": bp.skill_level,
                        "blueprintId": bp_id,
                        "byproduct": False,
                    })

            else:
                # Craft: inputs create the output
                # Determine target: if outputs contain "this" or are empty,
                # target = owner. If outputs contain a specific GUID,
                # target = that GUID.
                targets = _resolve_craft_targets(bp, owner_guid, id_to_guid)

                for target_guid in targets:
                    _ensure_stub_node(target_guid, guid_map, nodes, entries_by_guid)
                    is_byproduct = (
                        len(targets) > 1
                        and target_guid != owner_guid
                    )
                    for in_item in bp.inputs:
                        in_guid, in_qty, in_tool = _parse_item_ref(
                            in_item, owner_guid, id_to_guid
                        )
                        if not in_guid:
                            continue
                        _ensure_stub_node(in_guid, guid_map, nodes, entries_by_guid)
                        edges.append({
                            "source": in_guid,
                            "target": target_guid,
                            "type": edge_type,
                            "quantity": in_qty,
                            "tool": in_tool,
                            "workstations": workstation_names,
                            "skill": bp.skill,
                            "skillLevel": bp.skill_level,
                            "blueprintId": bp_id,
                            "byproduct": is_byproduct,
                        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def _resolve_craft_targets(
    bp: Blueprint,
    owner_guid: str,
    id_to_guid: dict[int, str] | None = None,
) -> list[str]:
    """Determine the target GUIDs for a craft blueprint.

    If outputs are empty or contain only "this" references, returns
    ``[owner_guid]``.  Otherwise returns the specific output GUIDs.
    """
    if not bp.outputs:
        return [owner_guid]

    targets: list[str] = []
    for out_item in bp.outputs:
        out_guid, _, _ = _parse_item_ref(out_item, owner_guid, id_to_guid)
        if out_guid:
            targets.append(out_guid)

    return targets if targets else [owner_guid]


def _ensure_stub_node(
    guid: str,
    guid_map: dict[str, str],
    nodes: dict[str, dict[str, Any]],
    entries_by_guid: dict[str, BundleEntry] | None = None,
) -> None:
    """Add a stub node for a GUID if not already present."""
    if guid not in nodes:
        entry = entries_by_guid.get(guid) if entries_by_guid else None
        if entry:
            nodes[guid] = {
                "id": guid,
                "name": entry.name or _resolve_name(guid, guid_map),
                "type": entry.type,
                "category": entry.category_parts,
                "rarity": entry.rarity,
                "maps": sorted(getattr(entry, "_map_spawnable", None) or []),
            }
        else:
            nodes[guid] = {
                "id": guid,
                "name": _resolve_name(guid, guid_map),
                "type": "",
                "category": [],
                "rarity": "",
                "maps": [],
            }


def entries_to_crafting_json(
    entries: list[BundleEntry],
    supplementary_guids: dict[str, str] | None = None,
    indent: int | None = None,
    crafting_blacklists: dict[str, CraftingBlacklist] | None = None,
    map_source_prefixes: dict[str, list[str]] | None = None,
) -> str:
    """Convert entries to a crafting-graph JSON string.

    Builds a GUID map from the entries (with optional supplementary
    names), then produces the graph structure.

    Returns a JSON string with ``nodes`` and ``edges`` arrays.
    """
    if not entries:
        return json.dumps({"nodes": [], "edges": []}, indent=indent)

    guid_map = build_guid_map(entries, supplementary_guids)
    graph = build_crafting_graph(
        entries, guid_map,
        crafting_blacklists=crafting_blacklists,
        map_source_prefixes=map_source_prefixes,
    )

    return json.dumps(graph, indent=indent, ensure_ascii=False)
