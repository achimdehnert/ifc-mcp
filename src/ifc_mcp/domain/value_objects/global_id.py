"""IFC GlobalId Value Object.

GlobalId is the unique identifier for IFC entities, encoded in base64.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# IFC GlobalId is 22 characters, base64 encoded (A-Z, a-z, 0-9, _, $)
GLOBAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_$]{22}$")


@dataclass(frozen=True, slots=True)
class GlobalId:
    """Value Object for IFC GlobalId.

    IFC GlobalId is a 22-character base64-encoded identifier that uniquely
    identifies each IFC entity instance.

    Attributes:
        value: The 22-character GlobalId string

    Example:
        >>> gid = GlobalId("2XQ$n5SLP5MBLyL442paFx")
        >>> str(gid)
        '2XQ$n5SLP5MBLyL442paFx'
    """

    value: str

    def __post_init__(self) -> None:
        """Validate GlobalId format."""
        if not self.value:
            raise ValueError("GlobalId cannot be empty")
        if not GLOBAL_ID_PATTERN.match(self.value):
            raise ValueError(
                f"Invalid GlobalId format: '{self.value}'. "
                "Must be 22 characters using A-Z, a-z, 0-9, _, $"
            )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"GlobalId('{self.value}')"

    def __hash__(self) -> int:
        """Return hash for use in sets/dicts."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if isinstance(other, GlobalId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    @classmethod
    def from_string(cls, value: str | None) -> GlobalId | None:
        """Create GlobalId from string, returning None if invalid.

        Args:
            value: String to convert

        Returns:
            GlobalId instance or None if invalid
        """
        if not value:
            return None
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if string is a valid GlobalId.

        Args:
            value: String to check

        Returns:
            True if valid GlobalId format
        """
        return bool(value and GLOBAL_ID_PATTERN.match(value))
