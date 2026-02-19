"""Integration tests for crafting blacklist with real server data."""
import pytest
from pathlib import Path

from unturned_data.crafting_blacklist import resolve_crafting_blacklist

# Real map paths — skip if not available
POLARIS_MAP = Path.home() / "unturned-server" / "Servers" / "MyServer" / "Workshop" / "Steam" / "content" / "304930" / "2898548949" / "A6 Polaris"
PEI_MAP = Path.home() / "unturned-server" / "Maps" / "PEI"

pytestmark = pytest.mark.skipif(
    not POLARIS_MAP.exists(),
    reason="Server data not available",
)


class TestRealPolaris:
    def test_polaris_disables_core_blueprints(self):
        bl = resolve_crafting_blacklist(POLARIS_MAP)
        assert bl is not None
        assert bl.allow_core_blueprints is False

    def test_polaris_blocks_car_battery(self):
        bl = resolve_crafting_blacklist(POLARIS_MAP)
        assert bl is not None
        # Car battery GUID from Frost_Craft.asset
        assert "098b13be34a7411db7736b7f866ada69" in bl.blocked_inputs

    def test_pei_has_no_blacklist(self):
        if not PEI_MAP.exists():
            pytest.skip("PEI not available")
        bl = resolve_crafting_blacklist(PEI_MAP)
        assert bl is None
