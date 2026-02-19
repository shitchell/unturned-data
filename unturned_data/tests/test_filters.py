"""Tests for the filter system."""

from unturned_data.filters import apply_filters, map_filter, EntryFilter
from unturned_data.models import BundleEntry


class TestMapFilter:
    def test_passes_spawnable_entry(self):
        entry = BundleEntry(id=42, name="Test")
        f = map_filter({"PEI"}, {"PEI": {42, 43, 44}})
        assert f(entry)

    def test_rejects_non_spawnable_entry(self):
        entry = BundleEntry(id=99, name="Test")
        f = map_filter({"PEI"}, {"PEI": {42, 43, 44}})
        assert not f(entry)


class TestApplyFilters:
    def test_no_filters_returns_all(self):
        entries = [BundleEntry(id=1), BundleEntry(id=2)]
        assert apply_filters(entries, []) == entries

    def test_single_filter(self):
        entries = [BundleEntry(id=1), BundleEntry(id=2), BundleEntry(id=3)]
        f: EntryFilter = lambda e: e.id > 1
        result = apply_filters(entries, [f])
        assert len(result) == 2

    def test_multiple_filters_all_must_pass(self):
        entries = [BundleEntry(id=1), BundleEntry(id=2), BundleEntry(id=3)]
        f1: EntryFilter = lambda e: e.id > 1
        f2: EntryFilter = lambda e: e.id < 3
        result = apply_filters(entries, [f1, f2])
        assert len(result) == 1
        assert result[0].id == 2
