"""
Shared models for Unturned bundle data.

Provides base BundleEntry (Pydantic BaseModel) and composable stat blocks
(DamageStats, ConsumableStats, StorageStats, Blueprint) that category-specific
models will reuse.
"""

from unturned_data.models.entry import (
    BundleEntry,
    CraftingBlacklist,
    ConsumableStats,
    DamageStats,
    SpawnTable,
    SpawnTableEntry,
    StorageStats,
)
from unturned_data.models.blueprint import (
    Blueprint,
    BlueprintCondition,
    BlueprintReward,
    format_blueprint_ingredients,
    format_blueprint_workstations,
)

__all__ = [
    "Blueprint",
    "BlueprintCondition",
    "BlueprintReward",
    "BundleEntry",
    "ConsumableStats",
    "CraftingBlacklist",
    "DamageStats",
    "SpawnTable",
    "SpawnTableEntry",
    "StorageStats",
    "format_blueprint_ingredients",
    "format_blueprint_workstations",
]
