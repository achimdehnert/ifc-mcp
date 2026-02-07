"""Result Pattern for explicit error handling.

Replaces exceptions with explicit Result types.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Success result containing a value."""

    value: T

    def is_success(self) -> bool:
        """Check if result is success."""
        return True

    def is_failure(self) -> bool:
        """Check if result is failure."""
        return False

    def unwrap(self) -> T:
        """Get the success value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get value or default."""
        return self.value


@dataclass(frozen=True)
class Failure(Generic[E]):
    """Failure result containing an error."""

    error: E

    def is_success(self) -> bool:
        """Check if result is success."""
        return False

    def is_failure(self) -> bool:
        """Check if result is failure."""
        return True

    def unwrap(self) -> never:
        """Raises the error."""
        raise ValueError(f"Called unwrap on Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get value or default."""
        return default


# Type alias for Result
Result = Success[T] | Failure[E]


# Convenience constructors
def success(value: T) -> Success[T]:
    """Create Success result.

    Args:
        value: Success value

    Returns:
        Success instance
    """
    return Success(value)


def failure(error: E) -> Failure[E]:
    """Create Failure result.

    Args:
        error: Error value

    Returns:
        Failure instance
    """
    return Failure(error)
