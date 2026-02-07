"""Ex-Zone Value Object.

Represents ATEX explosion protection zone classifications.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class ExZoneType(str, Enum):
    """ATEX Explosion Zone Classification.

    Gas/Vapor Zones (IEC 60079-10-1):
    - ZONE_0: Explosive atmosphere continuously present (>1000 h/year)
    - ZONE_1: Explosive atmosphere likely during normal operation (10-1000 h/year)
    - ZONE_2: Explosive atmosphere not likely, only briefly (<10 h/year)

    Dust Zones (IEC 60079-10-2):
    - ZONE_20: Explosive dust cloud continuously present
    - ZONE_21: Explosive dust cloud likely during normal operation
    - ZONE_22: Explosive dust cloud not likely, only briefly
    """

    ZONE_0 = "zone_0"
    ZONE_1 = "zone_1"
    ZONE_2 = "zone_2"
    ZONE_20 = "zone_20"
    ZONE_21 = "zone_21"
    ZONE_22 = "zone_22"
    NONE = "none"


class ExplosionType(str, Enum):
    """Type of explosive atmosphere."""

    GAS = "gas"  # Gas/Vapor/Mist (Zones 0, 1, 2)
    DUST = "dust"  # Combustible dust (Zones 20, 21, 22)
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ExZone:
    """Value Object for ATEX Explosion Zone Classification.

    Represents the explosion hazard classification of a space according
    to ATEX directives (2014/34/EU) and IEC 60079-10.

    Attributes:
        zone_type: The zone classification
        explosion_type: Type of explosive atmosphere (gas or dust)

    Example:
        >>> zone = ExZone.parse("Zone 1")
        >>> zone.is_hazardous
        True
        >>> zone.is_gas_zone
        True
        >>> zone.required_equipment_category
        2
    """

    zone_type: ExZoneType

    # Parse patterns for zone identification
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
        """Parse Ex-Zone from various string formats.

        Args:
            value: Zone string (e.g., "Zone 1", "2", "zone_20")

        Returns:
            ExZone instance or None if cannot be parsed
        """
        if not value:
            return None

        normalized = value.strip().lower()

        # Direct lookup
        if normalized in cls._ZONE_PATTERNS:
            return cls(zone_type=cls._ZONE_PATTERNS[normalized])

        # Try regex for patterns like "Zone: 1" or "Ex-Zone: 2"
        match = re.search(r"(\d{1,2})", normalized)
        if match:
            zone_num = match.group(1)
            if zone_num in cls._ZONE_PATTERNS:
                return cls(zone_type=cls._ZONE_PATTERNS[zone_num])

        return None

    @classmethod
    def from_type(cls, zone_type: ExZoneType) -> ExZone:
        """Create ExZone from ExZoneType enum.

        Args:
            zone_type: Zone type enum value

        Returns:
            ExZone instance
        """
        return cls(zone_type=zone_type)

    @classmethod
    def none(cls) -> ExZone:
        """Create non-hazardous zone.

        Returns:
            ExZone with NONE classification
        """
        return cls(zone_type=ExZoneType.NONE)

    @property
    def is_hazardous(self) -> bool:
        """Check if zone is explosion hazardous.

        Returns:
            True if zone has explosion risk
        """
        return self.zone_type != ExZoneType.NONE

    @property
    def is_gas_zone(self) -> bool:
        """Check if zone is for gas/vapor/mist.

        Returns:
            True for Zones 0, 1, 2
        """
        return self.zone_type in (
            ExZoneType.ZONE_0,
            ExZoneType.ZONE_1,
            ExZoneType.ZONE_2,
        )

    @property
    def is_dust_zone(self) -> bool:
        """Check if zone is for combustible dust.

        Returns:
            True for Zones 20, 21, 22
        """
        return self.zone_type in (
            ExZoneType.ZONE_20,
            ExZoneType.ZONE_21,
            ExZoneType.ZONE_22,
        )

    @property
    def explosion_type(self) -> ExplosionType:
        """Get the type of explosive atmosphere.

        Returns:
            Gas, Dust, or None
        """
        if self.is_gas_zone:
            return ExplosionType.GAS
        if self.is_dust_zone:
            return ExplosionType.DUST
        return ExplosionType.NONE

    @property
    def hazard_level(self) -> int:
        """Get hazard level (0-3, where 0 is most hazardous).

        Returns:
            0 for Zone 0/20 (highest risk)
            1 for Zone 1/21
            2 for Zone 2/22
            3 for non-hazardous
        """
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
        """Get required ATEX equipment category.

        Returns:
            1 for Zone 0/20 (Category 1 equipment required)
            2 for Zone 1/21 (Category 2 equipment required)
            3 for Zone 2/22 (Category 3 equipment required)
            None for non-hazardous
        """
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
        """Get typical duration of explosive atmosphere.

        Returns:
            Tuple of (min_hours, max_hours) per year, or None for non-hazardous
        """
        durations = {
            ExZoneType.ZONE_0: (1000, 8760),  # >1000 h/year
            ExZoneType.ZONE_20: (1000, 8760),
            ExZoneType.ZONE_1: (10, 1000),  # 10-1000 h/year
            ExZoneType.ZONE_21: (10, 1000),
            ExZoneType.ZONE_2: (0, 10),  # <10 h/year
            ExZoneType.ZONE_22: (0, 10),
        }
        return durations.get(self.zone_type)

    def __str__(self) -> str:
        """Return string representation."""
        if self.zone_type == ExZoneType.NONE:
            return "No Ex-Zone"
        return f"Zone {self.zone_type.value.replace('zone_', '')}"

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"ExZone(zone_type={self.zone_type})"

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if isinstance(other, ExZone):
            return self.zone_type == other.zone_type
        return False

    def __hash__(self) -> int:
        """Return hash."""
        return hash(self.zone_type)

    def is_more_hazardous_than(self, other: ExZone) -> bool:
        """Compare hazard levels.

        Args:
            other: Another ExZone to compare

        Returns:
            True if this zone is more hazardous (lower number = more hazardous)
        """
        return self.hazard_level < other.hazard_level
