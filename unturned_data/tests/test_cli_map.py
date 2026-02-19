"""Tests for CLI --map flag."""
import json
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from unturned_data.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestMapFlag:
    def test_map_flag_accepted(self, capsys):
        """The --map flag is accepted without error."""
        # Use fixtures as a minimal bundle dir -- will produce some output
        # but the key thing is --map doesn't cause an argument error
        main(["--map", str(FIXTURES / "fake_map"), str(FIXTURES)])

    def test_help_shows_map(self, capsys):
        """--help output includes --map."""
        with pytest.raises(SystemExit):
            main(["--help"])
        captured = capsys.readouterr()
        assert "--map" in captured.out

    def test_multiple_maps(self, capsys):
        """Multiple --map flags can be provided."""
        main([
            "--map", str(FIXTURES / "fake_map"),
            "--map", str(FIXTURES / "fake_map"),
            str(FIXTURES),
        ])
