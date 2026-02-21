"""Properties package for type-specific item property models."""

from __future__ import annotations

from unturned_data.models.properties.base import ItemProperties

PROPERTIES_REGISTRY: dict[str, type[ItemProperties]] = {}


def get_properties_class(item_type: str) -> type[ItemProperties] | None:
    """Look up the properties model class for a given item type."""
    return PROPERTIES_REGISTRY.get(item_type)
