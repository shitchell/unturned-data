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
