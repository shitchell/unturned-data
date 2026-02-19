"""CLI entry point for the unturned-data tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unturned_data.exporter import export_schema_c
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
        prog="unturned-data",
        description="Parse Unturned .dat bundle files and export data.",
    )
    parser.add_argument("path", type=Path, help="Path to a Bundles directory")
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
        type=Path,
        metavar="DIR",
        help="Path to a map directory (repeatable).",
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

    bundle_path: Path = args.path.resolve()
    if not bundle_path.is_dir():
        print(f"Error: {bundle_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        if not args.output:
            print("Error: --output is required for JSON format", file=sys.stderr)
            sys.exit(1)
        export_schema_c(
            base_bundles=bundle_path,
            map_dirs=[m.resolve() for m in (args.map or [])],
            output_dir=args.output.resolve(),
        )
        print(f"Export complete: {args.output}")

    elif args.format == "markdown":
        entries: list[BundleEntry] = []
        for raw, english, rel_path in walk_bundle_dir(bundle_path):
            if not raw:
                continue
            if args.exclude and _is_excluded(rel_path, args.exclude):
                continue
            entries.append(parse_entry(raw, english, rel_path))

        if args.map:
            for map_dir in args.map:
                map_bundles = map_dir / "Bundles"
                if map_bundles.is_dir():
                    for raw, english, rel_path in walk_bundle_dir(map_bundles):
                        if not raw:
                            continue
                        entries.append(parse_entry(raw, english, rel_path))

        supplementary: dict[str, str] = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        print(entries_to_markdown(entries, supplementary_guids=supplementary))


def _is_excluded(source_path: str, patterns: list[str]) -> bool:
    path_parts = source_path.split("/")
    for pattern in patterns:
        pat_parts = pattern.strip("/").split("/")
        for i in range(len(path_parts) - len(pat_parts) + 1):
            if path_parts[i : i + len(pat_parts)] == pat_parts:
                return True
    return False
