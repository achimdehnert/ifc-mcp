"""FireRating Value Object.

Represents fire resistance ratings in various notations (German, European, etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class FireRatingStandard(str, Enum):
    """Fire rating classification standards."""
    GERMAN = "german"
    EUROPEAN = "european"
    BRITISH = "british"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FireRating:
    """Value Object for fire resistance rating."""

    minutes: int
    classification: str
    standard: FireRatingStandard = FireRatingStandard.UNKNOWN

    VALID_MINUTES: ClassVar[set[int]] = {15, 20, 30, 45, 60, 90, 120, 180, 240}

    _GERMAN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[FfTtGgSsWw][-_]?(\d+)$"
    )
    _EUROPEAN_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[REIWMCreiwmc]+[-_]?(\d+)(?:[-/](\d+))?$"
    )
    _MINUTES_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(\d+)(?:\s*min)?$")

    def __post_init__(self) -> None:
        """Validate fire rating values."""
        if self.minutes < 0:
            raise ValueError(f"Fire rating minutes cannot be negative: {self.minutes}")
        if self.minutes > 360:
            raise ValueError(f"Fire rating minutes unrealistic: {self.minutes}")

    @classmethod
    def parse(cls, value: str | None) -> FireRating | None:
        """Parse fire rating from various string formats."""
        if not value:
            return None

        value = value.strip().upper()

        if match := cls._GERMAN_PATTERN.match(value):
            minutes = int(match.group(1))
            return cls(
                minutes=minutes,
                classification=value,
                standard=FireRatingStandard.GERMAN,
            )

        if match := cls._EUROPEAN_PATTERN.match(value):
            minutes = int(match.group(1))
            return cls(
                minutes=minutes,
                classification=value,
                standard=FireRatingStandard.EUROPEAN,
            )

        if match := cls._MINUTES_PATTERN.match(value):
            minutes = int(match.group(1))
            return cls(
                minutes=minutes,
                classification=f"F{minutes}",
                standard=FireRatingStandard.GERMAN,
            )

        return None

    @classmethod
    def from_minutes(cls, minutes: int) -> FireRating:
        """Create FireRating from minutes value."""
        return cls(
            minutes=minutes,
            classification=f"F{minutes}",
            standard=FireRatingStandard.GERMAN,
        )

    def __str__(self) -> str:
        return self.classification

    def __repr__(self) -> str:
        return (
            f"FireRating(minutes={self.minutes}, "
            f"classification='{self.classification}', "
            f"standard={self.standard})"
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FireRating):
            return self.minutes == other.minutes
        return False

    def __lt__(self, other: FireRating) -> bool:
        return self.minutes < other.minutes

    def __le__(self, other: FireRating) -> bool:
        return self.minutes <= other.minutes

    def __gt__(self, other: FireRating) -> bool:
        return self.minutes > other.minutes

    def __ge__(self, other: FireRating) -> bool:
        return self.minutes >= other.minutes

    def __hash__(self) -> int:
        return hash(self.minutes)

    def meets_requirement(self, required_minutes: int) -> bool:
        """Check if this rating meets a minimum requirement."""
        return self.minutes >= required_minutes

    def to_german(self) -> str:
        """Convert to German notation."""
        return f"F{self.minutes}"

    def to_european_ei(self) -> str:
        """Convert to European EI notation."""
        return f"EI{self.minutes}"
