"""
CLI entry point for the unturned-data tool.

Parses Unturned .dat bundle files and outputs JSON or markdown to stdout.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unturned_data.categories import parse_entry
from unturned_data.formatters.json_fmt import entries_to_json
from unturned_data.formatters.markdown_fmt import entries_to_markdown
from unturned_data.formatters.crafting_fmt import entries_to_crafting_json
from unturned_data.formatters.web_fmt import entries_to_web_json
from unturned_data.loader import (
    collect_comment_guids_from_dir,
    walk_asset_files,
    walk_bundle_dir,
)
from unturned_data.map_resolver import (
    collect_map_spawn_tables,
    determine_active_tables,
    resolve_spawn_table_items,
)
from unturned_data.models import BundleEntry, SpawnTable


def _is_excluded(source_path: str, patterns: list[str]) -> bool:
    """Check if a source path matches any exclude pattern.

    Each pattern is split on ``/`` and matched as a contiguous
    subsequence of the path segments.  E.g. pattern ``"Foo"`` matches
    ``"Items/Foo/Bar"`` and ``"Weapons/Foo/Baz"``, while
    ``"Items/Foo"`` only matches the first.
    """
    path_parts = source_path.split("/")
    for pattern in patterns:
        pat_parts = pattern.strip("/").split("/")
        # Slide pattern over path segments
        for i in range(len(path_parts) - len(pat_parts) + 1):
            if path_parts[i : i + len(pat_parts)] == pat_parts:
                return True
    return False


def main(argv: list[str] | None = None) -> None:
    """Parse Unturned bundle directories and output formatted data."""
    parser = argparse.ArgumentParser(
        prog="unturned-data",
        description="Parse Unturned .dat bundle files into JSON or markdown.",
    )
    parser.add_argument("path", type=Path, help="Path to a Bundles directory")
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown", "web", "crafting"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        nargs="+",
        default=[],
        metavar="PATH",
        help=(
            "Exclude entries whose path contains the given segment(s). "
            "Use a bare name to match any directory (e.g. -e Foo excludes "
            "Items/Foo/... and Weapons/Foo/...), or a slash-delimited "
            "path for a specific subtree (e.g. -e Items/Foo)."
        ),
    )
    parser.add_argument(
        "--map",
        action="append",
        default=None,
        type=Path,
        metavar="DIR",
        help=(
            "Path to a map directory (contains Spawns/, optionally Bundles/). "
            "Can be specified multiple times. Entries spawnable on each map "
            "are tagged with a _map_spawnable attribute."
        ),
    )
    args = parser.parse_args(argv)

    bundle_path: Path = args.path.resolve()
    if not bundle_path.is_dir():
        print(f"Error: {bundle_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    entries: list[BundleEntry] = []
    for raw, english, rel_path in walk_bundle_dir(bundle_path):
        if not raw:
            continue
        if _is_excluded(rel_path, args.exclude):
            continue
        entry = parse_entry(raw, english, rel_path)
        entries.append(entry)

    # --map processing: walk map Bundles/, resolve spawn tables, tag entries
    crafting_blacklists: dict = {}
    map_source_prefixes: dict = {}
    if args.map:
        # Index existing entries by GUID and ID to avoid duplicates
        seen_guids: set[str] = {e.guid for e in entries if e.guid}
        seen_ids: set[int] = {e.id for e in entries if e.id}

        # Walk each map's Bundles/ for additional entries.
        # Items defined in a map's own Bundles/ are tagged with that map
        # since they are map-specific content (even if not in spawn tables).
        for map_dir in args.map:
            map_name = map_dir.resolve().name
            map_bundles = map_dir / "Bundles"
            if not map_bundles.is_dir():
                continue
            for raw, english, rel_path in walk_bundle_dir(map_bundles):
                if not raw:
                    continue
                entry = parse_entry(raw, english, f"_map_{map_name}/{rel_path}")
                # Avoid duplicates by GUID (preferred) or ID
                if entry.guid and entry.guid in seen_guids:
                    continue
                if entry.id and entry.id in seen_ids:
                    continue
                if entry.guid:
                    seen_guids.add(entry.guid)
                if entry.id:
                    seen_ids.add(entry.id)
                # Tag map-specific entries with their map
                if not hasattr(entry, "_map_spawnable"):
                    entry._map_spawnable = set()
                entry._map_spawnable.add(map_name)
                entries.append(entry)

        # Collect all SpawnTable entries and build lookup dicts
        tables_by_id: dict[int, SpawnTable] = {}
        table_name_to_id: dict[str, int] = {}
        for entry in entries:
            if isinstance(entry, SpawnTable) and entry.id:
                tables_by_id[entry.id] = entry
                if entry.name:
                    table_name_to_id[entry.name] = entry.id

        # Build id->guid map for tagging
        id_to_guid: dict[int, str] = {}
        for entry in entries:
            if entry.id and entry.guid:
                id_to_guid[entry.id] = entry.guid

        # For each map, determine active tables and resolve spawnable items
        for map_dir in args.map:
            map_name = map_dir.resolve().name
            active_ids = determine_active_tables(
                map_dir, tables_by_id, table_name_to_id,
            )
            # Collect all item IDs spawnable on this map
            spawnable_item_ids: set[int] = set()
            for table_id in active_ids:
                spawnable_item_ids |= resolve_spawn_table_items(
                    table_id, tables_by_id,
                )
            # Tag matching entries with _map_spawnable
            for entry in entries:
                if entry.id and entry.id in spawnable_item_ids:
                    if not hasattr(entry, "_map_spawnable"):
                        entry._map_spawnable = set()
                    entry._map_spawnable.add(map_name)

        # Resolve crafting blacklists for each map
        from unturned_data.crafting_blacklist import resolve_crafting_blacklist

        crafting_blacklists = {}
        map_source_prefixes = {}
        for map_dir in args.map:
            map_name = map_dir.resolve().name
            bl = resolve_crafting_blacklist(map_dir)
            if bl is not None:
                crafting_blacklists[map_name] = bl
            # Track source prefixes for map-specific entries
            map_source_prefixes[map_name] = [f"_map_{map_name}/"]

    if args.format == "json":
        output = entries_to_json(entries)
    elif args.format == "web":
        supplementary: dict[str, str] = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        output = entries_to_web_json(entries, supplementary_guids=supplementary)
    elif args.format == "crafting":
        supplementary = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        output = entries_to_crafting_json(
            entries, supplementary_guids=supplementary,
            crafting_blacklists=crafting_blacklists if args.map else None,
            map_source_prefixes=map_source_prefixes if args.map else None,
            indent=2,
        )
    else:
        # Build supplementary GUID map from .asset files and .dat comments.
        # Priority: asset names (lowest) < comment names < entry names (highest).
        # We merge asset names first, then comment names on top, so comments
        # override asset names.  Entry names override both (handled in
        # build_guid_map).
        supplementary = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        output = entries_to_markdown(entries, supplementary_guids=supplementary)

    print(output)
