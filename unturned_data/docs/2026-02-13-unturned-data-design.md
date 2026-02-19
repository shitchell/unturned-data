# Unturned Bundle Data Parser — Design

## Purpose

A CLI tool that parses Unturned's `.dat` bundle files and outputs structured
JSON or markdown tables. Accepts a path to any Bundles directory (or
subdirectory) and deterministically produces a complete data dump of all
entities found therein.

## Architecture

### Layer 1: Generic `.dat` Parser (`dat_parser.py`)

Format-agnostic recursive descent parser. Converts any `.dat` file into a
Python dict tree.

**Handles:**
- `Key Value` lines → `{"Key": "value"}` with type coercion (int, float, str)
- Bare keywords (`Semi`, `Auto`, `Traction`) → `{"Key": true}` (flags)
- `Key [ { ... } { ... } ]` → `{"Key": [dict, dict, ...]}`
- `Key { ... }` → `{"Key": dict}`
- `// comments` stripped
- UTF-8 BOM handling
- `"GUID x N"` shorthand preserved as strings

This layer has no Unturned-specific knowledge.

### Layer 2: English.dat Loader

Parses `Name` and `Description` from sibling `English.dat` files and merges
into the entry.

### Layer 3: Category Parsers with Shared Mixins

#### Base: `BundleEntry`
All entries share: GUID, Type, ID, Name, Description, Rarity, Size (x, y), and
a `raw` dict containing the full Layer 1 output.

#### Mixins (dataclass-based composition):
- **DamageMixin**: Player/Zombie/Animal damage + body part multipliers +
  structure/barricade/vehicle/resource/object damage
- **BlueprintsMixin**: Crafting recipes with inputs, outputs, skill
  requirements, workstation tags
- **ConsumableMixin**: Health, Food, Water, Virus, Vision, Bleeding_Modifier
- **StorageMixin**: Width, Height (container grid dimensions)

#### Category Models:

| Model | Mixins | Extra Fields |
|-------|--------|--------------|
| Gun | Damage, Blueprints | caliber, firerate, range, spread, recoil, fire_modes, hooks, ammo, durability |
| Melee | Damage, Blueprints | range, strength, stamina, durability |
| Consumeable | Consumable, Blueprints | (food, water, medical share this) |
| Clothing | Storage, Blueprints | armor, slot |
| Throwable | Damage, Blueprints | fuse, explosion |
| Barricade | Damage, Blueprints | health, range, build |
| Structure | Blueprints | health, range, construct |
| Magazine | Blueprints | calibers, amount, count_min/max |
| Attachment | Blueprints | modifier fields per subtype |
| Supply/Box/Key | Blueprints | minimal |
| Vehicle | — | speed, steer, brake, fuel, health, trunk, engine, wheels |
| Animal | — | speed, behaviour, health, damage, regen, rewards |
| Spawn | — | tables with asset_id, spawn_id, weight |
| NPC | — | outfit, colors, dialogue_id |
| Object | — | health, rubble, interactability, conditions |
| Effect | — | blast, lifetime |
| Dialogue | — | messages, conditions, rewards |
| Quest | — | conditions, rewards |
| Vendor | — | items, conditions |
| GenericEntry | — | fallback: base fields + raw dict only |

### Type Dispatch

The `Type` field in each `.dat` file determines which parser class handles it.
A registry maps type strings to model classes. Unknown types use
`GenericEntry`.

### Output Formats

#### JSON (`--format json`)
- Raw GUIDs preserved (no resolution)
- Full nested structure
- Deterministic key ordering

#### Markdown (`--format markdown`)
- Separate table per entity type
- Columns relevant to each type
- GUIDs resolved to human-readable names via a two-pass approach:
  1. First pass: build GUID→name map from all entries
  2. Second pass: render markdown with resolved names

### CLI Interface

```
unturned-data <path> --format json|markdown
```

- `<path>`: any Bundles directory or subdirectory
- Output goes to stdout
- Deterministic: same input always produces same output (sorted by ID/name)

## File Structure

```
~/bin/unturned_data/
├── __init__.py
├── __main__.py           # entry point
├── cli.py                # argparse, orchestration
├── dat_parser.py         # Layer 1: generic .dat → dict
├── models.py             # BundleEntry base + all mixins
├── categories/
│   ├── __init__.py       # type registry + dispatch
│   ├── items.py          # Gun, Melee, Consumeable, Clothing, etc.
│   ├── vehicles.py
│   ├── animals.py
│   ├── spawns.py
│   ├── npcs.py
│   ├── objects.py
│   └── generic.py        # fallback
└── formatters/
    ├── __init__.py
    ├── json_fmt.py
    └── markdown_fmt.py   # GUID resolution here
```

Plus `~/bin/unturned-data` as a thin CLI entry point (or invoked via
`python -m unturned_data`).
