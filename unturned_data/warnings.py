"""Warning system for uncovered .dat fields and null field detection."""

from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from typing import Any

from unturned_data.models.properties.base import (
    GLOBAL_HANDLED,
    GLOBAL_IGNORE,
    ItemProperties,
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


class NullFieldReport:
    """Detects property fields that are None for ALL entries of a given type.

    After all entries are processed, this report identifies fields that were
    never populated from .dat files. This may indicate a misspelled field name,
    a removed game field, or schema drift.
    """

    def __init__(self) -> None:
        # {type: {field_name: count_of_non_none}}
        self.field_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.type_counts: dict[str, int] = defaultdict(int)

    def check_entry(
        self,
        item_type: str,
        properties: dict[str, Any],
        properties_cls: type[ItemProperties],
    ) -> None:
        """Record which fields have non-None values for this entry."""
        self.type_counts[item_type] += 1
        for field_name in properties_cls.model_fields:
            if field_name in properties and properties[field_name] is not None:
                self.field_counts[item_type][field_name] += 1

    def format_warnings(self) -> str:
        """Report fields that are None across ALL entries of a type."""
        from unturned_data.models.properties import PROPERTIES_REGISTRY

        lines: list[str] = []
        for item_type, count in sorted(self.type_counts.items()):
            if count == 0:
                continue
            props_cls = PROPERTIES_REGISTRY.get(item_type)
            if not props_cls:
                continue
            all_none_fields: list[str] = []
            for field_name in props_cls.model_fields:
                if field_name not in self.field_counts[item_type]:
                    all_none_fields.append(field_name)
            if all_none_fields:
                module = inspect.getmodule(props_cls)
                file_path = getattr(module, "__file__", "unknown")
                lines.append(
                    f"WARNING: {len(all_none_fields)} field(s) in {item_type} "
                    f"are None across all {count} entries: "
                    f"{', '.join(sorted(all_none_fields))}\n"
                    f"  -> Review: {file_path}"
                )
        return "\n".join(lines)

    def has_null_fields(self) -> bool:
        """Return True if any type has fields that are None everywhere."""
        from unturned_data.models.properties import PROPERTIES_REGISTRY

        for item_type, count in self.type_counts.items():
            if count == 0:
                continue
            props_cls = PROPERTIES_REGISTRY.get(item_type)
            if not props_cls:
                continue
            for field_name in props_cls.model_fields:
                if field_name not in self.field_counts[item_type]:
                    return True
        return False
