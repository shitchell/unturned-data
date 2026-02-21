"""Schema C origin-first export pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from unturned_data.categories import parse_entry
from unturned_data.crafting_blacklist import resolve_crafting_blacklist
from unturned_data.dat_parser import parse_asset_file
from unturned_data.loader import walk_bundle_dir
from unturned_data.map_resolver import (
    collect_map_spawn_tables,
    determine_active_tables,
    resolve_spawn_table_items,
)
from unturned_data.models import BundleEntry, SpawnTable
from unturned_data.schema import (
    AssetEntry,
    CraftingBlacklistInfo,
    GuidIndex,
    GuidIndexEntry,
    LevelAssetInfo,
    Manifest,
    ManifestMapInfo,
    MapConfig,
    SpawnResolution,
)

# Namespace mapping: top-level source directory -> namespace key
_SOURCE_DIR_TO_NAMESPACE: dict[str, str] = {
    "Items": "items",
    "Vehicles": "vehicles",
    "Objects": "objects",
    "Spawns": "spawns",
    "Animals": "animals",
    "Effects": "effects",
    "Trees": "resources",
    "Skins": "skins",
    "Mythics": "mythics",
    "NPCs": "npcs",
}


def _get_namespace(source_path: str) -> str:
    """Derive the asset namespace from source_path's top-level directory."""
    top_dir = source_path.split("/")[0] if source_path else ""
    return _SOURCE_DIR_TO_NAMESPACE.get(top_dir, top_dir.lower())


def _ensure_guids(entries: list[BundleEntry], source: str) -> None:
    """Assign deterministic synthetic GUIDs to entries that lack one.

    Synthetic GUIDs start with '00000' to distinguish them from real GUIDs.
    """
    for entry in entries:
        if not entry.guid:
            hash_input = f"{source}:{entry.type}:{entry.id}"
            digest = hashlib.sha256(hash_input.encode()).hexdigest()
            entry.guid = "00000" + digest[:27]


_GUID_RE = re.compile(r"^[0-9a-f]{32}$")


def _resolve_blueprint_ids(
    entries: list[BundleEntry],
    source: str,
    extra_entries: list[BundleEntry] | None = None,
) -> None:
    """Resolve numeric IDs in blueprint inputs/outputs to GUIDs.

    Builds an ID->GUID map from all provided entries, then walks
    every blueprint reference and replaces numeric IDs with GUIDs.

    Resolution priority:
    1. Same namespace (items) + same source
    2. Same namespace (items) + any source
    3. Any namespace + same source (with warning)
    4. Any namespace + any source (with warning)

    Args:
        entries: The entries to process (blueprints will be mutated in-place).
        source: Source label for these entries (e.g., "base" or map safe name).
        extra_entries: Additional entries for cross-source resolution (e.g.,
            base entries when resolving a map's blueprints).
    """
    # Build lookup: {numeric_id: {namespace: {source_label: guid}}}
    id_map: dict[int, dict[str, dict[str, str]]] = {}

    def _index(entry_list: list[BundleEntry], src: str) -> None:
        for e in entry_list:
            if not e.id or e.id == 0 or not e.guid:
                continue
            ns = _get_namespace(e.source_path)
            if e.id not in id_map:
                id_map[e.id] = {}
            if ns not in id_map[e.id]:
                id_map[e.id][ns] = {}
            id_map[e.id][ns][src] = e.guid

    _index(entries, source)
    if extra_entries:
        for e in extra_entries:
            _index([e], "base")

    def _resolve_id(numeric_id: int, entry_name: str, bp_name: str) -> str | None:
        """Resolve a numeric ID to a GUID using priority chain."""
        ns_map = id_map.get(numeric_id)
        if not ns_map:
            return None

        # Priority 1: items namespace, same source
        if "items" in ns_map and source in ns_map["items"]:
            return ns_map["items"][source]
        # Priority 2: items namespace, any source
        if "items" in ns_map:
            return next(iter(ns_map["items"].values()))
        # Priority 3: any namespace, same source (warn)
        for ns, sources in ns_map.items():
            if source in sources:
                logger.warning(
                    "Blueprint ref %d in %s/%s resolved to non-item "
                    "namespace '%s'", numeric_id, entry_name, bp_name, ns)
                return sources[source]
        # Priority 4: any namespace, any source (warn)
        for ns, sources in ns_map.items():
            guid = next(iter(sources.values()))
            logger.warning(
                "Blueprint ref %d in %s/%s resolved to non-item "
                "namespace '%s' (cross-source)", numeric_id, entry_name,
                bp_name, ns)
            return guid
        return None

    def _resolve_ref(ref, entry_name: str, bp_name: str):
        """Resolve a single blueprint input/output reference."""
        if isinstance(ref, dict):
            # Tool dict: {"ID": "76", "Amount": 1, "Delete": False}
            ref_id = ref.get("ID", "")
            if isinstance(ref_id, str) and ref_id.isdigit():
                guid = _resolve_id(int(ref_id), entry_name, bp_name)
                if guid:
                    ref = dict(ref)  # copy to avoid mutating shared dicts
                    ref["ID"] = guid
            return ref

        if not isinstance(ref, str):
            return ref
        if ref == "this":
            return ref

        # Parse "ID" or "ID x N"
        parts = ref.split(" x ")
        id_str = parts[0].strip()

        # Already a GUID?
        if _GUID_RE.match(id_str):
            return ref

        # Numeric ID?
        if id_str.isdigit():
            guid = _resolve_id(int(id_str), entry_name, bp_name)
            if guid:
                if len(parts) > 1:
                    return f"{guid} x {parts[1].strip()}"
                return guid
            else:
                logger.warning(
                    "Unresolvable blueprint ref ID %s in %s/%s",
                    id_str, entry_name, bp_name)
        return ref

    # Walk all entries and resolve
    for entry in entries:
        for bp in entry.blueprints:
            bp.inputs = [_resolve_ref(r, entry.name, bp.name) for r in bp.inputs]
            bp.outputs = [_resolve_ref(r, entry.name, bp.name) for r in bp.outputs]


# The fields that belong in Schema C entries.json -- only these are serialized
# at the top level, preventing subclass-specific Pydantic fields from leaking.
SCHEMA_C_FIELDS = {
    "guid",
    "type",
    "id",
    "name",
    "description",
    "rarity",
    "size_x",
    "size_y",
    "source_path",
    "category",
    "english",
    "parsed",
    "blueprints",
    "raw",
}


def discover_maps(server_root: Path) -> list[Path]:
    """Auto-discover all map directories in an Unturned server installation.

    Searches:
    - <server_root>/Maps/*/  (built-in maps)
    - <server_root>/Servers/*/Workshop/Steam/content/304930/*/*/  (workshop maps)

    A directory is a valid map if it contains Spawns/, Bundles/, or Config.json.
    """
    maps: list[Path] = []

    # Built-in maps
    builtin_maps = server_root / "Maps"
    if builtin_maps.is_dir():
        for candidate in sorted(builtin_maps.iterdir()):
            if candidate.is_dir() and _is_map_dir(candidate):
                maps.append(candidate)

    # Workshop maps (Servers/*/Workshop/Steam/content/304930/<workshop_id>/<map_name>/)
    servers_dir = server_root / "Servers"
    if servers_dir.is_dir():
        for server_instance in sorted(servers_dir.iterdir()):
            workshop_content = (
                server_instance / "Workshop" / "Steam" / "content" / "304930"
            )
            if not workshop_content.is_dir():
                continue
            for workshop_id_dir in sorted(workshop_content.iterdir()):
                if not workshop_id_dir.is_dir():
                    continue
                for candidate in sorted(workshop_id_dir.iterdir()):
                    if candidate.is_dir() and _is_map_dir(candidate):
                        maps.append(candidate)

    return maps


def _is_map_dir(path: Path) -> bool:
    """Check if a directory looks like an Unturned map."""
    return (
        (path / "Spawns").is_dir()
        or (path / "Bundles").is_dir()
        or (path / "Config.json").is_file()
    )


def _serialize_entry(entry: BundleEntry) -> dict[str, Any]:
    """Serialize a single entry to Schema C dict (only Schema C fields)."""
    return entry.model_dump(include=SCHEMA_C_FIELDS)


def _serialize_entries(entries: list[BundleEntry]) -> list[dict[str, Any]]:
    """Serialize entries sorted by (name, id)."""
    sorted_entries = sorted(entries, key=lambda e: (e.name, e.id))
    return [_serialize_entry(e) for e in sorted_entries]


def _collect_assets(bundles_path: Path) -> list[AssetEntry]:
    """Collect .asset file entries from a bundles directory."""
    assets: list[AssetEntry] = []
    for asset_file in sorted(bundles_path.rglob("*.asset")):
        try:
            parsed = parse_asset_file(asset_file)
        except Exception:
            continue
        # Try Metadata-nested format first (standard .asset files),
        # then top-level format (tag .asset files)
        meta = parsed.get("Metadata", {})
        if not isinstance(meta, dict):
            meta = {}
        guid = str(meta.get("GUID", "") or parsed.get("GUID", "")).lower()
        if not guid:
            continue
        csharp_type = str(meta.get("Type", "") or parsed.get("Type", ""))
        type_short = csharp_type.split(",")[0].rsplit(".", 1)[-1] if csharp_type else ""

        # For tag assets, read the friendly name from English.dat if available
        name = asset_file.stem.replace("_", " ")
        english_dat = asset_file.parent / "English.dat"
        if english_dat.exists():
            try:
                eng_text = english_dat.read_text(encoding="utf-8-sig")
                for line in eng_text.splitlines():
                    if line.startswith("Name "):
                        name = line[5:].strip()
                        break
            except Exception:
                pass

        rel_path = str(asset_file.relative_to(bundles_path))
        assets.append(
            AssetEntry(
                guid=guid,
                name=name,
                csharp_type=type_short,
                source_path=rel_path,
                raw=parsed,
            )
        )
    return assets


def _write_json(path: Path, data: Any) -> None:
    """Write JSON to file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _safe_name(name: str) -> str:
    """Convert a map directory name to a safe filesystem name."""
    safe = name.lower().replace(" ", "_")
    safe = re.sub(r"[^a-z0-9_]", "", safe)
    return safe or "unknown"


def _parse_entries(bundles_path: Path) -> list[BundleEntry]:
    """Parse all bundle entries from a directory."""
    entries: list[BundleEntry] = []
    for raw, english, rel_path in walk_bundle_dir(bundles_path):
        if not raw:
            continue
        entry = parse_entry(raw, english, rel_path)
        entries.append(entry)
    return entries


def _build_map_config(
    map_dir: Path,
    base_entries: list[BundleEntry],
    map_entries: list[BundleEntry],
) -> MapConfig:
    """Build a MapConfig for a given map directory."""
    map_name = map_dir.name

    # Read Config.json if present
    config: dict[str, Any] = {}
    config_path = map_dir / "Config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            pass

    # Resolve crafting blacklists
    blacklist = resolve_crafting_blacklist(map_dir)
    blacklist_infos: list[CraftingBlacklistInfo] = []
    if blacklist:
        blacklist_infos.append(
            CraftingBlacklistInfo(
                guid="",
                allow_core_blueprints=blacklist.allow_core_blueprints,
                blocked_input_guids=sorted(blacklist.blocked_inputs),
                blocked_output_guids=sorted(blacklist.blocked_outputs),
            )
        )

    # Build spawn table lookups from ALL entries (base + map)
    all_entries = base_entries + map_entries
    tables_by_id: dict[int, SpawnTable] = {}
    table_name_to_id: dict[str, int] = {}
    id_to_guid: dict[int, str] = {}

    for entry in all_entries:
        if entry.id:
            id_to_guid[entry.id] = entry.guid
        if isinstance(entry, SpawnTable) and entry.id:
            tables_by_id[entry.id] = entry
            if entry.name:
                table_name_to_id[entry.name] = entry.id

    # Determine active tables and resolve spawns
    active_ids = determine_active_tables(map_dir, tables_by_id, table_name_to_id)

    # Build table chains and collect all spawnable items
    table_chains: dict[int, list[int]] = {}
    all_spawnable: set[int] = set()
    active_names: list[str] = []

    for tid in sorted(active_ids):
        leaf_ids = resolve_spawn_table_items(tid, tables_by_id)
        table_chains[tid] = sorted(leaf_ids)
        all_spawnable |= leaf_ids
        table = tables_by_id.get(tid)
        if table and table.name:
            active_names.append(table.name)

    # Map spawnable IDs to GUIDs
    spawnable_guids = sorted(
        id_to_guid[sid]
        for sid in all_spawnable
        if sid in id_to_guid and id_to_guid[sid]
    )

    spawn_resolution = SpawnResolution(
        active_table_ids=sorted(active_ids),
        active_table_names=sorted(active_names),
        spawnable_item_ids=sorted(all_spawnable),
        spawnable_item_guids=spawnable_guids,
        table_chains=table_chains,
    )

    return MapConfig(
        name=map_name,
        source_path=str(map_dir),
        config=config,
        crafting_blacklists=blacklist_infos,
        spawn_resolution=spawn_resolution,
    )


def _build_guid_index(
    base_entries: list[BundleEntry],
    base_assets: list[AssetEntry],
    map_data: dict[str, tuple[list[BundleEntry], list[AssetEntry]]],
    now: str,
) -> GuidIndex:
    """Build a master GUID index covering all entries and assets."""
    entries_index: dict[str, GuidIndexEntry] = {}
    by_id: dict[str, dict[str, dict[str, str]]] = {}

    def _index_bundle_entries(
        items: list[BundleEntry],
        file_path: str,
        source_label: str = "base",
    ) -> None:
        # Entries are serialized sorted by (name, id)
        sorted_items = sorted(items, key=lambda e: (e.name, e.id))
        for idx, entry in enumerate(sorted_items):
            if entry.guid:
                entries_index[entry.guid] = GuidIndexEntry(
                    file=file_path,
                    index=idx,
                    id=entry.id,
                    type=entry.type,
                    name=entry.name,
                    kind="item",
                )
            if entry.id:
                id_str = str(entry.id)
                ns = _get_namespace(entry.source_path)
                if id_str not in by_id:
                    by_id[id_str] = {}
                if ns not in by_id[id_str]:
                    by_id[id_str][ns] = {}
                by_id[id_str][ns][source_label] = entry.guid

    def _index_assets(
        items: list[AssetEntry],
        file_path: str,
    ) -> None:
        for idx, asset in enumerate(items):
            if asset.guid and asset.guid not in entries_index:
                kind = "tag" if asset.csharp_type == "Tag" else "asset"
                entries_index[asset.guid] = GuidIndexEntry(
                    file=file_path,
                    index=idx,
                    id=0,
                    type=asset.csharp_type,
                    name=asset.name,
                    kind=kind,
                )

    # Index base entries and assets
    _index_bundle_entries(base_entries, "base/entries.json")
    _index_assets(base_assets, "base/assets.json")

    # Index map entries and assets
    for safe_name, (m_entries, m_assets) in sorted(map_data.items()):
        if m_entries:
            _index_bundle_entries(
                m_entries,
                f"maps/{safe_name}/entries.json",
                source_label=safe_name,
            )
        if m_assets:
            _index_assets(m_assets, f"maps/{safe_name}/assets.json")

    return GuidIndex(
        total_entries=len(entries_index),
        generated_at=now,
        entries=entries_index,
        by_id=by_id,
    )


def export_schema_c(
    base_bundles: Path,
    map_dirs: list[Path],
    output_dir: Path,
    generator: str = "unturned-data",
) -> None:
    """Run the full Schema C export pipeline.

    Args:
        base_bundles: Path to the base game Bundles directory.
        map_dirs: List of map directories (each containing optional
            Bundles/, Config.json, Spawns/, etc.).
        output_dir: Where to write the output files.
        generator: Generator name for the manifest.
    """
    now = datetime.now(timezone.utc).isoformat()

    # --- Base entries ---
    base_entries = _parse_entries(base_bundles)
    _ensure_guids(base_entries, "base")
    _resolve_blueprint_ids(base_entries, "base")
    base_serialized = _serialize_entries(base_entries)
    _write_json(output_dir / "base" / "entries.json", base_serialized)

    # --- Base assets ---
    base_assets = _collect_assets(base_bundles)
    base_assets_serialized = [a.model_dump() for a in base_assets]
    _write_json(output_dir / "base" / "assets.json", base_assets_serialized)

    # --- Maps ---
    map_manifest: dict[str, ManifestMapInfo] = {}
    # safe_name -> (entries, assets) for guid index
    map_data: dict[str, tuple[list[BundleEntry], list[AssetEntry]]] = {}

    for map_dir in map_dirs:
        safe = _safe_name(map_dir.name)
        map_prefix = f"maps/{safe}"

        # Parse map entries from map's Bundles/ if present
        map_bundles = map_dir / "Bundles"
        map_entries: list[BundleEntry] = []
        if map_bundles.is_dir():
            map_entries = _parse_entries(map_bundles)
            _ensure_guids(map_entries, safe)
            _resolve_blueprint_ids(map_entries, safe, extra_entries=base_entries)

        # Collect map assets
        map_assets: list[AssetEntry] = []
        if map_bundles.is_dir():
            map_assets = _collect_assets(map_bundles)

        map_data[safe] = (map_entries, map_assets)

        # Write entries and assets
        has_entries = len(map_entries) > 0
        has_assets = len(map_assets) > 0

        if has_entries:
            _write_json(
                output_dir / map_prefix / "entries.json",
                _serialize_entries(map_entries),
            )
        if has_assets:
            _write_json(
                output_dir / map_prefix / "assets.json",
                [a.model_dump() for a in map_assets],
            )

        # Build and write map.json
        map_config = _build_map_config(map_dir, base_entries, map_entries)
        _write_json(
            output_dir / map_prefix / "map.json",
            map_config.model_dump(),
        )

        map_manifest[safe] = ManifestMapInfo(
            map_file=f"{map_prefix}/map.json",
            has_custom_entries=has_entries,
            entries_file=f"{map_prefix}/entries.json" if has_entries else None,
            assets_file=f"{map_prefix}/assets.json" if has_assets else None,
            entry_count=len(map_entries),
            asset_count=len(map_assets),
        )

    # --- GUID index ---
    guid_index = _build_guid_index(base_entries, base_assets, map_data, now)
    _write_json(output_dir / "guid_index.json", guid_index.model_dump())

    # --- Manifest ---
    manifest = Manifest(
        generated_at=now,
        generator=generator,
        base_bundles_path=str(base_bundles),
        base_entry_count=len(base_entries),
        base_asset_count=len(base_assets),
        maps=map_manifest,
    )
    _write_json(output_dir / "manifest.json", manifest.model_dump())
