"""Tests for properties infrastructure, base classes, and warning system."""

import re

import pytest

from unturned_data.models.properties import PROPERTIES_REGISTRY, get_properties_class
from unturned_data.models.properties.base import (
    GLOBAL_HANDLED,
    GLOBAL_IGNORE,
    GLOBAL_HANDLED_PATTERNS,
    ItemProperties,
    _snake_to_dat_key,
    is_globally_handled,
)
from unturned_data.warnings import FieldCoverageReport


class TestItemPropertiesBase:
    """Tests for the ItemProperties base class."""

    def test_base_properties_from_raw_empty(self):
        """ItemProperties.from_raw({}) returns an empty model."""
        props = ItemProperties.from_raw({})
        assert isinstance(props, ItemProperties)
        assert props.model_dump() == {}

    def test_consumed_keys_empty_base(self):
        """Base class has no fields, so consumed_keys is always empty."""
        assert ItemProperties.consumed_keys({"Foo": 1, "Bar": 2}) == set()

    def test_is_ignored_empty_base(self):
        """Base class has no IGNORE entries."""
        assert not ItemProperties.is_ignored("Anything")


class TestGlobalHandled:
    """Tests for GLOBAL_HANDLED keys and patterns."""

    @pytest.mark.parametrize(
        "key",
        [
            "GUID",
            "ID",
            "Type",
            "Rarity",
            "Size_X",
            "Size_Y",
            "Useable",
            "Slot",
            "Can_Use_Underwater",
            "Equipable_Movement_Speed_Multiplier",
            "Should_Drop_On_Death",
            "Allow_Manual_Drop",
            "Blueprints",
            "Actions",
        ],
    )
    def test_global_handled_keys(self, key):
        """Each key in GLOBAL_HANDLED is recognized as globally handled."""
        assert is_globally_handled(key)

    @pytest.mark.parametrize(
        "key",
        [
            "Blueprint_0_Type",
            "Blueprint_12_Outputs",
            "Action_0_Type",
            "Action_3_Source",
        ],
    )
    def test_global_handled_patterns(self, key):
        """Blueprint_N_* and Action_N_* keys match GLOBAL_HANDLED_PATTERNS."""
        assert is_globally_handled(key)

    def test_unknown_key_not_handled(self):
        """An unrelated key is not globally handled."""
        assert not is_globally_handled("Damage_Player")
        assert not is_globally_handled("Health")


class TestGlobalIgnore:
    """Tests for GLOBAL_IGNORE keys."""

    @pytest.mark.parametrize(
        "key",
        [
            "Size_Z",
            "Size2_Z",
            "Pro",
            "Quality_Min",
            "Quality_Max",
            "Bypass_Hash_Verification",
            "WearAudio",
        ],
    )
    def test_global_ignore_keys(self, key):
        """Keys in GLOBAL_IGNORE are present in the set."""
        assert key in GLOBAL_IGNORE


class TestSnakeToDatKey:
    """Tests for _snake_to_dat_key conversion."""

    @pytest.mark.parametrize(
        "snake,expected",
        [
            ("damage_player", "Damage_Player"),
            ("health", "Health"),
            ("player_damage_multiplier", "Player_Damage_Multiplier"),
            ("id", "Id"),
        ],
    )
    def test_snake_to_dat_key(self, snake, expected):
        assert _snake_to_dat_key(snake) == expected


class TestFieldCoverageReport:
    """Tests for the FieldCoverageReport warning system."""

    def test_no_uncovered_all_consumed(self):
        """When all keys are consumed or globally handled, nothing is flagged."""
        report = FieldCoverageReport()
        raw = {"GUID": "abc", "ID": "5", "Type": "Gun", "Damage_Player": "50"}
        consumed = {"Damage_Player"}
        uncovered = report.check_entry("Gun", raw, consumed)
        assert uncovered == []
        assert not report.has_uncovered()
        assert report.total_entries == 1
        assert report.entries_with_uncovered == 0

    def test_uncovered_field_flagged(self):
        """An unknown, unconsumed key gets flagged."""
        report = FieldCoverageReport()
        raw = {"GUID": "abc", "Type": "Gun", "Mystery_Field": "yes"}
        consumed: set[str] = set()
        uncovered = report.check_entry("Gun", raw, consumed)
        assert "Mystery_Field" in uncovered
        assert report.has_uncovered()
        assert report.entries_with_uncovered == 1
        assert report.uncovered["Gun"]["Mystery_Field"] == 1

    def test_globally_ignored_not_flagged(self):
        """Keys in GLOBAL_IGNORE are not flagged as uncovered."""
        report = FieldCoverageReport()
        raw = {"GUID": "abc", "Type": "Gun", "Pro": "true", "Quality_Min": "10"}
        consumed: set[str] = set()
        uncovered = report.check_entry("Gun", raw, consumed)
        assert "Pro" not in uncovered
        assert "Quality_Min" not in uncovered

    def test_type_specific_ignore(self):
        """A properties class with is_ignored() suppresses its ignored keys."""

        class FakeProps:
            @classmethod
            def is_ignored(cls, key: str) -> bool:
                return key == "Special_Key"

        report = FieldCoverageReport()
        raw = {"GUID": "abc", "Type": "Gun", "Special_Key": "val", "Other_Key": "val"}
        consumed: set[str] = set()
        uncovered = report.check_entry("Gun", raw, consumed, properties_cls=FakeProps)
        assert "Special_Key" not in uncovered
        assert "Other_Key" in uncovered

    def test_format_warnings_empty(self):
        """No uncovered fields produces empty string."""
        report = FieldCoverageReport()
        assert report.format_warnings() == ""

    def test_format_warnings_content(self):
        """format_warnings() includes type, count, and field names."""
        report = FieldCoverageReport()
        report.check_entry("Gun", {"GUID": "a", "Foo": "1"}, set())
        report.check_entry("Gun", {"GUID": "b", "Foo": "2", "Bar": "3"}, set())
        output = report.format_warnings()
        assert "Gun" in output
        assert "Foo" in output
        assert "Bar" in output
        assert "2 uncovered field(s)" in output


class TestPropertiesRegistry:
    """Tests for the PROPERTIES_REGISTRY."""

    def test_registry_has_weapon_types(self):
        """PROPERTIES_REGISTRY contains weapon types after import."""
        assert "Gun" in PROPERTIES_REGISTRY
        assert "Melee" in PROPERTIES_REGISTRY
        assert "Throwable" in PROPERTIES_REGISTRY

    def test_get_properties_class_none(self):
        """get_properties_class returns None for unregistered types."""
        assert get_properties_class("NonExistentType") is None
