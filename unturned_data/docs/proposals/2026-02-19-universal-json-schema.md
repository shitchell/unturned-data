# Universal JSON Schema for Unturned Data Export

**Date:** 2026-02-19
**Status:** Accepted (Schema C: Origin-First Hierarchy)
**Author:** Claude (with Guy)
**Decision:** Going with **Schema C** -- the origin-first hierarchy approach. It matches
the mental model of "base game + map overlays", keeps per-map data self-contained, and
handles crafting blacklists naturally within each map's `map.json`.

## Problem Statement

The `unturned_data` package currently produces multiple purpose-built JSON formats:

| Format | Output | What's Lost |
|--------|--------|-------------|
| `json` | Nested tree by directory path | Type-specific fields (damage, consumable stats, etc.) |
| `web` | Flat table sections with columns/rows | Raw .dat fields, blueprints detail, .asset metadata |
| `crafting` | Cytoscape.js nodes + edges | Everything not related to crafting |
| `markdown` | Grouped tables | Same as web |

Each format is a **lossy, one-way transformation**. There is no single source of truth that preserves all parsed data. Downstream tools must re-parse .dat files or accept data loss.

**Goal:** Design a master JSON format that preserves ALL .dat file information, is readily exchangeable, and can serve as the single input for all downstream tools.

---

## Data Landscape Summary

### Scale

| Content Type | Base Game | A6 Polaris | Total |
|--------------|-----------|------------|-------|
| Item .dat entries | ~1,989 | ~647 | ~2,636 |
| Spawn tables | ~825 | ~4 | ~829 |
| Vehicles | ~64 | ~59 | ~123 |
| Objects | ~1,199 | varies | ~1,500+ |
| Animals | 7 | 9 | 16 |
| NPCs | ~116 | ~25 | ~141 |
| Effects | ~176 | ~26 | ~202 |
| .asset files | ~690 | ~50+ | ~740+ |
| **Total .dat files** | **~7,939** | **~800+** | **~8,700+** |

### File Format Zoo

| Format | Location | Parser Status |
|--------|----------|---------------|
| Text .dat (key-value) | `Bundles/**/*.dat` | Fully parsed by `dat_parser.py` |
| Text .asset (Metadata+Asset blocks) | `Bundles/**/*.asset`, map `Bundles/**/*.asset` | Parsed by `parse_asset_file()` |
| English.dat (localization) | Alongside .dat files | Parsed by `load_english_dat()` |
| Binary .dat (spawn locations) | `Maps/*/Spawns/*.dat` | Partial (name/ID extraction only) |
| Config.json | Map root directories | Parsed by `crafting_blacklist.py` |
| MasterBundle.dat | Bundle roots | Not currently parsed in pipeline |

### Key Architectural Facts

1. **GUID is the universal cross-reference key** -- 32-char hex, globally unique across base game + all mods
2. **Numeric IDs are namespaced by convention** -- base game uses 0-35999, Polaris uses 36000-57036
3. **Items own their blueprints** -- crafting recipes are inline in item .dat files, not centralized
4. **Maps are overlays** -- they add content (new IDs, new GUIDs) but don't modify base game files
5. **Spawn tables are recursive** -- tables reference other tables or leaf item IDs
6. **Two blueprint formats coexist** -- modern (block) and legacy (indexed); parser handles both
7. **44+ distinct Type values** map to 13 category model classes
8. **Bare keys = boolean true** -- field presence without a value means `True`
9. **.asset files define cross-cutting concerns** -- level config, crafting blacklists, weather, outfits
10. **MasterBundle.dat provides asset path resolution** -- bundle name + prefix for Unity asset loading

---

## Design Principles

1. **Lossless** -- every field from every .dat file must be preserved
2. **Path-aware** -- include the relative path of each .dat file source
3. **Origin-tagged** -- know whether data came from base game or a specific map/mod
4. **Cross-referenceable** -- GUIDs and IDs must be easy to look up
5. **Human-readable** -- meaningful key names, not just raw .dat keys
6. **Dual-layer** -- both parsed/semantic fields AND raw .dat dict preserved
7. **Incrementally adoptable** -- existing formatters can consume the master JSON

---

## Schema A: Single Master JSON

One file containing everything. Maximum simplicity for consumers -- one file to fetch, one file to query.

### Top-Level Structure

```json
{
  "meta": {
    "generated_at": "2026-02-19T14:30:00Z",
    "generator": "unturned_data v0.5.0",
    "base_bundles_path": "~/unturned-server/Bundles",
    "maps": ["PEI", "A6 Polaris"]
  },
  "indices": {
    "by_guid": { "<guid>": "<entry_type>/<array_index>" },
    "by_id": { "<numeric_id>": "<entry_type>/<array_index>" }
  },
  "items": [ ... ],
  "spawn_tables": [ ... ],
  "vehicles": [ ... ],
  "animals": [ ... ],
  "objects": [ ... ],
  "npcs": [ ... ],
  "effects": [ ... ],
  "assets": [ ... ],
  "maps": {
    "PEI": { ... },
    "A6 Polaris": { ... }
  }
}
```

### Entry Shape (Items Example)

```json
{
  "guid": "667ba2f0aba7484888bcfbec2a43798b",
  "id": 353,
  "type": "Gun",
  "name": "Eaglefire",
  "description": "American 5.56mm assault rifle.",
  "rarity": "Legendary",
  "source_path": "Items/Guns/Eaglefire",
  "origin": "base",
  "english": {
    "Name": "Eaglefire",
    "Description": "American 5.56mm assault rifle."
  },
  "parsed": {
    "slot": "Primary",
    "caliber": 1,
    "firerate": 10,
    "range": 200,
    "fire_modes": ["Safety", "Semi", "Auto"],
    "ammo_min": 1,
    "ammo_max": 30,
    "durability": 0.55,
    "spread_aim": 0.01,
    "spread_angle": 2.75,
    "damage": {
      "player": 40,
      "zombie": 99,
      "animal": 40,
      "player_multipliers": { "skull": 1.1, "spine": 0.8 },
      "zombie_multipliers": { "skull": 1.1, "spine": 0.8 }
    },
    "size": { "x": 5, "y": 2 }
  },
  "blueprints": [
    {
      "name": "",
      "operation": "",
      "category_tag": "ad1804b6945145f3b308738b0b8ea447",
      "inputs": [
        { "ref": "46218740c256475b87dbc6a2e9a1fb19", "quantity": 7 },
        { "ref": "5ff4bcf752554990bf06e103b996cef2", "quantity": 1 }
      ],
      "outputs": [{ "ref": "this", "quantity": 1 }],
      "skill": "Craft",
      "skill_level": 1,
      "workstation_tags": ["84347b13028340b8976033c08675d458"]
    },
    {
      "name": "Repair",
      "operation": "RepairTargetItem",
      "inputs": [
        { "ref": "46218740c256475b87dbc6a2e9a1fb19", "quantity": 4 }
      ],
      "outputs": []
    }
  ],
  "maps": ["PEI"],
  "raw": {
    "GUID": "667ba2f0aba7484888bcfbec2a43798b",
    "Type": "Gun",
    "Rarity": "Legendary",
    "Useable": "Gun",
    "Slot": "Primary",
    "ID": 353,
    "Size_X": 5,
    "Size_Y": 2,
    "Caliber": 1,
    "Firerate": 10,
    "Action": "Trigger",
    "Ammo_Min": 1,
    "Ammo_Max": 30,
    "Safety": true,
    "Semi": true,
    "Auto": true,
    "Player_Damage": 40,
    "Zombie_Damage": 99,
    "..."
  }
}
```

### Spawn Table Entry Example

```json
{
  "guid": "abc123...",
  "id": 228,
  "type": "Spawn",
  "name": "Militia",
  "source_path": "Spawns/Items/Militia",
  "origin": "base",
  "table_entries": [
    { "ref_type": "spawn", "ref_id": 229, "weight": 960 },
    { "ref_type": "asset", "ref_id": 1041, "weight": 200 },
    { "ref_type": "guid", "ref_guid": "e322656746a045a98eb6e5a6650a104e", "weight": 5 }
  ],
  "raw": { "..." }
}
```

### Map Data Shape

```json
{
  "maps": {
    "A6 Polaris": {
      "config": {
        "version": "1.0.3.4",
        "creators": ["Daniel Segboer"],
        "asset_guid": "77e3a2e0fd6b4c768928dc2861888a6e",
        "trains": [
          { "vehicle_id": 36024, "road_index": 40 }
        ],
        "mode_overrides": {
          "Vehicles.Armor_Multiplier": 0.375,
          "Players.Can_Break_Legs": false
        },
        "spawn_loadouts": [
          { "table_id": 36125, "amount": 1 }
        ]
      },
      "level_asset": {
        "guid": "77e3a2e0fd6b4c768928dc2861888a6e",
        "crafting_blacklists": [
          {
            "guid": "dcddca4d05564563aa2aac8144615c46",
            "allow_core_blueprints": false,
            "blocked_input_guids": ["098b13be34a7411db7736b7f866ada69"],
            "blocked_output_guids": ["098b13be34a7411db7736b7f866ada69"]
          }
        ],
        "skills": [
          { "id": "Sharpshooter", "default_level": 4 }
        ],
        "weather_types": [
          { "guid": "a26ceb552f244563a2aa0b2c967731a6" }
        ]
      },
      "spawnable_item_ids": [36001, 36002, 36003, "..."],
      "active_spawn_table_ids": [36100, 36101, "..."]
    }
  }
}
```

### Asset Entry Shape

```json
{
  "guid": "d293cbe22b8c40bf866c39ebbd952fe1",
  "csharp_type": "SDG.Unturned.OutfitAsset",
  "source_path": "Assets/Outfits/DemonOutfit.asset",
  "origin": "base",
  "parsed": {
    "items": [
      "3646d3095b0640adb7ca177ca2fc5b98",
      "5bc7742588024f01b5bf6a6db7d3ce08"
    ]
  },
  "raw": { "..." }
}
```

### Tradeoffs

| Pro | Con |
|-----|-----|
| One file = one fetch, simple tooling | File size: estimated 15-30 MB uncompressed |
| All cross-references resolvable in-memory | Browser memory pressure for web tools |
| Simple to generate and validate | Long generation time (must parse everything) |
| Atomic updates (no partial state) | Can't update items without regenerating everything |
| Great for offline/batch analysis | Overkill for "show me one item" queries |

### Map Integration

Map-specific items live in the same `items[]` array with `"origin": "A6 Polaris"`. The `maps` top-level object holds per-map configuration (blacklists, overrides, spawn loadout tables). The `maps` field on each entry lists which maps spawn that item.

### .asset Integration

All .asset files go into the `assets[]` array with their full parsed content and raw dict. GUIDs from .asset files are included in the `indices.by_guid` lookup alongside .dat entries.

---

## Schema B: Category-Split JSON

Multiple files split by game category. Each file is self-contained for its domain.

### File Split Strategy

```
output/
  meta.json              # Generation metadata + index of all files
  items.json             # All items (weapons, food, clothing, etc.)
  spawn_tables.json      # All spawn table definitions
  vehicles.json          # Vehicle definitions
  animals.json           # Animal definitions
  objects.json           # World objects
  npcs.json              # NPCs, quests, vendors, dialogue
  effects.json           # Visual/audio effects
  assets.json            # All .asset file data (outfits, weather, materials, etc.)
  maps/
    pei.json             # PEI map config + spawnable IDs
    a6_polaris.json      # A6 Polaris map config + spawnable IDs
  guid_index.json        # Master GUID -> {file, type, name} lookup
```

### Per-File Structure

**items.json:**

```json
{
  "meta": {
    "category": "items",
    "count": 2636,
    "generated_at": "2026-02-19T14:30:00Z"
  },
  "guid_index": {
    "667ba2f0aba7484888bcfbec2a43798b": 0,
    "...": "..."
  },
  "id_index": {
    "353": 0,
    "...": "..."
  },
  "entries": [
    {
      "guid": "667ba2f0aba7484888bcfbec2a43798b",
      "id": 353,
      "type": "Gun",
      "name": "Eaglefire",
      "description": "American 5.56mm assault rifle.",
      "rarity": "Legendary",
      "source_path": "Items/Guns/Eaglefire",
      "origin": "base",
      "english": { "Name": "Eaglefire", "Description": "..." },
      "parsed": { "...same as Schema A..." },
      "blueprints": [ "...same as Schema A..." ],
      "maps": ["PEI"],
      "raw": { "..." }
    }
  ]
}
```

**guid_index.json (master cross-reference):**

```json
{
  "667ba2f0aba7484888bcfbec2a43798b": {
    "file": "items.json",
    "index": 0,
    "type": "Gun",
    "name": "Eaglefire",
    "id": 353
  },
  "d293cbe22b8c40bf866c39ebbd952fe1": {
    "file": "assets.json",
    "index": 42,
    "type": "OutfitAsset",
    "name": "DemonOutfit"
  },
  "dcddca4d05564563aa2aac8144615c46": {
    "file": "assets.json",
    "index": 15,
    "type": "CraftingBlacklistAsset",
    "name": "Frost_Craft"
  }
}
```

**maps/a6_polaris.json:**

```json
{
  "name": "A6 Polaris",
  "workshop_id": 2898548949,
  "config": { "...same as Schema A map shape..." },
  "level_asset": { "...same as Schema A..." },
  "spawnable_item_guids": ["guid1", "guid2", "..."],
  "active_spawn_table_guids": ["guid1", "..."],
  "item_id_range": [36000, 57036],
  "master_bundle": {
    "name": "frost.masterbundle",
    "asset_prefix": "Assets/FrostMasterBundle",
    "version": 4
  }
}
```

### Tradeoffs

| Pro | Con |
|-----|-----|
| Smaller individual files (~2-5 MB each) | Cross-references require loading multiple files |
| Incremental updates (regenerate one file) | guid_index.json must be regenerated with any change |
| Browser-friendly (lazy load what you need) | More complex generation pipeline |
| Category-specific tooling can ignore other files | Blueprint inputs reference items in the same file (good) but also assets in assets.json (requires cross-file lookup) |
| Natural organization for humans | Split points are somewhat arbitrary (is an NPC vendor item data or NPC data?) |

### Map Integration

Each map gets its own file in `maps/`. Map-specific items still live in `items.json` with `"origin": "A6 Polaris"` -- the map file contains only map-level configuration and spawn reference lists.

### .asset Integration

All .asset data goes in `assets.json`. The `guid_index.json` provides the bridge -- if a blueprint references a GUID, consumers check guid_index to know which file contains the full entry.

---

## Schema C: Origin-First Hierarchy (Recommended)

**The key insight:** The most natural split isn't by data type -- it's by **origin**. Base game and each map are self-contained ecosystems with their own items, spawns, assets, and configuration. Tools always need to answer "what's available on THIS map?" which requires merging base + map data. An origin-first split makes this merge explicit and simple.

### File Structure

```
output/
  manifest.json           # What's in this export
  base/
    entries.json           # All base game entries (items, spawns, vehicles, etc.)
    assets.json            # All base game .asset files
  maps/
    pei/
      map.json             # PEI config, level asset, blacklists, spawn resolution
    a6_polaris/
      entries.json         # Polaris-specific entries (items 36000+, NPCs, etc.)
      assets.json          # Polaris-specific .asset files
      map.json             # Polaris config, level asset, blacklists, overrides
  guid_index.json          # Master GUID -> location lookup
```

### manifest.json

```json
{
  "version": "1.0.0",
  "schema": "unturned-data-export",
  "generated_at": "2026-02-19T14:30:00Z",
  "generator": "unturned_data v0.5.0",
  "base_bundles_path": "/home/guy/unturned-server/Bundles",
  "sources": {
    "base": {
      "entries": "base/entries.json",
      "assets": "base/assets.json",
      "entry_count": 4376,
      "asset_count": 690
    },
    "maps": {
      "PEI": {
        "map": "maps/pei/map.json",
        "has_custom_entries": false
      },
      "A6 Polaris": {
        "entries": "maps/a6_polaris/entries.json",
        "assets": "maps/a6_polaris/assets.json",
        "map": "maps/a6_polaris/map.json",
        "has_custom_entries": true,
        "entry_count": 800,
        "asset_count": 50
      }
    }
  },
  "guid_index": "guid_index.json"
}
```

### Entry Shape (same across all files)

Every entry in `entries.json` uses the same shape regardless of Type:

```json
{
  "guid": "667ba2f0aba7484888bcfbec2a43798b",
  "id": 353,
  "type": "Gun",
  "name": "Eaglefire",
  "description": "American 5.56mm assault rifle.",
  "rarity": "Legendary",
  "source_path": "Items/Guns/Eaglefire",
  "category": ["Items", "Guns"],
  "english": {
    "Name": "Eaglefire",
    "Description": "American 5.56mm assault rifle.",
    "Examine": "Reliable military issue."
  },
  "parsed": {
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
      "player": 40.0,
      "zombie": 99.0,
      "animal": 40.0,
      "barricade": 30.0,
      "structure": 30.0,
      "vehicle": 30.0,
      "resource": 20.0,
      "object": 20.0,
      "player_multipliers": { "skull": 1.1, "spine": 0.8, "arm": 0.6, "leg": 0.6 },
      "zombie_multipliers": { "skull": 1.1, "spine": 0.8, "arm": 0.6, "leg": 0.6 },
      "animal_multipliers": {}
    },
    "size": { "x": 5, "y": 2 },
    "storage": null,
    "consumable": null
  },
  "blueprints": [
    {
      "name": "",
      "category_tag": "ad1804b6945145f3b308738b0b8ea447",
      "operation": "",
      "inputs": [
        { "ref": "46218740c256475b87dbc6a2e9a1fb19", "quantity": 7, "is_tool": false },
        { "ref": "5ff4bcf752554990bf06e103b996cef2", "quantity": 1, "is_tool": false }
      ],
      "outputs": [
        { "ref": "this", "quantity": 1 }
      ],
      "skill": "Craft",
      "skill_level": 1,
      "workstation_tags": ["84347b13028340b8976033c08675d458"]
    },
    {
      "name": "Repair",
      "category_tag": "",
      "operation": "RepairTargetItem",
      "inputs": [
        { "ref": "46218740c256475b87dbc6a2e9a1fb19", "quantity": 4, "is_tool": false }
      ],
      "outputs": [],
      "skill": "",
      "skill_level": 0,
      "workstation_tags": []
    },
    {
      "name": "Salvage",
      "category_tag": "",
      "operation": "",
      "inputs": [
        { "ref": "this", "quantity": 1, "is_tool": false }
      ],
      "outputs": [
        { "ref": "46218740c256475b87dbc6a2e9a1fb19", "quantity": 2, "is_tool": false }
      ],
      "skill": "",
      "skill_level": 0,
      "workstation_tags": []
    }
  ],
  "raw": {
    "GUID": "667ba2f0aba7484888bcfbec2a43798b",
    "Type": "Gun",
    "Rarity": "Legendary",
    "Useable": "Gun",
    "Slot": "Primary",
    "ID": 353,
    "Size_X": 5,
    "Size_Y": 2,
    "Amount": 30,
    "Count_Min": 10,
    "Count_Max": 14,
    "Caliber": 1,
    "Firerate": 10,
    "Action": "Trigger",
    "Delete_Empty_Magazines": true,
    "Ammo_Min": 1,
    "Ammo_Max": 30,
    "Sight": 146,
    "Tactical": 151,
    "Grip": 143,
    "Barrel": 149,
    "Magazine": 17,
    "Unplace": 0.5,
    "Range": 200,
    "Safety": true,
    "Semi": true,
    "Auto": true,
    "Durability": 0.55,
    "Spread_Aim": 0.01,
    "Spread_Angle_Degrees": 2.75,
    "Player_Damage": 40,
    "Player_Leg_Multiplier": 0.6,
    "Player_Arm_Multiplier": 0.6,
    "Player_Spine_Multiplier": 0.8,
    "Player_Skull_Multiplier": 1.1,
    "Zombie_Damage": 99,
    "Zombie_Leg_Multiplier": 0.6,
    "Zombie_Arm_Multiplier": 0.6,
    "Zombie_Spine_Multiplier": 0.8,
    "Zombie_Skull_Multiplier": 1.1,
    "Animal_Damage": 40,
    "Barricade_Damage": 30,
    "Structure_Damage": 30,
    "Vehicle_Damage": 30,
    "Resource_Damage": 20,
    "Object_Damage": 20,
    "Recoil_Min_X": 2,
    "Recoil_Min_Y": 6,
    "Recoil_Max_X": -2,
    "Recoil_Max_Y": 4,
    "Shake_Min_X": 0.5,
    "Shake_Max_Y": 0.1,
    "Hook_Sight": true,
    "Hook_Tactical": true,
    "Hook_Grip": true,
    "Hook_Barrel": true,
    "Muzzle": 4,
    "Shell": 11,
    "Magazine_Replacements": [
      {"Magazine": 17, "ID": 17},
      {"Magazine": 17, "ID": 98}
    ],
    "Blueprints": "..."
  }
}
```

### Polaris Item Example (from maps/a6_polaris/entries.json)

```json
{
  "guid": "a1b2c3d4e5f6...",
  "id": 36139,
  "type": "Gun",
  "name": "Frost LMG",
  "description": "Heavy Polaris machine gun.",
  "rarity": "Epic",
  "source_path": "Items/Weapons/Frost_LMG",
  "category": ["Items", "Weapons"],
  "english": { "Name": "Frost LMG", "Description": "Heavy Polaris machine gun." },
  "parsed": {
    "slot": "Primary",
    "caliber": 36005,
    "firerate": 6,
    "range": 150.0,
    "fire_modes": ["Safety", "Auto"],
    "damage": {
      "player": 28.0,
      "zombie": 45.0,
      "animal": 28.0
    },
    "size": { "x": 6, "y": 2 }
  },
  "blueprints": [
    {
      "name": "Craft",
      "inputs": [
        { "ref": "36011", "quantity": 7, "is_tool": false },
        { "ref": "36139", "quantity": 1, "is_tool": true, "note": "workstation" }
      ],
      "outputs": [{ "ref": "this", "quantity": 1 }]
    }
  ],
  "raw": { "..." }
}
```

### Spawn Table Entry (from base/entries.json)

```json
{
  "guid": "...",
  "id": 228,
  "type": "Spawn",
  "name": "Militia",
  "source_path": "Spawns/Items/Militia",
  "category": ["Spawns", "Items"],
  "english": { "Name": "Militia" },
  "parsed": {},
  "blueprints": [],
  "table_entries": [
    { "ref_type": "spawn", "ref_id": 229, "ref_guid": "", "weight": 960 },
    { "ref_type": "spawn", "ref_id": 230, "ref_guid": "", "weight": 460 },
    { "ref_type": "asset", "ref_id": 1041, "ref_guid": "", "weight": 200 },
    { "ref_type": "guid", "ref_id": 0, "ref_guid": "e322656746a045a98eb6e5a6650a104e", "weight": 5 }
  ],
  "raw": { "..." }
}
```

### maps/a6_polaris/map.json

```json
{
  "name": "A6 Polaris",
  "workshop_id": 2898548949,
  "source_path": "Servers/MyServer/Workshop/Steam/content/304930/2898548949/A6 Polaris",
  "config": {
    "version": "1.0.3.4",
    "creators": ["Daniel Segboer"],
    "collaborators": ["Renaxon", "LVOmega"],
    "asset_guid": "77e3a2e0fd6b4c768928dc2861888a6e",
    "category": "",
    "trains": [
      { "vehicle_id": 36024, "road_index": 40 },
      { "vehicle_id": 36026, "road_index": 96 }
    ],
    "mode_overrides": {
      "Animals.Max_Instances_Medium": 256,
      "Items.Quality_Full_Chance": 0.25,
      "Vehicles.Gun_Lowcal_Damage_Multiplier": 2.0,
      "Vehicles.Armor_Multiplier": 0.375,
      "Players.Can_Break_Legs": false,
      "Zombies.Spawn_Chance": 1
    },
    "spawn_loadouts": [
      { "table_id": 36125, "amount": 1 },
      { "table_id": 36126, "amount": 1 }
    ],
    "raw_config": { "...full Config.json..." }
  },
  "level_asset": {
    "guid": "77e3a2e0fd6b4c768928dc2861888a6e",
    "source_path": "Bundles/Content/Level/Frost_Level_00.asset",
    "crafting_blacklists": [
      {
        "guid": "dcddca4d05564563aa2aac8144615c46",
        "source_path": "Bundles/Content/Level/Frost_Craft.asset",
        "allow_core_blueprints": false,
        "blocked_input_guids": ["098b13be34a7411db7736b7f866ada69"],
        "blocked_output_guids": ["098b13be34a7411db7736b7f866ada69"]
      }
    ],
    "skills": [
      { "id": "Sharpshooter", "default_level": 4, "cost_multiplier": 0.5 },
      { "id": "Dexterity", "max_unlockable_level": 0 },
      { "id": "Exercise", "max_unlockable_level": 0 }
    ],
    "weather_types": [
      { "guid": "a26ceb552f244563a2aa0b2c967731a6" },
      { "guid": "f30a01005f0b42baacd78f2d3002bfd2" },
      { "guid": "6574c05111e84c4c985d463a830f9a7a" }
    ],
    "raw": { "...full parsed .asset..." }
  },
  "master_bundle": {
    "name": "frost.masterbundle",
    "asset_prefix": "Assets/FrostMasterBundle",
    "version": 4
  },
  "spawn_resolution": {
    "active_table_ids": [36100, 36101, 36102, 36103],
    "spawnable_item_ids": [36001, 36002, 36003, "..."],
    "spawnable_item_guids": ["guid1", "guid2", "..."]
  }
}
```

### Asset Entry Shape (from base/assets.json or maps/a6_polaris/assets.json)

```json
{
  "guid": "22a2d4cf42d04f87a13a3b6e0c8c7e5f",
  "name": "GentleSnow",
  "csharp_type": "SDG.Unturned.WeatherAsset",
  "source_path": "Assets/Weather/GentleSnow.asset",
  "parsed": {
    "fade_in_duration": 30.0,
    "fade_out_duration": 15.0,
    "min_frequency": 180.0,
    "max_frequency": 600.0,
    "min_duration": 120.0,
    "max_duration": 300.0,
    "effects": [
      {
        "prefab": { "master_bundle": "core.masterbundle", "asset_path": "Effects/Weather/GentleSnowParticles.prefab" }
      }
    ]
  },
  "raw": {
    "Metadata": {
      "GUID": "22a2d4cf42d04f87a13a3b6e0c8c7e5f",
      "Type": "SDG.Unturned.WeatherAsset, Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null"
    },
    "Asset": { "..." }
  }
}
```

### guid_index.json

```json
{
  "meta": {
    "total_entries": 9500,
    "generated_at": "2026-02-19T14:30:00Z"
  },
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
      "type": "CraftingBlacklistAsset",
      "name": "Frost_Craft"
    }
  },
  "by_id": {
    "353": "667ba2f0aba7484888bcfbec2a43798b",
    "36139": "a1b2c3d4e5f6..."
  }
}
```

### Tradeoffs

| Pro | Con |
|-----|-----|
| Natural boundary: base vs map content | Resolving a Polaris blueprint that references a base game GUID requires loading both files |
| Incrementally updatable per origin | More files to manage |
| Clear data lineage ("this came from Polaris") | Some duplication in guid_index |
| Maps with no custom items (PEI) produce only a tiny map.json | New maps require creating a new directory |
| Parallel generation possible | Consumers need the manifest to know what to load |
| Best for "show me everything about this map" queries | Worst for "search all items across all maps" queries |
| Each file is a reasonable size (~5-10 MB max) | |

### Map Integration

This is the schema's strength. Each map is a directory. Maps that add content (Polaris) have their own `entries.json` + `assets.json`. Maps that don't (PEI) have just `map.json` with spawn resolution and config. To get "all items available on Polaris": load `base/entries.json`, filter by Polaris spawn resolution, then merge `maps/a6_polaris/entries.json`.

### .asset Integration

Split by origin like entries. Base game assets in `base/assets.json`, Polaris assets in `maps/a6_polaris/assets.json`. All indexed in `guid_index.json`.

---

## Comparison Matrix

| Criterion | A: Single File | B: Category Split | C: Origin-First |
|-----------|---------------|-------------------|-----------------|
| **File count** | 1 | ~12 | ~7 (scales with maps) |
| **Largest file** | ~25 MB | ~8 MB (items) | ~12 MB (base/entries) |
| **Cross-reference** | Trivial (same file) | guid_index required | guid_index required |
| **"Items on map X"** | Filter in-memory | Load items.json + map file | Load base + map entries |
| **"Everything about item X"** | Direct lookup | Direct lookup | May need base OR map file |
| **Incremental update** | Full regeneration | Per-category | Per-origin |
| **Browser friendliness** | Poor (large file) | Good (load what you need) | Good (load base + 1 map) |
| **Data lineage** | `origin` field | `origin` field | Directory structure |
| **New map support** | Regenerate | Regenerate + update index | Add new directory |
| **Pipeline complexity** | Simple | Medium | Medium |
| **Lossless** | Yes | Yes | Yes |
| **Human navigability** | Scroll a lot | Find the right file | Find the right directory |

---

## Recommendation

**Schema C (Origin-First)** is the best fit for this project because:

1. **Matches the mental model.** When Guy asks "what items does Polaris have?" the answer is literally one directory. When the crafting graph needs to know "is this blueprint blacklisted?", it loads the map's `map.json` and checks.

2. **Scales naturally.** Adding a new workshop map means adding one directory. No restructuring.

3. **Right-sized files.** Base game entries at ~12 MB is large but manageable. Each map's entries are small (Polaris: ~3 MB). No single file approaches the "too big for browser" threshold.

4. **Enables incremental work.** Re-parsing only Polaris after a map update doesn't require touching base game data.

5. **Preserves data lineage intrinsically.** The file path tells you where data came from -- no need to filter by an `origin` field.

6. **The guid_index bridges the gap.** Cross-origin references (Polaris blueprint using base game GUID) are resolvable via the lightweight index file.

### Implementation Path

1. Add a `--format master` (or `--format export`) CLI option
2. Generate `manifest.json` + `guid_index.json` first (requires full parse)
3. Generate `base/entries.json` by walking base Bundles/
4. Generate `base/assets.json` by walking base .asset files
5. For each `--map`, generate `maps/<name>/entries.json`, `maps/<name>/assets.json`, `maps/<name>/map.json`
6. Existing formatters (web, crafting, markdown) can be refactored to consume the master JSON instead of re-parsing .dat files

### Key Design Decisions Still Needed

1. **`parsed` field scope** -- Should `parsed` contain ALL semantically-meaningful fields extracted by the category models? Or just the type-specific extras (since common fields like guid/id/name are already top-level)? **Recommendation:** Type-specific extras only. Common fields live at top level; `parsed` holds what the category model adds (damage stats, consumable stats, etc.).

2. **`raw` field inclusion** -- Should every entry include the full raw .dat dict? This is ~60% of the file size. **Recommendation:** Yes, include it. It's the losslessness guarantee. Consumers that don't need it can ignore it. Consider a `--no-raw` flag for lighter output.

3. **Blueprint ref format** -- Should blueprint input/output refs be normalized to GUIDs only? Or preserve the original format (numeric IDs for legacy, GUIDs for modern)? **Recommendation:** Preserve original refs (for losslessness) but add a `resolved_guid` field when the ref can be resolved. This keeps both the original data and the convenience.

4. **Binary spawn data** -- The binary `Maps/*/Spawns/*.dat` files (item locations, zombie tables, etc.) are only partially parsed. Should the master JSON include what we can extract, or skip them? **Recommendation:** Include what we can extract (spawn names, table ID references) in the map's `map.json` under `spawn_resolution`. Note the limitation. Don't block the export on full binary parsing.

5. **Object entries** -- ~1,200 objects have minimal .dat data (just GUID, Type, ID, sometimes LOD flags). Include them in entries.json? **Recommendation:** Yes -- they have GUIDs and IDs that other things reference. They're small.
