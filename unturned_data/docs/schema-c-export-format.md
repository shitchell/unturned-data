# Schema C Export Format

## Overview

The `unturnedd` tool parses an Unturned dedicated server's game data files and exports structured JSON organized by **origin** -- base game content lives in `base/`, each map's content lives in `maps/<name>/`. A global GUID index ties everything together.

This document describes the output format, what each file contains, and how the data fits together. It is intended for anyone building tools or web pages that consume this data.

## Quick Start

```bash
# Export all maps
unturnedd ~/unturned-server -o ./export

# Export specific maps only
unturnedd ~/unturned-server -o ./export --map PEI --map "A6 Polaris"

# Markdown to stdout
unturnedd ~/unturned-server -f markdown
```

The tool auto-discovers maps from the server directory (built-in maps in `Maps/` and workshop maps in `Servers/*/Workshop/Steam/content/304930/*/`).

## Output Directory Structure

```
export/
  manifest.json                  # What's in this export
  guid_index.json                # Master GUID -> location lookup
  base/
    entries.json                 # All base game entries (~5 MB, ~5000 entries)
    assets.json                  # All base game .asset files
  maps/
    pei/
      map.json                   # PEI config, spawn resolution, blacklists
    a6_polaris/
      entries.json               # Polaris-specific entries (~3.5 MB, ~650 entries)
      assets.json                # Polaris-specific .asset files
      map.json                   # Polaris config, spawn resolution, blacklists
```

Key points:
- **Base game** content (items, spawn tables, vehicles, etc.) is in `base/`
- **Each map** gets a directory under `maps/<safe_name>/` (lowercase, spaces to underscores)
- Maps that add custom content (like A6 Polaris) have their own `entries.json` and `assets.json`
- Maps that only reference base game content (like PEI) have just `map.json`
- `guid_index.json` indexes everything by GUID for cross-file lookups

---

## manifest.json

Top-level metadata about the export.

```json
{
  "version": "1.0.0",
  "schema_name": "unturned-data-export",
  "generated_at": "2026-02-19T18:30:00.123456+00:00",
  "generator": "unturned-data",
  "base_bundles_path": "/home/guy/unturned-server/Bundles",
  "base_entry_count": 4981,
  "base_asset_count": 690,
  "maps": {
    "pei": {
      "map_file": "maps/pei/map.json",
      "has_custom_entries": false,
      "entries_file": null,
      "assets_file": null,
      "entry_count": 0,
      "asset_count": 0
    },
    "a6_polaris": {
      "map_file": "maps/a6_polaris/map.json",
      "has_custom_entries": true,
      "entries_file": "maps/a6_polaris/entries.json",
      "assets_file": "maps/a6_polaris/assets.json",
      "entry_count": 647,
      "asset_count": 52
    }
  },
  "guid_index_file": "guid_index.json"
}
```

| Field | Description |
|-------|-------------|
| `version` | Schema version (semver) |
| `generated_at` | ISO 8601 timestamp |
| `base_entry_count` | Number of entries in `base/entries.json` |
| `maps` | Per-map info keyed by safe name |
| `maps.*.has_custom_entries` | Whether this map adds its own items/spawns |
| `maps.*.entries_file` | Path to map's entries.json (null if no custom entries) |

---

## entries.json (base and per-map)

A flat JSON array of entry objects, sorted by `(name, id)`. Every entry -- whether it's a Gun, Food item, Vehicle, Spawn Table, or Animal -- uses the same 14-field shape:

```json
{
  "guid": "667ba2f0aba7484888bcfbec2a43798b",
  "type": "Gun",
  "id": 353,
  "name": "Eaglefire",
  "description": "American 5.56mm assault rifle.",
  "rarity": "Legendary",
  "size_x": 5,
  "size_y": 2,
  "source_path": "Items/Guns/Eaglefire",
  "category": ["Items", "Guns"],
  "english": {
    "Name": "Eaglefire",
    "Description": "American 5.56mm assault rifle.",
    "Examine": "Reliable military issue."
  },
  "parsed": { ... },
  "blueprints": [ ... ],
  "raw": { ... }
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `guid` | string | 32-char hex GUID, globally unique across all content |
| `type` | string | Unturned type (Gun, Food, Vehicle, Spawn, Animal, etc.) |
| `id` | int | Numeric ID (base game: 0-35999, workshop maps: 36000+) |
| `name` | string | Display name from English.dat |
| `description` | string | Description from English.dat |
| `rarity` | string | Common, Uncommon, Rare, Epic, Legendary, Mythical |
| `size_x`, `size_y` | int | Inventory grid dimensions |
| `source_path` | string | Relative path within the Bundles directory |
| `category` | string[] | Directory hierarchy (e.g. `["Items", "Guns"]`) |
| `english` | object | Full English.dat key-value pairs (Name, Description, Examine, etc.) |
| `parsed` | object | Type-specific extracted fields (see below) |
| `blueprints` | array | Crafting recipes owned by this item (see below) |
| `raw` | object | Complete parsed .dat file as-is (lossless) |

### The `parsed` Field

Contains type-specific fields extracted from the `.dat` file. The contents depend on the entry's `type`:

**Gun:**
```json
{
  "slot": "Primary",
  "caliber": 1,
  "firerate": 10,
  "range": 200.0,
  "fire_modes": ["Safety", "Semi", "Auto"],
  "hooks": ["Sight", "Tactical", "Grip", "Barrel"],
  "ammo_min": 1,
  "ammo_max": 30,
  "durability": 0.55,
  "spread_aim": 0.01,
  "spread_angle": 2.75,
  "damage": {
    "player": 40.0, "zombie": 99.0, "animal": 40.0,
    "barricade": 30.0, "structure": 30.0, "vehicle": 30.0,
    "resource": 20.0, "object": 20.0,
    "player_multipliers": {"skull": 1.1, "spine": 0.8, "arm": 0.6, "leg": 0.6},
    "zombie_multipliers": {"skull": 1.1, "spine": 0.8, "arm": 0.6, "leg": 0.6},
    "animal_multipliers": {}
  }
}
```

**Melee:** `slot`, `range`, `strength`, `stamina`, `durability`, `damage`

**Food / Water / Medical (Consumeable):**
```json
{
  "consumable": {
    "health": 20.0, "food": 50.0, "water": 30.0,
    "virus": 0.0, "vision": 0.0, "bleeding_modifier": ""
  }
}
```

**Clothing (Shirt, Pants, Hat, Vest, Backpack, Mask, Glasses):**
```json
{
  "storage": {"width": 5, "height": 3},
  "armor": 0.85
}
```

**Throwable:** `fuse`, `explosion`, `damage`

**Barricade / Trap / Storage / Sentry / Generator / Beacon / Oil_Pump:**
```json
{
  "health": 500.0, "range": 8.0, "build": "Plate",
  "storage": {"width": 6, "height": 4},
  "damage": { ... }
}
```

**Structure:** `health`, `range`, `construct`

**Magazine:** `amount`, `count_min`, `count_max`

**Attachment (Sight, Grip, Barrel, Tactical):** `{}` (no extra fields)

**Vehicle:**
```json
{
  "speed_min": 5.0, "speed_max": 14.0,
  "steer_min": 5.0, "steer_max": 5.0,
  "brake": 1.2,
  "fuel_min": 400.0, "fuel_max": 750.0, "fuel_capacity": 1500.0,
  "health_min": 200.0, "health_max": 200.0,
  "trunk_x": 6, "trunk_y": 4
}
```

**Animal:** `health`, `damage`, `speed_run`, `speed_walk`, `behaviour`, `regen`, `reward_id`, `reward_xp`

**Spawn (spawn tables):**
```json
{
  "table_entries": [
    {"ref_type": "spawn", "ref_id": 229, "ref_guid": "", "weight": 960},
    {"ref_type": "asset", "ref_id": 1041, "ref_guid": "", "weight": 200},
    {"ref_type": "guid", "ref_id": 0, "ref_guid": "e322656746a0...", "weight": 5}
  ]
}
```

**GenericEntry (unknown types):** `{}` (all data is in `raw`)

### The `blueprints` Field

Crafting recipes owned by this item. Each blueprint:

```json
{
  "name": "Craft",
  "category_tag": "ad1804b6945145f3b308738b0b8ea447",
  "operation": "",
  "inputs": ["46218740c256475b87dbc6a2e9a1fb19 x 7", "5ff4bcf752554990bf06e103b996cef2"],
  "outputs": ["this"],
  "skill": "Craft",
  "skill_level": 1,
  "workstation_tags": ["84347b13028340b8976033c08675d458"]
}
```

| Field | Description |
|-------|-------------|
| `name` | Blueprint type: "Craft", "Repair", "Salvage", or legacy type names |
| `inputs` | List of input items. Can be: `"GUID x N"`, `"GUID"`, `"this"`, `{"ID": "...", "Amount": N, "Delete": false}` (tools) |
| `outputs` | List of output items. `"this"` = the item that owns this blueprint |
| `skill` | Required skill (e.g. "Craft") |
| `skill_level` | Required skill level |
| `workstation_tags` | GUIDs of required nearby crafting stations |
| `operation` | Special operation type (e.g. "RepairTargetItem") |

**Legacy blueprints** (workshop maps) use numeric IDs instead of GUIDs: `"36011 x 7"`.

### The `raw` Field

The complete parsed `.dat` file as a Python dict -- every key and value from the original file, with type coercion (strings to int/float/bool where appropriate). This is the lossless guarantee: anything not captured in `parsed` is still available in `raw`.

---

## map.json

Per-map configuration, spawn resolution, and crafting restrictions.

```json
{
  "name": "A6 Polaris",
  "source_path": "/home/guy/unturned-server/Servers/MyServer/Workshop/.../A6 Polaris",
  "workshop_id": null,
  "config": { ... },
  "level_asset": null,
  "crafting_blacklists": [ ... ],
  "spawn_resolution": { ... },
  "master_bundle": null
}
```

### `config`

The raw contents of the map's `Config.json`, if present. Contains map-specific settings like mode overrides, train routes, and spawn loadouts.

### `crafting_blacklists`

List of crafting restrictions applied to this map:

```json
{
  "guid": "",
  "source_path": "",
  "allow_core_blueprints": false,
  "blocked_input_guids": ["098b13be34a7411db7736b7f866ada69"],
  "blocked_output_guids": ["098b13be34a7411db7736b7f866ada69"]
}
```

If `allow_core_blueprints` is `false`, ALL base game crafting recipes are disabled on this map. The map provides its own recipes via its own items.

### `spawn_resolution`

The resolved spawn data for this map -- which spawn tables are active and which items can spawn:

```json
{
  "active_table_ids": [228, 229, 230, ...],
  "active_table_names": ["Civilian", "Militia", "Military_Low", ...],
  "spawnable_item_ids": [15, 16, 17, 81, 143, ...],
  "spawnable_item_guids": ["abc123...", "def456...", ...],
  "table_chains": {
    "228": [15, 16, 17, 81, 143, 176, 234],
    "229": [1041, 1042, 1043],
    ...
  }
}
```

| Field | Description |
|-------|-------------|
| `active_table_ids` | Spawn table IDs active on this map |
| `active_table_names` | Human-readable names of active tables |
| `spawnable_item_ids` | All item IDs that can spawn (resolved from table chains) |
| `spawnable_item_guids` | Same as above, but as GUIDs |
| `table_chains` | Full resolution: table_id -> list of leaf item IDs reachable from that table |

#### How spawn tables work

Spawn tables are recursive. A table can reference other tables or leaf items:

```
Militia (228) -> Militia_Bottom (229) -> Asset 1041 (Military Vest)
                                      -> Asset 1042 (Military Top)
              -> Militia_Top (230)    -> Asset 1043 (Military Pants)
```

`table_chains` shows the fully resolved leaf items for each root table.

---

## assets.json (base and per-map)

A flat JSON array of `.asset` file entries. These are Unity asset definitions (weather, outfits, crafting effects, level config, etc.) -- not game items.

```json
{
  "guid": "22a2d4cf42d04f87a13a3b6e0c8c7e5f",
  "name": "GentleSnow",
  "csharp_type": "WeatherAsset",
  "source_path": "Assets/Weather/GentleSnow.asset",
  "raw": { ... }
}
```

Assets are primarily useful for resolving GUID references found in entries (blueprint workstation tags, crafting blacklist references, weather types, etc.).

---

## guid_index.json

Master cross-reference index. Maps every GUID to its file location, array index, and basic metadata.

```json
{
  "total_entries": 7447,
  "generated_at": "2026-02-19T18:30:00+00:00",
  "entries": {
    "667ba2f0aba7484888bcfbec2a43798b": {
      "file": "base/entries.json",
      "index": 1042,
      "id": 353,
      "type": "Gun",
      "name": "Eaglefire"
    },
    "dcddca4d05564563aa2aac8144615c46": {
      "file": "maps/a6_polaris/assets.json",
      "index": 15,
      "id": 0,
      "type": "CraftingBlacklistAsset",
      "name": "Frost Craft"
    }
  },
  "by_id": {
    "353": "667ba2f0aba7484888bcfbec2a43798b",
    "36139": "a1b2c3d4e5f6..."
  }
}
```

| Field | Description |
|-------|-------------|
| `entries` | GUID -> {file, index, id, type, name} |
| `by_id` | Numeric ID (as string) -> GUID |

Use cases:
- **Resolve a GUID** from a blueprint input to find the item's name and location
- **Find an item by numeric ID** via `by_id` -> GUID -> `entries`
- **Direct array access**: `entries[guid].file` + `entries[guid].index` points to the exact position in the JSON array

---

## How Data Fits Together

### "What items are available on PEI?"

1. Load `maps/pei/map.json`
2. Get `spawn_resolution.spawnable_item_ids` -- these are the base game item IDs that spawn on PEI
3. Load `base/entries.json`
4. Filter to entries whose `id` is in the spawnable set

PEI has no custom entries (`has_custom_entries: false`), so everything comes from `base/entries.json`.

### "What items are available on A6 Polaris?"

1. Load `maps/a6_polaris/map.json`
2. Get `spawn_resolution.spawnable_item_ids`
3. Check `crafting_blacklists` -- if `allow_core_blueprints` is `false`, base game recipes don't work here
4. Load `maps/a6_polaris/entries.json` -- these are Polaris's own items (IDs 36000+)
5. Optionally also load base game items that are spawnable (from step 2 + `base/entries.json`)

### "What can I craft on this map?"

1. Load the map's entries (and base entries if core blueprints are allowed)
2. For each entry, check `blueprints` array
3. Filter out blueprints where inputs/outputs are in the map's `crafting_blacklists.blocked_input_guids` / `blocked_output_guids`
4. Resolve blueprint input/output GUIDs to names using `guid_index.json`

### "Show me a crafting graph"

Build nodes and edges from blueprint data:

1. For each entry with blueprints, create a node (id=guid, label=name)
2. For each blueprint:
   - **Craft**: Draw edges from each input -> each output
   - **Repair**: Draw edges from inputs -> the owning item
   - **Salvage**: Draw edges from the owning item -> outputs
3. Resolve GUIDs to names via `guid_index.json`
4. Filter by map availability using `spawn_resolution`

### "Build a web page with map radio buttons"

The web page pattern:

1. On page load, fetch `manifest.json` to discover available maps
2. Fetch `base/entries.json` (always needed)
3. For each map with `has_custom_entries: true`, fetch its `entries.json`
4. Fetch each map's `map.json` for spawn resolution data
5. Build a merged item list, tagging each item with which maps it appears on
6. Render radio buttons from the manifest's map list
7. When a map is selected, filter the display to items in that map's `spawnable_item_ids` + the map's own entries

### Resolving GUID references

Many fields contain GUIDs that reference other items or assets:
- Blueprint inputs/outputs reference item GUIDs
- `workstation_tags` reference crafting station GUIDs
- `category_tag` in blueprints references category GUIDs
- `crafting_blacklists` reference item GUIDs to block

To resolve a GUID to a human-readable name:

```javascript
// 1. Check guid_index
const entry = guidIndex.entries[guid];
if (entry) return entry.name;

// 2. Fall back to first 8 chars
return `[${guid.substring(0, 8)}]`;
```

### Base game vs map-specific items

Items are separated by origin:
- `base/entries.json` contains all items from the base game `Bundles/` directory
- `maps/<name>/entries.json` contains items defined by that map

The ID ranges are a convention, not a rule:
- Base game items: IDs roughly 0-35999
- A6 Polaris items: IDs 36000+

But the authoritative source is which file an item appears in, not its ID range.

---

## Entry Types Reference

All `type` values found in the data and their category:

| Type | Category | Has `parsed` fields? |
|------|----------|---------------------|
| Gun | Weapon | Yes (damage, firerate, range, etc.) |
| Melee | Weapon | Yes (damage, strength, stamina) |
| Throwable | Weapon | Yes (damage, fuse, explosion) |
| Food | Consumable | Yes (health, food, water, virus) |
| Water | Consumable | Yes |
| Medical | Consumable | Yes |
| Shirt, Pants, Hat, Vest, Backpack, Mask, Glasses | Clothing | Yes (storage, armor) |
| Barricade, Trap, Storage, Sentry, Generator, Beacon, Oil_Pump | Barricade | Yes (health, storage, damage) |
| Structure | Structure | Yes (health, construct) |
| Magazine | Magazine | Yes (amount, count) |
| Sight, Grip, Barrel, Tactical | Attachment | No (base fields only) |
| Vehicle | Vehicle | Yes (speed, fuel, trunk) |
| Animal | Animal | Yes (health, damage, speed) |
| Spawn | Spawn Table | Yes (table_entries) |
| *(anything else)* | Generic | No (all data in `raw`) |
