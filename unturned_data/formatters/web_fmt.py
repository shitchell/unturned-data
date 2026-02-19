"""
Web-optimized JSON formatter for Unturned bundle entries.

Produces a flat list of table sections, each with a directory path,
column headers, and row arrays.  Designed for the interactive web
viewer at stuff.shitchell.com/unturned/.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from unturned_data.models import BundleEntry
from unturned_data.formatters.markdown_fmt import (
    _TreeNode,
    _build_tree,
    _non_empty_columns,
    build_guid_map,
    _DISPLAY_NAMES,
)


def entries_to_web_json(
    entries: list[BundleEntry],
    supplementary_guids: dict[str, str] | None = None,
    indent: int | None = None,
) -> str:
    """Convert entries to a web-optimized JSON string.

    Returns a JSON array of section objects, each with:

    - ``path``: directory path segments (e.g. ``["Items", "Guns"]``)
    - ``columns``: column header strings
    - ``rows``: array of arrays (one per entry, values match columns)
    - ``label``: (optional) type label when multiple classes share a dir

    Sparse columns (>80% empty) are auto-dropped.
    """
    if not entries:
        return json.dumps([], indent=indent, ensure_ascii=False)

    guid_map = build_guid_map(entries, supplementary_guids)
    tree = _build_tree(entries)

    sections: list[dict[str, Any]] = []
    _collect_sections(tree, guid_map, [], sections)

    return json.dumps(sections, indent=indent, ensure_ascii=False)


def _collect_sections(
    node: _TreeNode,
    guid_map: dict[str, str],
    path: list[str],
    sections: list[dict[str, Any]],
) -> None:
    """Recursively collect table sections from the tree."""
    if node.entries:
        groups: dict[str, list[BundleEntry]] = defaultdict(list)
        for entry in node.entries:
            groups[type(entry).__name__].append(entry)

        sorted_class_names = sorted(
            groups.keys(),
            key=lambda cn: _DISPLAY_NAMES.get(cn, cn),
        )

        for class_name in sorted_class_names:
            group_entries = groups[class_name]
            group_entries.sort(key=lambda e: (e.name, e.id))

            columns = group_entries[0].markdown_columns()
            all_rows: list[list[str]] = []
            for entry in group_entries:
                row = entry.markdown_row(guid_map)
                # Add Size if the entry has size_x/y and Size isn't already a column
                all_rows.append(row)

            # Drop sparse columns
            keep = _non_empty_columns(columns, all_rows)
            columns = [columns[i] for i in keep]
            all_rows = [[row[i] for i in keep] for row in all_rows]

            # Add Size column for entries that have it but don't show it
            if _should_add_size(group_entries, columns):
                columns.append("Size")
                for i, entry in enumerate(group_entries):
                    size = f"{entry.size_x}x{entry.size_y}" if entry.size_x or entry.size_y else ""
                    all_rows[i].append(size)

            # Add Maps column when any entry has _map_spawnable data
            if _should_add_maps(group_entries):
                columns.append("Maps")
                for i, entry in enumerate(group_entries):
                    maps = getattr(entry, "_map_spawnable", None) or set()
                    all_rows[i].append(", ".join(sorted(maps)))

            section: dict[str, Any] = {
                "path": list(path),
                "columns": columns,
                "rows": all_rows,
            }
            if len(sorted_class_names) > 1:
                section["label"] = _DISPLAY_NAMES.get(class_name, class_name)

            sections.append(section)

    for name in sorted(node.children.keys()):
        child = node.children[name]
        _collect_sections(child, guid_map, path + [name], sections)


def _should_add_size(entries: list[BundleEntry], columns: list[str]) -> bool:
    """Check if we should add a Size column (has size data, not already shown)."""
    if "Size" in columns:
        return False
    return any(e.size_x or e.size_y for e in entries)


def _should_add_maps(entries: list[BundleEntry]) -> bool:
    """Check if any entry has non-empty ``_map_spawnable`` data."""
    return any(getattr(e, "_map_spawnable", None) for e in entries)
