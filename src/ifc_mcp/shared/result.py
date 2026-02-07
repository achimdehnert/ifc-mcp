"""Result pattern for explicit error handling.

Provides Success and Failure types to replace exception-based control flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Successful result."""

    value: T

    def is_success(self) -> bool:
        """Check if result is success."""
        return True

    def is_failure(self) -> bool:
        """Check if result is failure."""
        return False

    def unwrap(self) -> T:
        """Get the value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or default."""
        return self.value


@dataclass(frozen=True)
class Failure(Generic[E]):
    """Failed result."""

    error: E

    def is_success(self) -> bool:
        """Check if result is success."""
        return False

    def is_failure(self) -> bool:
        """Check if result is failure."""
        return True

    def unwrap(self) -> None:
        """Raise error when unwrapping failure."""
        raise ValueError(f"Cannot unwrap Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get default value for failure."""
        return default


# Type alias
Result = Success[T] | Failure[E]


def ok(value: T) -> Success[T]:
    """Create a Success result.

    Args:
        value: The success value

    Returns:
        Success wrapping the value
    """
    return Success(value)


def err(error: E) -> Failure[E]:
    """Create a Failure result.

    Args:
        error: The error value

    Returns:
        Failure wrapping the error
    """
    return Failure(error)
