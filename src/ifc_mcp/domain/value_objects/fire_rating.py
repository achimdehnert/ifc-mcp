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

    GERMAN = "german"  # F30, F60, F90, F120
    EUROPEAN = "european"  # EI30, REI60, E30
    BRITISH = "british"  # 30/30, 60/60
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FireRating:
    """Value Object for fire resistance rating.

    Supports multiple notation systems:
    - German: F30, F60, F90, F120, F180 (minutes)
    - European: E30, EI30, EI60, REI90, EW30 (R=load, E=integrity, I=insulation, W=radiation)
    - Simple: 30, 60, 90 (just minutes)

    Attributes:
        minutes: Fire resistance duration in minutes
        classification: Original classification string
        standard: Classification standard used

    Example:
        >>> fr = FireRating.parse("F90")
        >>> fr.minutes
        90
        >>> fr >= FireRating.parse("F60")
        True
    """

    minutes: int
    classification: str
    standard: FireRatingStandard = FireRatingStandard.UNKNOWN

    # Common fire rating values for validation
    VALID_MINUTES: ClassVar[set[int]] = {15, 20, 30, 45, 60, 90, 120, 180, 240}

    # Regex patterns for parsing
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
        """Parse fire rating from various string formats.

        Args:
            value: Fire rating string (e.g., "F30", "EI60", "90")

        Returns:
            FireRating instance or None if cannot be parsed

        Examples:
            >>> FireRating.parse("F90")
            FireRating(minutes=90, classification='F90', standard=<FireRatingStandard.GERMAN>)
            >>> FireRating.parse("EI30")
            FireRating(minutes=30, classification='EI30', standard=<FireRatingStandard.EUROPEAN>)
            >>> FireRating.parse("invalid")
            None
        """
        if not value:
            return None

        value = value.strip().upper()

        # Try German pattern (F30, F60, etc.)
        if match := cls._GERMAN_PATTERN.match(value):
            minutes = int(match.group(1))
            return cls(
                minutes=minutes,
                classification=value,
                standard=FireRatingStandard.GERMAN,
            )

        # Try European pattern (EI30, REI60, etc.)
        if match := cls._EUROPEAN_PATTERN.match(value):
            minutes = int(match.group(1))
            return cls(
                minutes=minutes,
                classification=value,
                standard=FireRatingStandard.EUROPEAN,
            )

        # Try simple minutes
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
        """Create FireRating from minutes value.

        Args:
            minutes: Fire resistance duration in minutes

        Returns:
            FireRating instance with German notation
        """
        return cls(
            minutes=minutes,
            classification=f"F{minutes}",
            standard=FireRatingStandard.GERMAN,
        )

    def __str__(self) -> str:
        """Return string representation."""
        return self.classification

    def __repr__(self) -> str:
        """Return debug representation."""
        return (
            f"FireRating(minutes={self.minutes}, "
            f"classification='{self.classification}', "
            f"standard={self.standard})"
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on minutes."""
        if isinstance(other, FireRating):
            return self.minutes == other.minutes
        return False

    def __lt__(self, other: FireRating) -> bool:
        """Compare fire ratings."""
        return self.minutes < other.minutes

    def __le__(self, other: FireRating) -> bool:
        """Compare fire ratings."""
        return self.minutes <= other.minutes

    def __gt__(self, other: FireRating) -> bool:
        """Compare fire ratings."""
        return self.minutes > other.minutes

    def __ge__(self, other: FireRating) -> bool:
        """Compare fire ratings."""
        return self.minutes >= other.minutes

    def __hash__(self) -> int:
        """Return hash based on minutes."""
        return hash(self.minutes)

    def meets_requirement(self, required_minutes: int) -> bool:
        """Check if this rating meets a minimum requirement.

        Args:
            required_minutes: Required fire resistance in minutes

        Returns:
            True if this rating meets or exceeds the requirement
        """
        return self.minutes >= required_minutes

    def to_german(self) -> str:
        """Convert to German notation.

        Returns:
            German notation string (e.g., "F90")
        """
        return f"F{self.minutes}"

    def to_european_ei(self) -> str:
        """Convert to European EI notation.

        Returns:
            European notation string (e.g., "EI90")
        """
        return f"EI{self.minutes}"
