"""CLI entry point for the unturned-data tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unturned_data.exporter import discover_maps, export_schema_c
from unturned_data.categories import parse_entry
from unturned_data.loader import (
    collect_comment_guids_from_dir,
    walk_asset_files,
    walk_bundle_dir,
)
from unturned_data.formatters.markdown_fmt import entries_to_markdown
from unturned_data.models import BundleEntry


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="unturnedd",
        description="Parse Unturned server data and export as JSON or markdown.",
    )
    parser.add_argument(
        "server_root",
        type=Path,
        help="Path to the Unturned server root directory (contains Bundles/, Maps/, Servers/)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json). 'json' writes Schema C directory tree. 'markdown' prints to stdout.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output directory for JSON export (required for --format json)",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=None,
        metavar="NAME",
        help=(
            "Filter to a specific map by name (repeatable). "
            "If omitted, all discovered maps are included. "
            "Names are matched case-insensitively against discovered map directory names."
        ),
    )
    parser.add_argument(
        "--exclude",
        "-e",
        nargs="+",
        default=[],
        metavar="PATH",
        help="Exclude entries matching path segments.",
    )
    args = parser.parse_args(argv)

    server_root: Path = args.server_root.resolve()
    if not server_root.is_dir():
        print(f"Error: {server_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Locate base Bundles directory
    bundles_path = server_root / "Bundles"
    if not bundles_path.is_dir():
        print(
            f"Error: {bundles_path} not found. Is this an Unturned server root?",
            file=sys.stderr,
        )
        sys.exit(1)

    # Auto-discover maps
    all_maps = discover_maps(server_root)

    # Filter maps by --map flag if provided
    if args.map:
        map_names_lower = {m.lower() for m in args.map}
        selected_maps = [m for m in all_maps if m.name.lower() in map_names_lower]
        # Warn about unmatched names
        found_names = {m.name.lower() for m in selected_maps}
        for name in args.map:
            if name.lower() not in found_names:
                print(
                    f"Warning: map '{name}' not found. Available maps:",
                    file=sys.stderr,
                )
                for m in all_maps:
                    print(f"  - {m.name}", file=sys.stderr)
                break
    else:
        selected_maps = all_maps

    if args.format == "json":
        if not args.output:
            print("Error: --output is required for JSON format", file=sys.stderr)
            sys.exit(1)
        export_schema_c(
            base_bundles=bundles_path,
            map_dirs=selected_maps,
            output_dir=args.output.resolve(),
        )
        map_names_str = ", ".join(m.name for m in selected_maps) or "(none)"
        print(f"Export complete: {args.output}")
        print(f"Maps: {map_names_str}")

    elif args.format == "markdown":
        entries: list[BundleEntry] = []
        for raw, english, rel_path in walk_bundle_dir(bundles_path):
            if not raw:
                continue
            if args.exclude and _is_excluded(rel_path, args.exclude):
                continue
            entries.append(parse_entry(raw, english, rel_path))

        # Include entries from selected maps
        for map_dir in selected_maps:
            map_bundles = map_dir / "Bundles"
            if map_bundles.is_dir():
                for raw, english, rel_path in walk_bundle_dir(map_bundles):
                    if not raw:
                        continue
                    entries.append(parse_entry(raw, english, rel_path))

        supplementary: dict[str, str] = {}
        supplementary.update(walk_asset_files(bundles_path))
        supplementary.update(collect_comment_guids_from_dir(bundles_path))
        print(entries_to_markdown(entries, supplementary_guids=supplementary))


def _is_excluded(source_path: str, patterns: list[str]) -> bool:
    path_parts = source_path.split("/")
    for pattern in patterns:
        pat_parts = pattern.strip("/").split("/")
        for i in range(len(path_parts) - len(pat_parts) + 1):
            if path_parts[i : i + len(pat_parts)] == pat_parts:
                return True
    return False
