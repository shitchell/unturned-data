# Crafting Blacklist Parsing & Stub Node Fix

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix stub nodes missing map data, parse per-map crafting blacklists, and filter blueprints so the crafting graph only shows recipes available on each map.

**Architecture:** Extend the existing `unturned_data` package with: (1) a bug fix to `_ensure_stub_node()` that copies map/type/rarity from real entries, (2) an `.asset` file parser built on the existing `dat_parser`, (3) a `crafting_blacklist` module that reads the `Config.json` → `LevelAsset` → `CraftingBlacklistAsset` chain, and (4) integration into `cli.py` and `crafting_fmt.py` to filter blueprints per map. Workshop maps like A6 Polaris set `Allow_Core_Blueprints: False` to disable all vanilla recipes, so the pipeline must detect this and exclude base-game blueprints from those maps' crafting views.

**Tech Stack:** Python 3.11+, pytest, existing `unturned_data` package, vanilla JS frontend

**Reference files:**
- Package root: `/home/guy/bin/unturned_data/`
- Web frontend: `/home/guy/code/git/github.com/shitchell/stuff/site/unturned/`
- Server data: `/home/guy/unturned-server/`
- A6 Polaris map: `/home/guy/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2898548949/A6 Polaris/`
- Polaris Config.json: `.../A6 Polaris/Config.json` (JSON, has `"Asset": {"GUID": "..."}`)
- Polaris LevelAsset: `.../A6 Polaris/Bundles/Content/Level/Frost_Level_00.asset` (has `Crafting_Blacklists [...]`)
- Polaris CraftingBlacklist: `.../A6 Polaris/Bundles/Content/Level/Frost_Craft.asset` (has `Allow_Core_Blueprints False`)

**Crafting blacklist chain:**

```
Config.json                          → "Asset": {"GUID": "<level_asset_guid>"}
  └── LevelAsset (.asset file)       → Crafting_Blacklists [{"GUID": "<blacklist_guid>"}, ...]
        └── CraftingBlacklistAsset   → Allow_Core_Blueprints False
                                       Input_Items [{GUID ...}, ...]
                                       Output_Items [{GUID ...}, ...]
```

**.asset file format:** Identical to `.dat` format except keys are quoted:
```
"Metadata"
{
    "GUID" "dcddca4d05564563aa2aac8144615c46"
    "Type" "SDG.Unturned.CraftingBlacklistAsset, ..."
}
"Asset"
{
    "Allow_Core_Blueprints" "False"
}
```

The existing `dat_parser.py` can parse this if we strip quotes from keys. Values already have quotes stripped by `_coerce_value()`.

---

## Task 1: Fix stub node bug in crafting_fmt.py

**Files:**
- Modify: `~/bin/unturned_data/formatters/crafting_fmt.py`
- Create: `~/bin/unturned_data/tests/test_crafting_stub_fix.py`

The `_ensure_stub_node()` function creates nodes with `maps: []`, `type: ""`, etc. even when the item exists as a full `BundleEntry` with map data. This affects 321 nodes including the most heavily-used crafting materials (Cloth, Metal Scrap, Tape, Blowtorch).

**Step 1: Write the failing test**

Create `~/bin/unturned_data/tests/test_crafting_stub_fix.py`:

```python
"""Tests for stub node enrichment in crafting graph builder."""
import json
import pytest

from unturned_data.formatters.crafting_fmt import entries_to_crafting_json
from unturned_data.models import BundleEntry, Blueprint


class TestStubNodeEnrichment:
    def _make_entry(self, guid, name, type_, source, maps=None, blueprints=None):
        entry = BundleEntry(
            guid=guid, type=type_, id=0, name=name,
            source_path=source, blueprints=blueprints or [],
        )
        if maps:
            entry._map_spawnable = set(maps)
        return entry

    def test_stub_inherits_maps_from_real_entry(self):
        """Stub nodes should inherit maps/type/rarity from the real entry."""
        # Cloth: has no blueprints (will be a stub) but IS a real entry with map data
        cloth = self._make_entry(
            "aaa00000000000000000000000000001", "Cloth", "Supply",
            "Items/Supplies/Cloth", maps=["PEI", "Washington"],
        )
        cloth.rarity = "Common"

        # Bow: has blueprints that reference Cloth as input
        bow = self._make_entry(
            "bbb00000000000000000000000000002", "Birch Bow", "Bow",
            "Items/Weapons/Birch_Bow",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["aaa00000000000000000000000000001 x 3"],
                outputs=["this"],
            )],
        )
        bow._map_spawnable = {"PEI"}

        output = entries_to_crafting_json([cloth, bow])
        data = json.loads(output)

        # Find the Cloth node
        cloth_node = next(
            (n for n in data["nodes"] if n["name"] == "Cloth"), None
        )
        assert cloth_node is not None, "Cloth node should exist"
        assert cloth_node["type"] == "Supply", "Stub should inherit type"
        assert cloth_node["rarity"] == "Common", "Stub should inherit rarity"
        assert "PEI" in cloth_node["maps"], "Stub should inherit maps"
        assert "Washington" in cloth_node["maps"], "Stub should inherit maps"

    def test_unknown_stub_gets_empty_data(self):
        """Items not in the entries list should still get empty stub data."""
        bow = self._make_entry(
            "bbb00000000000000000000000000002", "Birch Bow", "Bow",
            "Items/Weapons/Birch_Bow",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ccc00000000000000000000000000003 x 2"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([bow])
        data = json.loads(output)

        # Unknown item should still get a stub
        unknown = next(
            (n for n in data["nodes"]
             if n["id"] == "ccc00000000000000000000000000003"),
            None,
        )
        assert unknown is not None
        assert unknown["maps"] == []
        assert unknown["type"] == ""

    def test_stub_gets_category_parts(self):
        """Stub nodes should inherit category_parts from real entries."""
        metal = self._make_entry(
            "ddd00000000000000000000000000004", "Metal Scrap", "Supply",
            "Items/Supplies/Scrap_Metal",
        )
        # Entry with blueprint that references metal
        plate = self._make_entry(
            "eee00000000000000000000000000005", "Metal Plate", "Supply",
            "Items/Supplies/Metal_Plate",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ddd00000000000000000000000000004 x 3"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([metal, plate])
        data = json.loads(output)

        metal_node = next(
            (n for n in data["nodes"] if n["name"] == "Metal Scrap"), None
        )
        assert metal_node is not None
        assert metal_node["category"] == ["Items", "Supplies"]
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_stub_fix.py -v
```

Expected: FAIL — `assert cloth_node["type"] == "Supply"` fails because type is `""`.

**Step 3: Implement the fix**

Modify `~/bin/unturned_data/formatters/crafting_fmt.py`:

1. In `build_crafting_graph()`, add an `entries_by_guid` lookup before the main loop (after `id_to_guid` at line 123):

```python
    # Build GUID -> entry lookup for enriching stub nodes
    entries_by_guid: dict[str, BundleEntry] = {}
    for entry in entries:
        if entry.guid:
            entries_by_guid[entry.guid.lower()] = entry
```

2. Replace `_ensure_stub_node()` with:

```python
def _ensure_stub_node(
    guid: str,
    guid_map: dict[str, str],
    nodes: dict[str, dict[str, Any]],
    entries_by_guid: dict[str, "BundleEntry"] | None = None,
) -> None:
    """Add a stub node for a GUID if not already present.

    If the GUID matches a known entry (via entries_by_guid), copies
    type, category, rarity, and map data from the real entry.
    """
    if guid not in nodes:
        entry = entries_by_guid.get(guid) if entries_by_guid else None
        if entry:
            nodes[guid] = {
                "id": guid,
                "name": entry.name or _resolve_name(guid, guid_map),
                "type": entry.type,
                "category": entry.category_parts,
                "rarity": entry.rarity,
                "maps": sorted(getattr(entry, "_map_spawnable", None) or []),
            }
        else:
            nodes[guid] = {
                "id": guid,
                "name": _resolve_name(guid, guid_map),
                "type": "",
                "category": [],
                "rarity": "",
                "maps": [],
            }
```

3. Update all 4 call sites (in salvage, repair, craft-targets, and craft-inputs sections) to pass `entries_by_guid`:

```python
_ensure_stub_node(out_guid, guid_map, nodes, entries_by_guid)
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_stub_fix.py -v
```

Expected: all PASS

**Step 5: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all 248+ tests PASS (backward compatible — the new parameter is optional)

---

## Task 2: Add .asset file parsing to dat_parser

**Files:**
- Modify: `~/bin/unturned_data/dat_parser.py`
- Modify: `~/bin/unturned_data/tests/test_dat_parser.py`

The `.asset` file format is identical to `.dat` except keys are quoted (`"GUID" "value"` instead of `GUID value`). The existing parser already handles quoted values via `_coerce_value()`, but keys retain their quotes. We need to strip quotes from keys so both formats produce the same dict structure.

**Step 1: Write the failing test**

Add to `~/bin/unturned_data/tests/test_dat_parser.py`:

```python
class TestAssetFileParsing:
    """Tests for .asset file format (quoted keys)."""

    def test_parse_asset_format(self):
        """Keys in .asset files are quoted — parser should strip them."""
        text = '''
"Metadata"
{
    "GUID" "dcddca4d05564563aa2aac8144615c46"
    "Type" "SDG.Unturned.CraftingBlacklistAsset"
}
"Asset"
{
    "Allow_Core_Blueprints" "False"
    "Input_Items"
    [
        {
        "NoteToSelf" "car battery"
        "GUID" "098b13be34a7411db7736b7f866ada69"
        }
    ]
}
'''
        result = parse_dat(text)
        # Keys should NOT have quotes
        assert "Metadata" in result
        assert "Asset" in result
        assert result["Metadata"]["GUID"] == "dcddca4d05564563aa2aac8144615c46"
        assert result["Asset"]["Allow_Core_Blueprints"] is False
        assert len(result["Asset"]["Input_Items"]) == 1
        assert result["Asset"]["Input_Items"][0]["GUID"] == "098b13be34a7411db7736b7f866ada69"

    def test_parse_level_asset_format(self):
        """LevelAsset with Crafting_Blacklists array."""
        text = '''
"Metadata"
{
    "GUID" "77e3a2e0fd6b4c768928dc2861888a6e"
    "Type" "SDG.Unturned.LevelAsset"
}
"Asset"
{
    "Crafting_Blacklists"
    [
        {"GUID" "dcddca4d05564563aa2aac8144615c46"}
    ]
}
'''
        result = parse_dat(text)
        assert result["Metadata"]["GUID"] == "77e3a2e0fd6b4c768928dc2861888a6e"
        blacklists = result["Asset"]["Crafting_Blacklists"]
        assert len(blacklists) == 1
        assert blacklists[0]["GUID"] == "dcddca4d05564563aa2aac8144615c46"

    def test_existing_dat_format_unaffected(self):
        """Unquoted .dat keys still parse correctly after the change."""
        text = '''GUID f019fcaa2e8e4c92b17259025c80ff77
Type Spawn
ID 228
Tables 2
Table_0_Spawn_ID 229
Table_0_Weight 31
'''
        result = parse_dat(text)
        assert result["GUID"] == "f019fcaa2e8e4c92b17259025c80ff77"
        assert result["Type"] == "Spawn"
        assert result["ID"] == 228
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py::TestAssetFileParsing -v
```

Expected: FAIL — `assert "Metadata" in result` fails because the key is `'"Metadata"'` (with quotes).

**Step 3: Implement quote stripping**

Modify `_split_key_value()` in `~/bin/unturned_data/dat_parser.py` to strip quotes from keys. Add this at the end, before the return statements:

```python
def _split_key_value(line: str) -> tuple[str, str | None]:
    """Split a line into key and optional value."""
    line = line.strip()
    if not line:
        return ("", None)

    # Handle quoted keys: "Key" "Value" or "Key" Value or "Key"
    if line.startswith('"'):
        # Find the closing quote for the key
        close = line.index('"', 1)
        key = line[1:close]  # strip quotes
        rest = line[close + 1:].strip()
        if not rest:
            return (key, None)
        return (key, rest)

    # Find first whitespace
    space_idx = None
    for i, c in enumerate(line):
        if c in (' ', '\t'):
            space_idx = i
            break
    if space_idx is None:
        return (line, None)
    key = line[:space_idx]
    rest = line[space_idx:].strip()
    if not rest:
        return (key, None)
    return (key, rest)
```

Also add a convenience function for parsing .asset files:

```python
def parse_asset_file(path: Path) -> dict[str, Any]:
    """Parse an .asset file from disk.

    Uses the same parser as .dat files — the format is identical
    except that .asset files quote their keys.
    """
    text = path.read_text(encoding="utf-8-sig")
    return parse_dat(text)
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py -v
```

Expected: all PASS (new tests + existing tests)

**Step 5: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS (quote stripping is backward-compatible since no .dat key legitimately starts with `"`)

---

## Task 3: CraftingBlacklist model

**Files:**
- Modify: `~/bin/unturned_data/models.py`
- Modify: `~/bin/unturned_data/tests/test_models.py`

**Step 1: Write the failing test**

Add to `~/bin/unturned_data/tests/test_models.py`:

```python
from unturned_data.models import CraftingBlacklist


class TestCraftingBlacklist:
    def test_default_allows_core(self):
        bl = CraftingBlacklist()
        assert bl.allow_core_blueprints is True
        assert bl.blocked_inputs == set()
        assert bl.blocked_outputs == set()

    def test_blocks_core(self):
        bl = CraftingBlacklist(allow_core_blueprints=False)
        assert bl.allow_core_blueprints is False

    def test_merge_combines_blocks(self):
        a = CraftingBlacklist(
            allow_core_blueprints=True,
            blocked_inputs={"guid-a"},
        )
        b = CraftingBlacklist(
            allow_core_blueprints=False,
            blocked_outputs={"guid-b"},
        )
        merged = CraftingBlacklist.merge([a, b])
        # If ANY blacklist disables core, merged disables core
        assert merged.allow_core_blueprints is False
        assert merged.blocked_inputs == {"guid-a"}
        assert merged.blocked_outputs == {"guid-b"}

    def test_merge_empty_list(self):
        merged = CraftingBlacklist.merge([])
        assert merged.allow_core_blueprints is True
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_models.py::TestCraftingBlacklist -v
```

Expected: FAIL — `ImportError: cannot import name 'CraftingBlacklist'`

**Step 3: Implement**

Add to the end of `~/bin/unturned_data/models.py` (after `SpawnTable`):

```python
# ---------------------------------------------------------------------------
# CraftingBlacklist
# ---------------------------------------------------------------------------
@dataclass
class CraftingBlacklist:
    """Per-map crafting restrictions parsed from CraftingBlacklistAsset."""

    allow_core_blueprints: bool = True
    blocked_inputs: set[str] = field(default_factory=set)   # item GUIDs
    blocked_outputs: set[str] = field(default_factory=set)  # item GUIDs

    @classmethod
    def merge(cls, blacklists: list[CraftingBlacklist]) -> CraftingBlacklist:
        """Merge multiple blacklists. Any False wins for allow_core."""
        if not blacklists:
            return cls()
        return cls(
            allow_core_blueprints=all(bl.allow_core_blueprints for bl in blacklists),
            blocked_inputs=set().union(*(bl.blocked_inputs for bl in blacklists)),
            blocked_outputs=set().union(*(bl.blocked_outputs for bl in blacklists)),
        )
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_models.py::TestCraftingBlacklist -v
```

Expected: all PASS

---

## Task 4: Crafting blacklist resolver module

**Files:**
- Create: `~/bin/unturned_data/crafting_blacklist.py`
- Create: `~/bin/unturned_data/tests/test_crafting_blacklist.py`
- Create: `~/bin/unturned_data/tests/fixtures/fake_blacklist_map/` (test fixtures)

This module reads the `Config.json` → `LevelAsset` → `CraftingBlacklistAsset` chain for a given map directory to determine crafting restrictions.

**Step 1: Create test fixtures**

Create a minimal fake map with a crafting blacklist:

`~/bin/unturned_data/tests/fixtures/fake_blacklist_map/Config.json`:
```json
{
    "Asset": {"GUID": "aaa00000000000000000000000000001"}
}
```

`~/bin/unturned_data/tests/fixtures/fake_blacklist_map/Bundles/Level/FakeLevel.asset`:
```
"Metadata"
{
    "GUID" "aaa00000000000000000000000000001"
    "Type" "SDG.Unturned.LevelAsset"
}
"Asset"
{
    "Crafting_Blacklists"
    [
        {"GUID" "bbb00000000000000000000000000002"}
    ]
}
```

`~/bin/unturned_data/tests/fixtures/fake_blacklist_map/Bundles/Level/FakeCraft.asset`:
```
"Metadata"
{
    "GUID" "bbb00000000000000000000000000002"
    "Type" "SDG.Unturned.CraftingBlacklistAsset"
}
"Asset"
{
    "Allow_Core_Blueprints" "False"
    "Input_Items"
    [
        {
        "GUID" "ccc00000000000000000000000000003"
        }
    ]
    "Output_Items"
    [
        {
        "GUID" "ddd00000000000000000000000000004"
        }
    ]
}
```

Also create a fixture for a map with NO blacklist:

`~/bin/unturned_data/tests/fixtures/fake_vanilla_map/Config.json`:
```json
{
    "Asset": {"GUID": "eee00000000000000000000000000005"}
}
```

`~/bin/unturned_data/tests/fixtures/fake_vanilla_map/Bundles/Level/VanillaLevel.asset`:
```
"Metadata"
{
    "GUID" "eee00000000000000000000000000005"
    "Type" "SDG.Unturned.LevelAsset"
}
"Asset"
{
    "ID" "0"
}
```

**Step 2: Write the failing test**

Create `~/bin/unturned_data/tests/test_crafting_blacklist.py`:

```python
"""Tests for crafting blacklist resolution."""
import pytest
from pathlib import Path

from unturned_data.crafting_blacklist import resolve_crafting_blacklist
from unturned_data.models import CraftingBlacklist

FIXTURES = Path(__file__).parent / "fixtures"
BLACKLIST_MAP = FIXTURES / "fake_blacklist_map"
VANILLA_MAP = FIXTURES / "fake_vanilla_map"


class TestResolveCraftingBlacklist:
    def test_map_with_blacklist(self):
        """Map with Allow_Core_Blueprints False returns correct blacklist."""
        bl = resolve_crafting_blacklist(BLACKLIST_MAP)
        assert bl is not None
        assert bl.allow_core_blueprints is False
        assert "ccc00000000000000000000000000003" in bl.blocked_inputs
        assert "ddd00000000000000000000000000004" in bl.blocked_outputs

    def test_vanilla_map_no_blacklist(self):
        """Map without Crafting_Blacklists returns None."""
        bl = resolve_crafting_blacklist(VANILLA_MAP)
        assert bl is None

    def test_missing_config_json(self, tmp_path):
        """Map directory without Config.json returns None."""
        bl = resolve_crafting_blacklist(tmp_path)
        assert bl is None

    def test_config_without_asset_guid(self, tmp_path):
        """Config.json without Asset.GUID returns None."""
        config = tmp_path / "Config.json"
        config.write_text('{"Name": "Test"}')
        bl = resolve_crafting_blacklist(tmp_path)
        assert bl is None
```

**Step 3: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_blacklist.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'unturned_data.crafting_blacklist'`

**Step 4: Implement**

Create `~/bin/unturned_data/crafting_blacklist.py`:

```python
"""
Crafting blacklist resolution for Unturned maps.

Reads the Config.json → LevelAsset → CraftingBlacklistAsset chain
to determine which crafting restrictions apply on a given map.

Workshop maps like A6 Polaris use this to disable all vanilla
recipes (Allow_Core_Blueprints: False) and define their own
crafting system with map-specific item IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unturned_data.dat_parser import parse_asset_file
from unturned_data.models import CraftingBlacklist


def _find_asset_by_guid(
    search_dirs: list[Path],
    target_guid: str,
) -> Path | None:
    """Find an .asset file containing the given GUID.

    Walks .asset files in the search directories, parsing each
    to check its Metadata.GUID field.
    """
    target_lower = target_guid.lower()
    for root in search_dirs:
        if not root.is_dir():
            continue
        for asset_path in root.rglob("*.asset"):
            try:
                parsed = parse_asset_file(asset_path)
            except Exception:
                continue
            meta = parsed.get("Metadata", {})
            if isinstance(meta, dict):
                guid = str(meta.get("GUID", "")).lower()
                if guid == target_lower:
                    return asset_path
    return None


def _parse_blacklist_asset(parsed: dict[str, Any]) -> CraftingBlacklist:
    """Extract CraftingBlacklist fields from a parsed CraftingBlacklistAsset."""
    asset = parsed.get("Asset", {})
    if not isinstance(asset, dict):
        return CraftingBlacklist()

    allow_core = asset.get("Allow_Core_Blueprints", True)
    # Handle string "False" / "True" (already coerced by parser, but be safe)
    if isinstance(allow_core, str):
        allow_core = allow_core.lower() != "false"

    blocked_inputs: set[str] = set()
    for item in asset.get("Input_Items", []):
        if isinstance(item, dict) and "GUID" in item:
            blocked_inputs.add(str(item["GUID"]).lower())

    blocked_outputs: set[str] = set()
    for item in asset.get("Output_Items", []):
        if isinstance(item, dict) and "GUID" in item:
            blocked_outputs.add(str(item["GUID"]).lower())

    return CraftingBlacklist(
        allow_core_blueprints=bool(allow_core),
        blocked_inputs=blocked_inputs,
        blocked_outputs=blocked_outputs,
    )


def resolve_crafting_blacklist(
    map_dir: Path,
    extra_bundle_dirs: list[Path] | None = None,
) -> CraftingBlacklist | None:
    """Resolve crafting blacklists for a map directory.

    Reads Config.json to find the LevelAsset GUID, then finds the
    LevelAsset .asset file, reads its Crafting_Blacklists array,
    and parses each referenced CraftingBlacklistAsset.

    Returns None if the map has no crafting blacklists.
    Returns a merged CraftingBlacklist if it does.
    """
    config_path = map_dir / "Config.json"
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Extract LevelAsset GUID from Config.json
    asset_ref = config.get("Asset", {})
    if not isinstance(asset_ref, dict):
        return None
    level_guid = asset_ref.get("GUID", "")
    if not level_guid:
        return None

    # Search for the LevelAsset .asset file
    search_dirs = [map_dir / "Bundles"]
    if extra_bundle_dirs:
        search_dirs.extend(extra_bundle_dirs)

    level_asset_path = _find_asset_by_guid(search_dirs, level_guid)
    if not level_asset_path:
        return None

    level_parsed = parse_asset_file(level_asset_path)
    asset_section = level_parsed.get("Asset", {})
    if not isinstance(asset_section, dict):
        return None

    blacklist_refs = asset_section.get("Crafting_Blacklists", [])
    if not isinstance(blacklist_refs, list) or not blacklist_refs:
        return None

    # Resolve each blacklist GUID
    blacklists: list[CraftingBlacklist] = []
    for ref in blacklist_refs:
        if isinstance(ref, dict):
            bl_guid = str(ref.get("GUID", ""))
        else:
            bl_guid = str(ref)
        if not bl_guid:
            continue

        bl_path = _find_asset_by_guid(search_dirs, bl_guid)
        if not bl_path:
            continue

        bl_parsed = parse_asset_file(bl_path)
        meta_type = bl_parsed.get("Metadata", {}).get("Type", "")
        if isinstance(meta_type, str) and "CraftingBlacklist" in meta_type:
            blacklists.append(_parse_blacklist_asset(bl_parsed))

    if not blacklists:
        return None

    return CraftingBlacklist.merge(blacklists)
```

**Step 5: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_blacklist.py -v
```

Expected: all PASS

**Step 6: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS

---

## Task 5: Integration test with real A6 Polaris data

**Files:**
- Create: `~/bin/unturned_data/tests/test_blacklist_integration.py`

**Step 1: Write integration test**

```python
"""Integration tests for crafting blacklist with real server data."""
import pytest
from pathlib import Path

from unturned_data.crafting_blacklist import resolve_crafting_blacklist

# Real map paths — skip if not available
POLARIS_MAP = Path.home() / "unturned-server" / "Servers" / "MyServer" / "Workshop" / "Steam" / "content" / "304930" / "2898548949" / "A6 Polaris"
PEI_MAP = Path.home() / "unturned-server" / "Maps" / "PEI"

pytestmark = pytest.mark.skipif(
    not POLARIS_MAP.exists(),
    reason="Server data not available",
)


class TestRealPolaris:
    def test_polaris_disables_core_blueprints(self):
        bl = resolve_crafting_blacklist(POLARIS_MAP)
        assert bl is not None
        assert bl.allow_core_blueprints is False

    def test_polaris_blocks_car_battery(self):
        bl = resolve_crafting_blacklist(POLARIS_MAP)
        assert bl is not None
        # Car battery GUID from Frost_Craft.asset
        assert "098b13be34a7411db7736b7f866ada69" in bl.blocked_inputs

    def test_pei_has_no_blacklist(self):
        if not PEI_MAP.exists():
            pytest.skip("PEI not available")
        bl = resolve_crafting_blacklist(PEI_MAP)
        assert bl is None
```

**Step 2: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_blacklist_integration.py -v
```

Expected: PASS if server data available, SKIP otherwise

---

## Task 6: Wire blacklists into CLI and crafting formatter

**Files:**
- Modify: `~/bin/unturned_data/cli.py`
- Modify: `~/bin/unturned_data/formatters/crafting_fmt.py`
- Modify: `~/bin/unturned_data/tests/test_crafting_stub_fix.py` (add blacklist filtering tests)

This is the core integration: when `--map` is used with `--format crafting`, resolve each map's crafting blacklist and filter blueprints accordingly. When `Allow_Core_Blueprints` is False, only include blueprints owned by items from that map's own Bundles/ (not from the base game Bundles/).

**Step 1: Write the failing test**

Add to `~/bin/unturned_data/tests/test_crafting_stub_fix.py`:

```python
from unturned_data.models import CraftingBlacklist


class TestBlacklistFiltering:
    def _make_entry(self, guid, name, type_, source, maps=None, blueprints=None):
        entry = BundleEntry(
            guid=guid, type=type_, id=0, name=name,
            source_path=source, blueprints=blueprints or [],
        )
        if maps:
            entry._map_spawnable = set(maps)
        return entry

    def test_core_blueprints_excluded_when_blacklisted(self):
        """When allow_core_blueprints=False, base-game item blueprints are excluded."""
        # Base-game item (source_path starts with "Items/")
        tomato = self._make_entry(
            "aaa00000000000000000000000000001", "Tomato", "Food",
            "Items/Edible/Tomato",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["bbb00000000000000000000000000002 x 2"],
                outputs=["this"],
            )],
        )

        # Workshop map item (source_path starts with map-specific prefix)
        snowberry = self._make_entry(
            "ccc00000000000000000000000000003", "Snowberry", "Food",
            "Polaris/Items/Edible/Snowberry",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["ddd00000000000000000000000000004 x 1"],
                outputs=["this"],
            )],
        )

        blacklists = {
            "A6 Polaris": CraftingBlacklist(allow_core_blueprints=False),
        }
        # Map source prefixes: tells the formatter which source_path prefixes
        # belong to each map's own bundles (non-core items)
        map_source_prefixes = {
            "A6 Polaris": ["Polaris/"],
        }

        output = entries_to_crafting_json(
            [tomato, snowberry],
            crafting_blacklists=blacklists,
            map_source_prefixes=map_source_prefixes,
        )
        data = json.loads(output)

        # Tomato edges should be excluded (core blueprint on blacklisted map)
        node_names = {n["name"] for n in data["nodes"]}
        edge_targets = {
            next((n["name"] for n in data["nodes"] if n["id"] == e["target"]), None)
            for e in data["edges"]
        }
        assert "Snowberry" in node_names, "Workshop item should be present"
        assert "Tomato" not in edge_targets, "Core blueprint should be excluded"

    def test_no_blacklist_keeps_all_blueprints(self):
        """Without blacklists, all blueprints are included."""
        tomato = self._make_entry(
            "aaa00000000000000000000000000001", "Tomato", "Food",
            "Items/Edible/Tomato",
            blueprints=[Blueprint(
                name="Craft",
                inputs=["bbb00000000000000000000000000002 x 2"],
                outputs=["this"],
            )],
        )

        output = entries_to_crafting_json([tomato])
        data = json.loads(output)

        assert any(n["name"] == "Tomato" for n in data["nodes"])
        assert len(data["edges"]) > 0
```

**Step 2: Run test to verify it fails**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_stub_fix.py::TestBlacklistFiltering -v
```

Expected: FAIL — `entries_to_crafting_json` doesn't accept `crafting_blacklists` parameter yet.

**Step 3: Implement**

**A. Modify `entries_to_crafting_json()` in `crafting_fmt.py`:**

```python
def entries_to_crafting_json(
    entries: list[BundleEntry],
    supplementary_guids: dict[str, str] | None = None,
    indent: int | None = None,
    crafting_blacklists: dict[str, "CraftingBlacklist"] | None = None,
    map_source_prefixes: dict[str, list[str]] | None = None,
) -> str:
    """Convert entries to a crafting-graph JSON string."""
    if not entries:
        return json.dumps({"nodes": [], "edges": []}, indent=indent)

    guid_map = build_guid_map(entries, supplementary_guids)
    graph = build_crafting_graph(
        entries, guid_map,
        crafting_blacklists=crafting_blacklists,
        map_source_prefixes=map_source_prefixes,
    )

    return json.dumps(graph, indent=indent, ensure_ascii=False)
```

**B. Modify `build_crafting_graph()` in `crafting_fmt.py`:**

Add `crafting_blacklists` and `map_source_prefixes` params. Before processing each entry's blueprints, check if the entry's blueprints should be included:

```python
def build_crafting_graph(
    entries: list[BundleEntry],
    guid_map: dict[str, str],
    crafting_blacklists: dict[str, "CraftingBlacklist"] | None = None,
    map_source_prefixes: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
```

Add a helper inside or before this function:

```python
def _is_entry_core(entry: BundleEntry, map_source_prefixes: dict[str, list[str]] | None) -> bool:
    """Check if an entry is from the core/base game (not a map-specific item)."""
    if not map_source_prefixes:
        return True  # No map info — assume core
    for prefixes in map_source_prefixes.values():
        for prefix in prefixes:
            if entry.source_path.startswith(prefix):
                return False
    return True
```

Then in the main loop, after `if not blueprints: continue`, add:

```python
        # Check crafting blacklists: if ANY map disables core blueprints
        # and this entry is a core item, skip its blueprints entirely.
        if crafting_blacklists and _is_entry_core(entry, map_source_prefixes):
            # If all maps with blacklists disable core, skip
            any_allows_core = False
            for map_name, bl in crafting_blacklists.items():
                if bl is None or bl.allow_core_blueprints:
                    any_allows_core = True
                    break
            if not any_allows_core:
                continue
```

**C. Modify `cli.py`** to resolve blacklists and pass them through:

In the `--map` processing section, after collecting spawn tables (around line 136), add:

```python
    from unturned_data.crafting_blacklist import resolve_crafting_blacklist

    # Resolve crafting blacklists for each map
    crafting_blacklists: dict[str, CraftingBlacklist | None] = {}
    map_source_prefixes: dict[str, list[str]] = {}
    for map_dir in args.map:
        map_name = map_dir.resolve().name
        bl = resolve_crafting_blacklist(map_dir, extra_bundle_dirs=[bundle_path])
        if bl is not None:
            crafting_blacklists[map_name] = bl
        # Track source path prefixes for map-specific entries
        # Entries loaded from map bundles get rel_paths relative to the map's Bundles/
        # We tag them during loading so we can identify them later
        map_source_prefixes[map_name] = [f"_map_{map_name}/"]
```

Also modify the map bundle walking loop (line 117-134) to prefix source paths for map entries:

```python
                entry = parse_entry(raw, english, f"_map_{map_name}/{rel_path}")
```

Then in the format section, pass blacklists to crafting formatter:

```python
    elif args.format == "crafting":
        supplementary = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        output = entries_to_crafting_json(
            entries, supplementary_guids=supplementary,
            crafting_blacklists=crafting_blacklists if args.map else None,
            map_source_prefixes=map_source_prefixes if args.map else None,
            indent=2,
        )
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_crafting_stub_fix.py -v
```

Expected: all PASS

**Step 5: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all PASS (blacklist params are optional, so existing tests unaffected)

---

## Task 7: Regenerate data and deploy

**Files:**
- Regenerate: `~/code/git/github.com/shitchell/stuff/site/unturned/crafting/crafting.json`
- Regenerate: `~/code/git/github.com/shitchell/stuff/site/unturned/data.json`

**Step 1: Sync unturned_data to localAI** (if running generation there)

```bash
rsync -av ~/bin/unturned_data/ localAI:~/bin/unturned_data/
```

Or run locally since we now have `~/unturned-server/` synced.

**Step 2: Generate crafting.json with blacklists**

```bash
cd ~/bin && python3 -m unturned_data ~/unturned-server/Bundles \
    --format crafting \
    --map ~/unturned-server/Maps/PEI \
    --map ~/unturned-server/Maps/Washington \
    --map ~/unturned-server/Maps/Russia \
    --map ~/unturned-server/Maps/Germany \
    --map ~/unturned-server/Maps/Yukon \
    --map ~/unturned-server/Maps/Tutorial \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2898548949/A6 Polaris" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2985553935/Alpha Valley" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2975386502/Monolith" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/3003498177/Destruction" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2953498384/Paintball_Arena_0" \
    > ~/code/git/github.com/shitchell/stuff/site/unturned/crafting/crafting.json
```

**Step 3: Verify the output**

```bash
python3 -c "
import json
with open('$HOME/code/git/github.com/shitchell/stuff/site/unturned/crafting/crafting.json') as f:
    data = json.load(f)
nodes = data['nodes']
edges = data['edges']
# Count nodes with maps
polaris_only = [n for n in nodes if n.get('maps') == ['A6 Polaris']]
no_maps = [n for n in nodes if not n.get('maps')]
with_maps = [n for n in nodes if n.get('maps')]
print(f'Total nodes: {len(nodes)}')
print(f'Total edges: {len(edges)}')
print(f'Nodes with maps: {len(with_maps)}')
print(f'Nodes without maps: {len(no_maps)}')
print(f'Polaris-only nodes: {len(polaris_only)}')
# The key check: no_maps should be much lower than before (was 769)
# Stub node fix should populate most of those
print()
# Verify no core blueprint edges for Polaris-only items referencing base-game ingredients
print('Sample Polaris-only items:', [n['name'] for n in polaris_only[:5]])
"
```

Expected:
- `Nodes without maps` should be significantly lower than 769 (stub fix)
- Polaris-only items should still be present
- Core blueprint edges (e.g., base-game Tomato recipes) should NOT appear

**Step 4: Also regenerate data.json** (for the items page)

```bash
cd ~/bin && python3 -m unturned_data ~/unturned-server/Bundles \
    --format web \
    --map ~/unturned-server/Maps/PEI \
    --map ~/unturned-server/Maps/Washington \
    --map ~/unturned-server/Maps/Russia \
    --map ~/unturned-server/Maps/Germany \
    --map ~/unturned-server/Maps/Yukon \
    --map ~/unturned-server/Maps/Tutorial \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2898548949/A6 Polaris" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2985553935/Alpha Valley" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2975386502/Monolith" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/3003498177/Destruction" \
    --map "~/unturned-server/Servers/MyServer/Workshop/Steam/content/304930/2953498384/Paintball_Arena_0" \
    > ~/code/git/github.com/shitchell/stuff/site/unturned/data.json
```

**Step 5: Test locally with npx serve**

```bash
cd ~/code/git/github.com/shitchell/stuff && npx serve site -l 8080
```

Open `http://localhost:8080/unturned/crafting/` and verify:
1. Map filter checkboxes appear
2. Checking "A6 Polaris" only → shows Polaris items (Snowberry, BVL weapons)
3. Base-game-only items (Eaglefire, Timberwolf) are NOT in the Polaris-filtered view
4. Checking "PEI" only → shows PEI items, NO Polaris items
5. Debug stats at bottom-left show reduced `polarisOnly` count if blacklist filtering works

**Step 6: Commit and push**

```bash
cd ~/code/git/github.com/shitchell/stuff && \
    git add site/unturned/data.json site/unturned/crafting/crafting.json && \
    git commit -m "data(unturned): regenerate with stub fix and blacklist filtering" && \
    git push
```

---

## Task 8: Remove debug overlay from crafting.js

**Files:**
- Modify: `~/code/git/github.com/shitchell/stuff/site/unturned/crafting/crafting.js`

Remove the debug stats `<div>` and `onFiltersChanged()` debug logging that were added during the investigation. Keep the `{ cache: 'no-cache' }` on the fetch.

**Step 1: Remove debug code from `init()`**

Remove the block that creates `#debug-stats` element (approximately lines 1786-1795).

**Step 2: Remove debug code from `onFiltersChanged()`**

Remove the block that updates `#debug-stats` text content (approximately lines 1412-1417).

**Step 3: Commit**

```bash
cd ~/code/git/github.com/shitchell/stuff && \
    git add site/unturned/crafting/crafting.js && \
    git commit -m "chore(unturned): remove debug overlay from crafting page" && \
    git push
```

---

## Summary

| Task | Component | Key Files | Depends On |
|------|-----------|-----------|------------|
| 1 | Stub node fix | `crafting_fmt.py`, `test_crafting_stub_fix.py` | — |
| 2 | .asset parsing | `dat_parser.py`, `test_dat_parser.py` | — |
| 3 | CraftingBlacklist model | `models.py`, `test_models.py` | — |
| 4 | Blacklist resolver | `crafting_blacklist.py`, `test_crafting_blacklist.py` | 2, 3 |
| 5 | Integration test | `test_blacklist_integration.py` | 4 |
| 6 | CLI + formatter wiring | `cli.py`, `crafting_fmt.py` | 1, 4 |
| 7 | Data regeneration | `data.json`, `crafting.json` | 6 |
| 8 | Remove debug overlay | `crafting.js` | 7 |

**Dependencies:** Tasks 1, 2, 3 can run in parallel. Task 4 needs 2+3. Task 5 needs 4. Task 6 needs 1+4. Task 7 needs 6. Task 8 needs 7.
