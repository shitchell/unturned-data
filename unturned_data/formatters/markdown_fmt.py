"""
Markdown formatter for Unturned bundle entries.

Organizes entries by directory hierarchy, using heading levels that
mirror the folder structure.  Within each directory node, entries are
grouped by model class so each group uses appropriate columns.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from unturned_data.models import BundleEntry


# Maps class name -> plural display name for sub-grouping within directories
_DISPLAY_NAMES: dict[str, str] = {
    "Gun": "Guns",
    "MeleeWeapon": "Melee Weapons",
    "Consumeable": "Consumeables",
    "Clothing": "Clothing",
    "Throwable": "Throwables",
    "BarricadeItem": "Barricades",
    "StructureItem": "Structures",
    "Magazine": "Magazines",
    "Attachment": "Attachments",
    "Vehicle": "Vehicles",
    "Animal": "Animals",
    "GenericEntry": "Other",
}


def build_guid_map(
    entries: list[BundleEntry],
    supplementary: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a GUID -> name mapping from all entries.

    Skips entries with empty GUIDs.

    If *supplementary* is provided, its entries are included but at
    lower priority than entry names (which come from English.dat and
    are the most human-readable).

    Intended merge priority: entry names > supplementary names.
    The caller should pre-merge comment names and asset names into
    the supplementary map in the desired priority order.
    """
    guid_map: dict[str, str] = {}
    # Start with supplementary (lower priority)
    if supplementary:
        guid_map.update(supplementary)
    # Entry names override supplementary
    for entry in entries:
        if entry.guid:
            guid_map[entry.guid] = entry.name
    return guid_map


def _escape_pipe(value: str) -> str:
    """Escape pipe characters for markdown table cells."""
    return value.replace("|", "\\|")


# ---------------------------------------------------------------------------
# Tree structure for directory hierarchy
# ---------------------------------------------------------------------------

@dataclass
class _TreeNode:
    """A node in the directory tree."""
    entries: list[BundleEntry] = field(default_factory=list)
    children: dict[str, "_TreeNode"] = field(default_factory=dict)


def _build_tree(entries: list[BundleEntry]) -> _TreeNode:
    """Build a tree from entries based on their category_parts."""
    root = _TreeNode()
    for entry in entries:
        node = root
        for part in entry.category_parts:
            if part not in node.children:
                node.children[part] = _TreeNode()
            node = node.children[part]
        node.entries.append(entry)
    return root


def _render_table(
    group_entries: list[BundleEntry],
    guid_map: dict[str, str],
) -> str:
    """Render a markdown table for a list of same-class entries."""
    group_entries.sort(key=lambda e: (e.name, e.id))

    columns = group_entries[0].markdown_columns()
    all_cells: list[list[str]] = []
    for entry in group_entries:
        all_cells.append(entry.markdown_row(guid_map))

    # Drop columns that are empty/zero in >80% of rows (keep Name always)
    keep = _non_empty_columns(columns, all_cells)
    columns = [columns[i] for i in keep]
    all_cells = [[row[i] for i in keep] for row in all_cells]

    # Build table
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"

    rows: list[str] = []
    for cells in all_cells:
        escaped = [_escape_pipe(str(cell)) for cell in cells]
        rows.append("| " + " | ".join(escaped) + " |")

    return f"{header}\n{separator}\n" + "\n".join(rows)


def _render_node(
    node: _TreeNode,
    guid_map: dict[str, str],
    depth: int,
    sections: list[str],
) -> None:
    """Recursively render a tree node into markdown sections."""
    # Render entries at this level (grouped by model class)
    if node.entries:
        # Group by class name
        groups: dict[str, list[BundleEntry]] = defaultdict(list)
        for entry in node.entries:
            groups[type(entry).__name__].append(entry)

        sorted_class_names = sorted(
            groups.keys(),
            key=lambda cn: _DISPLAY_NAMES.get(cn, cn),
        )

        for class_name in sorted_class_names:
            group_entries = groups[class_name]
            # If multiple classes share this directory, add a type label
            if len(sorted_class_names) > 1:
                display = _DISPLAY_NAMES.get(class_name, class_name)
                sections.append(f"**{display}**\n")
            sections.append(_render_table(group_entries, guid_map))

    # Recurse into children (sorted alphabetically)
    for name in sorted(node.children.keys()):
        child = node.children[name]
        display_name = name.replace("_", " ")
        heading = "#" * (depth + 2)  # ## for depth 0, ### for depth 1, etc.
        sections.append(f"{heading} {display_name}")
        _render_node(child, guid_map, depth + 1, sections)


def entries_to_markdown(
    entries: list[BundleEntry],
    supplementary_guids: dict[str, str] | None = None,
) -> str:
    """Convert entries to a markdown string with directory-based hierarchy.

    - Builds a GUID map for cross-references
    - Organizes entries into a tree matching the directory structure
    - Each directory level gets a heading (## for top, ### for sub, etc.)
    - Within each directory, entries are grouped by model class
    - Entries within groups sorted by (name, id)
    - Sparse columns (>80% empty) are auto-dropped
    - Pipe characters in cell values are escaped

    *supplementary_guids* is an optional map of extra GUID->name
    mappings (from .asset files and .dat file comments) that will
    be merged at lower priority than entry names.
    """
    if not entries:
        return ""

    guid_map = build_guid_map(entries, supplementary_guids)

    tree = _build_tree(entries)

    sections: list[str] = []
    _render_node(tree, guid_map, 0, sections)

    return "\n\n".join(sections) + "\n"


def _non_empty_columns(
    columns: list[str],
    rows: list[list[str]],
    threshold: float = 0.8,
) -> list[int]:
    """Return indices of columns that have non-empty values in enough rows.

    A column is kept if:
    - It's the first column (Name) -- always kept
    - More than (1 - threshold) of its values are non-empty/non-zero
    """
    if not rows:
        return list(range(len(columns)))

    keep: list[int] = []
    for i in range(len(columns)):
        if i == 0:
            keep.append(i)
            continue
        empty = 0
        for row in rows:
            val = row[i] if i < len(row) else ""
            if val in ("", "0", "0.0", "0/0", "0.0/0.0", "0.0/0.0/0.0"):
                empty += 1
        if empty / len(rows) < threshold:
            keep.append(i)
    return keep
