"""Extensible entry filter system.

Filters are predicates on BundleEntry objects. The CLI collects filters
from command-line flags, and the exporter/formatter applies them.

To add a new filter type:
1. Create a function that returns Callable[[BundleEntry], bool]
2. Add the corresponding CLI flag in cli.py
3. Append the filter to the filters list
"""

from __future__ import annotations

from typing import Callable

from unturned_data.models import BundleEntry

# Type alias for filter predicates
EntryFilter = Callable[[BundleEntry], bool]


def map_filter(map_names: set[str], spawnable_ids: dict[str, set[int]]) -> EntryFilter:
    """Filter entries to those available on specific maps.

    An entry passes if:
    - It's a map-specific entry (its origin map is in map_names), OR
    - Its ID is in the spawnable items for any of the named maps

    Args:
        map_names: Set of map names to filter to (case-sensitive, matched
            against map dir names)
        spawnable_ids: Dict mapping map_name -> set of spawnable item IDs
            on that map
    """

    def _filter(entry: BundleEntry) -> bool:
        for name in map_names:
            if name in spawnable_ids and entry.id in spawnable_ids[name]:
                return True
        return False

    return _filter


def apply_filters(
    entries: list[BundleEntry], filters: list[EntryFilter]
) -> list[BundleEntry]:
    """Apply all filters to an entry list. Entry must pass ALL filters."""
    if not filters:
        return entries
    return [e for e in entries if all(f(e) for f in filters)]
