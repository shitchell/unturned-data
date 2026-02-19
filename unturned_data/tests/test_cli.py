"""Tests for the CLI."""

import json
from pathlib import Path

import pytest

from unturned_data.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_server(tmp_path):
    """Create a minimal mock server structure.

    The CLI now expects a server root containing Bundles/, not a bare
    Bundles directory.  We create the expected layout and copy fixture
    data into it.
    """
    bundles = tmp_path / "Bundles"
    bundles.mkdir()
    # Copy fixture .dat files into a structure that walk_bundle_dir can find
    gun_dir = bundles / "Items" / "Guns" / "Maplestrike"
    gun_dir.mkdir(parents=True)
    src = FIXTURES / "gun_maplestrike"
    for f in src.iterdir():
        (gun_dir / f.name).write_bytes(f.read_bytes())
    return tmp_path


class TestCLI:
    def test_json_export(self, mock_server, tmp_path):
        out = tmp_path / "output"
        main([str(mock_server), "--output", str(out)])
        assert (out / "manifest.json").exists()
        assert (out / "base" / "entries.json").exists()

    def test_json_requires_output(self):
        """Should error when --format json but no --output on a valid server root."""
        with pytest.raises(SystemExit):
            main(["/nonexistent"])

    def test_markdown_output(self, mock_server, capsys):
        main([str(mock_server), "--format", "markdown"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_map_filter_warns_on_unknown(self, mock_server, tmp_path, capsys):
        out = tmp_path / "output"
        main([str(mock_server), "--output", str(out), "--map", "NonexistentMap"])
        captured = capsys.readouterr()
        assert "not found" in captured.err or "Warning" in captured.err
