"""Tests for the new CLI."""

import json
from pathlib import Path
from unturned_data.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLI:
    def test_json_export(self, tmp_path):
        main([str(FIXTURES), "--output", str(tmp_path)])
        assert (tmp_path / "manifest.json").exists()
        assert (tmp_path / "base" / "entries.json").exists()

    def test_json_requires_output(self, capsys):
        """Should error if --format json but no --output."""
        import pytest

        with pytest.raises(SystemExit):
            main([str(FIXTURES)])

    def test_markdown_output(self, capsys):
        main([str(FIXTURES), "--format", "markdown"])
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_exclude_flag(self, capsys):
        """Exclude should filter entries in markdown mode."""
        main([str(FIXTURES), "--format", "markdown", "--exclude", "gun_maplestrike"])
        captured = capsys.readouterr()
        assert "Maplestrike" not in captured.out
