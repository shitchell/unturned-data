"""
Tests for the English.dat loader and directory walker.

Covers: load_english_dat, load_entry_raw, walk_bundle_dir.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from unturned_data.loader import load_english_dat, load_entry_raw, walk_bundle_dir

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# TestLoadEnglishDat
# ---------------------------------------------------------------------------
class TestLoadEnglishDat:
    """Parsing English.dat files into {key: value} dicts."""

    def test_load_name_and_description(self):
        english = load_english_dat(FIXTURES / "food_beans" / "English.dat")
        assert english["Name"] == "Canned Beans"
        assert english["Description"] == "Very tactically packed for maximum taste."

    def test_missing_file(self):
        english = load_english_dat(FIXTURES / "nonexistent" / "English.dat")
        assert english == {}

    def test_npc_with_character(self):
        english = load_english_dat(FIXTURES / "npc_sample" / "English.dat")
        assert english["Name"] == "Security Lookout Keith"
        assert english["Character"] == "Keith"

    def test_name_only(self):
        english = load_english_dat(FIXTURES / "animal_bear" / "English.dat")
        assert english["Name"] == "Bear"
        assert "Description" not in english


# ---------------------------------------------------------------------------
# TestLoadEntryRaw
# ---------------------------------------------------------------------------
class TestLoadEntryRaw:
    """Loading both .dat and English.dat from a single entry directory."""

    def test_load_combines_dat_and_english(self):
        raw, english = load_entry_raw(FIXTURES / "food_beans")
        # raw should come from Canned_Beans.dat
        assert raw["Type"] == "Food"
        assert raw["ID"] == 13
        assert raw["Health"] == 10
        assert raw["Food"] == 55
        # english should come from English.dat
        assert english["Name"] == "Canned Beans"
        assert english["Description"] == "Very tactically packed for maximum taste."

    def test_load_entry_with_different_name(self):
        """Directory name doesn't match .dat name -- fallback to first non-English .dat."""
        raw, english = load_entry_raw(FIXTURES / "food_beans")
        assert raw["GUID"] == "78fefdd23def4ab6ac8301adfcc3b2d4"

    def test_load_entry_no_english(self):
        """spawn_sample has no English.dat."""
        raw, english = load_entry_raw(FIXTURES / "spawn_sample")
        assert raw["Type"] == "Spawn"
        assert english == {}


# ---------------------------------------------------------------------------
# TestWalkBundleDir
# ---------------------------------------------------------------------------
class TestWalkBundleDir:
    """Walking a bundle directory tree.

    walk_bundle_dir requires .dat filenames to match their parent
    directory names (the real Unturned Bundles convention).  The test
    fixtures use category-prefixed dir names that don't match, so we
    build a proper mini-bundle tree with tmp_path.
    """

    @pytest.fixture()
    def bundle_tree(self, tmp_path: Path) -> Path:
        """Create a mini Bundles directory with the real naming convention."""
        root = tmp_path / "Bundles"
        root.mkdir()

        # Entry 1: Canned_Beans/Canned_Beans.dat + English.dat
        beans_dir = root / "Items" / "Food" / "Canned_Beans"
        beans_dir.mkdir(parents=True)
        shutil.copy(
            FIXTURES / "food_beans" / "Canned_Beans.dat",
            beans_dir / "Canned_Beans.dat",
        )
        shutil.copy(
            FIXTURES / "food_beans" / "English.dat",
            beans_dir / "English.dat",
        )

        # Entry 2: Maplestrike/Maplestrike.dat + English.dat
        maple_dir = root / "Items" / "Guns" / "Maplestrike"
        maple_dir.mkdir(parents=True)
        shutil.copy(
            FIXTURES / "gun_maplestrike" / "Maplestrike.dat",
            maple_dir / "Maplestrike.dat",
        )
        shutil.copy(
            FIXTURES / "gun_maplestrike" / "English.dat",
            maple_dir / "English.dat",
        )

        # Entry 3: Alicepack/Alicepack.dat + English.dat
        alice_dir = root / "Items" / "Clothing" / "Alicepack"
        alice_dir.mkdir(parents=True)
        shutil.copy(
            FIXTURES / "backpack_alice" / "Alicepack.dat",
            alice_dir / "Alicepack.dat",
        )
        shutil.copy(
            FIXTURES / "backpack_alice" / "English.dat",
            alice_dir / "English.dat",
        )

        # Non-entry: a stray MasterBundle.dat at root (should be skipped)
        (root / "MasterBundle.dat").write_text("BundleName Test\n")

        # Non-entry: an English.dat without a matching dir-named .dat
        orphan_dir = root / "Orphan"
        orphan_dir.mkdir()
        (orphan_dir / "English.dat").write_text("Name Orphan\n")

        return root

    def test_walks_fixtures(self, bundle_tree: Path):
        """walk_bundle_dir should find the entries we created."""
        entries = list(walk_bundle_dir(bundle_tree))
        assert len(entries) == 3

    def test_returns_relative_paths(self, bundle_tree: Path):
        """Returned paths should not start with /."""
        entries = list(walk_bundle_dir(bundle_tree))
        for _raw, _english, rel_path in entries:
            assert not rel_path.startswith("/"), f"Path should be relative: {rel_path}"

    def test_results_are_sorted(self, bundle_tree: Path):
        """Results should be in sorted order by relative path."""
        entries = list(walk_bundle_dir(bundle_tree))
        paths = [rel_path for _, _, rel_path in entries]
        assert paths == sorted(paths)

    def test_skips_english_dat(self, bundle_tree: Path):
        """walk_bundle_dir should not treat English.dat as a main entry."""
        entries = list(walk_bundle_dir(bundle_tree))
        for raw, _english, rel_path in entries:
            assert "English.dat" not in rel_path

    def test_skips_masterbundle(self, bundle_tree: Path):
        """walk_bundle_dir should skip MasterBundle.dat."""
        entries = list(walk_bundle_dir(bundle_tree))
        for raw, _english, rel_path in entries:
            assert "MasterBundle" not in rel_path

    def test_entry_data_loaded(self, bundle_tree: Path):
        """Verify that walked entries have correct raw + english data."""
        entries = list(walk_bundle_dir(bundle_tree))
        by_path = {rel: (raw, eng) for raw, eng, rel in entries}

        # Check Canned_Beans
        beans_path = "Items/Food/Canned_Beans"
        assert beans_path in by_path
        raw, eng = by_path[beans_path]
        assert raw["Type"] == "Food"
        assert eng["Name"] == "Canned Beans"

        # Check Maplestrike
        maple_path = "Items/Guns/Maplestrike"
        assert maple_path in by_path
        raw, eng = by_path[maple_path]
        assert raw["Type"] == "Gun"
        assert eng["Name"] == "Maplestrike"
