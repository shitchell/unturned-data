"""Warning system for uncovered .dat fields."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from unturned_data.models.properties.base import (
    GLOBAL_HANDLED,
    GLOBAL_IGNORE,
    is_globally_handled,
)

logger = logging.getLogger(__name__)


class FieldCoverageReport:
    """Tracks which .dat fields are not consumed by any model.

    Used during export to detect fields that may need new properties
    models or additions to existing ones.
    """

    def __init__(self) -> None:
        self.uncovered: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.total_entries: int = 0
        self.entries_with_uncovered: int = 0

    def check_entry(
        self,
        item_type: str,
        raw: dict[str, Any],
        consumed_keys: set[str],
        properties_cls: type | None = None,
    ) -> list[str]:
        """Check a single entry for uncovered fields.

        Args:
            item_type: The item's Type value (e.g. "Gun", "Melee").
            raw: The parsed .dat dict.
            consumed_keys: Keys already consumed by the properties model.
            properties_cls: The ItemProperties subclass (for type-specific ignores).

        Returns:
            List of uncovered field names.
        """
        self.total_entries += 1
        uncovered: list[str] = []

        for key in raw:
            if key in consumed_keys:
                continue
            if is_globally_handled(key):
                continue
            if key in GLOBAL_IGNORE:
                continue
            if (
                properties_cls
                and hasattr(properties_cls, "is_ignored")
                and properties_cls.is_ignored(key)
            ):
                continue
            uncovered.append(key)

        if uncovered:
            self.entries_with_uncovered += 1
            for field in uncovered:
                self.uncovered[item_type][field] += 1

        return uncovered

    def format_warnings(self) -> str:
        """Format all uncovered fields as a human-readable warning string."""
        if not self.uncovered:
            return ""
        lines: list[str] = []
        for item_type, fields in sorted(self.uncovered.items()):
            field_list = ", ".join(sorted(fields.keys()))
            total = sum(fields.values())
            lines.append(
                f"WARNING: {len(fields)} uncovered field(s) in {item_type} "
                f"entries ({total} occurrences): {field_list}"
            )
        return "\n".join(lines)

    def has_uncovered(self) -> bool:
        """Return True if any uncovered fields were found."""
        return bool(self.uncovered)
