# Schema C Universal Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current multi-format output system with a single Schema C origin-first export pipeline that produces lossless JSON and human-readable markdown from Pydantic models.

**Architecture:** Parse .dat files into Pydantic models matching the Schema C entry shape (guid, id, type, name, description, rarity, source_path, category, english, parsed, blueprints, raw). Organize entries by origin (base game vs each map). Export to a directory tree: `base/entries.json`, `maps/<name>/entries.json`, `maps/<name>/map.json`, `manifest.json`, `guid_index.json`. Markdown formatter consumes the same models with GUID-resolved names.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, existing dat_parser/loader/map_resolver/crafting_blacklist modules (kept as-is)

---

## Design Decisions

These were settled during planning:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Origin detection | Directory tree (base Bundles/ vs map Bundles/) | Most likely matches game engine behavior |
| Model framework | Pydantic v2 BaseModel | User preference; gives `.model_dump()`, JSON schema, validation |
| Backward compat | None | Sole user; keep it clean |
| `to_dict()` approach | Replace with Pydantic `.model_dump()` | No separate method needed |
| Formatters kept | json (Schema C entries.json), markdown | Drop web_fmt and crafting_fmt |
| Spawn data | Full table chains (lossless) | In map.json spawn_resolution |
| `--no-raw` flag | Follow-up | Full lossless first |
| Output | Directory on disk via `--output` param | No stdout for single files |

## Dependency Graph

```
Task 1 (pydantic dep)
  └→ Task 2 (base models)
       └→ Task 3 (stat blocks)
            └→ Task 4 (blueprint model)
                 └→ Task 5 (category models)
                      └→ Task 6 (spawn table model)
                           └→ Task 7 (export models)
                                ├→ Task 8 (exporter core)
                                │    └→ Task 9 (map.json builder)
                                │         └→ Task 10 (guid index builder)
                                │              └→ Task 11 (CLI rewrite)
                                └→ Task 12 (json formatter)
                                     └→ Task 13 (markdown formatter)
                                          └→ Task 14 (cleanup)
                                               └→ Task 15 (integration test)
```

---

## Phase 1: Pydantic Model Migration

### Task 1: Add Pydantic dependency

**Files:**
- Create: `pyproject.toml` (or update if exists)

**Step 1: Check for existing project config**

```bash
ls pyproject.toml setup.py setup.cfg requirements.txt 2>/dev/null
```

**Step 2: Create pyproject.toml with pydantic dependency**

```toml
[project]
name = "unturned-data"
version = "0.6.0"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
unturned-data = "unturned_data.cli:main"
```

**Step 3: Install**

```bash
pip install -e ".[dev]"
```

**Step 4: Verify pydantic imports**

```bash
python -c "from pydantic import BaseModel; print('ok')"
```

**Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "build: add pydantic dependency and pyproject.toml"
```

---

### Task 2: Convert BundleEntry to Pydantic BaseModel

This is the foundation everything else builds on. Convert the base class, keep the same fields, add `english` dict, restructure `to_dict()` into Pydantic's `model_dump()`.

**Files:**
- Modify: `unturned_data/models.py:431-520`
- Test: `unturned_data/tests/test_models.py`

**Step 1: Write failing test for new BundleEntry shape**

Add to `test_models.py`:

```python
class TestBundleEntrySchemaC:
    """BundleEntry produces Schema C dict shape."""

    def test_model_dump_has_all_schema_c_fields(self):
        entry = BundleEntry(
            guid="abc123",
            type="Gun",
            id=42,
            name="Test Gun",
            description="A test",
            rarity="Common",
            size_x=2,
            size_y=1,
            source_path="Items/Guns/TestGun",
            english={"Name": "Test Gun", "Description": "A test"},
            raw={"GUID": "abc123", "Type": "Gun", "ID": 42},
            blueprints=[],
        )
        d = entry.model_dump()
        # All Schema C top-level fields present
        assert d["guid"] == "abc123"
        assert d["type"] == "Gun"
        assert d["id"] == 42
        assert d["name"] == "Test Gun"
        assert d["description"] == "A test"
        assert d["rarity"] == "Common"
        assert d["source_path"] == "Items/Guns/TestGun"
        assert d["category"] == ["Items", "Guns"]
        assert d["english"] == {"Name": "Test Gun", "Description": "A test"}
        assert d["parsed"] == {}
        assert d["blueprints"] == []
        assert d["raw"] == {"GUID": "abc123", "Type": "Gun", "ID": 42}

    def test_category_parts_from_source_path(self):
        entry = BundleEntry(source_path="Items/Backpacks/Alicepack")
        assert entry.category == ["Items", "Backpacks"]

    def test_category_empty_source_path(self):
        entry = BundleEntry(source_path="")
        assert entry.category == []

    def test_from_raw_stores_english(self):
        raw = {"GUID": "aaa", "Type": "Gun", "ID": 1}
        english = {"Name": "MyGun", "Description": "Desc", "Examine": "Look"}
        entry = BundleEntry.from_raw(raw, english, "Items/Guns/MyGun")
        assert entry.english == english
```

**Step 2: Run test to verify it fails**

```bash
pytest unturned_data/tests/test_models.py::TestBundleEntrySchemaC -v
```

Expected: FAIL (BundleEntry is still a dataclass, no `model_dump`, no `english` field)

**Step 3: Convert BundleEntry to Pydantic BaseModel**

Replace the BundleEntry dataclass in `models.py`:

```python
from pydantic import BaseModel, computed_field

class BundleEntry(BaseModel):
    """Base entry parsed from a bundle directory."""
    model_config = {"arbitrary_types_allowed": True}

    guid: str = ""
    type: str = ""
    id: int = 0
    name: str = ""
    description: str = ""
    rarity: str = ""
    size_x: int = 0
    size_y: int = 0
    source_path: str = ""
    english: dict[str, str] = {}
    raw: dict[str, Any] = {}
    blueprints: list[Blueprint] = []

    @computed_field
    @property
    def category(self) -> list[str]:
        """Directory path segments excluding the entry's own directory."""
        if not self.source_path:
            return []
        parts = self.source_path.split("/")
        return parts[:-1] if len(parts) > 1 else []

    @computed_field
    @property
    def parsed(self) -> dict[str, Any]:
        """Type-specific parsed fields. Base returns empty; subclasses override."""
        return {}

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> BundleEntry:
        name = english.get("Name", "")
        if not name and source_path:
            dir_name = source_path.rsplit("/", 1)[-1]
            name = dir_name.replace("_", " ")

        return cls(
            guid=str(raw.get("GUID", "")),
            type=str(raw.get("Type", "")),
            id=int(raw.get("ID", 0)),
            name=name,
            description=english.get("Description", ""),
            rarity=str(raw.get("Rarity", "")),
            size_x=int(raw.get("Size_X", 0)),
            size_y=int(raw.get("Size_Y", 0)),
            source_path=source_path,
            english=english,
            raw=raw,
            blueprints=Blueprint.list_from_raw(raw),
        )

    # Keep markdown methods for markdown formatter
    @staticmethod
    def markdown_columns() -> list[str]:
        return ["Name", "Type", "ID", "Rarity", "Size"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        size = f"{self.size_x}x{self.size_y}" if self.size_x or self.size_y else ""
        return [self.name, self.type, str(self.id), self.rarity, size]
```

**Important notes:**
- `to_dict()` is replaced by Pydantic's `model_dump()`
- `category_parts` property renamed to `category` (Schema C field name) via `@computed_field`
- `english` dict stored alongside raw
- `parsed` is a `@computed_field` that subclasses override
- `Blueprint` must also be converted to Pydantic (next task handles this)
- Keep `markdown_columns()` and `markdown_row()` -- the markdown formatter still needs them

**Step 4: Run test to verify it passes**

```bash
pytest unturned_data/tests/test_models.py::TestBundleEntrySchemaC -v
```

Expected: PASS

**Step 5: Fix existing BundleEntry tests**

Existing tests reference `to_dict()` and `category_parts`. Update:
- `entry.to_dict()` → `entry.model_dump()`
- `entry.category_parts` → `entry.category`
- Any test constructing BundleEntry via positional args needs keyword args (Pydantic)

```bash
pytest unturned_data/tests/test_models.py -v
```

Fix until all pass.

**Step 6: Commit**

```bash
git add unturned_data/models.py unturned_data/tests/test_models.py
git commit -m "refactor: convert BundleEntry to Pydantic BaseModel with Schema C shape"
```

---

### Task 3: Convert stat blocks to Pydantic

Convert DamageStats, ConsumableStats, StorageStats from dataclasses to Pydantic BaseModel.

**Files:**
- Modify: `unturned_data/models.py:15-128`
- Test: `unturned_data/tests/test_models.py`

**Step 1: Convert the three stat dataclasses**

Replace `@dataclass` with Pydantic `BaseModel` for DamageStats, ConsumableStats, StorageStats. The `from_raw()` static methods stay the same -- they already return instances. Remove `field(default_factory=dict)` and use plain `dict[str, float] = {}` (Pydantic handles this).

**Step 2: Run existing stat tests**

```bash
pytest unturned_data/tests/test_models.py::TestDamageStats -v
pytest unturned_data/tests/test_models.py::TestConsumableStats -v
pytest unturned_data/tests/test_models.py::TestStorageStats -v
```

Fix any failures from the dataclass→BaseModel switch (e.g., `field()` → default values).

**Step 3: Commit**

```bash
git add unturned_data/models.py unturned_data/tests/test_models.py
git commit -m "refactor: convert stat blocks to Pydantic BaseModel"
```

---

### Task 4: Convert Blueprint to Pydantic

**Files:**
- Modify: `unturned_data/models.py:133-296`
- Test: `unturned_data/tests/test_models.py`

**Step 1: Write test for Blueprint.model_dump()**

```python
class TestBlueprintSchemaC:
    def test_modern_blueprint_model_dump(self):
        bp = Blueprint(
            name="Craft",
            category_tag="abc123",
            operation="",
            inputs=["def456 x 3", "ghi789"],
            outputs=["this"],
            skill="Craft",
            skill_level=1,
            workstation_tags=["ws123"],
        )
        d = bp.model_dump()
        assert d["name"] == "Craft"
        assert d["inputs"] == ["def456 x 3", "ghi789"]
        assert d["outputs"] == ["this"]
        assert d["skill"] == "Craft"
        assert d["workstation_tags"] == ["ws123"]
```

**Step 2: Convert Blueprint to BaseModel**

Same fields, replace `@dataclass` with `BaseModel`. The `list_from_raw()` and `_parse_legacy_blueprints()` static methods stay identical.

**Step 3: Run all blueprint tests**

```bash
pytest unturned_data/tests/test_models.py -k blueprint -v
```

**Step 4: Commit**

```bash
git add unturned_data/models.py unturned_data/tests/test_models.py
git commit -m "refactor: convert Blueprint to Pydantic BaseModel"
```

---

### Task 5: Update category models (items, animals, vehicles, generic)

Each category subclass needs:
1. Convert from `@dataclass` to Pydantic BaseModel subclass
2. Replace `to_dict()` with a `parsed` computed_field that returns type-specific fields
3. Keep `from_raw()` logic (it works)
4. Keep `markdown_columns()` and `markdown_row()`

**Files:**
- Modify: `unturned_data/categories/items.py` (all 9 classes)
- Modify: `unturned_data/categories/animals.py`
- Modify: `unturned_data/categories/vehicles.py`
- Modify: `unturned_data/categories/generic.py`
- Test: `unturned_data/tests/test_categories.py`

**Step 1: Write test for Gun.parsed field**

```python
class TestGunSchemaC:
    def test_gun_parsed_field(self):
        raw, english = _load_fixture("gun_maplestrike")
        gun = Gun.from_raw(raw, english, "Items/Guns/Maplestrike")
        d = gun.model_dump()
        # parsed contains gun-specific fields
        parsed = d["parsed"]
        assert "slot" in parsed
        assert "firerate" in parsed
        assert "damage" in parsed
        assert parsed["damage"]["player"] == 40
        # top-level has Schema C fields
        assert d["guid"]
        assert d["type"] == "Gun"
        assert d["english"]["Name"] == "Maplestrike"
        assert d["raw"]["Type"] == "Gun"
```

**Step 2: Convert Gun as the template**

```python
class Gun(BundleEntry):
    """Firearm (Type=Gun)."""
    damage: DamageStats | None = None
    slot: str = ""
    caliber: int = 0
    firerate: int = 0
    gun_range: float = 0  # 'range' is a Python builtin, renamed
    fire_modes: list[str] = []
    hooks: list[str] = []
    ammo_min: int = 0
    ammo_max: int = 0
    durability: float = 0
    spread_aim: float = 0
    spread_angle: float = 0

    @computed_field
    @property
    def parsed(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "slot": self.slot,
            "caliber": self.caliber,
            "firerate": self.firerate,
            "range": self.gun_range,
            "fire_modes": self.fire_modes,
            "hooks": self.hooks,
            "ammo_min": self.ammo_min,
            "ammo_max": self.ammo_max,
            "durability": self.durability,
            "spread_aim": self.spread_aim,
            "spread_angle": self.spread_angle,
        }
        if self.damage:
            d["damage"] = self.damage.model_dump()
        else:
            d["damage"] = None
        return d

    @classmethod
    def from_raw(cls, raw, english, source_path) -> Gun:
        base = BundleEntry.from_raw(raw, english, source_path)
        fire_modes = [m for m in ("Safety", "Semi", "Auto", "Burst") if raw.get(m)]
        hooks = [k[5:] for k, v in raw.items() if k.startswith("Hook_") and v]
        return cls(
            **base.model_dump(exclude={"category", "parsed"}),
            damage=DamageStats.from_raw(raw),
            slot=str(raw.get("Slot", "")),
            caliber=int(raw.get("Caliber", 0)),
            firerate=int(raw.get("Firerate", 0)),
            gun_range=float(raw.get("Range", 0)),
            fire_modes=fire_modes,
            hooks=hooks,
            ammo_min=int(raw.get("Ammo_Min", 0)),
            ammo_max=int(raw.get("Ammo_Max", 0)),
            durability=float(raw.get("Durability", 0)),
            spread_aim=float(raw.get("Spread_Aim", 0)),
            spread_angle=float(raw.get("Spread_Angle_Degrees", 0)),
        )
```

**Key pattern:** Each category class:
- Stores type-specific fields as model attributes (for the markdown formatter to access)
- Overrides the `parsed` computed_field to expose them in `model_dump()` output
- Uses `base.model_dump(exclude={"category", "parsed"})` to spread base fields into constructor (computed fields can't be passed to constructor)

**Note on `from_raw()` inheritance pattern change:** Currently uses `**{k: v for k, v in base.__dict__.items()}`. With Pydantic, use `**base.model_dump(exclude={"category", "parsed"})` since computed fields aren't constructor args.

**Step 3: Apply the same pattern to all 12 remaining classes**

- `MeleeWeapon`: parsed = {slot, range, strength, stamina, durability, damage}
- `Consumeable`: parsed = {consumable: {health, food, water, virus, vision, bleeding_modifier}}
- `Clothing`: parsed = {storage: {width, height}, armor}
- `Throwable`: parsed = {fuse, explosion, damage}
- `BarricadeItem`: parsed = {health, range, build, storage, damage}
- `StructureItem`: parsed = {health, range, construct}
- `Magazine`: parsed = {amount, count_min, count_max}
- `Attachment`: parsed = {} (no extra fields)
- `Animal`: parsed = {health, damage, speed_run, speed_walk, behaviour, regen, reward_id, reward_xp}
- `Vehicle`: parsed = {speed_min, speed_max, steer_min, steer_max, brake, fuel_min, fuel_max, fuel_capacity, health_min, health_max, trunk_x, trunk_y}
- `GenericEntry`: parsed = {} (raw is already at top level)

**Step 4: Run all category tests**

```bash
pytest unturned_data/tests/test_categories.py -v
```

Fix any failures. Existing tests that check `entry.to_dict()["slot"]` need updating to `entry.model_dump()["parsed"]["slot"]`.

**Step 5: Commit**

```bash
git add unturned_data/categories/ unturned_data/tests/test_categories.py
git commit -m "refactor: convert all category models to Pydantic with parsed field"
```

---

### Task 6: Convert SpawnTable and SpawnTableEntry to Pydantic

**Files:**
- Modify: `unturned_data/models.py:522-556` (SpawnTable, SpawnTableEntry)
- Modify: `unturned_data/categories/spawns.py`
- Test: `unturned_data/tests/test_spawn_model.py`, `unturned_data/tests/test_spawn_parsing.py`

**Step 1: Write test for SpawnTable Schema C shape**

```python
def test_spawn_table_model_dump():
    table = SpawnTable(
        guid="abc", type="Spawn", id=228, name="Militia",
        source_path="Spawns/Items/Militia",
        english={"Name": "Militia"}, raw={},
        table_entries=[
            SpawnTableEntry(ref_type="spawn", ref_id=229, weight=960),
            SpawnTableEntry(ref_type="asset", ref_id=1041, weight=200),
        ],
    )
    d = table.model_dump()
    assert d["type"] == "Spawn"
    parsed = d["parsed"]
    assert "table_entries" in parsed
    assert len(parsed["table_entries"]) == 2
    assert parsed["table_entries"][0]["ref_type"] == "spawn"
```

**Step 2: Convert SpawnTableEntry and SpawnTable**

SpawnTableEntry → Pydantic BaseModel (simple).

SpawnTable → Pydantic BaseModel extending BundleEntry. Override `parsed` to include `table_entries`.

SpawnTableCategory stays as subclass of SpawnTable; its `from_raw()` logic is unchanged.

**Step 3: Run spawn tests**

```bash
pytest unturned_data/tests/ -k spawn -v
```

**Step 4: Commit**

```bash
git add unturned_data/models.py unturned_data/categories/spawns.py unturned_data/tests/
git commit -m "refactor: convert SpawnTable to Pydantic with parsed field"
```

---

## Phase 2: Schema C Export Pipeline

### Task 7: Create Schema C output models

Pydantic models for the export file structures (manifest, map config, guid index).

**Files:**
- Create: `unturned_data/schema.py`
- Create: `unturned_data/tests/test_schema.py`

**Step 1: Write tests for export models**

```python
from unturned_data.schema import Manifest, MapConfig, GuidIndexEntry

class TestManifest:
    def test_manifest_structure(self):
        m = Manifest(
            version="1.0.0",
            generated_at="2026-02-19T14:30:00Z",
            generator="unturned_data v0.6.0",
            base_bundles_path="/path/to/Bundles",
            base_entry_count=4376,
            base_asset_count=690,
            maps={},
        )
        d = m.model_dump()
        assert d["version"] == "1.0.0"
        assert d["base_entry_count"] == 4376

class TestMapConfig:
    def test_map_config_with_blacklist(self):
        mc = MapConfig(
            name="A6 Polaris",
            source_path="/path/to/A6 Polaris",
            config={"version": "1.0.3.4"},
            level_asset={"guid": "abc123"},
            crafting_blacklists=[],
            spawn_resolution={"active_table_ids": [36100]},
        )
        d = mc.model_dump()
        assert d["name"] == "A6 Polaris"
```

**Step 2: Create schema.py**

```python
"""Pydantic models for Schema C export file structures."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ManifestMapInfo(BaseModel):
    """Per-map info in the manifest."""
    map_file: str                # e.g. "maps/a6_polaris/map.json"
    has_custom_entries: bool = False
    entries_file: str | None = None
    assets_file: str | None = None
    entry_count: int = 0
    asset_count: int = 0


class Manifest(BaseModel):
    """manifest.json structure."""
    version: str = "1.0.0"
    schema_name: str = "unturned-data-export"
    generated_at: str = ""
    generator: str = ""
    base_bundles_path: str = ""
    base_entry_count: int = 0
    base_asset_count: int = 0
    maps: dict[str, ManifestMapInfo] = {}
    guid_index_file: str = "guid_index.json"


class CraftingBlacklistInfo(BaseModel):
    """Crafting blacklist info for map.json."""
    guid: str
    source_path: str = ""
    allow_core_blueprints: bool = True
    blocked_input_guids: list[str] = []
    blocked_output_guids: list[str] = []


class LevelAssetInfo(BaseModel):
    """Level asset info for map.json."""
    guid: str
    source_path: str = ""
    crafting_blacklists: list[CraftingBlacklistInfo] = []
    skills: list[dict[str, Any]] = []
    weather_types: list[dict[str, Any]] = []
    raw: dict[str, Any] = {}


class SpawnResolution(BaseModel):
    """Spawn resolution results for map.json."""
    active_table_ids: list[int] = []
    active_table_names: list[str] = []
    spawnable_item_ids: list[int] = []
    spawnable_item_guids: list[str] = []
    table_chains: dict[int, list[int]] = {}
    # table_chains: table_id -> list of resolved leaf item IDs


class MapConfig(BaseModel):
    """map.json structure."""
    name: str
    source_path: str = ""
    workshop_id: int | None = None
    config: dict[str, Any] = {}       # raw Config.json contents
    level_asset: LevelAssetInfo | None = None
    crafting_blacklists: list[CraftingBlacklistInfo] = []
    spawn_resolution: SpawnResolution = SpawnResolution()
    master_bundle: dict[str, Any] | None = None


class AssetEntry(BaseModel):
    """Entry in assets.json."""
    guid: str
    name: str = ""
    csharp_type: str = ""
    source_path: str = ""
    raw: dict[str, Any] = {}


class GuidIndexEntry(BaseModel):
    """Entry in guid_index.json."""
    file: str          # e.g. "base/entries.json"
    index: int
    id: int = 0
    type: str = ""
    name: str = ""


class GuidIndex(BaseModel):
    """guid_index.json structure."""
    total_entries: int = 0
    generated_at: str = ""
    entries: dict[str, GuidIndexEntry] = {}  # guid -> entry
    by_id: dict[str, str] = {}               # str(id) -> guid
```

**Step 3: Run tests**

```bash
pytest unturned_data/tests/test_schema.py -v
```

**Step 4: Commit**

```bash
git add unturned_data/schema.py unturned_data/tests/test_schema.py
git commit -m "feat: add Pydantic models for Schema C export structures"
```

---

### Task 8: Create exporter core (entries.json generation)

The core function that walks bundles, categorizes by origin, and writes entries.json files.

**Files:**
- Create: `unturned_data/exporter.py`
- Create: `unturned_data/tests/test_exporter.py`

**Step 1: Write tests**

```python
import json
import tempfile
from pathlib import Path
from unturned_data.exporter import export_schema_c
from unturned_data.models import BundleEntry

class TestExporterCore:
    def test_creates_output_directory_structure(self, tmp_path):
        """Export creates manifest.json and base/ directory."""
        # Use test fixtures as a minimal "bundles" dir
        fixtures = Path(__file__).parent / "fixtures"
        export_schema_c(
            base_bundles=fixtures,
            map_dirs=[],
            output_dir=tmp_path,
        )
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "base" / "entries.json").exists()
        assert (tmp_path / "guid_index.json").exists()

    def test_entries_json_has_schema_c_shape(self, tmp_path):
        fixtures = Path(__file__).parent / "fixtures"
        export_schema_c(
            base_bundles=fixtures,
            map_dirs=[],
            output_dir=tmp_path,
        )
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        assert isinstance(entries, list)
        if entries:
            e = entries[0]
            assert "guid" in e
            assert "parsed" in e
            assert "english" in e
            assert "raw" in e
            assert "blueprints" in e
            assert "category" in e
```

**Step 2: Implement exporter core**

```python
"""Schema C origin-first export pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unturned_data.categories import parse_entry
from unturned_data.loader import walk_bundle_dir, walk_asset_files
from unturned_data.models import BundleEntry
from unturned_data.schema import (
    AssetEntry, GuidIndex, GuidIndexEntry, Manifest, ManifestMapInfo,
)


def _serialize_entries(entries: list[BundleEntry]) -> list[dict[str, Any]]:
    """Serialize entries to Schema C dicts, sorted by (name, id)."""
    entries_sorted = sorted(entries, key=lambda e: (e.name, e.id))
    return [e.model_dump() for e in entries_sorted]


def _collect_assets(bundles_path: Path) -> list[AssetEntry]:
    """Collect .asset file entries from a bundles directory."""
    from unturned_data.dat_parser import parse_asset_file

    assets: list[AssetEntry] = []
    for asset_file in sorted(bundles_path.rglob("*.asset")):
        try:
            parsed = parse_asset_file(asset_file)
        except Exception:
            continue
        meta = parsed.get("Metadata", {})
        if not isinstance(meta, dict):
            continue
        guid = str(meta.get("GUID", "")).lower()
        if not guid:
            continue
        csharp_type = str(meta.get("Type", ""))
        # Extract just the class name from fully qualified C# type
        type_short = csharp_type.split(",")[0].rsplit(".", 1)[-1] if csharp_type else ""
        rel_path = str(asset_file.relative_to(bundles_path))
        assets.append(AssetEntry(
            guid=guid,
            name=asset_file.stem.replace("_", " "),
            csharp_type=type_short,
            source_path=rel_path,
            raw=parsed,
        ))
    return assets


def export_schema_c(
    base_bundles: Path,
    map_dirs: list[Path],
    output_dir: Path,
) -> None:
    """Run the full Schema C export pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    # --- Parse base game entries ---
    base_entries: list[BundleEntry] = []
    for raw, english, rel_path in walk_bundle_dir(base_bundles):
        if not raw:
            continue
        base_entries.append(parse_entry(raw, english, rel_path))

    # --- Write base/entries.json ---
    base_dir = output_dir / "base"
    base_dir.mkdir(exist_ok=True)
    base_dicts = _serialize_entries(base_entries)
    (base_dir / "entries.json").write_text(
        json.dumps(base_dicts, indent=2, ensure_ascii=False)
    )

    # --- Collect and write base/assets.json ---
    base_assets = _collect_assets(base_bundles)
    (base_dir / "assets.json").write_text(
        json.dumps([a.model_dump() for a in base_assets], indent=2, ensure_ascii=False)
    )

    # --- Process each map (Task 9 fills in map.json details) ---
    manifest_maps: dict[str, ManifestMapInfo] = {}
    all_entries = list(base_entries)  # for guid index
    all_assets = list(base_assets)

    for map_dir in map_dirs:
        map_name = map_dir.resolve().name
        safe_name = map_name.lower().replace(" ", "_")
        map_out = output_dir / "maps" / safe_name
        map_out.mkdir(parents=True, exist_ok=True)

        map_info = ManifestMapInfo(
            map_file=f"maps/{safe_name}/map.json",
        )

        # Parse map-specific entries
        map_bundles = map_dir / "Bundles"
        map_entries: list[BundleEntry] = []
        if map_bundles.is_dir():
            for raw, english, rel_path in walk_bundle_dir(map_bundles):
                if not raw:
                    continue
                map_entries.append(parse_entry(raw, english, rel_path))

        if map_entries:
            map_dicts = _serialize_entries(map_entries)
            (map_out / "entries.json").write_text(
                json.dumps(map_dicts, indent=2, ensure_ascii=False)
            )
            map_info.has_custom_entries = True
            map_info.entries_file = f"maps/{safe_name}/entries.json"
            map_info.entry_count = len(map_entries)
            all_entries.extend(map_entries)

        # Map assets
        if map_bundles.is_dir():
            map_assets = _collect_assets(map_bundles)
            if map_assets:
                (map_out / "assets.json").write_text(
                    json.dumps([a.model_dump() for a in map_assets],
                               indent=2, ensure_ascii=False)
                )
                map_info.assets_file = f"maps/{safe_name}/assets.json"
                map_info.asset_count = len(map_assets)
                all_assets.extend(map_assets)

        manifest_maps[map_name] = map_info

    # --- Write guid_index.json (Task 10) ---
    guid_index = _build_guid_index(
        base_entries, base_assets, map_dirs, all_entries, all_assets, now
    )
    (output_dir / "guid_index.json").write_text(
        json.dumps(guid_index.model_dump(), indent=2, ensure_ascii=False)
    )

    # --- Write manifest.json ---
    manifest = Manifest(
        generated_at=now,
        generator="unturned_data v0.6.0",
        base_bundles_path=str(base_bundles),
        base_entry_count=len(base_entries),
        base_asset_count=len(base_assets),
        maps=manifest_maps,
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), indent=2, ensure_ascii=False)
    )


def _build_guid_index(
    base_entries, base_assets, map_dirs, all_entries, all_assets, now,
) -> GuidIndex:
    """Placeholder -- Task 10 implements this fully."""
    return GuidIndex(generated_at=now, total_entries=len(all_entries))
```

**Step 3: Run tests**

```bash
pytest unturned_data/tests/test_exporter.py -v
```

**Step 4: Commit**

```bash
git add unturned_data/exporter.py unturned_data/tests/test_exporter.py
git commit -m "feat: core Schema C exporter (entries.json + assets.json)"
```

---

### Task 9: Build map.json with spawn resolution and blacklists

**Files:**
- Modify: `unturned_data/exporter.py`
- Test: `unturned_data/tests/test_exporter.py`

**Step 1: Write tests for map.json generation**

```python
class TestMapJsonGeneration:
    def test_map_json_created_for_each_map(self, tmp_path, mock_map_dir):
        """map.json is created with config, spawn resolution, blacklists."""
        export_schema_c(
            base_bundles=fixtures,
            map_dirs=[mock_map_dir],
            output_dir=tmp_path,
        )
        map_json_path = tmp_path / "maps" / mock_map_dir.name.lower().replace(" ", "_") / "map.json"
        assert map_json_path.exists()
        data = json.loads(map_json_path.read_text())
        assert "name" in data
        assert "spawn_resolution" in data
```

**Step 2: Add map.json generation to exporter**

Inside the map processing loop in `export_schema_c()`, after parsing map entries:

```python
from unturned_data.crafting_blacklist import resolve_crafting_blacklist
from unturned_data.map_resolver import (
    determine_active_tables, resolve_spawn_table_items,
)
from unturned_data.schema import MapConfig, SpawnResolution

# Build spawn table lookups from all entries
tables_by_id = {e.id: e for e in all_entries if isinstance(e, SpawnTable) and e.id}
table_name_to_id = {e.name: e.id for e in all_entries if isinstance(e, SpawnTable) and e.id and e.name}
id_to_guid = {e.id: e.guid for e in all_entries if e.id and e.guid}

# Resolve active tables and spawnable items
active_ids = determine_active_tables(map_dir, tables_by_id, table_name_to_id)
table_chains: dict[int, list[int]] = {}
spawnable_ids: set[int] = set()
for tid in active_ids:
    resolved = resolve_spawn_table_items(tid, tables_by_id)
    table_chains[tid] = sorted(resolved)
    spawnable_ids |= resolved

spawnable_guids = sorted(id_to_guid[i] for i in spawnable_ids if i in id_to_guid)
active_names = sorted(tables_by_id[i].name for i in active_ids if i in tables_by_id)

# Resolve crafting blacklists
blacklist = resolve_crafting_blacklist(map_dir, [base_bundles])

# Read Config.json if present
config_data = {}
config_path = map_dir / "Config.json"
if config_path.exists():
    import json as json_mod
    config_data = json_mod.loads(config_path.read_text())

# Build and write map.json
map_config = MapConfig(
    name=map_name,
    source_path=str(map_dir),
    config=config_data,
    spawn_resolution=SpawnResolution(
        active_table_ids=sorted(active_ids),
        active_table_names=active_names,
        spawnable_item_ids=sorted(spawnable_ids),
        spawnable_item_guids=spawnable_guids,
        table_chains=table_chains,
    ),
)
(map_out / "map.json").write_text(
    json.dumps(map_config.model_dump(), indent=2, ensure_ascii=False)
)
```

**Step 3: Run tests**

```bash
pytest unturned_data/tests/test_exporter.py -v
```

**Step 4: Commit**

```bash
git add unturned_data/exporter.py unturned_data/tests/test_exporter.py
git commit -m "feat: map.json with spawn resolution and crafting blacklists"
```

---

### Task 10: Build guid_index.json

**Files:**
- Modify: `unturned_data/exporter.py` (replace `_build_guid_index` placeholder)
- Test: `unturned_data/tests/test_exporter.py`

**Step 1: Write test**

```python
class TestGuidIndex:
    def test_guid_index_contains_all_entries(self, tmp_path):
        fixtures = Path(__file__).parent / "fixtures"
        export_schema_c(base_bundles=fixtures, map_dirs=[], output_dir=tmp_path)
        index = json.loads((tmp_path / "guid_index.json").read_text())
        # Every entry with a GUID should be in the index
        entries = json.loads((tmp_path / "base" / "entries.json").read_text())
        for e in entries:
            if e["guid"]:
                assert e["guid"] in index["entries"]

    def test_by_id_reverse_lookup(self, tmp_path):
        fixtures = Path(__file__).parent / "fixtures"
        export_schema_c(base_bundles=fixtures, map_dirs=[], output_dir=tmp_path)
        index = json.loads((tmp_path / "guid_index.json").read_text())
        # by_id maps str(id) -> guid
        for id_str, guid in index["by_id"].items():
            assert guid in index["entries"]
```

**Step 2: Implement _build_guid_index**

```python
def _build_guid_index(
    base_entries, base_assets, map_dirs, all_entries, all_assets, now,
) -> GuidIndex:
    entries_map: dict[str, GuidIndexEntry] = {}
    by_id: dict[str, str] = {}

    # Base entries
    for i, e in enumerate(sorted(base_entries, key=lambda x: (x.name, x.id))):
        if e.guid:
            entries_map[e.guid] = GuidIndexEntry(
                file="base/entries.json", index=i,
                id=e.id, type=e.type, name=e.name,
            )
            if e.id:
                by_id[str(e.id)] = e.guid

    # Base assets
    for i, a in enumerate(base_assets):
        if a.guid and a.guid not in entries_map:
            entries_map[a.guid] = GuidIndexEntry(
                file="base/assets.json", index=i,
                type=a.csharp_type, name=a.name,
            )

    # Map entries and assets
    for map_dir in map_dirs:
        map_name = map_dir.resolve().name
        safe_name = map_name.lower().replace(" ", "_")
        map_entries_in_all = [
            e for e in all_entries
            if e not in base_entries  # crude; real impl tracks per-map
        ]
        # (Real implementation tracks which entries belong to which map)

    return GuidIndex(
        generated_at=now,
        total_entries=len(entries_map),
        entries=entries_map,
        by_id=by_id,
    )
```

**Note:** The real implementation needs to properly track per-map entry indices. The exporter should maintain per-map entry lists during processing and pass them to this function.

**Step 3: Run tests**

```bash
pytest unturned_data/tests/test_exporter.py -v
```

**Step 4: Commit**

```bash
git add unturned_data/exporter.py unturned_data/tests/test_exporter.py
git commit -m "feat: guid_index.json with entry and asset cross-references"
```

---

### Task 11: Rewrite CLI

Replace the existing format-selection CLI with Schema C export.

**Files:**
- Rewrite: `unturned_data/cli.py`
- Modify: `unturned_data/__main__.py` (if needed)
- Test: `unturned_data/tests/test_cli.py` (new)

**Step 1: Write CLI test**

```python
import json
from pathlib import Path
from unturned_data.cli import main

class TestCLI:
    def test_basic_export(self, tmp_path):
        fixtures = Path(__file__).parent / "fixtures"
        main([str(fixtures), "--output", str(tmp_path)])
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "base" / "entries.json").exists()

    def test_format_json_default(self, tmp_path):
        fixtures = Path(__file__).parent / "fixtures"
        main([str(fixtures), "--output", str(tmp_path), "--format", "json"])
        assert (tmp_path / "base" / "entries.json").exists()

    def test_format_markdown(self, tmp_path, capsys):
        fixtures = Path(__file__).parent / "fixtures"
        main([str(fixtures), "--format", "markdown"])
        captured = capsys.readouterr()
        assert "##" in captured.out
```

**Step 2: Rewrite cli.py**

```python
"""CLI entry point for the unturned-data tool."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unturned_data.exporter import export_schema_c
from unturned_data.categories import parse_entry
from unturned_data.loader import (
    collect_comment_guids_from_dir,
    walk_asset_files,
    walk_bundle_dir,
)
from unturned_data.formatters.markdown_fmt import entries_to_markdown
from unturned_data.models import BundleEntry


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="unturned-data",
        description="Parse Unturned .dat bundle files and export data.",
    )
    parser.add_argument("path", type=Path, help="Path to a Bundles directory")
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json). 'json' writes Schema C directory tree. 'markdown' prints to stdout.",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output directory for JSON export (required for --format json)",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=None,
        type=Path,
        metavar="DIR",
        help="Path to a map directory (repeatable).",
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=[],
        metavar="PATH",
        help="Exclude entries matching path segments.",
    )
    args = parser.parse_args(argv)

    bundle_path: Path = args.path.resolve()
    if not bundle_path.is_dir():
        print(f"Error: {bundle_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        if not args.output:
            print("Error: --output is required for JSON format", file=sys.stderr)
            sys.exit(1)
        export_schema_c(
            base_bundles=bundle_path,
            map_dirs=[m.resolve() for m in (args.map or [])],
            output_dir=args.output.resolve(),
        )
        print(f"Export complete: {args.output}")

    elif args.format == "markdown":
        entries: list[BundleEntry] = []
        for raw, english, rel_path in walk_bundle_dir(bundle_path):
            if not raw:
                continue
            if args.exclude and _is_excluded(rel_path, args.exclude):
                continue
            entries.append(parse_entry(raw, english, rel_path))

        # Add map entries if specified
        if args.map:
            for map_dir in args.map:
                map_bundles = map_dir / "Bundles"
                if map_bundles.is_dir():
                    for raw, english, rel_path in walk_bundle_dir(map_bundles):
                        if not raw:
                            continue
                        entries.append(parse_entry(raw, english, rel_path))

        supplementary: dict[str, str] = {}
        supplementary.update(walk_asset_files(bundle_path))
        supplementary.update(collect_comment_guids_from_dir(bundle_path))
        print(entries_to_markdown(entries, supplementary_guids=supplementary))


def _is_excluded(source_path: str, patterns: list[str]) -> bool:
    path_parts = source_path.split("/")
    for pattern in patterns:
        pat_parts = pattern.strip("/").split("/")
        for i in range(len(path_parts) - len(pat_parts) + 1):
            if path_parts[i : i + len(pat_parts)] == pat_parts:
                return True
    return False
```

**Step 3: Run tests**

```bash
pytest unturned_data/tests/test_cli.py -v
```

**Step 4: Commit**

```bash
git add unturned_data/cli.py unturned_data/tests/test_cli.py
git commit -m "feat: rewrite CLI for Schema C export + markdown output"
```

---

## Phase 3: Update Formatters

### Task 12: Update json_fmt.py for Schema C

The JSON formatter now only needs to serialize entries to a flat list (the nested tree format is replaced by Schema C's origin-first directories). However, the actual JSON writing is done by the exporter. The formatter becomes a thin utility.

**Files:**
- Modify: `unturned_data/formatters/json_fmt.py`
- Test: `unturned_data/tests/test_json_fmt.py`

**Step 1: Simplify json_fmt to work with new model_dump()**

The exporter already calls `model_dump()` and writes JSON. The json_fmt module can be simplified or its tests updated to use `model_dump()` instead of `to_dict()`.

**Step 2: Run tests**

```bash
pytest unturned_data/tests/test_json_fmt.py -v
```

Fix any `to_dict()` → `model_dump()` references.

**Step 3: Commit**

```bash
git add unturned_data/formatters/json_fmt.py unturned_data/tests/test_json_fmt.py
git commit -m "refactor: update json_fmt for Pydantic model_dump()"
```

---

### Task 13: Update markdown_fmt.py

The markdown formatter needs to work with the new Pydantic models. The main change: `entry.category_parts` → `entry.category`. The `markdown_columns()` and `markdown_row()` methods are preserved on the model classes.

**Files:**
- Modify: `unturned_data/formatters/markdown_fmt.py`
- Test: `unturned_data/tests/test_markdown_fmt.py`

**Step 1: Update `_build_tree` to use `entry.category`**

In `markdown_fmt.py:77-87`, change `entry.category_parts` → `entry.category`.

**Step 2: Run tests**

```bash
pytest unturned_data/tests/test_markdown_fmt.py -v
```

Fix any other references to old field names.

**Step 3: Commit**

```bash
git add unturned_data/formatters/markdown_fmt.py unturned_data/tests/test_markdown_fmt.py
git commit -m "refactor: update markdown_fmt for Pydantic models"
```

---

## Phase 4: Cleanup & Integration

### Task 14: Remove dead code and update formatters/__init__.py

**Files:**
- Delete: `unturned_data/formatters/web_fmt.py`
- Delete: `unturned_data/formatters/crafting_fmt.py`
- Delete: `unturned_data/generate_web_data.sh`
- Delete: `unturned_data/tests/test_web_map.py`
- Delete: `unturned_data/tests/test_crafting_fmt.py`
- Delete: `unturned_data/tests/test_crafting_stub_fix.py`
- Modify: `unturned_data/formatters/__init__.py`
- Delete related tests: `test_blacklist_integration.py` (if only testing crafting fmt), `test_cli_map.py` (old CLI)

**Step 1: Remove files**

```bash
git rm unturned_data/formatters/web_fmt.py
git rm unturned_data/formatters/crafting_fmt.py
git rm unturned_data/generate_web_data.sh
git rm unturned_data/tests/test_web_map.py
git rm unturned_data/tests/test_crafting_fmt.py
git rm unturned_data/tests/test_crafting_stub_fix.py
```

**Step 2: Update formatters/__init__.py**

Remove imports of deleted modules.

**Step 3: Run full test suite**

```bash
pytest unturned_data/tests/ -v
```

Fix any remaining import errors or references to deleted code.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove web_fmt, crafting_fmt, and dead code"
```

---

### Task 15: Integration test with real bundle data

**Files:**
- Modify: `unturned_data/tests/test_integration.py`

**Step 1: Update integration test for Schema C**

```python
class TestSchemaC:
    """Integration test with full bundle data."""

    @pytest.fixture(scope="class")
    def export_dir(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("export")
        export_schema_c(
            base_bundles=BUNDLES,
            map_dirs=[],  # add real maps if available
            output_dir=out,
        )
        return out

    def test_manifest_exists(self, export_dir):
        assert (export_dir / "manifest.json").exists()

    def test_entry_count(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        assert len(entries) > 1000

    def test_all_entries_have_schema_c_fields(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        required = {"guid", "type", "id", "name", "description", "rarity",
                     "source_path", "category", "english", "parsed",
                     "blueprints", "raw"}
        for e in entries[:100]:  # spot check first 100
            assert required.issubset(e.keys()), f"Missing fields in {e.get('name')}"

    def test_guid_index_covers_entries(self, export_dir):
        entries = json.loads((export_dir / "base" / "entries.json").read_text())
        index = json.loads((export_dir / "guid_index.json").read_text())
        guids_with_values = [e["guid"] for e in entries if e["guid"]]
        for guid in guids_with_values[:50]:
            assert guid in index["entries"]
```

**Step 2: Run integration test (requires real data at ~/unturned-bundles)**

```bash
pytest unturned_data/tests/test_integration.py -v
```

**Step 3: Commit**

```bash
git add unturned_data/tests/test_integration.py
git commit -m "test: update integration tests for Schema C export"
```

---

## Notes for Implementation

### Watch out for these:

1. **Pydantic computed_field + inheritance**: When a subclass overrides `parsed`, Pydantic needs the `@computed_field` decorator on each override. Test that `Gun.model_dump()["parsed"]` actually contains gun fields and not empty `{}`.

2. **`from_raw()` constructor spreading**: With Pydantic, `base.__dict__` won't work. Use `base.model_dump(exclude={"category", "parsed"})` to get a dict of field values suitable for passing to the subclass constructor. `category` and `parsed` are computed fields that aren't constructor parameters.

3. **Default mutable values**: Pydantic v2 handles `list[str] = []` correctly (creates new list per instance), unlike dataclasses which need `field(default_factory=list)`. However, `dict` defaults should use `Field(default_factory=dict)` to be safe.

4. **Test fixture compatibility**: The `_load_fixture()` helper in tests loads real .dat files. These tests should continue to work since `from_raw()` API is unchanged. But assertions on `to_dict()` need updating to `model_dump()`.

5. **Markdown formatter stability**: `markdown_row()` and `markdown_columns()` stay on the model classes. The formatter calls them directly. This interface is unchanged.

6. **CraftingBlacklist**: This model is only used internally (not serialized to entries.json). It can stay as a dataclass or be converted too -- implementer's choice. Converting keeps consistency.

7. **Performance**: `model_dump()` on 8000+ entries will be slower than raw dict construction. If this becomes a problem, consider `model_dump(mode="python")` or caching. Likely fine for batch export.
