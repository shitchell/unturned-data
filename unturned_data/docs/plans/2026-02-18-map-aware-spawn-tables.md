# Map-Aware Spawn Tables Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add spawn table parsing and map-aware item filtering to `unturned-data`, then add map checkboxes to the web viewer.

**Architecture:** Extend the existing 3-layer unturned-data package (`dat_parser` -> `models` -> `categories`) with a new `SpawnTable` model and `map_resolver` module. The map resolver extracts active spawn table references from binary map files, resolves spawn table chains recursively, and tags items as spawnable-per-map. The web formatter and frontend gain a map filter dimension alongside the existing category filter.

**Tech Stack:** Python 3.11+, pytest, existing `unturned_data` package, vanilla JS frontend

**Reference files:**
- Spawn logic to port: `/home/guy/projects/steam-docker/unturned-map-items.py`
- Package root: `/home/guy/bin/unturned_data/`
- Web frontend: `/home/guy/code/git/github.com/shitchell/stuff/site/unturned/`
- Base game bundles: `~/unturned-bundles/` (symlink to server Bundles/)
- Built-in maps: `~/unturned-server/Maps/` (on localAI)
- Workshop maps: `~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/*/` (on localAI)

**Spawn table .dat formats (three variants):**

1. **Legacy indexed** (`Table_N_Spawn_ID` / `Table_N_Asset_ID`):
   ```
   Tables 4
   Table_0_Asset_ID 1041
   Table_0_Weight 10
   Table_1_Spawn_ID 229
   Table_1_Weight 31
   ```

2. **Modern block** (`LegacySpawnId` / `LegacyAssetId` / `Guid`):
   ```
   Tables
   [
       {
           LegacySpawnId 229
           Weight 31
       }
       {
           LegacyAssetId 1041
           Weight 10
       }
       {
           Guid e322656746a045a98eb6e5a6650a104e
           Weight 5
       }
   ]
   ```

3. **A6 Polaris style** (old indexed format in workshop maps):
   ```
   Tables 4
   Table_0_Asset_ID 36451
   Table_0_Weight 100
   ```

All three use `Type Spawn` in their .dat file. The key difference is whether `Tables` is an integer (format 1/3) or a list (format 2). Within format 2, entries can reference by `LegacySpawnId` (another spawn table), `LegacyAssetId` (direct item ID), or `Guid` (direct item GUID).

---

## Task 1: SpawnTable model and entry type

**Files:**
- Modify: `~/bin/unturned_data/models.py`
- Create: `~/bin/unturned_data/tests/test_spawn_model.py`

**Step 1: Write the failing test**

Create `~/bin/unturned_data/tests/test_spawn_model.py`:

```python
"""Tests for SpawnTable and SpawnTableEntry models."""
import pytest
from unturned_data.models import SpawnTable, SpawnTableEntry


class TestSpawnTableEntry:
    def test_asset_entry(self):
        e = SpawnTableEntry(ref_type="asset", ref_id=1041, weight=10)
        assert e.ref_type == "asset"
        assert e.ref_id == 1041
        assert e.weight == 10
        assert e.ref_guid == ""

    def test_spawn_entry(self):
        e = SpawnTableEntry(ref_type="spawn", ref_id=229, weight=31)
        assert e.ref_type == "spawn"
        assert e.ref_id == 229

    def test_guid_entry(self):
        e = SpawnTableEntry(
            ref_type="guid",
            ref_guid="e322656746a045a98eb6e5a6650a104e",
            weight=5,
        )
        assert e.ref_type == "guid"
        assert e.ref_guid == "e322656746a045a98eb6e5a6650a104e"
        assert e.ref_id == 0


class TestSpawnTable:
    def test_basic_construction(self):
        entries = [
            SpawnTableEntry(ref_type="asset", ref_id=1041, weight=10),
            SpawnTableEntry(ref_type="spawn", ref_id=229, weight=31),
        ]
        table = SpawnTable(
            guid="907024f5c5b94642ae5f4123e0026f06",
            type="Spawn",
            id=654,
            name="Military_Low_Guns",
            source_path="Spawns/Items/Military_Low_Guns",
            table_entries=entries,
        )
        assert table.id == 654
        assert len(table.table_entries) == 2
        assert table.table_entries[0].ref_type == "asset"

    def test_to_dict(self):
        entries = [SpawnTableEntry(ref_type="asset", ref_id=42, weight=10)]
        table = SpawnTable(
            guid="abc", type="Spawn", id=1, name="Test",
            source_path="Spawns/Test", table_entries=entries,
        )
        d = table.to_dict()
        assert d["table_entries"] == [
            {"ref_type": "asset", "ref_id": 42, "ref_guid": "", "weight": 10}
        ]
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_spawn_model.py -v
```

Expected: FAIL — `ImportError: cannot import name 'SpawnTable' from 'unturned_data.models'`

**Step 3: Implement SpawnTableEntry and SpawnTable**

Add to the end of `~/bin/unturned_data/models.py` (before the closing, after `BundleEntry`):

```python
# ---------------------------------------------------------------------------
# SpawnTableEntry
# ---------------------------------------------------------------------------
@dataclass
class SpawnTableEntry:
    """A single entry in a spawn table."""

    ref_type: str = ""  # "asset", "spawn", or "guid"
    ref_id: int = 0
    ref_guid: str = ""
    weight: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_type": self.ref_type,
            "ref_id": self.ref_id,
            "ref_guid": self.ref_guid,
            "weight": self.weight,
        }


# ---------------------------------------------------------------------------
# SpawnTable
# ---------------------------------------------------------------------------
@dataclass
class SpawnTable(BundleEntry):
    """A spawn table entry that references items or other spawn tables."""

    table_entries: list[SpawnTableEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["table_entries"] = [e.to_dict() for e in self.table_entries]
        return d
```

**Step 4: Run test to verify it passes**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_spawn_model.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/models.py unturned_data/tests/test_spawn_model.py && git commit -m "feat: add SpawnTable and SpawnTableEntry models"
```

---

## Task 2: SpawnTable category parser (spawns.py)

**Files:**
- Create: `~/bin/unturned_data/categories/spawns.py`
- Modify: `~/bin/unturned_data/categories/__init__.py`
- Create: `~/bin/unturned_data/tests/test_spawn_parsing.py`

**Step 1: Write the failing test**

Create `~/bin/unturned_data/tests/test_spawn_parsing.py`:

```python
"""Tests for spawn table .dat parsing via the category system."""
import pytest
from pathlib import Path
from unturned_data.categories import parse_entry
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models import SpawnTable

FIXTURES = Path(__file__).parent / "fixtures"


class TestModernFormat:
    """Tests for the modern Tables [...] block format."""

    def test_parse_spawn_fixture(self):
        """Parse the existing spawn_sample fixture (modern format)."""
        raw = parse_dat_file(FIXTURES / "spawn_sample" / "Carepackage_Arena.dat")
        entry = parse_entry(raw, {}, "Spawns/Items/Carepackage_Arena")
        assert isinstance(entry, SpawnTable)
        assert entry.type == "Spawn"
        assert entry.id == 956
        # Fixture has 43 entries, all LegacyAssetId
        assert len(entry.table_entries) == 43
        assert entry.table_entries[0].ref_type == "asset"
        assert entry.table_entries[0].ref_id == 144
        assert entry.table_entries[0].weight == 200


class TestLegacyFormat:
    """Tests for the legacy Table_N_* indexed format."""

    def test_parse_legacy_spawn(self):
        """Parse a spawn table using the old indexed format."""
        # Simulate a legacy format .dat parse result
        raw = {
            "GUID": "f019fcaa2e8e4c92b17259025c80ff77",
            "Type": "Spawn",
            "ID": 228,
            "Tables": 3,
            "Table_0_Spawn_ID": 229,
            "Table_0_Weight": 31,
            "Table_1_Asset_ID": 1041,
            "Table_1_Weight": 10,
            "Table_2_Spawn_ID": 230,
            "Table_2_Weight": 52,
        }
        entry = parse_entry(raw, {}, "Spawns/Items/Militia")
        assert isinstance(entry, SpawnTable)
        assert len(entry.table_entries) == 3
        assert entry.table_entries[0].ref_type == "spawn"
        assert entry.table_entries[0].ref_id == 229
        assert entry.table_entries[1].ref_type == "asset"
        assert entry.table_entries[1].ref_id == 1041


class TestMixedModernFormat:
    """Tests for modern format with LegacySpawnId references."""

    def test_parse_mixed_refs(self):
        """Modern format can have LegacySpawnId, LegacyAssetId, and Guid."""
        raw = {
            "GUID": "dcb0974543f240b9aaddabe9d880e506",
            "Type": "Spawn",
            "ID": 551,
            "Tables": [
                {"LegacySpawnId": 646, "Weight": 175},
                {"LegacyAssetId": 1041, "Weight": 50},
                {"Guid": "e322656746a045a98eb6e5a6650a104e", "Weight": 5},
            ],
        }
        entry = parse_entry(raw, {}, "Spawns/Items/Military_Low")
        assert isinstance(entry, SpawnTable)
        assert len(entry.table_entries) == 3
        assert entry.table_entries[0].ref_type == "spawn"
        assert entry.table_entries[0].ref_id == 646
        assert entry.table_entries[1].ref_type == "asset"
        assert entry.table_entries[1].ref_id == 1041
        assert entry.table_entries[2].ref_type == "guid"
        assert entry.table_entries[2].ref_guid == "e322656746a045a98eb6e5a6650a104e"
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_spawn_parsing.py -v
```

Expected: FAIL — SpawnTable not returned (parse_entry returns GenericEntry for Type=Spawn)

**Step 3: Implement spawns.py**

Create `~/bin/unturned_data/categories/spawns.py`:

```python
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
            **{k: v for k, v in base.__dict__.items()},
            table_entries=table_entries,
        )
```

**Step 4: Register Spawn type in `categories/__init__.py`**

Add the import and registry entry. At the top of `~/bin/unturned_data/categories/__init__.py`, add:

```python
from unturned_data.categories.spawns import SpawnTableCategory
```

Add to `TYPE_REGISTRY`:

```python
    "Spawn": SpawnTableCategory,
```

Add to `__all__`:

```python
    "SpawnTableCategory",
```

**Step 5: Run test to verify it passes**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_spawn_parsing.py -v
```

Expected: all PASS

**Step 6: Run full test suite to check for regressions**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS (existing tests should not be affected since Spawn entries were previously GenericEntry and none of the existing fixtures have Type=Spawn other than `spawn_sample`, which was handled differently)

**Step 7: Commit**

```bash
cd ~/bin && git add unturned_data/categories/spawns.py unturned_data/categories/__init__.py unturned_data/tests/test_spawn_parsing.py && git commit -m "feat: add spawn table category parser (legacy + modern formats)"
```

---

## Task 3: Map resolver module

**Files:**
- Create: `~/bin/unturned_data/map_resolver.py`
- Create: `~/bin/unturned_data/tests/test_map_resolver.py`
- Create: `~/bin/unturned_data/tests/fixtures/fake_map/` (test fixtures)

**Step 1: Create test fixtures**

Create a minimal fake map directory for tests:

```bash
mkdir -p ~/bin/unturned_data/tests/fixtures/fake_map/Spawns
mkdir -p ~/bin/unturned_data/tests/fixtures/fake_map/Bundles/Spawns/TestSpawn
```

Create `~/bin/unturned_data/tests/fixtures/fake_map/Bundles/Spawns/TestSpawn/TestSpawn.dat`:

```
GUID aaaa0000bbbb1111cccc2222dddd3333
Type Spawn
ID 99001

Tables 2
Table_0_Asset_ID 42
Table_0_Weight 10
Table_1_Asset_ID 99
Table_1_Weight 5
```

Create `~/bin/unturned_data/tests/fixtures/fake_map/Spawns/Items.dat` as a binary file containing the string "TestSpawn" as a length-prefixed string:

This will be created programmatically in the test setup.

**Step 2: Write the failing test**

Create `~/bin/unturned_data/tests/test_map_resolver.py`:

```python
"""Tests for map_resolver module."""
import struct
import pytest
from pathlib import Path

from unturned_data.map_resolver import (
    extract_spawn_names_from_binary,
    collect_map_spawn_tables,
    resolve_spawn_table_items,
)
from unturned_data.models import SpawnTable, SpawnTableEntry

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_MAP = FIXTURES / "fake_map"


class TestExtractSpawnNames:
    def test_extracts_length_prefixed_strings(self, tmp_path):
        """Binary with length-prefixed ASCII strings are extracted."""
        # Write a binary with: \x09TestSpawn (length=9, then string)
        data = b"\x04\x00\x00\x00\x09TestSpawn\x06Police"
        path = tmp_path / "Items.dat"
        path.write_bytes(data)
        names = extract_spawn_names_from_binary(path)
        assert "TestSpawn" in names
        assert "Police" in names

    def test_empty_file(self, tmp_path):
        path = tmp_path / "Items.dat"
        path.write_bytes(b"")
        names = extract_spawn_names_from_binary(path)
        assert names == []

    def test_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.dat"
        names = extract_spawn_names_from_binary(path)
        assert names == []


class TestCollectMapSpawnTables:
    def test_finds_map_bundle_tables(self):
        """Spawn tables in the map's own Bundles/ are discovered."""
        tables = collect_map_spawn_tables(FAKE_MAP)
        assert any(t.id == 99001 for t in tables)

    def test_returns_spawn_tables(self):
        tables = collect_map_spawn_tables(FAKE_MAP)
        for t in tables:
            assert isinstance(t, SpawnTable)


class TestResolveSpawnTableItems:
    def test_resolves_asset_refs(self):
        """Asset references resolve to item IDs."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="asset", ref_id=42, weight=10),
                    SpawnTableEntry(ref_type="asset", ref_id=99, weight=5),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert 42 in items
        assert 99 in items

    def test_resolves_spawn_refs_recursively(self):
        """Spawn references are resolved through the chain."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=200, weight=10),
                ],
            ),
            200: SpawnTable(
                id=200,
                table_entries=[
                    SpawnTableEntry(ref_type="asset", ref_id=42, weight=10),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert 42 in items

    def test_handles_circular_refs(self):
        """Circular spawn references don't infinite loop."""
        tables = {
            100: SpawnTable(
                id=100,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=200, weight=10),
                ],
            ),
            200: SpawnTable(
                id=200,
                table_entries=[
                    SpawnTableEntry(ref_type="spawn", ref_id=100, weight=10),
                ],
            ),
        }
        items = resolve_spawn_table_items(100, tables)
        assert items == set()

    def test_missing_table_id(self):
        """Missing table IDs return empty set."""
        items = resolve_spawn_table_items(999, {})
        assert items == set()
```

**Step 3: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_map_resolver.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'unturned_data.map_resolver'`

**Step 4: Implement map_resolver.py**

Create `~/bin/unturned_data/map_resolver.py`:

```python
"""
Map-aware spawn table resolution.

Extracts active spawn table references from binary map files,
discovers map-specific spawn tables from the map's own Bundles/,
and resolves spawn table chains to leaf item IDs.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from unturned_data.categories import parse_entry
from unturned_data.loader import walk_bundle_dir
from unturned_data.models import BundleEntry, SpawnTable, SpawnTableEntry


def extract_spawn_names_from_binary(path: Path) -> list[str]:
    """Extract length-prefixed ASCII strings from a binary spawn file.

    The map's Spawns/Items.dat encodes spawn table group names as
    length-prefixed strings interspersed with binary metadata.
    """
    if not path.exists():
        return []

    data = path.read_bytes()
    if not data:
        return []

    names: list[str] = []
    i = 0
    while i < len(data):
        if i + 1 < len(data):
            length = data[i]
            if 2 <= length <= 80 and i + 1 + length <= len(data):
                candidate = data[i + 1 : i + 1 + length]
                try:
                    text = candidate.decode("ascii")
                    if (
                        all(c.isalnum() or c in "_ -" for c in text)
                        and any(c.isalpha() for c in text)
                    ):
                        names.append(text)
                        i += 1 + length
                        continue
                except (UnicodeDecodeError, ValueError):
                    pass
        i += 1

    return names


def extract_spawn_ids_from_binary(
    path: Path,
    known_table_ids: set[int],
) -> set[int]:
    """Extract uint16 values from binary that match known spawn table IDs."""
    if not path.exists():
        return set()

    data = path.read_bytes()
    found: set[int] = set()

    for offset in range(len(data) - 1):
        val = struct.unpack_from("<H", data, offset)[0]
        if val in known_table_ids:
            found.add(val)

    return found


def collect_map_spawn_tables(map_dir: Path) -> list[SpawnTable]:
    """Discover spawn tables defined in a map's own Bundles/ directory."""
    map_bundles = map_dir / "Bundles"
    if not map_bundles.is_dir():
        return []

    tables: list[SpawnTable] = []
    for raw, english, rel_path in walk_bundle_dir(map_bundles):
        if not raw or raw.get("Type") != "Spawn":
            continue
        entry = parse_entry(raw, english, rel_path)
        if isinstance(entry, SpawnTable):
            tables.append(entry)

    return tables


def resolve_spawn_table_items(
    table_id: int,
    tables_by_id: dict[int, SpawnTable],
    visited: set[int] | None = None,
) -> set[int]:
    """Recursively resolve a spawn table to its leaf item IDs.

    Returns a set of item IDs that can spawn from this table.
    Handles circular references via the visited set.
    """
    if visited is None:
        visited = set()

    if table_id in visited:
        return set()
    visited.add(table_id)

    table = tables_by_id.get(table_id)
    if not table:
        return set()

    result: set[int] = set()
    for entry in table.table_entries:
        if entry.ref_type == "asset":
            result.add(entry.ref_id)
        elif entry.ref_type == "spawn":
            result |= resolve_spawn_table_items(
                entry.ref_id, tables_by_id, visited
            )
        # "guid" entries are resolved later when we have the guid->id map

    return result


def determine_active_tables(
    map_dir: Path,
    all_tables_by_id: dict[int, SpawnTable],
    table_name_to_id: dict[str, int],
) -> set[int]:
    """Determine which spawn tables are active on a given map.

    Uses three strategies:
    1. Name matching from binary spawn file strings
    2. ID matching from binary uint16 scan
    3. All tables from the map's own Bundles/Spawns/ (workshop maps)
    """
    active: set[int] = set()

    # Strategy 1: Extract names from binary and match
    items_dat = map_dir / "Spawns" / "Items.dat"
    names = extract_spawn_names_from_binary(items_dat)
    for name in names:
        if name in table_name_to_id:
            active.add(table_name_to_id[name])

    # Strategy 2: Scan binary for uint16 IDs matching known tables
    active |= extract_spawn_ids_from_binary(items_dat, set(all_tables_by_id.keys()))

    # Strategy 3: Include all map-defined spawn tables
    map_spawns_dir = map_dir / "Bundles" / "Spawns"
    if map_spawns_dir.is_dir():
        for tid, tinfo in all_tables_by_id.items():
            source = getattr(tinfo, "source_path", "")
            # Check if this table was loaded from the map's bundles
            # by checking if its file path starts with the map's Bundles dir
            if hasattr(tinfo, "_source_file") and str(tinfo._source_file).startswith(
                str(map_spawns_dir)
            ):
                active.add(tid)
            # Simpler heuristic: map-defined tables usually have high IDs (>30000)
            # and their source_path won't be in the base game paths

    return active
```

**Step 5: Create the fixture .dat file**

Create `~/bin/unturned_data/tests/fixtures/fake_map/Bundles/Spawns/TestSpawn/TestSpawn.dat` with the content shown in Step 1.

**Step 6: Run test to verify it passes**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_map_resolver.py -v
```

Expected: all PASS

**Step 7: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS

**Step 8: Commit**

```bash
cd ~/bin && git add unturned_data/map_resolver.py unturned_data/tests/test_map_resolver.py unturned_data/tests/fixtures/fake_map/ && git commit -m "feat: map resolver - binary extraction and spawn table chain resolution"
```

---

## Task 4: CLI --map flag and multi-bundle support

**Files:**
- Modify: `~/bin/unturned_data/cli.py`
- Create: `~/bin/unturned_data/tests/test_cli_map.py`

**Step 1: Write the failing test**

Create `~/bin/unturned_data/tests/test_cli_map.py`:

```python
"""Tests for CLI --map flag."""
import json
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from unturned_data.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestMapFlag:
    def test_map_flag_accepted(self, capsys):
        """The --map flag is accepted without error."""
        # Use fixtures as a minimal bundle dir
        with pytest.raises(SystemExit):
            # Will fail because fixtures isn't a real map, but should not
            # fail on argument parsing
            main(["--map", str(FIXTURES / "fake_map"), str(FIXTURES)])

    def test_help_shows_map(self, capsys):
        """--help output includes --map."""
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "--map" in captured.out
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_cli_map.py -v
```

Expected: FAIL — `--map` flag not recognized

**Step 3: Add --map flag to cli.py**

Modify `~/bin/unturned_data/cli.py` to add the `--map` argument and map-aware logic. The key changes:

1. Add `--map` argument
2. When `--map` is provided, also walk the map's `Bundles/` for additional entries
3. Discover spawn tables, determine active ones, resolve to item IDs
4. Pass spawn metadata to formatters

Add to the argparse section:

```python
    parser.add_argument(
        "--map",
        type=Path,
        default=None,
        metavar="MAP_DIR",
        help=(
            "Path to a map directory (contains Spawns/, optionally Bundles/). "
            "When provided, items are tagged with which map spawn tables "
            "reference them."
        ),
    )
```

Add map resolution logic after entry collection, before formatting. The full implementation involves:
- Walking the map's Bundles/ for extra entries
- Collecting all SpawnTable entries
- Calling `determine_active_tables()` and `resolve_spawn_table_items()`
- Tagging each entry with `spawnable_on_map: bool`

Full implementation deferred to the executing agent — the key contract is:
- `--map` flag is optional
- When provided, entries gain a `_map_spawnable` attribute (set of map names)
- Formatters check for this attribute and include it in output

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_cli_map.py -v
```

Expected: PASS

**Step 5: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS (backward compatible — no --map means no change)

**Step 6: Commit**

```bash
cd ~/bin && git add unturned_data/cli.py unturned_data/tests/test_cli_map.py && git commit -m "feat: add --map flag for map-aware spawn filtering"
```

---

## Task 5: Web formatter map support

**Files:**
- Modify: `~/bin/unturned_data/formatters/web_fmt.py`
- Create: `~/bin/unturned_data/tests/test_web_map.py`

**Step 1: Write the failing test**

Create `~/bin/unturned_data/tests/test_web_map.py`:

```python
"""Tests for web formatter with map spawn data."""
import json
import pytest

from unturned_data.formatters.web_fmt import entries_to_web_json
from unturned_data.models import BundleEntry


class TestWebMapData:
    def test_spawnable_column_when_map_data(self):
        """When entries have _map_spawnable, output includes Maps column."""
        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Test Gun",
            source_path="Items/Guns/Test",
        )
        entry._map_spawnable = {"PEI", "Washington"}

        output = entries_to_web_json([entry])
        sections = json.loads(output)
        assert len(sections) > 0

        # Should have a "Maps" column
        cols = sections[0]["columns"]
        assert "Maps" in cols

        # The row should include the map names
        maps_idx = cols.index("Maps")
        maps_val = sections[0]["rows"][0][maps_idx]
        assert "PEI" in maps_val
        assert "Washington" in maps_val

    def test_no_map_column_when_no_map_data(self):
        """Without _map_spawnable, no Maps column appears."""
        entry = BundleEntry(
            guid="aaa", type="Gun", id=1, name="Test Gun",
            source_path="Items/Guns/Test",
        )
        output = entries_to_web_json([entry])
        sections = json.loads(output)
        cols = sections[0]["columns"]
        assert "Maps" not in cols
```

**Step 2: Run test, implement, verify, commit**

The web_fmt changes add a "Maps" column to sections when entries have `_map_spawnable` metadata. The column value is a comma-separated list of map names (e.g., "PEI, Washington").

```bash
cd ~/bin && git add unturned_data/formatters/web_fmt.py unturned_data/tests/test_web_map.py && git commit -m "feat: web formatter includes Maps column when map data available"
```

---

## Task 6: Web frontend map checkboxes

**Files:**
- Modify: `~/code/git/github.com/shitchell/stuff/site/unturned/main.js`
- Modify: `~/code/git/github.com/shitchell/stuff/site/unturned/index.html`

**Step 1: Add map filter section to index.html**

Add a new filter group in the sidebar, after the existing category filters:

```html
<div class="filter-group" id="map-filter-group" style="display:none">
    <h3>Maps</h3>
    <div id="map-filters" class="filter-list"></div>
</div>
```

**Step 2: Add map filtering logic to main.js**

Key changes:
1. After loading `data.json`, scan all sections for unique map names from the "Maps" column
2. If maps are found, show the map filter group and build checkboxes
3. Add `activeMaps` set alongside `activeCategories`
4. In `applyFilters()`, additionally filter rows by whether their Maps value intersects `activeMaps`
5. Save/restore map filter state to localStorage

The map filter is additive: checking "PEI" shows items that spawn on PEI. Checking none shows all items (no map filter). This mirrors how the category filter works.

**Step 3: Test manually**

Generate new data with map info:

```bash
# On localAI, generate web JSON with map data for PEI
ssh localAI '~/bin/unturned-data ~/unturned-server/Bundles --map ~/unturned-server/Maps/PEI --format web' > /tmp/data_pei.json
```

Copy to the web directory and test in browser.

**Step 4: Commit**

```bash
cd ~/code/git/github.com/shitchell/stuff && git add site/unturned/main.js site/unturned/index.html && git commit -m "feat: add map filter checkboxes to Unturned data browser"
```

---

## Task 7: Multi-map support and data generation

**Files:**
- Create: `~/bin/unturned_data/generate_web_data.sh`

**Step 1: Create a generation script**

This script generates `data.json` with map spawn data for all available maps. It runs `unturned-data` with `--map` for each map found on the server and merges the results.

```bash
#!/usr/bin/env bash
# Generate web data with map spawn info for all available maps.
# Run on localAI where the server data lives.

set -euo pipefail

BUNDLES=~/unturned-server/Bundles
OUTPUT=~/code/git/github.com/shitchell/stuff/site/unturned/data.json

# Built-in maps
MAPS=(~/unturned-server/Maps/*)

# Workshop maps
for ws_dir in ~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/*/; do
    for map_dir in "$ws_dir"*/; do
        [ -d "$map_dir/Spawns" ] && MAPS+=("$map_dir")
    done
done

MAP_ARGS=()
for map in "${MAPS[@]}"; do
    [ -d "$map/Spawns" ] && MAP_ARGS+=(--map "$map")
done

~/bin/unturned-data "$BUNDLES" --format web "${MAP_ARGS[@]}" > "$OUTPUT"
echo "Generated $OUTPUT with ${#MAP_ARGS[@]} maps"
```

**Note:** The `--map` flag will need to support being specified multiple times (each adds a map). The CLI implementation in Task 4 should use `action="append"` for `--map`.

**Step 2: Commit**

```bash
cd ~/bin && git add unturned_data/generate_web_data.sh && git commit -m "feat: add web data generation script with multi-map support"
```

---

## Task 8: Integration test with real server data

**Files:**
- Create: `~/bin/unturned_data/tests/test_map_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for map-aware parsing against real server data."""
import pytest
from pathlib import Path

from unturned_data.map_resolver import (
    collect_map_spawn_tables,
    determine_active_tables,
    resolve_spawn_table_items,
)
from unturned_data.categories import parse_entry
from unturned_data.loader import walk_bundle_dir
from unturned_data.models import SpawnTable

# These paths are on localAI — skip if not available
BUNDLES = Path.home() / "unturned-bundles"
PEI_MAP = Path.home() / "unturned-server" / "Maps" / "PEI"

pytestmark = pytest.mark.skipif(
    not BUNDLES.exists() or not PEI_MAP.exists(),
    reason="Full server data not available",
)


class TestPEIMap:
    @pytest.fixture(scope="class")
    def all_tables(self):
        tables_by_id = {}
        name_to_id = {}
        for raw, english, rel_path in walk_bundle_dir(BUNDLES):
            if raw.get("Type") != "Spawn":
                continue
            entry = parse_entry(raw, english, rel_path)
            if isinstance(entry, SpawnTable):
                tables_by_id[entry.id] = entry
                name_to_id[entry.name] = entry.id
        return tables_by_id, name_to_id

    def test_finds_spawn_tables(self, all_tables):
        tables_by_id, _ = all_tables
        assert len(tables_by_id) > 100

    def test_determines_active_tables(self, all_tables):
        tables_by_id, name_to_id = all_tables
        active = determine_active_tables(PEI_MAP, tables_by_id, name_to_id)
        assert len(active) > 10

    def test_resolves_items(self, all_tables):
        tables_by_id, name_to_id = all_tables
        active = determine_active_tables(PEI_MAP, tables_by_id, name_to_id)
        all_items = set()
        for tid in active:
            all_items |= resolve_spawn_table_items(tid, tables_by_id)
        assert len(all_items) > 100
```

**Step 2: Run on localAI**

```bash
ssh localAI 'cd ~/bin && python3 -m pytest unturned_data/tests/test_map_integration.py -v'
```

Expected: all PASS

**Step 3: Commit**

```bash
cd ~/bin && git add unturned_data/tests/test_map_integration.py && git commit -m "test: integration tests for map-aware spawn resolution"
```

---

## Summary

| Task | Component | Key Files |
|------|-----------|-----------|
| 1 | SpawnTable model | `models.py`, `test_spawn_model.py` |
| 2 | Spawn category parser | `categories/spawns.py`, `test_spawn_parsing.py` |
| 3 | Map resolver | `map_resolver.py`, `test_map_resolver.py` |
| 4 | CLI --map flag | `cli.py`, `test_cli_map.py` |
| 5 | Web formatter maps | `formatters/web_fmt.py`, `test_web_map.py` |
| 6 | Frontend map checkboxes | `main.js`, `index.html` |
| 7 | Data generation script | `generate_web_data.sh` |
| 8 | Integration tests | `test_map_integration.py` |

**Dependencies:** Tasks 1→2→3→4→5→6→7→8 (mostly sequential, though 6 can start in parallel with 5)
