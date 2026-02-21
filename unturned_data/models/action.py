"""
Action model for Unturned item Action_N_* fields.

Items can define Actions that link to blueprints on other items, enabling
cross-item recipe references in the crafting system.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Action(BaseModel):
    """A single Action entry parsed from Action_N_* fields."""

    type: str = ""
    source: str = ""
    blueprint_indices: list[int] = []
    key: str = ""
    text: str = ""
    tooltip: str = ""

    @staticmethod
    def list_from_raw(raw: dict[str, Any]) -> list[Action]:
        """Parse Action_N_* fields from a parsed .dat dict."""
        count = raw.get("Actions")
        if not count or not isinstance(count, int):
            return []

        results: list[Action] = []
        for i in range(count):
            prefix = f"Action_{i}_"
            action_type = str(raw.get(f"{prefix}Type", ""))
            source = str(raw.get(f"{prefix}Source", ""))

            # Parse blueprint indices
            bp_count = raw.get(f"{prefix}Blueprints", 0)
            indices: list[int] = []
            if isinstance(bp_count, int):
                for j in range(bp_count):
                    idx = raw.get(f"{prefix}Blueprint_{j}_Index")
                    if idx is not None:
                        indices.append(int(idx))

            key = str(raw.get(f"{prefix}Key", ""))
            text = str(raw.get(f"{prefix}Text", ""))
            tooltip = str(raw.get(f"{prefix}Tooltip", ""))

            results.append(Action(
                type=action_type,
                source=source,
                blueprint_indices=indices,
                key=key,
                text=text,
                tooltip=tooltip,
            ))
        return results
