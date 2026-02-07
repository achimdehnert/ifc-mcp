"""Ex-Zone Value Object.

Represents ATEX explosion protection zone classifications.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class ExZoneType(str, Enum):
    """ATEX Explosion Zone Classification."""
    ZONE_0 = "zone_0"
    ZONE_1 = "zone_1"
    ZONE_2 = "zone_2"
    ZONE_20 = "zone_20"
    ZONE_21 = "zone_21"
    ZONE_22 = "zone_22"
    NONE = "none"


class ExplosionType(str, Enum):
    """Type of explosive atmosphere."""
    GAS = "gas"
    DUST = "dust"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ExZone:
    """Value Object for ATEX Explosion Zone Classification."""

    zone_type: ExZoneType

    _ZONE_PATTERNS: ClassVar[dict[str, ExZoneType]] = {
        "0": ExZoneType.ZONE_0,
        "1": ExZoneType.ZONE_1,
        "2": ExZoneType.ZONE_2,
        "20": ExZoneType.ZONE_20,
        "21": ExZoneType.ZONE_21,
        "22": ExZoneType.ZONE_22,
        "zone 0": ExZoneType.ZONE_0,
        "zone 1": ExZoneType.ZONE_1,
        "zone 2": ExZoneType.ZONE_2,
        "zone 20": ExZoneType.ZONE_20,
        "zone 21": ExZoneType.ZONE_21,
        "zone 22": ExZoneType.ZONE_22,
        "zone_0": ExZoneType.ZONE_0,
        "zone_1": ExZoneType.ZONE_1,
        "zone_2": ExZoneType.ZONE_2,
        "zone_20": ExZoneType.ZONE_20,
        "zone_21": ExZoneType.ZONE_21,
        "zone_22": ExZoneType.ZONE_22,
        "ex-zone 0": ExZoneType.ZONE_0,
        "ex-zone 1": ExZoneType.ZONE_1,
        "ex-zone 2": ExZoneType.ZONE_2,
        "ex zone 0": ExZoneType.ZONE_0,
        "ex zone 1": ExZoneType.ZONE_1,
        "ex zone 2": ExZoneType.ZONE_2,
    }

    @classmethod
    def parse(cls, value: str | None) -> ExZone | None:
        """Parse Ex-Zone from various string formats."""
        if not value:
            return None

        normalized = value.strip().lower()

        if normalized in cls._ZONE_PATTERNS:
            return cls(zone_type=cls._ZONE_PATTERNS[normalized])

        match = re.search(r"(\d{1,2})", normalized)
        if match:
            zone_num = match.group(1)
            if zone_num in cls._ZONE_PATTERNS:
                return cls(zone_type=cls._ZONE_PATTERNS[zone_num])

        return None

    @classmethod
    def from_type(cls, zone_type: ExZoneType) -> ExZone:
        """Create ExZone from ExZoneType enum."""
        return cls(zone_type=zone_type)

    @classmethod
    def none(cls) -> ExZone:
        """Create non-hazardous zone."""
        return cls(zone_type=ExZoneType.NONE)

    @property
    def is_hazardous(self) -> bool:
        """Check if zone is explosion hazardous."""
        return self.zone_type != ExZoneType.NONE

    @property
    def is_gas_zone(self) -> bool:
        """Check if zone is for gas/vapor/mist."""
        return self.zone_type in (
            ExZoneType.ZONE_0,
            ExZoneType.ZONE_1,
            ExZoneType.ZONE_2,
        )

    @property
    def is_dust_zone(self) -> bool:
        """Check if zone is for combustible dust."""
        return self.zone_type in (
            ExZoneType.ZONE_20,
            ExZoneType.ZONE_21,
            ExZoneType.ZONE_22,
        )

    @property
    def explosion_type(self) -> ExplosionType:
        """Get the type of explosive atmosphere."""
        if self.is_gas_zone:
            return ExplosionType.GAS
        if self.is_dust_zone:
            return ExplosionType.DUST
        return ExplosionType.NONE

    @property
    def hazard_level(self) -> int:
        """Get hazard level (0-3, where 0 is most hazardous)."""
        mapping = {
            ExZoneType.ZONE_0: 0,
            ExZoneType.ZONE_20: 0,
            ExZoneType.ZONE_1: 1,
            ExZoneType.ZONE_21: 1,
            ExZoneType.ZONE_2: 2,
            ExZoneType.ZONE_22: 2,
            ExZoneType.NONE: 3,
        }
        return mapping[self.zone_type]

    @property
    def required_equipment_category(self) -> int | None:
        """Get required ATEX equipment category."""
        if not self.is_hazardous:
            return None

        mapping = {
            ExZoneType.ZONE_0: 1,
            ExZoneType.ZONE_20: 1,
            ExZoneType.ZONE_1: 2,
            ExZoneType.ZONE_21: 2,
            ExZoneType.ZONE_2: 3,
            ExZoneType.ZONE_22: 3,
        }
        return mapping.get(self.zone_type)

    @property
    def typical_duration_hours_per_year(self) -> tuple[int, int] | None:
        """Get typical duration of explosive atmosphere."""
        durations = {
            ExZoneType.ZONE_0: (1000, 8760),
            ExZoneType.ZONE_20: (1000, 8760),
            ExZoneType.ZONE_1: (10, 1000),
            ExZoneType.ZONE_21: (10, 1000),
            ExZoneType.ZONE_2: (0, 10),
            ExZoneType.ZONE_22: (0, 10),
        }
        return durations.get(self.zone_type)

    def __str__(self) -> str:
        if self.zone_type == ExZoneType.NONE:
            return "No Ex-Zone"
        return f"Zone {self.zone_type.value.replace('zone_', '')}"

    def __repr__(self) -> str:
        return f"ExZone(zone_type={self.zone_type})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ExZone):
            return self.zone_type == other.zone_type
        return False

    def __hash__(self) -> int:
        return hash(self.zone_type)

    def is_more_hazardous_than(self, other: ExZone) -> bool:
        """Compare hazard levels."""
        return self.hazard_level < other.hazard_level
