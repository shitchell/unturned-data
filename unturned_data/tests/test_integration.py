"""Integration tests against full bundle data."""
import json
import pytest
from pathlib import Path
from unturned_data.loader import walk_bundle_dir
from unturned_data.categories import parse_entry
from unturned_data.formatters.json_fmt import entries_to_json
from unturned_data.formatters.crafting_fmt import entries_to_crafting_json
from unturned_data.formatters.markdown_fmt import entries_to_markdown

BUNDLES = Path.home() / "unturned-bundles"

pytestmark = pytest.mark.skipif(
    not BUNDLES.exists(), reason="Full bundle data not available"
)


class TestFullParse:
    @pytest.fixture(scope="class")
    def all_entries(self):
        entries = []
        errors = []
        for raw, english, rel_path in walk_bundle_dir(BUNDLES):
            try:
                entry = parse_entry(raw, english, rel_path)
                entries.append(entry)
            except Exception as e:
                errors.append((rel_path, str(e)))
        return entries, errors

    def test_no_parse_errors(self, all_entries):
        """Less than 1% error rate."""
        entries, errors = all_entries
        total = len(entries) + len(errors)
        error_rate = len(errors) / total if total > 0 else 0
        assert error_rate < 0.01, (
            f"{len(errors)} errors out of {total}:\n"
            + "\n".join(f"  {p}: {e}" for p, e in errors[:20])
        )

    def test_entry_count(self, all_entries):
        """Should find 1000+ entries."""
        entries, _ = all_entries
        assert len(entries) > 1000

    def test_json_valid(self, all_entries):
        """JSON output parses back as a nested dict."""
        entries, _ = all_entries
        output = entries_to_json(entries)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        # Should have top-level category keys
        assert len(parsed) > 0

    def test_json_deterministic(self, all_entries):
        entries, _ = all_entries
        assert entries_to_json(entries) == entries_to_json(entries)

    def test_markdown_valid(self, all_entries):
        entries, _ = all_entries
        output = entries_to_markdown(entries)
        assert len(output) > 0
        assert "##" in output

    def test_has_expected_types(self, all_entries):
        """Verify we parsed items from major categories."""
        entries, _ = all_entries
        types_found = {e.type for e in entries}
        for expected in ["Gun", "Food", "Vehicle", "Animal", "Melee"]:
            assert expected in types_found, f"Missing type: {expected}"

    def test_crafting_json_valid(self, all_entries):
        """Crafting JSON has nodes and edges."""
        entries, _ = all_entries
        output = entries_to_crafting_json(entries)
        data = json.loads(output)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0
