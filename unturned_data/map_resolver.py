"""
Map-aware spawn table resolution.

Extracts active spawn table references from binary map files,
discovers map-specific spawn tables from the map's own Bundles/,
and resolves spawn table chains to leaf item IDs.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from unturned_data.categories import parse_entry
from unturned_data.loader import walk_bundle_dir
from unturned_data.models import BundleEntry, SpawnTable, SpawnTableEntry


def extract_spawn_names_from_binary(path: Path) -> list[str]:
    """Extract length-prefixed ASCII strings from a binary spawn file.

    The map's Spawns/Items.dat encodes spawn table group names as
    length-prefixed strings interspersed with binary metadata.
    """
    if not path.exists():
        return []

    data = path.read_bytes()
    if not data:
        return []

    names: list[str] = []
    i = 0
    while i < len(data):
        if i + 1 < len(data):
            length = data[i]
            if 2 <= length <= 80 and i + 1 + length <= len(data):
                candidate = data[i + 1 : i + 1 + length]
                try:
                    text = candidate.decode("ascii")
                    if (
                        all(c.isalnum() or c in "_ -" for c in text)
                        and any(c.isalpha() for c in text)
                    ):
                        names.append(text)
                        i += 1 + length
                        continue
                except (UnicodeDecodeError, ValueError):
                    pass
        i += 1

    return names


def extract_spawn_ids_from_binary(
    path: Path,
    known_table_ids: set[int],
) -> set[int]:
    """Extract uint16 values from binary that match known spawn table IDs."""
    if not path.exists():
        return set()

    data = path.read_bytes()
    found: set[int] = set()

    for offset in range(len(data) - 1):
        val = struct.unpack_from("<H", data, offset)[0]
        if val in known_table_ids:
            found.add(val)

    return found


def collect_map_spawn_tables(map_dir: Path) -> list[SpawnTable]:
    """Discover spawn tables defined in a map's own Bundles/ directory."""
    map_bundles = map_dir / "Bundles"
    if not map_bundles.is_dir():
        return []

    tables: list[SpawnTable] = []
    for raw, english, rel_path in walk_bundle_dir(map_bundles):
        if not raw or raw.get("Type") != "Spawn":
            continue
        entry = parse_entry(raw, english, rel_path)
        if isinstance(entry, SpawnTable):
            tables.append(entry)

    return tables


def resolve_spawn_table_items(
    table_id: int,
    tables_by_id: dict[int, SpawnTable],
    visited: set[int] | None = None,
) -> set[int]:
    """Recursively resolve a spawn table to its leaf item IDs.

    Returns a set of item IDs that can spawn from this table.
    Handles circular references via the visited set.
    """
    if visited is None:
        visited = set()

    if table_id in visited:
        return set()
    visited.add(table_id)

    table = tables_by_id.get(table_id)
    if not table:
        return set()

    result: set[int] = set()
    for entry in table.table_entries:
        if entry.ref_type == "asset":
            result.add(entry.ref_id)
        elif entry.ref_type == "spawn":
            result |= resolve_spawn_table_items(
                entry.ref_id, tables_by_id, visited
            )
        # "guid" entries are resolved later when we have the guid->id map

    return result


def determine_active_tables(
    map_dir: Path,
    all_tables_by_id: dict[int, SpawnTable],
    table_name_to_id: dict[str, int],
) -> set[int]:
    """Determine which spawn tables are active on a given map.

    Uses three strategies:
    1. Name matching from binary spawn file strings
    2. ID matching from binary uint16 scan
    3. All tables from the map's own Bundles/Spawns/ (workshop maps)
    """
    active: set[int] = set()

    # Strategy 1: Extract names from binary and match
    items_dat = map_dir / "Spawns" / "Items.dat"
    names = extract_spawn_names_from_binary(items_dat)
    for name in names:
        if name in table_name_to_id:
            active.add(table_name_to_id[name])

    # Strategy 2: Scan binary for uint16 IDs matching known tables
    active |= extract_spawn_ids_from_binary(items_dat, set(all_tables_by_id.keys()))

    # Strategy 3: Include all map-defined spawn tables
    map_tables = collect_map_spawn_tables(map_dir)
    for t in map_tables:
        if t.id:
            active.add(t.id)

    return active
