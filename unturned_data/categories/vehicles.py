"""
Category model for Unturned vehicles.
"""
from __future__ import annotations

from typing import Any

from pydantic import computed_field

from unturned_data.models import BundleEntry


class Vehicle(BundleEntry):
    """Vehicle entry (Type=Vehicle)."""

    speed_min: float = 0
    speed_max: float = 0
    steer_min: float = 0
    steer_max: float = 0
    brake: float = 0
    fuel_min: float = 0
    fuel_max: float = 0
    fuel_capacity: float = 0
    health_min: float = 0
    health_max: float = 0
    trunk_x: int = 0
    trunk_y: int = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Vehicle:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{f: getattr(base, f) for f in BundleEntry.model_fields},
            speed_min=float(raw.get("Speed_Min", 0)),
            speed_max=float(raw.get("Speed_Max", 0)),
            steer_min=float(raw.get("Steer_Min", 0)),
            steer_max=float(raw.get("Steer_Max", 0)),
            brake=float(raw.get("Brake", 0)),
            fuel_min=float(raw.get("Fuel_Min", 0)),
            fuel_max=float(raw.get("Fuel_Max", 0)),
            fuel_capacity=float(raw.get("Fuel", 0)),
            health_min=float(raw.get("Health_Min", 0)),
            health_max=float(raw.get("Health_Max", 0)),
            trunk_x=int(raw.get("Trunk_Storage_X", 0)),
            trunk_y=int(raw.get("Trunk_Storage_Y", 0)),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parsed(self) -> dict[str, Any]:
        return {
            "speed_min": self.speed_min,
            "speed_max": self.speed_max,
            "steer_min": self.steer_min,
            "steer_max": self.steer_max,
            "brake": self.brake,
            "fuel_min": self.fuel_min,
            "fuel_max": self.fuel_max,
            "fuel_capacity": self.fuel_capacity,
            "health_min": self.health_min,
            "health_max": self.health_max,
            "trunk_x": self.trunk_x,
            "trunk_y": self.trunk_y,
        }

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Rarity",
            "Speed",
            "Health",
            "Fuel Cap",
            "Trunk",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        speed = f"{self.speed_min}/{self.speed_max}"
        health = f"{self.health_min}-{self.health_max}"
        if self.trunk_x or self.trunk_y:
            total = self.trunk_x * self.trunk_y
            trunk = f"{total} ({self.trunk_x}x{self.trunk_y})"
        else:
            trunk = ""
        return [
            self.name,
            str(self.id),
            self.rarity,
            speed,
            health,
            str(self.fuel_capacity),
            trunk,
        ]
