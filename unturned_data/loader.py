"""
Loaders for Unturned bundle directories.

Handles English.dat parsing, single-entry loading, and recursive
directory walking to discover all entries in a Bundles tree.
Also provides utilities for extracting GUID→name mappings from
.asset files and from inline comments in .dat files.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from unturned_data.dat_parser import parse_dat, parse_dat_file


def load_english_dat(path: Path) -> dict[str, str]:
    """Parse an English.dat file into a {key: value} dict.

    English.dat uses a simple ``Key Value`` format (one per line), where
    the key is the first whitespace-delimited token and the value is
    everything after the first whitespace.

    Returns an empty dict if the file does not exist.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Split on first whitespace
        parts = line.split(None, 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
        elif len(parts) == 1:
            result[parts[0]] = ""
    return result


def load_entry_raw(directory: Path) -> tuple[dict, dict]:
    """Load both the main .dat file and English.dat from an entry directory.

    The main .dat file's name is expected to match the directory name
    (e.g. ``Canned_Beans/Canned_Beans.dat``).  If that file doesn't
    exist, falls back to the first ``.dat`` file found that isn't
    ``English.dat``.

    Returns ``(raw_dict, english_dict)``.
    """
    english_path = directory / "English.dat"
    english = load_english_dat(english_path)

    # Primary: directory-name matching .dat file
    main_dat = directory / f"{directory.name}.dat"
    if main_dat.exists():
        raw = parse_dat_file(main_dat)
        return raw, english

    # Fallback: first non-English .dat file
    dat_files = sorted(
        f for f in directory.glob("*.dat")
        if f.name.lower() != "english.dat"
    )
    if dat_files:
        raw = parse_dat_file(dat_files[0])
        return raw, english

    return {}, english


# Names to skip when deciding if a directory is an entry directory
_SKIP_DAT_NAMES = {"english.dat", "masterbundle.dat"}


def walk_bundle_dir(
    root: Path,
) -> Iterator[tuple[dict, dict, str]]:
    """Walk a Bundles directory tree, yielding entries.

    Yields ``(raw_dict, english_dict, relative_path)`` for each entry
    directory found.  An entry directory is one that contains a ``.dat``
    file whose stem matches the directory name.

    Results are sorted by relative path for determinism.
    """
    entries: list[tuple[str, Path]] = []

    for dat_file in sorted(root.rglob("*.dat")):
        # Skip files we don't want to treat as entries
        if dat_file.name.lower() in _SKIP_DAT_NAMES:
            continue

        parent = dat_file.parent
        # Only process if the .dat file name matches the directory name
        if dat_file.stem == parent.name:
            rel = str(parent.relative_to(root))
            entries.append((rel, parent))

    # Sort by relative path
    entries.sort(key=lambda x: x[0])

    # Deduplicate (a dir should only appear once)
    seen: set[str] = set()
    for rel_path, entry_dir in entries:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        raw, english = load_entry_raw(entry_dir)
        yield raw, english, rel_path


# ---------------------------------------------------------------------------
# .asset file GUID extraction
# ---------------------------------------------------------------------------

# Regex to match a GUID line (32 hex chars) inside a Metadata block or at
# the top level of an .asset file.
_GUID_RE = re.compile(r"^\s*GUID\s+([0-9a-fA-F]{32})\s*$")
# Detects the start of a ``Metadata`` wrapper block
_METADATA_RE = re.compile(r"^\s*Metadata\s*$", re.IGNORECASE)


def _extract_asset_guid(text: str) -> str | None:
    """Extract the GUID from an .asset file's text.

    Handles two formats:

    **Simple** (same key-value format as .dat files)::

        GUID 61edeaee95b742a3a0b589f769261cdb
        Type Effect

    **Metadata wrapper**::

        Metadata
        {
            GUID d293cbe22b8c40bf866c39ebbd952fe1
            Type SDG.Unturned.OutfitAsset, ...
        }
        Asset
        {
            ...
        }

    Returns the GUID string (lowercase), or None if not found.
    """
    in_metadata = False
    for line in text.splitlines():
        stripped = line.strip()
        # Track entry into Metadata block
        if _METADATA_RE.match(stripped):
            in_metadata = True
            continue
        if stripped == "{" and in_metadata:
            continue
        if stripped == "}" and in_metadata:
            # Exiting Metadata block without finding GUID
            break
        m = _GUID_RE.match(line)
        if m:
            return m.group(1).lower()
    return None


def walk_asset_files(root: Path) -> dict[str, str]:
    """Walk a directory tree for .asset files and build a GUID→name map.

    The name is derived from the filename stem with underscores
    replaced by spaces (e.g. ``DyeVatCraftingEffect.asset`` becomes
    ``"DyeVatCraftingEffect"``).

    Returns ``{guid: name}`` with lowercase GUIDs.
    """
    guid_map: dict[str, str] = {}
    for asset_file in sorted(root.rglob("*.asset")):
        try:
            text = asset_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        guid = _extract_asset_guid(text)
        if guid:
            name = asset_file.stem.replace("_", " ")
            guid_map[guid] = name
    return guid_map


# ---------------------------------------------------------------------------
# Comment-based GUID extraction from .dat file text
# ---------------------------------------------------------------------------

# Matches: "32-hex-chars" followed later by // comment-text
# The GUID is in quotes, the name is after the //
_COMMENT_GUID_RE = re.compile(
    r'"([0-9a-fA-F]{32})(?:\s+x\s+\d+)?"'  # "GUID" or "GUID x N"
    r'.*?//\s*(.+?)$',                        # // Name
    re.MULTILINE,
)


def extract_comment_guids(text: str) -> dict[str, str]:
    """Extract GUID→name mappings from ``// comments`` in .dat file text.

    Scans for patterns like::

        InputItems "3e78a9db8cf74f4e830df4c06f2e9273 x 2" // Rag
        CategoryTag "d089feb7e43f40c5a7dfcefc36998cfb" // Supplies
        RequiresNearbyCraftingTags ["7b82c125a5a54984b8bb26576b59e977" // Workbench]

    Returns ``{guid: name}`` with lowercase GUIDs.  The name is
    stripped of trailing whitespace, brackets, etc.
    """
    guid_map: dict[str, str] = {}
    for m in _COMMENT_GUID_RE.finditer(text):
        guid = m.group(1).lower()
        name = m.group(2).strip().rstrip("]").strip()
        if name:
            guid_map[guid] = name
    return guid_map


def collect_comment_guids_from_dir(root: Path) -> dict[str, str]:
    """Walk a directory tree and extract comment-based GUIDs from all .dat files.

    Returns a merged ``{guid: name}`` map.
    """
    guid_map: dict[str, str] = {}
    for dat_file in sorted(root.rglob("*.dat")):
        if dat_file.name.lower() in _SKIP_DAT_NAMES:
            continue
        try:
            text = dat_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        guid_map.update(extract_comment_guids(text))
    return guid_map
