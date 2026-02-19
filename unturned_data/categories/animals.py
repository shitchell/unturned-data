"""
Category model for Unturned animals.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from unturned_data.models import BundleEntry


@dataclass
class Animal(BundleEntry):
    """Animal entry (Type=Animal)."""

    health: float = 0
    damage: float = 0
    speed_run: float = 0
    speed_walk: float = 0
    behaviour: str = ""
    regen: float = 0
    reward_id: int = 0
    reward_xp: int = 0

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        english: dict[str, str],
        source_path: str,
    ) -> Animal:
        base = BundleEntry.from_raw(raw, english, source_path)
        return cls(
            **{k: v for k, v in base.__dict__.items()},
            health=float(raw.get("Health", 0)),
            damage=float(raw.get("Damage", 0)),
            speed_run=float(raw.get("Speed_Run", 0)),
            speed_walk=float(raw.get("Speed_Walk", 0)),
            behaviour=str(raw.get("Behaviour", "")),
            regen=float(raw.get("Regen", 0)),
            reward_id=int(raw.get("Reward_ID", 0)),
            reward_xp=int(raw.get("Reward_XP", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update(
            {
                "health": self.health,
                "damage": self.damage,
                "speed_run": self.speed_run,
                "speed_walk": self.speed_walk,
                "behaviour": self.behaviour,
                "regen": self.regen,
                "reward_id": self.reward_id,
                "reward_xp": self.reward_xp,
            }
        )
        return d

    @staticmethod
    def markdown_columns() -> list[str]:
        return [
            "Name",
            "ID",
            "Health",
            "Damage",
            "Speed (Run/Walk)",
            "Behaviour",
        ]

    def markdown_row(self, guid_map: dict[str, str]) -> list[str]:
        speed = f"{self.speed_run}/{self.speed_walk}"
        return [
            self.name,
            str(self.id),
            str(self.health),
            str(self.damage),
            speed,
            self.behaviour,
        ]
