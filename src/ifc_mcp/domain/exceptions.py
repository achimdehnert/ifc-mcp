"""Domain layer exceptions.

All domain-specific exceptions inherit from DomainError.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID


class DomainError(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


# =============================================================================
# Entity Errors
# =============================================================================


class EntityNotFoundError(DomainError):
    """Raised when an entity is not found."""

    def __init__(
        self,
        entity_type: str,
        entity_id: UUID | str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{entity_type} not found: {entity_id}"
        super().__init__(message, details)
        self.entity_type = entity_type
        self.entity_id = entity_id


class EntityAlreadyExistsError(DomainError):
    """Raised when attempting to create a duplicate entity."""

    def __init__(
        self,
        entity_type: str,
        identifier: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{entity_type} already exists: {identifier}"
        super().__init__(message, details)
        self.entity_type = entity_type
        self.identifier = identifier


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(DomainError):
    """Raised when domain validation fails."""

    def __init__(
        self,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        full_message = f"Validation error for '{field}': {message}"
        details = {"field": field, "value": value}
        super().__init__(full_message, details)
        self.field = field
        self.value = value


class InvalidGlobalIdError(ValidationError):
    """Raised when IFC GlobalId is invalid."""

    def __init__(self, value: str) -> None:
        super().__init__(
            field="global_id",
            message="Invalid IFC GlobalId format (must be 22 characters)",
            value=value,
        )


class InvalidFireRatingError(ValidationError):
    """Raised when FireRating cannot be parsed."""

    def __init__(self, value: str) -> None:
        super().__init__(
            field="fire_rating",
            message="Cannot parse FireRating value",
            value=value,
        )


# =============================================================================
# IFC Import Errors
# =============================================================================


class IfcImportError(DomainError):
    """Base exception for IFC import errors."""

    pass


class IfcFileNotFoundError(IfcImportError):
    """Raised when IFC file is not found."""

    def __init__(self, file_path: str) -> None:
        super().__init__(f"IFC file not found: {file_path}")
        self.file_path = file_path


class IfcParseError(IfcImportError):
    """Raised when IFC file cannot be parsed."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(
            f"Failed to parse IFC file: {file_path}",
            {"reason": reason},
        )
        self.file_path = file_path
        self.reason = reason


class UnsupportedIfcSchemaError(IfcImportError):
    """Raised when IFC schema version is not supported."""

    def __init__(self, schema: str, supported: list[str]) -> None:
        super().__init__(
            f"Unsupported IFC schema: {schema}",
            {"supported_schemas": supported},
        )
        self.schema = schema
        self.supported = supported


# =============================================================================
# Repository Errors
# =============================================================================


class RepositoryError(DomainError):
    """Base exception for repository errors."""

    pass


class ConcurrencyError(RepositoryError):
    """Raised when a concurrency conflict occurs."""

    def __init__(self, entity_type: str, entity_id: UUID) -> None:
        super().__init__(
            f"Concurrency conflict for {entity_type}: {entity_id}",
            {"entity_type": entity_type, "entity_id": str(entity_id)},
        )
