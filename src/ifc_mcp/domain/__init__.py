"""Domain Layer.

Contains the core business logic, entities, value objects, and repository interfaces.
This layer has NO external dependencies (no SQLAlchemy, no frameworks).
"""
from __future__ import annotations

from ifc_mcp.domain.exceptions import (
    ConcurrencyError,
    DomainError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    IfcFileNotFoundError,
    IfcImportError,
    IfcParseError,
    InvalidFireRatingError,
    InvalidGlobalIdError,
    RepositoryError,
    UnsupportedIfcSchemaError,
    ValidationError,
)
from ifc_mcp.domain.models import (
    BuildingElement,
    ElementCategory,
    IfcSchemaVersion,
    MaterialLayer,
    Project,
    PropertyValue,
    QuantityValue,
    Space,
    SpaceBoundary,
    Storey,
)
from ifc_mcp.domain.repositories import (
    IElementRepository,
    IProjectRepository,
    ISpaceRepository,
    IStoreyRepository,
    IUnitOfWork,
)
from ifc_mcp.domain.value_objects import (
    ExplosionType,
    ExZone,
    ExZoneType,
    FireRating,
    FireRatingStandard,
    GlobalId,
)

__all__ = [
    # Exceptions
    "DomainError",
    "EntityNotFoundError",
    "EntityAlreadyExistsError",
    "ValidationError",
    "InvalidGlobalIdError",
    "InvalidFireRatingError",
    "IfcImportError",
    "IfcFileNotFoundError",
    "IfcParseError",
    "UnsupportedIfcSchemaError",
    "RepositoryError",
    "ConcurrencyError",
    # Models
    "Project",
    "Storey",
    "IfcSchemaVersion",
    "BuildingElement",
    "ElementCategory",
    "PropertyValue",
    "QuantityValue",
    "MaterialLayer",
    "Space",
    "SpaceBoundary",
    # Value Objects
    "GlobalId",
    "FireRating",
    "FireRatingStandard",
    "ExZone",
    "ExZoneType",
    "ExplosionType",
    # Repositories
    "IProjectRepository",
    "IStoreyRepository",
    "IElementRepository",
    "ISpaceRepository",
    "IUnitOfWork",
]
