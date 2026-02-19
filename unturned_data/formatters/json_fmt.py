"""
JSON formatter for Unturned bundle entries.

Serializes entries into a nested JSON tree reflecting the directory
hierarchy.  Each directory level is an object keyed by subdirectory
name.  Entries at each level live in an ``_entries`` array.

Example structure::

    {
      "Animals": {
        "_entries": [{"name": "Bear", ...}, ...]
      },
      "Items": {
        "_entries": [...],
        "Backpacks": {
          "_entries": [{"name": "Alicepack", ...}, ...]
        }
      }
    }
"""
from __future__ import annotations

import json
from typing import Any

from unturned_data.models import BundleEntry


def entries_to_json(entries: list[BundleEntry], indent: int = 2) -> str:
    """Convert entries to a nested JSON string.

    Entries are placed into a tree based on their ``category_parts``
    (derived from ``source_path``).  Within each ``_entries`` array,
    entries are sorted by ``(name, id)`` for deterministic output.
    """
    if not entries:
        return json.dumps({}, indent=indent, ensure_ascii=False)

    tree: dict[str, Any] = {}

    for entry in entries:
        parts = entry.category_parts
        node = tree
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        if "_entries" not in node:
            node["_entries"] = []
        node["_entries"].append(entry.to_dict())

    # Sort _entries arrays at every level
    _sort_entries(tree)

    return json.dumps(tree, indent=indent, sort_keys=True, ensure_ascii=False)


def _sort_entries(node: dict[str, Any]) -> None:
    """Recursively sort ``_entries`` arrays by (name, id)."""
    if "_entries" in node:
        node["_entries"].sort(key=lambda e: (e.get("name", ""), e.get("id", 0)))
    for key, value in node.items():
        if key != "_entries" and isinstance(value, dict):
            _sort_entries(value)
