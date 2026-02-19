"""Tests for map discovery and filter system."""

from pathlib import Path

import pytest

from unturned_data.exporter import discover_maps, _is_map_dir


class TestIsMapDir:
    def test_with_spawns(self, tmp_path):
        (tmp_path / "Spawns").mkdir()
        assert _is_map_dir(tmp_path)

    def test_with_bundles(self, tmp_path):
        (tmp_path / "Bundles").mkdir()
        assert _is_map_dir(tmp_path)

    def test_with_config(self, tmp_path):
        (tmp_path / "Config.json").write_text("{}")
        assert _is_map_dir(tmp_path)

    def test_empty_dir(self, tmp_path):
        assert not _is_map_dir(tmp_path)


class TestDiscoverMaps:
    def test_builtin_maps(self, tmp_path):
        maps_dir = tmp_path / "Maps"
        maps_dir.mkdir()
        pei = maps_dir / "PEI"
        pei.mkdir()
        (pei / "Spawns").mkdir()
        wash = maps_dir / "Washington"
        wash.mkdir()
        (wash / "Bundles").mkdir()

        found = discover_maps(tmp_path)
        names = [m.name for m in found]
        assert "PEI" in names
        assert "Washington" in names

    def test_workshop_maps(self, tmp_path):
        # Create workshop structure
        ws = (
            tmp_path
            / "Servers"
            / "MyServer"
            / "Workshop"
            / "Steam"
            / "content"
            / "304930"
            / "12345"
        )
        ws.mkdir(parents=True)
        polaris = ws / "A6 Polaris"
        polaris.mkdir()
        (polaris / "Config.json").write_text("{}")

        found = discover_maps(tmp_path)
        names = [m.name for m in found]
        assert "A6 Polaris" in names

    def test_skips_non_map_dirs(self, tmp_path):
        maps_dir = tmp_path / "Maps"
        maps_dir.mkdir()
        # Dir without any map indicators
        (maps_dir / "NotAMap").mkdir()

        found = discover_maps(tmp_path)
        assert len(found) == 0

    def test_no_maps_dir(self, tmp_path):
        """Server root with no Maps/ directory."""
        found = discover_maps(tmp_path)
        assert len(found) == 0
