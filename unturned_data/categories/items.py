"""
Category models for Unturned item types.

Covers: Gun, MeleeWeapon, Consumeable, Clothing, Throwable,
BarricadeItem, StructureItem, Magazine, Attachment.
"""
from __future__ import annotations

from typing import Any


from unturned_data.models import (
    Blueprint,
    BundleEntry,
    ConsumableStats,
    DamageStats,
    StorageStats,
    format_blueprint_ingredients,
    format_blueprint_workstations,
)


# ---------------------------------------------------------------------------
# Gun
# ---------------------------------------------------------------------------
class Gun(BundleEntry):
    """Firearm (Type=Gun)."""


    damage: DamageStats | None = None

    slot: str = ""
    caliber: int = 0
    firerate: int = 0
    range: float = 0
    fire_modes: list[str] = []
    hooks: list[str] = []
    ammo_min: int = 0
    ammo_max: int = 0
    durability: float = 0
    spread_aim: float = 0
    spread_angle: float = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Gun:
        base = BundleEntry.from_raw(raw, english, source_path)

        # Fire modes: check for Safety, Semi, Auto, Burst flags
        fire_modes: list[str] = []
        for mode in ("Safety", "Semi", "Auto", "Burst"):
            if raw.get(mode):
                fire_modes.append(mode)

        # Hooks: collect Hook_* keys that are True
        hooks: list[str] = []
        for key, val in raw.items():
            if key.startswith("Hook_") and val:
                hooks.append(key[5:])  # strip "Hook_" prefix

        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            damage=DamageStats.from_raw(raw),

            slot=str(raw.get("Slot", "")),
            caliber=int(raw.get("Caliber", 0)),
            firerate=int(raw.get("Firerate", 0)),
            range=float(raw.get("Range", 0)),
            fire_modes=fire_modes,
            hooks=hooks,
            ammo_min=int(raw.get("Ammo_Min", 0)),
            ammo_max=int(raw.get("Ammo_Max", 0)),
            durability=float(raw.get("Durability", 0)),
            spread_aim=float(raw.get("Spread_Aim", 0)),
            spread_angle=float(raw.get("Spread_Angle_Degrees", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "slot": self.slot,
                "caliber": self.caliber,
                "firerate": self.firerate,
                "range": self.range,
                "fire_modes": self.fire_modes,
                "hooks": self.hooks,
                "ammo_min": self.ammo_min,
                "ammo_max": self.ammo_max,
                "durability": self.durability,
                "spread_aim": self.spread_aim,
                "spread_angle": self.spread_angle,
                "damage": {
                    "player": self.damage.player,
                    "zombie": self.damage.zombie,
                    "animal": self.damage.animal,
                }
                if self.damage
                else None,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Slot",
            "Dmg (P/Z/A)",
            "Firerate",
            "Range",
            "Modes",
            "Caliber",
            "Ammo",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        dmg = ""
        if self.damage:
            dmg = f"{self.damage.player}/{self.damage.zombie}/{self.damage.animal}"
        modes = "/".join(self.fire_modes)
        ammo = f"{self.ammo_min}-{self.ammo_max}" if self.ammo_max else str(self.ammo_min)
        return [
            self.name,
            str(self.id),
            self.rarity,
            self.slot,
            dmg,
            str(self.firerate),
            str(self.range),
            modes,
            str(self.caliber),
            ammo,
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# MeleeWeapon
# ---------------------------------------------------------------------------
class MeleeWeapon(BundleEntry):
    """Melee weapon (Type=Melee)."""


    damage: DamageStats | None = None

    slot: str = ""
    range: float = 0
    strength: float = 0
    stamina: float = 0
    durability: float = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> MeleeWeapon:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            damage=DamageStats.from_raw(raw),

            slot=str(raw.get("Slot", "")),
            range=float(raw.get("Range", 0)),
            strength=float(raw.get("Strength", 0)),
            stamina=float(raw.get("Stamina", 0)),
            durability=float(raw.get("Durability", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "slot": self.slot,
                "range": self.range,
                "strength": self.strength,
                "stamina": self.stamina,
                "durability": self.durability,
                "damage": {
                    "player": self.damage.player,
                    "zombie": self.damage.zombie,
                    "animal": self.damage.animal,
                }
                if self.damage
                else None,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Slot",
            "Dmg (P/Z/A)",
            "Range",
            "Strength",
            "Stamina",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        dmg = ""
        if self.damage:
            dmg = f"{self.damage.player}/{self.damage.zombie}/{self.damage.animal}"
        return [
            self.name,
            str(self.id),
            self.rarity,
            self.slot,
            dmg,
            str(self.range),
            str(self.strength),
            str(self.stamina),
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# Consumeable
# ---------------------------------------------------------------------------
class Consumeable(BundleEntry):
    """Consumable item (Type=Food, Water, Medical)."""


    consumable: ConsumableStats | None = None


    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Consumeable:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            consumable=ConsumableStats.from_raw(raw),

        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "consumable": {
                    "health": self.consumable.health,
                    "food": self.consumable.food,
                    "water": self.consumable.water,
                    "virus": self.consumable.virus,
                    "vision": self.consumable.vision,
                    "bleeding_modifier": self.consumable.bleeding_modifier,
                }
                if self.consumable
                else None,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Health",
            "Food",
            "Water",
            "Virus",
            "Bleeding",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        ingredients = format_blueprint_ingredients(self.blueprints, guid_map)
        workstations = format_blueprint_workstations(self.blueprints, guid_map)
        if self.consumable:
            return [
                self.name,
                str(self.id),
                self.rarity,
                str(self.consumable.health),
                str(self.consumable.food),
                str(self.consumable.water),
                str(self.consumable.virus),
                self.consumable.bleeding_modifier,
                ingredients,
                workstations,
            ]
        return [
            self.name,
            str(self.id),
            self.rarity,
            "",
            "",
            "",
            "",
            "",
            ingredients,
            workstations,
        ]


# ---------------------------------------------------------------------------
# Clothing
# ---------------------------------------------------------------------------
class Clothing(BundleEntry):
    """Clothing item (Type=Shirt, Pants, Hat, Vest, Backpack, Mask, Glasses)."""


    storage: StorageStats | None = None

    armor: float = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Clothing:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            storage=StorageStats.from_raw(raw),

            armor=float(raw.get("Armor", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "storage": {
                    "width": self.storage.width,
                    "height": self.storage.height,
                }
                if self.storage
                else None,
                "armor": self.armor,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Capacity",
            "Armor",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        capacity = ""
        if self.storage and (self.storage.width or self.storage.height):
            total = self.storage.width * self.storage.height
            capacity = f"{total} ({self.storage.width}x{self.storage.height})"
        return [
            self.name,
            str(self.id),
            self.rarity,
            capacity,
            str(self.armor) if self.armor else "",
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# Throwable
# ---------------------------------------------------------------------------
class Throwable(BundleEntry):
    """Throwable item (Type=Throwable)."""


    damage: DamageStats | None = None

    fuse: float = 0
    explosion: float = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Throwable:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            damage=DamageStats.from_raw(raw),

            fuse=float(raw.get("Fuse", 0)),
            explosion=float(raw.get("Explosion", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "fuse": self.fuse,
                "explosion": self.explosion,
                "damage": {
                    "player": self.damage.player,
                    "zombie": self.damage.zombie,
                    "animal": self.damage.animal,
                }
                if self.damage
                else None,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Dmg (P/Z/A)",
            "Fuse",
            "Explosion",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        dmg = ""
        if self.damage:
            dmg = f"{self.damage.player}/{self.damage.zombie}/{self.damage.animal}"
        return [
            self.name,
            str(self.id),
            self.rarity,
            dmg,
            str(self.fuse),
            str(self.explosion),
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# BarricadeItem
# ---------------------------------------------------------------------------
class BarricadeItem(BundleEntry):
    """Barricade-type item (Type=Barricade, Trap, Storage, Sentry, Generator, Beacon, Oil_Pump)."""


    damage: DamageStats | None = None
    storage: StorageStats | None = None

    health: float = 0
    range: float = 0
    build: str = ""

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> BarricadeItem:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            damage=DamageStats.from_raw(raw),
            storage=StorageStats.from_raw(raw),

            health=float(raw.get("Health", 0)),
            range=float(raw.get("Range", 0)),
            build=str(raw.get("Build", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "health": self.health,
                "range": self.range,
                "build": self.build,
                "storage": {
                    "width": self.storage.width,
                    "height": self.storage.height,
                }
                if self.storage
                else None,
                "damage": {
                    "player": self.damage.player,
                    "zombie": self.damage.zombie,
                    "animal": self.damage.animal,
                }
                if self.damage
                else None,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Health",
            "Capacity",
            "Dmg (P/Z/A)",
            "Range",
            "Build",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        dmg = ""
        if self.damage:
            dmg = f"{self.damage.player}/{self.damage.zombie}/{self.damage.animal}"
        capacity = ""
        if self.storage and (self.storage.width or self.storage.height):
            total = self.storage.width * self.storage.height
            capacity = f"{total} ({self.storage.width}x{self.storage.height})"
        return [
            self.name,
            str(self.id),
            self.rarity,
            str(self.health),
            capacity,
            dmg,
            str(self.range),
            self.build,
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# StructureItem
# ---------------------------------------------------------------------------
class StructureItem(BundleEntry):
    """Structure item (Type=Structure)."""


    health: float = 0
    range: float = 0
    construct: str = ""

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> StructureItem:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},

            health=float(raw.get("Health", 0)),
            range=float(raw.get("Range", 0)),
            construct=str(raw.get("Construct", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "health": self.health,
                "range": self.range,
                "construct": self.construct,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Health",
            "Range",
            "Construct",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        return [
            self.name,
            str(self.id),
            self.rarity,
            str(self.health),
            str(self.range),
            self.construct,
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# Magazine
# ---------------------------------------------------------------------------
class Magazine(BundleEntry):
    """Magazine item (Type=Magazine)."""


    amount: int = 0
    count_min: int = 0
    count_max: int = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Magazine:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},

            amount=int(raw.get("Amount", 0)),
            count_min=int(raw.get("Count_Min", 0)),
            count_max=int(raw.get("Count_Max", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "amount": self.amount,
                "count_min": self.count_min,
                "count_max": self.count_max,
                "blueprints_count": len(self.blueprints),
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Amount",
            "Count",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        count = f"{self.count_min}-{self.count_max}" if self.count_max else str(self.count_min)
        return [
            self.name,
            str(self.id),
            self.rarity,
            str(self.amount),
            count,
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]


# ---------------------------------------------------------------------------
# Attachment
# ---------------------------------------------------------------------------
class Attachment(BundleEntry):
    """Attachment item (Type=Sight, Grip, Barrel, Tactical)."""



    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Attachment:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},

        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["blueprints_count"] = len(self.blueprints)
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Size",
            "Ingredients",
            "Requires Nearby",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        size = f"{self.size_x}x{self.size_y}" if self.size_x or self.size_y else ""
        return [
            self.name,
            str(self.id),
            self.rarity,
            size,
            format_blueprint_ingredients(self.blueprints, guid_map),
            format_blueprint_workstations(self.blueprints, guid_map),
        ]
