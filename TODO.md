# TODO

## Investigate Game Engine Default Values

**Priority:** Medium
**Context:** The property models currently use `None` for absent fields, which faithfully represents "not in the .dat file." However, we don't know what the game engine actually does when a field is missing — it might use 0, a type-specific sentinel, or something else entirely.

**Goal:** Research how Unturned's C# code handles missing .dat fields for each item type. This would let us:
1. Set up strong contracts that match the game engine's actual behavior
2. Distinguish between "field absent, engine uses its default" and "field absent, something is wrong"
3. Potentially catch cases where the engine default is non-obvious (e.g., `spread_sprint` defaults to 1.25 in-engine, not 0)

**Possible approaches:**
- Decompile the game's C# assemblies (Unity/IL2CPP) and inspect the field initialization in each ItemAsset subclass
- Check the Unturned modding wiki or community documentation for documented defaults
- Cross-reference `ItemData.yml` from the [unturned-3-knowledgebase](https://github.com/unturned-info/unturned-3-knowledgebase) — it may note some defaults
- Empirically test in-game by creating items with missing fields and observing behavior

**Reference:** `~/code/git/github.com/unturned-info/unturned-3-knowledgebase/data/ItemData.yml`

**Files affected:** All `unturned_data/models/properties/*.py` — once we know the real defaults, we can add validation that distinguishes "absent = engine default" from "absent = unexpected"
