"""
Category model registry and type dispatch.

Maps Unturned Type values to the appropriate model class and provides
``parse_entry()`` for dispatching raw data to the correct model.
"""
from __future__ import annotations

from typing import Any

from unturned_data.models import BundleEntry
from unturned_data.models.properties import PROPERTIES_REGISTRY

from unturned_data.categories.animals import Animal
from unturned_data.categories.generic import GenericEntry
from unturned_data.categories.items import (
    Attachment,
    BarricadeItem,
    Clothing,
    Consumeable,
    Gun,
    Magazine,
    MeleeWeapon,
    StructureItem,
    Throwable,
)
from unturned_data.categories.spawns import SpawnTableCategory
from unturned_data.categories.vehicles import Vehicle

TYPE_REGISTRY: dict[str, type[BundleEntry]] = {
    # Weapons
    "Gun": Gun,
    "Melee": MeleeWeapon,
    "Throwable": Throwable,
    # Consumables
    "Food": Consumeable,
    "Water": Consumeable,
    "Medical": Consumeable,
    # Clothing
    "Shirt": Clothing,
    "Pants": Clothing,
    "Hat": Clothing,
    "Vest": Clothing,
    "Backpack": Clothing,
    "Mask": Clothing,
    "Glasses": Clothing,
    # Barricades
    "Barricade": BarricadeItem,
    "Trap": BarricadeItem,
    "Storage": BarricadeItem,
    "Sentry": BarricadeItem,
    "Generator": BarricadeItem,
    "Beacon": BarricadeItem,
    "Oil_Pump": BarricadeItem,
    # Structures
    "Structure": StructureItem,
    # Magazines
    "Magazine": Magazine,
    # Attachments
    "Sight": Attachment,
    "Grip": Attachment,
    "Barrel": Attachment,
    "Tactical": Attachment,
    # Vehicles & Animals
    "Vehicle": Vehicle,
    "Animal": Animal,
    # Spawn tables
    "Spawn": SpawnTableCategory,
}

__all__ = [
    "TYPE_REGISTRY",
    "parse_entry",
    "Animal",
    "Attachment",
    "BarricadeItem",
    "Clothing",
    "Consumeable",
    "GenericEntry",
    "Gun",
    "Magazine",
    "MeleeWeapon",
    "StructureItem",
    "Throwable",
    "SpawnTableCategory",
    "Vehicle",
]


def parse_entry(
    raw: dict[str, Any],
    english: dict[str, str],
    source_path: str,
) -> BundleEntry:
    """Dispatch raw data to the appropriate category model.

    Looks up ``raw["Type"]`` in the TYPE_REGISTRY.  Falls back to
    GenericEntry for unknown types.
    """
    entry_type = str(raw.get("Type", ""))
    model_cls = TYPE_REGISTRY.get(entry_type, GenericEntry)
    entry = model_cls.from_raw(raw, english, source_path)

    # Populate properties from registry
    props_cls = PROPERTIES_REGISTRY.get(entry_type)
    if props_cls:
        props = props_cls.from_raw(raw)
        entry.properties = props.model_dump(exclude_defaults=True)

    return entry
