"""Pydantic models for Schema C export file structures."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ManifestMapInfo(BaseModel):
    """Per-map info in the manifest."""

    map_file: str
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


class MapConfig(BaseModel):
    """map.json structure."""

    name: str
    source_path: str = ""
    workshop_id: int | None = None
    config: dict[str, Any] = {}
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

    file: str
    index: int
    id: int = 0
    type: str = ""
    name: str = ""


class GuidIndex(BaseModel):
    """guid_index.json structure."""

    total_entries: int = 0
    generated_at: str = ""
    entries: dict[str, GuidIndexEntry] = {}
    by_id: dict[str, dict[str, dict[str, str]]] = {}
