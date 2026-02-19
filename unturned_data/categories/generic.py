"""
Generic fallback model for unknown Unturned entry types.

Used when a Type value doesn't match any entry in the TYPE_REGISTRY.
Preserves the full raw dict for inspection.
"""
from __future__ import annotations

from typing import Any

from unturned_data.models import BundleEntry


class GenericEntry(BundleEntry):
    """Fallback for any Type not in the registry.

    Carries the full raw dict so nothing is lost.
    """

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> GenericEntry:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(**{f: getattr(base, f) for f in BundleEntry.model_fields})

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["raw"] = self.raw
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return BundleEntry.markdown_columns()

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return super().markdown_row(guid_map)
