"""IFC GlobalId Value Object.

GlobalId is the unique identifier for IFC entities, encoded in base64.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


GLOBAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_$]{22}$")


@dataclass(frozen=True, slots=True)
class GlobalId:
    """Value Object for IFC GlobalId."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("GlobalId cannot be empty")
        if not GLOBAL_ID_PATTERN.match(self.value):
            raise ValueError(f"Invalid GlobalId format: '{self.value}'.")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"GlobalId('{self.value}')"

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GlobalId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    @classmethod
    def from_string(cls, value: str | None) -> GlobalId | None:
        if not value:
            return None
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return bool(value and GLOBAL_ID_PATTERN.match(value))
