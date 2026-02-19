"""
Crafting blacklist resolution for Unturned maps.

Reads the Config.json -> LevelAsset -> CraftingBlacklistAsset chain
to determine which crafting restrictions apply on a given map.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unturned_data.dat_parser import parse_asset_file
from unturned_data.models import CraftingBlacklist


def _find_asset_by_guid(
    search_dirs: list[Path],
    target_guid: str,
) -> Path | None:
    """Find an .asset file containing the given GUID."""
    target_lower = target_guid.lower()
    for root in search_dirs:
        if not root.is_dir():
            continue
        for asset_path in root.rglob("*.asset"):
            try:
                parsed = parse_asset_file(asset_path)
            except Exception:
                continue
            meta = parsed.get("Metadata", {})
            if isinstance(meta, dict):
                guid = str(meta.get("GUID", "")).lower()
                if guid == target_lower:
                    return asset_path
    return None


def _parse_blacklist_asset(parsed: dict[str, Any]) -> CraftingBlacklist:
    """Extract CraftingBlacklist fields from a parsed CraftingBlacklistAsset."""
    asset = parsed.get("Asset", {})
    if not isinstance(asset, dict):
        return CraftingBlacklist()

    allow_core = asset.get("Allow_Core_Blueprints", True)
    if isinstance(allow_core, str):
        allow_core = allow_core.lower() != "false"

    blocked_inputs: set[str] = set()
    for item in asset.get("Input_Items", []):
        if isinstance(item, dict) and "GUID" in item:
            blocked_inputs.add(str(item["GUID"]).lower())

    blocked_outputs: set[str] = set()
    for item in asset.get("Output_Items", []):
        if isinstance(item, dict) and "GUID" in item:
            blocked_outputs.add(str(item["GUID"]).lower())

    return CraftingBlacklist(
        allow_core_blueprints=bool(allow_core),
        blocked_inputs=blocked_inputs,
        blocked_outputs=blocked_outputs,
    )


def resolve_crafting_blacklist(
    map_dir: Path,
    extra_bundle_dirs: list[Path] | None = None,
) -> CraftingBlacklist | None:
    """Resolve crafting blacklists for a map directory.

    Returns None if the map has no crafting blacklists.
    Returns a merged CraftingBlacklist if it does.
    """
    config_path = map_dir / "Config.json"
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    asset_ref = config.get("Asset", {})
    if not isinstance(asset_ref, dict):
        return None
    level_guid = asset_ref.get("GUID", "")
    if not level_guid:
        return None

    search_dirs = [map_dir / "Bundles"]
    if extra_bundle_dirs:
        search_dirs.extend(extra_bundle_dirs)

    level_asset_path = _find_asset_by_guid(search_dirs, level_guid)
    if not level_asset_path:
        return None

    level_parsed = parse_asset_file(level_asset_path)
    asset_section = level_parsed.get("Asset", {})
    if not isinstance(asset_section, dict):
        return None

    blacklist_refs = asset_section.get("Crafting_Blacklists", [])
    if not isinstance(blacklist_refs, list) or not blacklist_refs:
        return None

    blacklists: list[CraftingBlacklist] = []
    for ref in blacklist_refs:
        if isinstance(ref, dict):
            bl_guid = str(ref.get("GUID", ""))
        else:
            bl_guid = str(ref)
        if not bl_guid:
            continue

        bl_path = _find_asset_by_guid(search_dirs, bl_guid)
        if not bl_path:
            continue

        bl_parsed = parse_asset_file(bl_path)
        meta_type = bl_parsed.get("Metadata", {}).get("Type", "")
        if isinstance(meta_type, str) and "CraftingBlacklist" in meta_type:
            blacklists.append(_parse_blacklist_asset(bl_parsed))

    if not blacklists:
        return None

    return CraftingBlacklist.merge(blacklists)
