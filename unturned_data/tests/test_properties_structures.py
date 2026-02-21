"""Tests for structure property models."""

from __future__ import annotations

from pathlib import Path

import pytest

from unturned_data.dat_parser import parse_dat_file
from unturned_data.loader import load_english_dat
from unturned_data.models.properties.structures import StructureProperties

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> tuple[dict, dict]:
    """Helper: load raw + english from a fixture directory."""
    fixture_dir = FIXTURES / name
    dat_files = [f for f in fixture_dir.glob("*.dat") if f.name != "English.dat"]
    assert dat_files, f"No .dat files in {fixture_dir}"
    raw = parse_dat_file(dat_files[0])
    english = load_english_dat(fixture_dir / "English.dat")
    return raw, english


# ---------------------------------------------------------------------------
# StructureProperties from fixture
# ---------------------------------------------------------------------------


class TestStructureFromFixture:
    """StructureProperties.from_raw parsing using structure_wall fixture."""

    def test_structure_from_fixture(self):
        raw, _ = _load_fixture("structure_wall")
        props = StructureProperties.from_raw(raw)

        assert props.construct == "Wall"
        assert props.health == 350
        assert props.range == 8.0
        # Defaults for fields not in fixture (now None)
        assert props.can_be_damaged is None
        assert props.requires_pillars is None
        assert props.vulnerable is None
        assert props.unrepairable is None
        assert props.proof_explosion is None
        assert props.unpickupable is None
        assert props.unsalvageable is None
        assert props.salvage_duration_multiplier is None
        assert props.unsaveable is None
        assert props.armor_tier is None
        assert props.foliage_cut_radius is None


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestStructureDefaults:
    """StructureProperties default values."""

    def test_structure_defaults(self):
        props = StructureProperties()
        assert props.construct is None
        assert props.health is None
        assert props.range is None
        assert props.can_be_damaged is None
        assert props.requires_pillars is None
        assert props.vulnerable is None
        assert props.unrepairable is None
        assert props.proof_explosion is None
        assert props.unpickupable is None
        assert props.unsalvageable is None
        assert props.salvage_duration_multiplier is None
        assert props.unsaveable is None
        assert props.armor_tier is None
        assert props.foliage_cut_radius is None


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestStructureSerializes:
    """Structure properties serialize to/from dict."""

    def test_structure_serializes(self):
        raw, _ = _load_fixture("structure_wall")
        props = StructureProperties.from_raw(raw)
        data = props.model_dump()
        restored = StructureProperties(**data)
        assert restored.construct == props.construct
        assert restored.health == props.health
        assert restored.range == props.range
        assert restored.can_be_damaged == props.can_be_damaged
        assert restored.requires_pillars == props.requires_pillars
        assert restored.foliage_cut_radius == props.foliage_cut_radius


# ---------------------------------------------------------------------------
# Ignored keys
# ---------------------------------------------------------------------------


class TestStructureIgnoredKeys:
    """Structure IGNORE set."""

    def test_ignored_keys(self):
        assert StructureProperties.is_ignored("Has_Clip_Prefab")
        assert StructureProperties.is_ignored("Explosion")
        assert StructureProperties.is_ignored("Eligible_For_Pooling")
        assert StructureProperties.is_ignored("PlacementAudioClip")
        assert not StructureProperties.is_ignored("Health")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestStructureRegistry:
    """Structure type is registered in PROPERTIES_REGISTRY."""

    def test_registry(self):
        from unturned_data.models.properties import PROPERTIES_REGISTRY

        assert PROPERTIES_REGISTRY.get("Structure") is StructureProperties
