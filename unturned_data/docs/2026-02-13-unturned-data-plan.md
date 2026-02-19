# Unturned Bundle Data Parser — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A Python CLI tool that parses Unturned `.dat` bundle files and outputs structured JSON or grouped markdown tables.

**Architecture:** Three-layer design: (1) generic `.dat` format parser → Python dicts, (2) shared dataclasses for common stat groups (damage, consumable, storage, blueprints), (3) per-category model classes that compose those shared classes and define their own markdown columns. Type dispatch via registry mapping `.dat` `Type` field → model class.

**Tech Stack:** Python 3.10+ (dataclasses, pathlib, argparse, json). No external dependencies. pytest for tests.

**Test data location:** `~/unturned-bundles/` (local copy of server's `Bundles/` directory)

---

## Task 1: Project scaffolding + test fixtures

**Files:**
- Create: `~/bin/unturned_data/__init__.py`
- Create: `~/bin/unturned_data/tests/__init__.py`
- Create: `~/bin/unturned_data/tests/fixtures/` (directory with sample .dat files)

**Step 1: Create directory structure**

```bash
mkdir -p ~/bin/unturned_data/tests/fixtures
mkdir -p ~/bin/unturned_data/categories
mkdir -p ~/bin/unturned_data/formatters
```

**Step 2: Create `__init__.py` files**

```bash
touch ~/bin/unturned_data/__init__.py
touch ~/bin/unturned_data/categories/__init__.py
touch ~/bin/unturned_data/formatters/__init__.py
touch ~/bin/unturned_data/tests/__init__.py
```

**Step 3: Create test fixtures from real data**

Copy representative samples from `~/unturned-bundles/` into
`~/bin/unturned_data/tests/fixtures/`. We need one fixture per format
variation:

| Fixture dir | Source | Why |
|-------------|--------|-----|
| `food_beans/` | Items/Food/Canned_Beans/ | Simple consumable, no blueprints |
| `medical_bandage/` | Items/Medical/Bandage/ | Consumable + blueprint with string shorthand inputs |
| `gun_maplestrike/` | Items/Guns/Maplestrike/ | Complex: nested blueprint arrays, fire modes, hooks, damage |
| `gun_ace/` | Items/Guns/Ace/ | Gun with nested InputItems array-of-objects |
| `melee_katana/` | Items/Melee/Katana/ | Melee damage + blueprints |
| `backpack_alice/` | Items/Backpacks/Alicepack/ | Clothing with storage Width/Height |
| `vehicle_humvee/` | Vehicles/Humvee/ | Vehicle with WheelConfigurations, EngineSound{}, paint colors |
| `animal_bear/` | Animals/Bear/ | Animal stats |
| `structure_wall/` | Items/Structures/ (birch wall) | Structure with health + blueprints |
| `barricade_wire/` | Items/Barricades/ (first trap) | Trap with damage |
| `spawn_sample/` | Spawns/ (first file) | Spawn tables |
| `npc_sample/` | NPCs/Characters/ (first file) | NPC with outfit |
| `object_sample/` | Objects/Small/Quests/ (first) | Object with conditions/interactability |
| `food_sandwich/` | Items/Food/Sandwich_Beef/ | Craftable food: blueprint with skill + workstation |
| `water_berries/` | Items/Water/ (Raw Amber Berries) | Water/food item with Virus field |

For each, copy both `<Name>.dat` and `English.dat`.

```bash
# Example for one fixture:
mkdir -p ~/bin/unturned_data/tests/fixtures/food_beans
cp ~/unturned-bundles/Items/Food/Canned_Beans/Canned_Beans.dat \
   ~/bin/unturned_data/tests/fixtures/food_beans/Canned_Beans.dat
cp ~/unturned-bundles/Items/Food/Canned_Beans/English.dat \
   ~/bin/unturned_data/tests/fixtures/food_beans/English.dat
# ... repeat for each fixture
```

**Step 4: Verify fixtures are readable**

```bash
python3 -c "
from pathlib import Path
fixtures = Path.home() / 'bin/unturned_data/tests/fixtures'
for d in sorted(fixtures.iterdir()):
    if d.is_dir():
        dats = list(d.glob('*.dat'))
        print(f'{d.name}: {len(dats)} .dat files')
"
```

Expected: each fixture dir shows 2 .dat files.

---

## Task 2: Generic `.dat` parser — core key-value parsing

The `.dat` format is line-oriented key-value with nested blocks. This task
handles the simple cases first (flat key-value lines, flags, type coercion).

**Files:**
- Create: `~/bin/unturned_data/dat_parser.py`
- Create: `~/bin/unturned_data/tests/test_dat_parser.py`

**Step 1: Write failing tests for flat key-value parsing**

```python
"""Tests for generic .dat file parser."""
import pytest
from pathlib import Path
from unturned_data.dat_parser import parse_dat, parse_dat_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestFlatKeyValue:
    """Test basic Key Value line parsing."""

    def test_string_value(self):
        result = parse_dat("Type Food")
        assert result["Type"] == "Food"

    def test_integer_value(self):
        result = parse_dat("ID 13")
        assert result["ID"] == 13

    def test_float_value(self):
        result = parse_dat("Durability 0.2")
        assert result["Durability"] == 0.2

    def test_negative_float(self):
        result = parse_dat("Recoil_Min_X -0.5")
        assert result["Recoil_Min_X"] == -0.5

    def test_boolean_true(self):
        result = parse_dat("Invulnerable true")
        assert result["Invulnerable"] is True

    def test_boolean_false(self):
        result = parse_dat("Delete false")
        assert result["Delete"] is False

    def test_bare_flag(self):
        """A key with no value is a boolean flag (True)."""
        result = parse_dat("Semi")
        assert result["Semi"] is True

    def test_multiple_flags(self):
        result = parse_dat("Safety\nSemi\nAuto")
        assert result["Safety"] is True
        assert result["Semi"] is True
        assert result["Auto"] is True

    def test_quoted_string(self):
        result = parse_dat('GUID "abc123"')
        assert result["GUID"] == "abc123"

    def test_unquoted_guid(self):
        result = parse_dat("GUID 78fefdd23def4ab6ac8301adfcc3b2d4")
        assert result["GUID"] == "78fefdd23def4ab6ac8301adfcc3b2d4"

    def test_path_value(self):
        result = parse_dat("ConsumeAudioClip Sounds/EatCrunchy.mp3")
        assert result["ConsumeAudioClip"] == "Sounds/EatCrunchy.mp3"

    def test_value_with_spaces(self):
        """Multi-word unquoted value after key."""
        result = parse_dat("OutputItems this x 2")
        assert result["OutputItems"] == "this x 2"

    def test_quoted_value_with_spaces(self):
        result = parse_dat(
            'InputItems "3e78a9db8cf74f4e830df4c06f2e9273 x 2"'
        )
        assert result["InputItems"] == "3e78a9db8cf74f4e830df4c06f2e9273 x 2"


class TestComments:
    """Test // comment stripping."""

    def test_inline_comment(self):
        result = parse_dat(
            'CategoryTag "d089feb7e43f40c5a7dfcefc36998cfb" // Supplies'
        )
        assert result["CategoryTag"] == "d089feb7e43f40c5a7dfcefc36998cfb"

    def test_comment_does_not_strip_inside_quotes(self):
        """A // inside quotes is NOT a comment."""
        result = parse_dat('Path "http://example.com"')
        assert result["Path"] == "http://example.com"

    def test_path_with_single_slash(self):
        """Single / in a value is not a comment."""
        result = parse_dat("AudioClip Sounds/Eat.mp3")
        assert result["AudioClip"] == "Sounds/Eat.mp3"


class TestBOM:
    """Test BOM handling."""

    def test_utf8_bom(self):
        result = parse_dat("\ufeffGUID abc123\nType Food")
        assert result["GUID"] == "abc123"
        assert result["Type"] == "Food"


class TestBlankLines:
    """Blank lines are ignored."""

    def test_blank_lines_between_keys(self):
        result = parse_dat("Type Food\n\nID 13\n\nHealth 10")
        assert result["Type"] == "Food"
        assert result["ID"] == 13
        assert result["Health"] == 10
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py -v
```

Expected: ImportError (module doesn't exist yet).

**Step 3: Implement flat key-value parser**

```python
"""
Generic parser for Unturned .dat files.

Converts the key-value + nested block format into Python dicts/lists.
Knows nothing about Unturned semantics -- just handles the file format.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_dat_file(path: Path) -> dict[str, Any]:
    """Parse a .dat file from disk."""
    text = path.read_text(encoding="utf-8-sig")  # handles BOM
    return parse_dat(text)


def parse_dat(text: str) -> dict[str, Any]:
    """Parse .dat format text into a dict."""
    # Strip BOM if read_text didn't handle it
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    result, _ = _parse_mapping(lines, 0)
    return result


def _strip_comment(line: str) -> str:
    """Strip // comments, respecting quoted strings."""
    in_quote = False
    i = 0
    while i < len(line):
        c = line[i]
        if c == '"':
            in_quote = not in_quote
        elif c == '/' and not in_quote and i + 1 < len(line) and line[i + 1] == '/':
            return line[:i].rstrip()
        i += 1
    return line


def _coerce_value(val: str) -> Any:
    """Coerce a string value to int, float, bool, or string."""
    if not val:
        return ""
    # Booleans
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    # Integers
    try:
        return int(val)
    except ValueError:
        pass
    # Floats
    try:
        return float(val)
    except ValueError:
        pass
    # Quoted strings -- strip quotes
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        return val[1:-1]
    return val


def _split_key_value(line: str) -> tuple[str, str | None]:
    """Split a line into key and optional value.

    The key is the first whitespace-delimited token. The value is everything
    after the first whitespace. If the value starts with a quote, we take
    everything from the opening quote to the closing quote (to handle quoted
    strings with spaces correctly).
    """
    line = line.strip()
    if not line:
        return ("", None)

    # Find end of key
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


def _next_content_line(lines: list[str], start: int) -> tuple[str, int] | None:
    """Find the next non-empty line after stripping comments."""
    for i in range(start, len(lines)):
        stripped = _strip_comment(lines[i]).strip()
        if stripped:
            return (stripped, i)
    return None


def _parse_mapping(lines: list[str], start: int) -> tuple[dict[str, Any], int]:
    """Parse key-value pairs until end of input or closing bracket."""
    result: dict[str, Any] = {}
    i = start

    while i < len(lines):
        line = _strip_comment(lines[i]).strip()

        if not line:
            i += 1
            continue

        # End of block
        if line in ("}", "]"):
            return result, i + 1

        key, value = _split_key_value(line)
        if not key:
            i += 1
            continue

        if value is not None and value in ("[", "{"):
            # Block opener on same line as key
            if value == "[":
                parsed, i = _parse_array(lines, i + 1)
            else:
                parsed, i = _parse_mapping(lines, i + 1)
            result[key] = parsed
            continue

        if value is None:
            # Check if next content line is a block opener
            nxt = _next_content_line(lines, i + 1)
            if nxt is not None and nxt[0] in ("[", "{"):
                if nxt[0] == "[":
                    parsed, i = _parse_array(lines, nxt[1] + 1)
                else:
                    parsed, i = _parse_mapping(lines, nxt[1] + 1)
                result[key] = parsed
                continue
            # Bare flag
            result[key] = True
            i += 1
            continue

        # Regular key-value
        result[key] = _coerce_value(value)
        i += 1

    return result, i


def _parse_array(lines: list[str], start: int) -> tuple[list[Any], int]:
    """Parse array contents until closing ]."""
    result: list[Any] = []
    i = start

    while i < len(lines):
        line = _strip_comment(lines[i]).strip()

        if not line:
            i += 1
            continue

        if line == "]":
            return result, i + 1

        if line == "{":
            obj, i = _parse_mapping(lines, i + 1)
            result.append(obj)
            continue

        # Bare value (number, quoted string, etc.)
        result.append(_coerce_value(line))
        i += 1

    return result, i
```

**Step 4: Run tests to verify they pass**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: generic .dat parser with flat key-value support"
```

---

## Task 3: Generic `.dat` parser — nested blocks

**Files:**
- Modify: `~/bin/unturned_data/tests/test_dat_parser.py` (add tests)
- Modify: `~/bin/unturned_data/dat_parser.py` (should already handle these)

**Step 1: Write failing tests for nested blocks**

Append to `test_dat_parser.py`:

```python
class TestNestedBlocks:
    """Test [...] and {...} block parsing."""

    def test_simple_array_of_objects(self):
        text = """\
Blueprints
[
\t{
\t\tName Repair
\t\tSkill_Level 3
\t}
\t{
\t\tName Salvage
\t}
]"""
        result = parse_dat(text)
        assert len(result["Blueprints"]) == 2
        assert result["Blueprints"][0]["Name"] == "Repair"
        assert result["Blueprints"][0]["Skill_Level"] == 3
        assert result["Blueprints"][1]["Name"] == "Salvage"

    def test_array_of_strings(self):
        text = """\
DefaultPaintColors
[
\t"#475e83"
\t"#a69884"
]"""
        result = parse_dat(text)
        assert result["DefaultPaintColors"] == ["#475e83", "#a69884"]

    def test_array_of_numbers(self):
        text = """\
ForwardGearRatios
[
\t20
\t12.56
]"""
        result = parse_dat(text)
        assert result["ForwardGearRatios"] == [20, 12.56]

    def test_nested_object(self):
        text = """\
EngineSound
{
\tIdlePitch 1.0
\tMaxPitch 2
}"""
        result = parse_dat(text)
        assert result["EngineSound"]["IdlePitch"] == 1.0
        assert result["EngineSound"]["MaxPitch"] == 2

    def test_deeply_nested(self):
        """Array containing objects that themselves contain arrays."""
        text = """\
Blueprints
[
\t{
\t\tName Repair
\t\tInputItems
\t\t[
\t\t\t{
\t\t\t\tID "abc123"
\t\t\t\tAmount 4
\t\t\t}
\t\t\t{
\t\t\t\tID "def456"
\t\t\t\tDelete false
\t\t\t}
\t\t]
\t\tRequiresNearbyCraftingTags
\t\t[
\t\t\t"tag1"
\t\t\t"tag2"
\t\t]
\t}
]"""
        result = parse_dat(text)
        bp = result["Blueprints"][0]
        assert bp["Name"] == "Repair"
        assert len(bp["InputItems"]) == 2
        assert bp["InputItems"][0]["ID"] == "abc123"
        assert bp["InputItems"][0]["Amount"] == 4
        assert bp["InputItems"][1]["Delete"] is False
        assert bp["RequiresNearbyCraftingTags"] == ["tag1", "tag2"]

    def test_mixed_array(self):
        """Array with both bare values and objects."""
        text = """\
OutputItems
[
\tthis
\t"abc123 x 9"
]"""
        result = parse_dat(text)
        assert result["OutputItems"] == ["this", "abc123 x 9"]

    def test_inline_comments_in_blocks(self):
        text = """\
Blueprints
[
\t{
\t\tCategoryTag "abc" // Supplies
\t\tInputItems "def x 2" // Rag
\t\tOutputItems this
\t}
]"""
        result = parse_dat(text)
        bp = result["Blueprints"][0]
        assert bp["CategoryTag"] == "abc"
        assert bp["InputItems"] == "def x 2"
        assert bp["OutputItems"] == "this"


class TestRealFixtures:
    """Parse actual fixture files end-to-end."""

    def test_canned_beans(self):
        result = parse_dat_file(
            FIXTURES / "food_beans" / "Canned_Beans.dat"
        )
        assert result["Type"] == "Food"
        assert result["ID"] == 13
        assert result["Health"] == 10
        assert result["Food"] == 55
        assert result["Size_X"] == 1
        assert result["Size_Y"] == 1

    def test_maplestrike(self):
        result = parse_dat_file(
            FIXTURES / "gun_maplestrike" / "Maplestrike.dat"
        )
        assert result["Type"] == "Gun"
        assert result["Player_Damage"] == 40
        assert result["Firerate"] == 5
        assert result["Semi"] is True
        assert result["Auto"] is True
        assert len(result["Blueprints"]) == 2
        assert result["Blueprints"][0]["Name"] == "Repair"

    def test_bandage(self):
        result = parse_dat_file(
            FIXTURES / "medical_bandage" / "Bandage.dat"
        )
        assert result["Type"] == "Medical"
        assert result["Health"] == 15
        assert result["Bleeding_Modifier"] == "Heal"
        assert len(result["Blueprints"]) == 1

    def test_humvee(self):
        result = parse_dat_file(
            FIXTURES / "vehicle_humvee" / "Humvee.dat"
        )
        assert result["Type"] == "Vehicle"
        assert result["Speed_Max"] == 14
        assert result["Fuel"] == 2000
        assert len(result["WheelConfigurations"]) == 4
        assert isinstance(result["EngineSound"], dict)
        assert result["EngineSound"]["IdlePitch"] == 1.0
        assert result["DefaultPaintColors"] == [
            "#475e83", "#a69884", "#437c44", "#495631"
        ]
        assert result["ForwardGearRatios"] == [20, 12.56]

    def test_bear(self):
        result = parse_dat_file(FIXTURES / "animal_bear" / "Bear.dat")
        assert result["Type"] == "Animal"
        assert result["Health"] == 100
        assert result["Speed_Run"] == 12
        assert result["Damage"] == 20

    def test_katana(self):
        result = parse_dat_file(FIXTURES / "melee_katana" / "Katana.dat")
        assert result["Type"] == "Melee"
        assert result["Player_Damage"] == 50
        assert result["Strength"] == 1.5
        assert result["Range"] == 2.25
```

**Step 2: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py -v
```

Expected: `TestRealFixtures` tests fail (fixtures not yet copied), nested
block tests should pass (parser from Task 2 already handles them).

**Step 3: Copy fixture files (if not done in Task 1)**

Ensure all fixture files are in place. Then re-run:

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_dat_parser.py -v
```

Expected: all pass.

**Step 4: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "test: nested block and real fixture tests for dat parser"
```

---

## Task 4: English.dat loader + directory walker

**Files:**
- Create: `~/bin/unturned_data/loader.py`
- Create: `~/bin/unturned_data/tests/test_loader.py`

**Step 1: Write failing tests**

```python
"""Tests for bundle directory walking and English.dat loading."""
import pytest
from pathlib import Path
from unturned_data.loader import load_english_dat, walk_bundle_dir, load_entry_raw

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestEnglishDat:
    def test_load_name_and_description(self):
        result = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        assert result["Name"] == "Canned Beans"
        assert result["Description"] == "Very tactically packed for maximum taste."

    def test_missing_file(self):
        result = load_english_dat(FIXTURES / "nonexistent" / "English.dat")
        assert result == {}


class TestLoadEntryRaw:
    def test_load_combines_dat_and_english(self):
        raw, english = load_entry_raw(FIXTURES / "food_beans")
        assert raw["Type"] == "Food"
        assert raw["ID"] == 13
        assert english["Name"] == "Canned Beans"


class TestWalkBundleDir:
    def test_walks_fixtures(self):
        entries = list(walk_bundle_dir(FIXTURES))
        # Should find all fixture directories that contain .dat files
        assert len(entries) > 0
        # Each entry is (raw_dict, english_dict, relative_path)
        for raw, english, rel_path in entries:
            assert "Type" in raw or "GUID" in raw or "ID" in raw

    def test_returns_relative_paths(self):
        entries = list(walk_bundle_dir(FIXTURES))
        for _, _, rel_path in entries:
            assert not rel_path.startswith("/")
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_loader.py -v
```

**Step 3: Implement loader**

```python
"""
Walk bundle directories and load .dat + English.dat file pairs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from .dat_parser import parse_dat_file


def load_english_dat(path: Path) -> dict[str, str]:
    """Parse an English.dat localization file.

    Format is simple Key Value pairs (Name, Description, etc.).
    """
    if not path.exists():
        return {}
    result = {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
        elif len(parts) == 1:
            result[parts[0]] = ""
    return result


def load_entry_raw(directory: Path) -> tuple[dict[str, Any], dict[str, str]]:
    """Load the .dat and English.dat from a single entry directory.

    The main .dat file is the one whose stem matches the directory name.
    If no exact match, uses the first non-English .dat file found.
    """
    # Find main .dat file
    dat_path = directory / f"{directory.name}.dat"
    if not dat_path.exists():
        # Fallback: first .dat that isn't English.dat
        candidates = [
            f for f in directory.glob("*.dat")
            if f.name.lower() != "english.dat"
            and f.name.lower() != "masterbundle.dat"
        ]
        if not candidates:
            return {}, {}
        dat_path = candidates[0]

    try:
        raw = parse_dat_file(dat_path)
    except (OSError, UnicodeDecodeError):
        raw = {}

    english = load_english_dat(directory / "English.dat")
    return raw, english


def walk_bundle_dir(
    root: Path,
) -> Iterator[tuple[dict[str, Any], dict[str, str], str]]:
    """Walk a Bundles directory tree, yielding parsed entries.

    Yields (raw_dict, english_dict, relative_path) for each entry directory
    that contains a parseable .dat file.

    Skips directories that only contain subdirectories (category folders).
    """
    root = root.resolve()

    for dat_file in sorted(root.rglob("*.dat")):
        # Skip English.dat, MasterBundle.dat, and manifest files
        if dat_file.name.lower() in ("english.dat", "masterbundle.dat"):
            continue
        if dat_file.suffix != ".dat":
            continue

        entry_dir = dat_file.parent
        # Only process if the .dat file matches directory name pattern
        # (i.e., it's an entry directory, not a config file)
        expected_name = f"{entry_dir.name}.dat"
        if dat_file.name != expected_name:
            continue

        raw, english = load_entry_raw(entry_dir)
        if not raw:
            continue

        rel_path = str(entry_dir.relative_to(root))
        yield raw, english, rel_path
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_loader.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: English.dat loader and bundle directory walker"
```

---

## Task 5: Base model + shared stat dataclasses

**Files:**
- Create: `~/bin/unturned_data/models.py`
- Create: `~/bin/unturned_data/tests/test_models.py`

**Step 1: Write failing tests**

```python
"""Tests for base model and shared stat classes."""
import pytest
from pathlib import Path
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models import (
    BundleEntry,
    DamageStats,
    ConsumableStats,
    StorageStats,
    Blueprint,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestDamageStats:
    def test_from_raw_gun(self):
        raw = parse_dat_file(FIXTURES / "gun_maplestrike" / "Maplestrike.dat")
        dmg = DamageStats.from_raw(raw)
        assert dmg is not None
        assert dmg.player == 40
        assert dmg.zombie == 99
        assert dmg.animal == 40
        assert dmg.player_multipliers["skull"] == 1.1
        assert dmg.player_multipliers["leg"] == 0.6
        assert dmg.barricade == 20
        assert dmg.vehicle == 35

    def test_from_raw_no_damage(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        dmg = DamageStats.from_raw(raw)
        assert dmg is None

    def test_from_raw_melee(self):
        raw = parse_dat_file(FIXTURES / "melee_katana" / "Katana.dat")
        dmg = DamageStats.from_raw(raw)
        assert dmg is not None
        assert dmg.player == 50


class TestConsumableStats:
    def test_from_raw_food(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        stats = ConsumableStats.from_raw(raw)
        assert stats is not None
        assert stats.health == 10
        assert stats.food == 55
        assert stats.water == 0

    def test_from_raw_with_virus(self):
        raw = parse_dat_file(FIXTURES / "water_berries" / "Raw_Amber_Berries.dat")
        stats = ConsumableStats.from_raw(raw)
        assert stats is not None
        assert stats.virus == 5
        assert stats.vision == 20

    def test_from_raw_no_consumable(self):
        raw = parse_dat_file(FIXTURES / "gun_maplestrike" / "Maplestrike.dat")
        stats = ConsumableStats.from_raw(raw)
        assert stats is None


class TestStorageStats:
    def test_from_raw_backpack(self):
        raw = parse_dat_file(FIXTURES / "backpack_alice" / "Alicepack.dat")
        storage = StorageStats.from_raw(raw)
        assert storage is not None
        assert storage.width == 8
        assert storage.height == 7

    def test_from_raw_no_storage(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        storage = StorageStats.from_raw(raw)
        assert storage is None


class TestBlueprint:
    def test_from_raw_simple(self):
        raw = parse_dat_file(FIXTURES / "medical_bandage" / "Bandage.dat")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        assert bps[0].category_tag == "d089feb7e43f40c5a7dfcefc36998cfb"

    def test_from_raw_complex(self):
        raw = parse_dat_file(FIXTURES / "gun_maplestrike" / "Maplestrike.dat")
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 2
        assert bps[0].name == "Repair"
        assert bps[1].name == "Salvage"

    def test_from_raw_with_skill(self):
        raw = parse_dat_file(
            FIXTURES / "food_sandwich" / "Sandwich_Beef.dat"
        )
        bps = Blueprint.list_from_raw(raw)
        assert len(bps) == 1
        assert bps[0].skill == "Cook"
        assert bps[0].skill_level == 2
        assert len(bps[0].workstation_tags) == 1

    def test_no_blueprints(self):
        raw = parse_dat_file(FIXTURES / "animal_bear" / "Bear.dat")
        bps = Blueprint.list_from_raw(raw)
        assert bps == []


class TestBundleEntry:
    def test_from_raw(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        english = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = BundleEntry.from_raw(raw, english, "Items/Food/Canned_Beans")
        assert entry.guid == "78fefdd23def4ab6ac8301adfcc3b2d4"
        assert entry.type == "Food"
        assert entry.id == 13
        assert entry.name == "Canned Beans"
        assert entry.size_x == 1
        assert entry.size_y == 1
        assert entry.source_path == "Items/Food/Canned_Beans"
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_models.py -v
```

**Step 3: Implement models**

```python
"""
Base model and shared stat dataclasses for Unturned bundle entries.

Shared stats (DamageStats, ConsumableStats, etc.) are composed into
category-specific models rather than inherited.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DamageStats:
    """Damage values shared by guns, melee, throwables, traps, animals."""

    player: float = 0
    zombie: float = 0
    animal: float = 0
    player_multipliers: dict[str, float] = field(default_factory=dict)
    zombie_multipliers: dict[str, float] = field(default_factory=dict)
    animal_multipliers: dict[str, float] = field(default_factory=dict)
    barricade: float = 0
    structure: float = 0
    vehicle: float = 0
    resource: float = 0
    object: float = 0

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> DamageStats | None:
        if not any(
            k in raw
            for k in ("Player_Damage", "Zombie_Damage", "Animal_Damage", "Damage")
        ):
            return None
        multiplier_parts = ("Skull", "Spine", "Arm", "Leg")
        return DamageStats(
            player=raw.get("Player_Damage", 0),
            zombie=raw.get("Zombie_Damage", 0),
            animal=raw.get("Animal_Damage", raw.get("Damage", 0)),
            player_multipliers={
                p.lower(): raw.get(f"Player_{p}_Multiplier", 1.0)
                for p in multiplier_parts
                if f"Player_{p}_Multiplier" in raw
            },
            zombie_multipliers={
                p.lower(): raw.get(f"Zombie_{p}_Multiplier", 1.0)
                for p in multiplier_parts
                if f"Zombie_{p}_Multiplier" in raw
            },
            animal_multipliers={
                p.lower(): raw.get(f"Animal_{p}_Multiplier", 1.0)
                for p in multiplier_parts
                if f"Animal_{p}_Multiplier" in raw
            },
            barricade=raw.get("Barricade_Damage", 0),
            structure=raw.get("Structure_Damage", 0),
            vehicle=raw.get("Vehicle_Damage", 0),
            resource=raw.get("Resource_Damage", 0),
            object=raw.get("Object_Damage", 0),
        )


@dataclass
class ConsumableStats:
    """Stats for food, water, and medical items."""

    health: float = 0
    food: float = 0
    water: float = 0
    virus: float = 0
    vision: float = 0
    bleeding_modifier: str = ""

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> ConsumableStats | None:
        has_any = any(
            k in raw for k in ("Food", "Water", "Virus", "Bleeding_Modifier")
        )
        # Health alone isn't enough (structures have Health too)
        useable = raw.get("Useable", "")
        if not has_any and useable != "Consumeable":
            return None
        return ConsumableStats(
            health=raw.get("Health", 0),
            food=raw.get("Food", 0),
            water=raw.get("Water", 0),
            virus=raw.get("Virus", 0),
            vision=raw.get("Vision", 0),
            bleeding_modifier=raw.get("Bleeding_Modifier", ""),
        )


@dataclass
class StorageStats:
    """Container dimensions (backpacks, vests, clothing with pockets)."""

    width: int = 0
    height: int = 0

    @staticmethod
    def from_raw(raw: dict[str, Any]) -> StorageStats | None:
        if "Width" not in raw and "Height" not in raw:
            return None
        return StorageStats(
            width=raw.get("Width", 0),
            height=raw.get("Height", 0),
        )


@dataclass
class Blueprint:
    """A single crafting recipe."""

    name: str = ""
    category_tag: str = ""
    operation: str = ""
    inputs: list[Any] = field(default_factory=list)
    outputs: list[Any] = field(default_factory=list)
    skill: str = ""
    skill_level: int = 0
    workstation_tags: list[str] = field(default_factory=list)

    @staticmethod
    def list_from_raw(raw: dict[str, Any]) -> list[Blueprint]:
        bp_data = raw.get("Blueprints")
        if not bp_data or not isinstance(bp_data, list):
            return []
        result = []
        for bp in bp_data:
            if not isinstance(bp, dict):
                continue
            # Inputs can be string shorthand or array of objects
            inputs = bp.get("InputItems", [])
            if isinstance(inputs, str):
                inputs = [inputs]
            outputs = bp.get("OutputItems", [])
            if isinstance(outputs, str):
                outputs = [outputs]
            workstations = bp.get("RequiresNearbyCraftingTags", [])
            if isinstance(workstations, str):
                workstations = [workstations]
            result.append(
                Blueprint(
                    name=bp.get("Name", ""),
                    category_tag=bp.get("CategoryTag", ""),
                    operation=bp.get("Operation", ""),
                    inputs=inputs if isinstance(inputs, list) else [inputs],
                    outputs=outputs if isinstance(outputs, list) else [outputs],
                    skill=bp.get("Skill", ""),
                    skill_level=bp.get("Skill_Level", 0),
                    workstation_tags=(
                        workstations
                        if isinstance(workstations, list)
                        else [workstations]
                    ),
                )
            )
        return result


@dataclass
class BundleEntry:
    """Base class for all bundle entries."""

    guid: str = ""
    type: str = ""
    id: int = 0
    name: str = ""
    description: str = ""
    rarity: str = ""
    size_x: int = 0
    size_y: int = 0
    source_path: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> BundleEntry:
        return cls(
            guid=str(raw.get("GUID", "")),
            type=str(raw.get("Type", "")),
            id=raw.get("ID", 0) if isinstance(raw.get("ID"), int) else 0,
            name=english.get("Name", ""),
            description=english.get("Description", ""),
            rarity=str(raw.get("Rarity", "")),
            size_x=raw.get("Size_X", 0) if isinstance(raw.get("Size_X"), int) else 0,
            size_y=raw.get("Size_Y", 0) if isinstance(raw.get("Size_Y"), int) else 0,
            source_path=source_path,
            raw=raw,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON output. Subclasses extend this."""
        d: dict[str, Any] = {}
        if self.guid:
            d["guid"] = self.guid
        d["type"] = self.type
        if self.id:
            d["id"] = self.id
        if self.name:
            d["name"] = self.name
        if self.description:
            d["description"] = self.description
        if self.rarity:
            d["rarity"] = self.rarity
        if self.size_x or self.size_y:
            d["size"] = {"x": self.size_x, "y": self.size_y}
        d["source_path"] = self.source_path
        d["raw"] = self.raw
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return ["Name", "ID", "Type", "Rarity", "Size"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        size = (
            f"{self.size_x}x{self.size_y}"
            if self.size_x or self.size_y
            else ""
        )
        return [self.name, str(self.id), self.type, self.rarity, size]
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_models.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: base model and shared stat dataclasses"
```

---

## Task 6: Category models — Items

The largest category. Each item subtype gets its own class composing the
relevant shared stats.

**Files:**
- Create: `~/bin/unturned_data/categories/items.py`
- Create: `~/bin/unturned_data/tests/test_categories.py`

**Step 1: Write failing tests**

```python
"""Tests for category-specific models."""
import pytest
from pathlib import Path
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.categories import parse_entry

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(fixture_name: str, dat_name: str):
    d = FIXTURES / fixture_name
    raw = parse_dat_file(d / f"{dat_name}.dat")
    english = load_english_dat(d / "English.dat")
    return raw, english


class TestGun:
    def test_parse(self):
        raw, eng = _load("gun_maplestrike", "Maplestrike")
        entry = parse_entry(raw, eng, "Items/Guns/Maplestrike")
        assert entry.type == "Gun"
        assert entry.name == "Maplestrike"
        assert entry.damage is not None
        assert entry.damage.player == 40
        assert entry.firerate == 5
        assert entry.range == 200
        assert "Auto" in entry.fire_modes
        assert "Semi" in entry.fire_modes
        assert entry.slot == "Primary"
        assert len(entry.blueprints) == 2

    def test_markdown_row(self):
        raw, eng = _load("gun_maplestrike", "Maplestrike")
        entry = parse_entry(raw, eng, "Items/Guns/Maplestrike")
        cols = type(entry).markdown_columns()
        row = entry.markdown_row({})
        assert len(cols) == len(row)
        assert "Maplestrike" in row


class TestMelee:
    def test_parse(self):
        raw, eng = _load("melee_katana", "Katana")
        entry = parse_entry(raw, eng, "Items/Melee/Katana")
        assert entry.type == "Melee"
        assert entry.damage is not None
        assert entry.damage.player == 50
        assert entry.strength == 1.5
        assert entry.range == 2.25


class TestConsumeable:
    def test_food(self):
        raw, eng = _load("food_beans", "Canned_Beans")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        assert entry.consumable is not None
        assert entry.consumable.food == 55
        assert entry.consumable.health == 10

    def test_medical(self):
        raw, eng = _load("medical_bandage", "Bandage")
        entry = parse_entry(raw, eng, "Items/Medical/Bandage")
        assert entry.consumable is not None
        assert entry.consumable.bleeding_modifier == "Heal"

    def test_water_with_virus(self):
        raw, eng = _load("water_berries", "Raw_Amber_Berries")
        entry = parse_entry(raw, eng, "Items/Water/Raw_Amber_Berries")
        assert entry.consumable is not None
        assert entry.consumable.virus == 5


class TestClothing:
    def test_backpack(self):
        raw, eng = _load("backpack_alice", "Alicepack")
        entry = parse_entry(raw, eng, "Items/Backpacks/Alicepack")
        assert entry.storage is not None
        assert entry.storage.width == 8
        assert entry.storage.height == 7


class TestVehicle:
    def test_parse(self):
        raw, eng = _load("vehicle_humvee", "Humvee")
        entry = parse_entry(raw, eng, "Vehicles/Humvee")
        assert entry.type == "Vehicle"
        assert entry.speed_max == 14
        assert entry.fuel_capacity == 2000
        assert entry.health_max == 450
        assert entry.trunk_x == 6
        assert entry.trunk_y == 5


class TestAnimal:
    def test_parse(self):
        raw, eng = _load("animal_bear", "Bear")
        entry = parse_entry(raw, eng, "Animals/Bear")
        assert entry.type == "Animal"
        assert entry.health == 100
        assert entry.speed_run == 12
        assert entry.damage == 20
        assert entry.behaviour == "Offense"


class TestGenericFallback:
    def test_unknown_type_uses_generic(self):
        raw = {"Type": "SomeNewType", "ID": 9999, "Foo": "bar"}
        entry = parse_entry(raw, {}, "Unknown/Thing")
        assert entry.type == "SomeNewType"
        assert entry.raw["Foo"] == "bar"
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_categories.py -v
```

**Step 3: Implement category models**

`~/bin/unturned_data/categories/items.py`:

```python
"""Item category models: Gun, Melee, Consumeable, Clothing, etc."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import BundleEntry, DamageStats, ConsumableStats, StorageStats, Blueprint

# Fire mode flags found in .dat files
FIRE_MODES = ("Safety", "Semi", "Auto", "Burst")


@dataclass
class Gun(BundleEntry):
    damage: DamageStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)
    slot: str = ""
    caliber: int = 0
    firerate: int = 0
    range: float = 0
    fire_modes: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    ammo_min: int = 0
    ammo_max: int = 0
    durability: float = 0
    spread_aim: float = 0
    spread_angle: float = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Gun:
        base = BundleEntry.from_raw(raw, english, source_path)
        hook_keys = [k for k in raw if k.startswith("Hook_")]
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            damage=DamageStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
            slot=str(raw.get("Slot", "")),
            caliber=raw.get("Caliber", 0),
            firerate=raw.get("Firerate", 0),
            range=raw.get("Range", 0),
            fire_modes=[m for m in FIRE_MODES if raw.get(m) is True],
            hooks=[k.removeprefix("Hook_") for k in hook_keys],
            ammo_min=raw.get("Ammo_Min", 0),
            ammo_max=raw.get("Ammo_Max", 0),
            durability=raw.get("Durability", 0),
            spread_aim=raw.get("Spread_Aim", 0),
            spread_angle=raw.get("Spread_Angle_Degrees", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Size", "Slot", "Range", "Firerate",
            "Modes", "Player Dmg", "Zombie Dmg", "Animal Dmg",
            "Durability",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            self.slot, str(self.range), str(self.firerate),
            "/".join(self.fire_modes),
            str(self.damage.player) if self.damage else "",
            str(self.damage.zombie) if self.damage else "",
            str(self.damage.animal) if self.damage else "",
            str(self.durability),
        ]


@dataclass
class MeleeWeapon(BundleEntry):
    damage: DamageStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)
    slot: str = ""
    range: float = 0
    strength: float = 0
    stamina: float = 0
    durability: float = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> MeleeWeapon:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            damage=DamageStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
            slot=str(raw.get("Slot", "")),
            range=raw.get("Range", 0),
            strength=raw.get("Strength", 0),
            stamina=raw.get("Stamina", 0),
            durability=raw.get("Durability", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Size", "Range", "Strength",
            "Player Dmg", "Zombie Dmg", "Durability",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(self.range), str(self.strength),
            str(self.damage.player) if self.damage else "",
            str(self.damage.zombie) if self.damage else "",
            str(self.durability),
        ]


@dataclass
class Consumeable(BundleEntry):
    consumable: ConsumableStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Consumeable:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            consumable=ConsumableStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Size", "Health", "Food", "Water",
            "Virus", "Bleeding",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        c = self.consumable
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(c.health) if c else "",
            str(c.food) if c else "",
            str(c.water) if c else "",
            str(c.virus) if c else "",
            c.bleeding_modifier if c else "",
        ]


@dataclass
class Clothing(BundleEntry):
    storage: StorageStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)
    armor: float = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Clothing:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            storage=StorageStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
            armor=raw.get("Armor", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Type", "Rarity", "Size", "Storage", "Armor",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        storage = (
            f"{self.storage.width}x{self.storage.height}"
            if self.storage else ""
        )
        return [
            self.name, str(self.id), self.type, self.rarity,
            f"{self.size_x}x{self.size_y}",
            storage, str(self.armor) if self.armor else "",
        ]


@dataclass
class Throwable(BundleEntry):
    damage: DamageStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)
    fuse: float = 0
    explosion: int = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Throwable:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            damage=DamageStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
            fuse=raw.get("Fuse", 0),
            explosion=raw.get("Explosion", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Size", "Fuse",
            "Player Dmg", "Zombie Dmg",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(self.fuse),
            str(self.damage.player) if self.damage else "",
            str(self.damage.zombie) if self.damage else "",
        ]


@dataclass
class BarricadeItem(BundleEntry):
    damage: DamageStats | None = None
    blueprints: list[Blueprint] = field(default_factory=list)
    health: int = 0
    range: float = 0
    build: str = ""

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> BarricadeItem:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            damage=DamageStats.from_raw(raw),
            blueprints=Blueprint.list_from_raw(raw),
            health=raw.get("Health", 0),
            range=raw.get("Range", 0),
            build=str(raw.get("Build", "")),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Size", "Health", "Build",
            "Player Dmg", "Zombie Dmg",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(self.health), self.build,
            str(self.damage.player) if self.damage else "",
            str(self.damage.zombie) if self.damage else "",
        ]


@dataclass
class StructureItem(BundleEntry):
    blueprints: list[Blueprint] = field(default_factory=list)
    health: int = 0
    range: float = 0
    construct: str = ""

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> StructureItem:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            blueprints=Blueprint.list_from_raw(raw),
            health=raw.get("Health", 0),
            range=raw.get("Range", 0),
            construct=str(raw.get("Construct", "")),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return ["Name", "ID", "Rarity", "Size", "Health", "Construct"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(self.health), self.construct,
        ]


@dataclass
class Magazine(BundleEntry):
    blueprints: list[Blueprint] = field(default_factory=list)
    amount: int = 0
    count_min: int = 0
    count_max: int = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Magazine:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            blueprints=Blueprint.list_from_raw(raw),
            amount=raw.get("Amount", 0),
            count_min=raw.get("Count_Min", 0),
            count_max=raw.get("Count_Max", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return ["Name", "ID", "Rarity", "Size", "Amount"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.rarity,
            f"{self.size_x}x{self.size_y}",
            str(self.amount),
        ]


@dataclass
class Attachment(BundleEntry):
    """Sight, Grip, Barrel, Tactical attachments."""
    blueprints: list[Blueprint] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Attachment:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            blueprints=Blueprint.list_from_raw(raw),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return ["Name", "ID", "Type", "Rarity", "Size"]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), self.type, self.rarity,
            f"{self.size_x}x{self.size_y}",
        ]
```

`~/bin/unturned_data/categories/vehicles.py`:

```python
"""Vehicle model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import BundleEntry


@dataclass
class Vehicle(BundleEntry):
    speed_min: float = 0
    speed_max: float = 0
    steer_min: float = 0
    steer_max: float = 0
    brake: float = 0
    fuel_min: int = 0
    fuel_max: int = 0
    fuel_capacity: int = 0
    health_min: int = 0
    health_max: int = 0
    trunk_x: int = 0
    trunk_y: int = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Vehicle:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            speed_min=raw.get("Speed_Min", 0),
            speed_max=raw.get("Speed_Max", 0),
            steer_min=raw.get("Steer_Min", 0),
            steer_max=raw.get("Steer_Max", 0),
            brake=raw.get("Brake", 0),
            fuel_min=raw.get("Fuel_Min", 0),
            fuel_max=raw.get("Fuel_Max", 0),
            fuel_capacity=raw.get("Fuel", 0),
            health_min=raw.get("Health_Min", 0),
            health_max=raw.get("Health_Max", 0),
            trunk_x=raw.get("Trunk_Storage_X", 0),
            trunk_y=raw.get("Trunk_Storage_Y", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Rarity", "Speed Min", "Speed Max",
            "Fuel Cap", "Health Max", "Trunk",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        trunk = (
            f"{self.trunk_x}x{self.trunk_y}"
            if self.trunk_x or self.trunk_y else ""
        )
        return [
            self.name, str(self.id), self.rarity,
            str(self.speed_min), str(self.speed_max),
            str(self.fuel_capacity), str(self.health_max),
            trunk,
        ]
```

`~/bin/unturned_data/categories/animals.py`:

```python
"""Animal model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import BundleEntry


@dataclass
class Animal(BundleEntry):
    health: int = 0
    damage: int = 0
    speed_run: float = 0
    speed_walk: float = 0
    behaviour: str = ""
    regen: float = 0
    reward_id: int = 0
    reward_xp: int = 0

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> Animal:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            health=raw.get("Health", 0),
            damage=raw.get("Damage", 0),
            speed_run=raw.get("Speed_Run", 0),
            speed_walk=raw.get("Speed_Walk", 0),
            behaviour=str(raw.get("Behaviour", "")),
            regen=raw.get("Regen", 0),
            reward_id=raw.get("Reward_ID", 0),
            reward_xp=raw.get("Reward_XP", 0),
        )

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name", "ID", "Health", "Damage", "Speed Run",
            "Speed Walk", "Behaviour",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name, str(self.id), str(self.health), str(self.damage),
            str(self.speed_run), str(self.speed_walk), self.behaviour,
        ]
```

`~/bin/unturned_data/categories/generic.py`:

```python
"""Generic fallback for unknown types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import BundleEntry


@dataclass
class GenericEntry(BundleEntry):
    """Fallback for any Type without a dedicated parser."""

    @classmethod
    def from_raw(cls, raw: dict, english: dict, source_path: str) -> GenericEntry:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(**{k: v for k, v in base.__dict__.items()})
```

`~/bin/unturned_data/categories/__init__.py` — type registry + dispatch:

```python
"""Type registry mapping .dat Type values to model classes."""
from __future__ import annotations

from typing import Any

from ..models import BundleEntry
from .items import (
    Gun, MeleeWeapon, Consumeable, Clothing, Throwable,
    BarricadeItem, StructureItem, Magazine, Attachment,
)
from .vehicles import Vehicle
from .animals import Animal
from .generic import GenericEntry

# Maps .dat "Type" field to parser class
TYPE_REGISTRY: dict[str, type[BundleEntry]] = {
    # Weapons
    "Gun": Gun,
    "Melee": MeleeWeapon,
    "Throwable": Throwable,
    # Consumeables
    "Food": Consumeable,
    "Water": Consumeable,
    "Medical": Consumeable,
    # Clothing
    "Shirt": Clothing,
    "Pants": Clothing,
    "Hat": Clothing,
    "Vest": Clothing,
    "Backpack": Clothing,
    "Mask": Clothing,
    "Glasses": Clothing,
    # Buildables
    "Barricade": BarricadeItem,
    "Trap": BarricadeItem,
    "Storage": BarricadeItem,
    "Sentry": BarricadeItem,
    "Generator": BarricadeItem,
    "Beacon": BarricadeItem,
    "Oil_Pump": BarricadeItem,
    "Structure": StructureItem,
    # Equipment
    "Magazine": Magazine,
    "Sight": Attachment,
    "Grip": Attachment,
    "Barrel": Attachment,
    "Tactical": Attachment,
    # Vehicles & Animals
    "Vehicle": Vehicle,
    "Animal": Animal,
}


def parse_entry(
    raw: dict[str, Any],
    english: dict[str, str],
    source_path: str,
) -> BundleEntry:
    """Dispatch to the appropriate model class based on Type field."""
    entry_type = str(raw.get("Type", ""))
    cls = TYPE_REGISTRY.get(entry_type, GenericEntry)
    return cls.from_raw(raw, english, source_path)
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_categories.py -v
```

Expected: all pass.

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: category models with type dispatch"
```

---

## Task 7: JSON formatter

**Files:**
- Create: `~/bin/unturned_data/formatters/json_fmt.py`
- Create: `~/bin/unturned_data/tests/test_json_fmt.py`

**Step 1: Write failing tests**

```python
"""Tests for JSON output formatter."""
import json
import pytest
from pathlib import Path
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.categories import parse_entry
from unturned_data.formatters.json_fmt import entries_to_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestJsonFormatter:
    def test_produces_valid_json(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        eng = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        output = entries_to_json([entry])
        parsed = json.loads(output)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "Canned Beans"

    def test_deterministic_output(self):
        """Same input produces identical output."""
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        eng = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        output1 = entries_to_json([entry])
        output2 = entries_to_json([entry])
        assert output1 == output2

    def test_sorted_by_type_then_name(self):
        entries = []
        for name, dat in [
            ("gun_maplestrike", "Maplestrike"),
            ("food_beans", "Canned_Beans"),
            ("animal_bear", "Bear"),
        ]:
            d = FIXTURES / name
            raw = parse_dat_file(d / f"{dat}.dat")
            eng = load_english_dat(d / "English.dat")
            entries.append(parse_entry(raw, eng, f"test/{name}"))
        output = json.loads(entries_to_json(entries))
        types = [e["type"] for e in output]
        # Should be sorted: Animal, Food, Gun
        assert types == sorted(types)
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_json_fmt.py -v
```

**Step 3: Implement JSON formatter**

```python
"""JSON output formatter."""
from __future__ import annotations

import json
from typing import Any

from ..models import BundleEntry


def entries_to_json(entries: list[BundleEntry], indent: int = 2) -> str:
    """Serialize entries to deterministic JSON.

    Sorted by (type, name, id) for deterministic output.
    """
    sorted_entries = sorted(entries, key=lambda e: (e.type, e.name, e.id))
    data = [_entry_to_dict(e) for e in sorted_entries]
    return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)


def _entry_to_dict(entry: BundleEntry) -> dict[str, Any]:
    """Convert a BundleEntry to a JSON-serializable dict."""
    return entry.to_dict()
```

Note: `BundleEntry.to_dict()` was defined in Task 5. Subclasses should
override it to include their category-specific fields. Add `to_dict()` methods
to each category model, e.g. for `Gun`:

```python
def to_dict(self) -> dict[str, Any]:
    d = super().to_dict()
    d["slot"] = self.slot
    d["firerate"] = self.firerate
    d["range"] = self.range
    d["fire_modes"] = self.fire_modes
    # ... etc
    return d
```

Implement `to_dict()` on every category model class during this step.

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_json_fmt.py -v
```

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: JSON output formatter"
```

---

## Task 8: Markdown formatter with GUID resolution

**Files:**
- Create: `~/bin/unturned_data/formatters/markdown_fmt.py`
- Create: `~/bin/unturned_data/tests/test_markdown_fmt.py`

**Step 1: Write failing tests**

```python
"""Tests for markdown output formatter."""
import pytest
from pathlib import Path
from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.categories import parse_entry
from unturned_data.formatters.markdown_fmt import (
    entries_to_markdown,
    build_guid_map,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestGuidMap:
    def test_builds_map(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        eng = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        guid_map = build_guid_map([entry])
        assert guid_map["78fefdd23def4ab6ac8301adfcc3b2d4"] == "Canned Beans"


class TestMarkdownFormatter:
    def test_produces_tables(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        eng = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        output = entries_to_markdown([entry])
        assert "| Name |" in output
        assert "Canned Beans" in output

    def test_groups_by_model_class(self):
        entries = []
        for name, dat in [
            ("gun_maplestrike", "Maplestrike"),
            ("food_beans", "Canned_Beans"),
        ]:
            d = FIXTURES / name
            raw = parse_dat_file(d / f"{dat}.dat")
            eng = load_english_dat(d / "English.dat")
            entries.append(parse_entry(raw, eng, f"test/{name}"))
        output = entries_to_markdown(entries)
        # Should have separate sections for Gun and Consumeable
        assert "## Gun" in output or "## Guns" in output
        assert "## Consumeable" in output or "## Consumeables" in output

    def test_deterministic(self):
        raw = parse_dat_file(FIXTURES / "food_beans" / "Canned_Beans.dat")
        eng = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        entry = parse_entry(raw, eng, "Items/Food/Canned_Beans")
        output1 = entries_to_markdown([entry])
        output2 = entries_to_markdown([entry])
        assert output1 == output2
```

**Step 2: Run tests to verify they fail**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_markdown_fmt.py -v
```

**Step 3: Implement markdown formatter**

```python
"""Markdown table output formatter with GUID resolution."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..models import BundleEntry


# Display names for model classes
CLASS_DISPLAY_NAMES: dict[str, str] = {
    "Gun": "Guns",
    "MeleeWeapon": "Melee Weapons",
    "Consumeable": "Consumeables",
    "Clothing": "Clothing",
    "Throwable": "Throwables",
    "BarricadeItem": "Barricades",
    "StructureItem": "Structures",
    "Magazine": "Magazines",
    "Attachment": "Attachments",
    "Vehicle": "Vehicles",
    "Animal": "Animals",
    "GenericEntry": "Other",
}


def build_guid_map(entries: list[BundleEntry]) -> dict[str, str]:
    """Build GUID → human-readable name mapping from all entries."""
    guid_map: dict[str, str] = {}
    for entry in entries:
        if entry.guid and entry.name:
            guid_map[entry.guid] = entry.name
    return guid_map


def entries_to_markdown(entries: list[BundleEntry]) -> str:
    """Format entries as grouped markdown tables."""
    guid_map = build_guid_map(entries)

    # Group entries by their class name
    groups: dict[str, list[BundleEntry]] = defaultdict(list)
    for entry in entries:
        class_name = type(entry).__name__
        groups[class_name].append(entry)

    sections: list[str] = []
    for class_name in sorted(groups.keys()):
        group = sorted(groups[class_name], key=lambda e: (e.name, e.id))
        display_name = CLASS_DISPLAY_NAMES.get(class_name, class_name)
        columns = group[0].markdown_columns()

        lines: list[str] = []
        lines.append(f"## {display_name}")
        lines.append("")
        lines.append("| " + " | ".join(columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")

        for entry in group:
            row = entry.markdown_row(guid_map)
            # Escape pipe characters in cell values
            row = [cell.replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(row) + " |")

        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"
```

**Step 4: Run tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_markdown_fmt.py -v
```

**Step 5: Commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "feat: markdown formatter with GUID resolution"
```

---

## Task 9: CLI entry point

**Files:**
- Create: `~/bin/unturned_data/cli.py`
- Create: `~/bin/unturned_data/__main__.py`
- Create: `~/bin/unturned-data` (entry script)

**Step 1: Implement CLI**

`~/bin/unturned_data/cli.py`:

```python
"""CLI entry point for unturned-data."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .loader import walk_bundle_dir
from .categories import parse_entry
from .formatters.json_fmt import entries_to_json
from .formatters.markdown_fmt import entries_to_markdown


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="unturned-data",
        description="Parse Unturned .dat bundle files into JSON or markdown.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a Bundles directory (or any subdirectory)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args(argv)

    if not args.path.is_dir():
        print(f"Error: {args.path} is not a directory", file=sys.stderr)
        sys.exit(1)

    entries = []
    for raw, english, rel_path in walk_bundle_dir(args.path):
        entry = parse_entry(raw, english, rel_path)
        entries.append(entry)

    if not entries:
        print("No entries found.", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(entries_to_json(entries))
    else:
        print(entries_to_markdown(entries))
```

`~/bin/unturned_data/__main__.py`:

```python
from .cli import main
main()
```

`~/bin/unturned-data`:

```python
#!/usr/bin/env python3
"""Unturned bundle data parser."""
import sys
from pathlib import Path

# Add ~/bin to path so unturned_data package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from unturned_data.cli import main

if __name__ == "__main__":
    main()
```

Make it executable:

```bash
chmod +x ~/bin/unturned-data
```

**Step 2: Smoke test with real data**

```bash
# JSON — small subset
~/bin/unturned-data ~/unturned-bundles/Animals/ --format json | python3 -m json.tool | head -40

# Markdown — small subset
~/bin/unturned-data ~/unturned-bundles/Animals/ --format markdown

# Full run — Items
~/bin/unturned-data ~/unturned-bundles/Items/ --format json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} entries')"

# Full run — everything
~/bin/unturned-data ~/unturned-bundles/ --format json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} entries')"
```

Expected: valid JSON with all entries. Markdown with grouped tables.

**Step 3: Commit**

```bash
cd ~/bin && git add unturned_data/ unturned-data && git commit -m "feat: CLI entry point for unturned-data"
```

---

## Task 10: Integration test with full data

**Files:**
- Create: `~/bin/unturned_data/tests/test_integration.py`

**Step 1: Write integration tests**

```python
"""Integration tests against full bundle data."""
import json
import pytest
from pathlib import Path
from unturned_data.loader import walk_bundle_dir
from unturned_data.categories import parse_entry
from unturned_data.formatters.json_fmt import entries_to_json
from unturned_data.formatters.markdown_fmt import entries_to_markdown

BUNDLES = Path.home() / "unturned-bundles"

# Skip if full data not available
pytestmark = pytest.mark.skipif(
    not BUNDLES.exists(), reason="Full bundle data not available"
)


class TestFullParse:
    @pytest.fixture(scope="class")
    def all_entries(self):
        entries = []
        errors = []
        for raw, english, rel_path in walk_bundle_dir(BUNDLES):
            try:
                entry = parse_entry(raw, english, rel_path)
                entries.append(entry)
            except Exception as e:
                errors.append((rel_path, str(e)))
        return entries, errors

    def test_no_parse_errors(self, all_entries):
        entries, errors = all_entries
        # Allow no more than 1% error rate
        error_rate = len(errors) / (len(entries) + len(errors))
        assert error_rate < 0.01, (
            f"{len(errors)} errors out of {len(entries) + len(errors)} entries: "
            + "\n".join(f"  {p}: {e}" for p, e in errors[:20])
        )

    def test_entry_count(self, all_entries):
        entries, _ = all_entries
        # We know there are ~5000+ .dat files
        assert len(entries) > 1000

    def test_json_valid(self, all_entries):
        entries, _ = all_entries
        output = entries_to_json(entries)
        parsed = json.loads(output)
        assert len(parsed) == len(entries)

    def test_json_deterministic(self, all_entries):
        entries, _ = all_entries
        output1 = entries_to_json(entries)
        output2 = entries_to_json(entries)
        assert output1 == output2

    def test_markdown_valid(self, all_entries):
        entries, _ = all_entries
        output = entries_to_markdown(entries)
        assert len(output) > 0
        assert "##" in output  # Has section headers
```

**Step 2: Run integration tests**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/test_integration.py -v
```

Expected: all pass. Fix any parse errors discovered.

**Step 3: Run full test suite**

```bash
cd ~/bin && python3 -m pytest unturned_data/tests/ -v
```

Expected: all pass.

**Step 4: Final commit**

```bash
cd ~/bin && git add unturned_data/ && git commit -m "test: integration tests against full bundle data"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Scaffolding + fixtures | dirs, `__init__.py`, fixture .dat files |
| 2 | `.dat` parser — flat | `dat_parser.py`, `test_dat_parser.py` |
| 3 | `.dat` parser — nested blocks | same files (extend) |
| 4 | English.dat + directory walker | `loader.py`, `test_loader.py` |
| 5 | Base model + shared stats | `models.py`, `test_models.py` |
| 6 | Category models + dispatch | `categories/*.py`, `test_categories.py` |
| 7 | JSON formatter | `formatters/json_fmt.py`, `test_json_fmt.py` |
| 8 | Markdown formatter | `formatters/markdown_fmt.py`, `test_markdown_fmt.py` |
| 9 | CLI entry point | `cli.py`, `__main__.py`, `~/bin/unturned-data` |
| 10 | Integration tests | `test_integration.py` |
