"""Properties package for type-specific item property models."""

from __future__ import annotations

from unturned_data.models.properties.base import ItemProperties
from unturned_data.models.properties.clothing import (
    BagProperties,
    ClothingProperties,
    GearProperties,
)
from unturned_data.models.properties.consumables import ConsumableProperties
from unturned_data.models.properties.weapons import (
    GunProperties,
    MeleeProperties,
    ThrowableProperties,
)
from unturned_data.models.properties.attachments import (
    BarrelProperties,
    CaliberProperties,
    GripProperties,
    MagazineProperties,
    SightProperties,
    TacticalProperties,
)
from unturned_data.models.properties.barricades import (
    BarricadeProperties,
    BeaconProperties,
    ChargeProperties,
    FarmProperties,
    GeneratorProperties,
    LibraryProperties,
    OilPumpProperties,
    SentryProperties,
    StorageProperties,
    TankProperties,
    TrapProperties,
)
from unturned_data.models.properties.structures import StructureProperties

PROPERTIES_REGISTRY: dict[str, type[ItemProperties]] = {}

# Weapon types
PROPERTIES_REGISTRY["Gun"] = GunProperties
PROPERTIES_REGISTRY["Melee"] = MeleeProperties
PROPERTIES_REGISTRY["Throwable"] = ThrowableProperties

# Consumable types
PROPERTIES_REGISTRY["Food"] = ConsumableProperties
PROPERTIES_REGISTRY["Medical"] = ConsumableProperties
PROPERTIES_REGISTRY["Water"] = ConsumableProperties

# Clothing types — bag (have storage)
PROPERTIES_REGISTRY["Backpack"] = BagProperties
PROPERTIES_REGISTRY["Pants"] = BagProperties
PROPERTIES_REGISTRY["Shirt"] = BagProperties
PROPERTIES_REGISTRY["Vest"] = BagProperties

# Clothing types — gear (head slots)
PROPERTIES_REGISTRY["Hat"] = GearProperties
PROPERTIES_REGISTRY["Mask"] = GearProperties
PROPERTIES_REGISTRY["Glasses"] = GearProperties

# Attachment types
PROPERTIES_REGISTRY["Sight"] = SightProperties
PROPERTIES_REGISTRY["Barrel"] = BarrelProperties
PROPERTIES_REGISTRY["Grip"] = GripProperties
PROPERTIES_REGISTRY["Tactical"] = TacticalProperties
PROPERTIES_REGISTRY["Magazine"] = MagazineProperties

# Barricade types
PROPERTIES_REGISTRY["Barricade"] = BarricadeProperties
PROPERTIES_REGISTRY["Storage"] = StorageProperties
PROPERTIES_REGISTRY["Sentry"] = SentryProperties
PROPERTIES_REGISTRY["Farm"] = FarmProperties
PROPERTIES_REGISTRY["Generator"] = GeneratorProperties
PROPERTIES_REGISTRY["Trap"] = TrapProperties
PROPERTIES_REGISTRY["Beacon"] = BeaconProperties
PROPERTIES_REGISTRY["Tank"] = TankProperties
PROPERTIES_REGISTRY["Charge"] = ChargeProperties
PROPERTIES_REGISTRY["Library"] = LibraryProperties
PROPERTIES_REGISTRY["Oil_Pump"] = OilPumpProperties

# Structure types
PROPERTIES_REGISTRY["Structure"] = StructureProperties


def get_properties_class(item_type: str) -> type[ItemProperties] | None:
    """Look up the properties model class for a given item type."""
    return PROPERTIES_REGISTRY.get(item_type)
