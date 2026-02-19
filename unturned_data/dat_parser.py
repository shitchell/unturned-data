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


def parse_asset_file(path: Path) -> dict[str, Any]:
    """Parse an .asset file from disk."""
    text = path.read_text(encoding="utf-8-sig")
    return parse_dat(text)


def parse_dat(text: str) -> dict[str, Any]:
    """Parse .dat format text into a dict."""
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
    # Strip outer quotes first so "False", "13", etc. coerce correctly
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _split_key_value(line: str) -> tuple[str, str | None]:
    """Split a line into key and optional value.

    The key is everything up to the first whitespace. The value is
    everything after the first whitespace, stripped.
    """
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
        if line in ("}", "]"):
            return result, i + 1

        key, value = _split_key_value(line)
        if not key:
            i += 1
            continue

        # Case 1: value is an opening bracket on the same line (e.g. "Key [" or "Key {")
        if value is not None and value in ("[", "{"):
            if value == "[":
                parsed, i = _parse_array(lines, i + 1)
            else:
                parsed, i = _parse_mapping(lines, i + 1)
            result[key] = parsed
            continue

        # Case 2: bare key -- check if next content line is an opening bracket
        if value is None:
            nxt = _next_content_line(lines, i + 1)
            if nxt is not None and nxt[0] in ("[", "{"):
                if nxt[0] == "[":
                    parsed, i = _parse_array(lines, nxt[1] + 1)
                else:
                    parsed, i = _parse_mapping(lines, nxt[1] + 1)
                result[key] = parsed
                continue
            # It's a bare flag
            result[key] = True
            i += 1
            continue

        # Case 3: key with a value
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
        if line.startswith("{") and line.endswith("}"):
            # Inline object, e.g. {"Key" "Value"}
            inner = line[1:-1].strip()
            obj, _ = _parse_mapping([inner], 0)
            result.append(obj)
            i += 1
            continue
        # Bare value (number, quoted string, etc.)
        result.append(_coerce_value(line))
        i += 1
    return result, i
