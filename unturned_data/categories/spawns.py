"""
Category parser for Unturned spawn tables.

Handles three .dat format variants:
1. Legacy indexed: Tables N + Table_N_Spawn_ID / Table_N_Asset_ID
2. Modern block: Tables [...] with LegacySpawnId / LegacyAssetId / Guid
3. Workshop legacy: Same as #1 but in workshop map bundles
"""
from __future__ import annotations

from typing import Any

from unturned_data.models import BundleEntry, SpawnTable, SpawnTableEntry


def _parse_legacy_tables(raw: dict[str, Any]) -> list[SpawnTableEntry]:
    """Parse legacy Table_N_* indexed format."""
    count = int(raw.get("Tables", 0))
    entries: list[SpawnTableEntry] = []

    for i in range(count):
        spawn_ref = raw.get(f"Table_{i}_Spawn_ID")
        asset_ref = raw.get(f"Table_{i}_Asset_ID")
        weight = int(raw.get(f"Table_{i}_Weight", 10))

        if spawn_ref is not None:
            entries.append(SpawnTableEntry(
                ref_type="spawn", ref_id=int(spawn_ref), weight=weight,
            ))
        elif asset_ref is not None:
            entries.append(SpawnTableEntry(
                ref_type="asset", ref_id=int(asset_ref), weight=weight,
            ))

    return entries


def _parse_modern_tables(tables_list: list[Any]) -> list[SpawnTableEntry]:
    """Parse modern Tables [...] block format."""
    entries: list[SpawnTableEntry] = []

    for item in tables_list:
        if not isinstance(item, dict):
            continue

        weight = int(item.get("Weight", 10))

        if "LegacySpawnId" in item:
            entries.append(SpawnTableEntry(
                ref_type="spawn",
                ref_id=int(item["LegacySpawnId"]),
                weight=weight,
            ))
        elif "LegacyAssetId" in item:
            entries.append(SpawnTableEntry(
                ref_type="asset",
                ref_id=int(item["LegacyAssetId"]),
                weight=weight,
            ))
        elif "Guid" in item:
            entries.append(SpawnTableEntry(
                ref_type="guid",
                ref_guid=str(item["Guid"]).lower(),
                weight=weight,
            ))

    return entries


class SpawnTableCategory(SpawnTable):
    """Spawn table parsed from a .dat file."""

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> SpawnTableCategory:
        base = BundleEntry.from_raw(raw, english, source_path)

        tables_val = raw.get("Tables")

        if isinstance(tables_val, list):
            table_entries = _parse_modern_tables(tables_val)
        elif isinstance(tables_val, int):
            table_entries = _parse_legacy_tables(raw)
        else:
            table_entries = []

        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            table_entries=table_entries,
        )
