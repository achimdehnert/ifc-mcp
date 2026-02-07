"""Repository Interfaces (Protocols).

Defines the contracts for data access without implementation details.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from ifc_mcp.domain.models import (
    BuildingElement,
    ElementCategory,
    Project,
    Space,
    Storey,
)


@runtime_checkable
class IProjectRepository(Protocol):
    """Repository interface for Project aggregate."""

    async def get_by_id(self, project_id: UUID) -> Project | None: ...
    async def get_by_file_hash(self, file_hash: str) -> Project | None: ...
    async def list_all(
        self, *, include_deleted: bool = False, limit: int = 100, offset: int = 0,
    ) -> list[Project]: ...
    async def add(self, project: Project) -> Project: ...
    async def update(self, project: Project) -> Project: ...
    async def delete(self, project_id: UUID, *, hard: bool = False) -> bool: ...
    async def count(self, *, include_deleted: bool = False) -> int: ...


@runtime_checkable
class IStoreyRepository(Protocol):
    """Repository interface for Storey entities."""

    async def get_by_id(self, storey_id: UUID) -> Storey | None: ...
    async def get_by_project(self, project_id: UUID) -> list[Storey]: ...
    async def add(self, storey: Storey) -> Storey: ...
    async def add_batch(self, storeys: list[Storey]) -> int: ...


@runtime_checkable
class IElementRepository(Protocol):
    """Repository interface for BuildingElement entities."""

    async def get_by_id(self, element_id: UUID) -> BuildingElement | None: ...
    async def get_by_global_id(
        self, project_id: UUID, global_id: str,
    ) -> BuildingElement | None: ...
    async def find_by_project(
        self, project_id: UUID, *, ifc_class: str | None = None,
        category: ElementCategory | None = None, storey_id: UUID | None = None,
        limit: int = 100, offset: int = 0,
    ) -> list[BuildingElement]: ...
    async def find_by_property(
        self, project_id: UUID, pset_name: str,
        property_name: str, property_value: str,
    ) -> list[BuildingElement]: ...
    async def find_by_material(
        self, project_id: UUID, material_keyword: str,
    ) -> list[BuildingElement]: ...
    async def add(self, element: BuildingElement) -> BuildingElement: ...
    async def add_batch(self, elements: list[BuildingElement]) -> int: ...
    async def update(self, element: BuildingElement) -> BuildingElement: ...
    async def delete(self, element_id: UUID) -> bool: ...
    async def count_by_project(
        self, project_id: UUID, *, ifc_class: str | None = None,
        category: ElementCategory | None = None,
    ) -> int: ...


@runtime_checkable
class ISpaceRepository(Protocol):
    """Repository interface for Space entities."""

    async def get_by_id(self, space_id: UUID) -> Space | None: ...
    async def get_by_global_id(
        self, project_id: UUID, global_id: str,
    ) -> Space | None: ...
    async def find_by_project(
        self, project_id: UUID, *, storey_id: UUID | None = None,
        ex_zone_only: bool = False, limit: int = 100, offset: int = 0,
    ) -> list[Space]: ...
    async def find_by_ex_zone(
        self, project_id: UUID, zone_types: list[str] | None = None,
    ) -> list[Space]: ...
    async def add(self, space: Space) -> Space: ...
    async def add_batch(self, spaces: list[Space]) -> int: ...
    async def update(self, space: Space) -> Space: ...
    async def count_by_project(
        self, project_id: UUID, *, ex_zone_only: bool = False,
    ) -> int: ...


@runtime_checkable
class IUnitOfWork(Protocol):
    """Unit of Work pattern for transaction management."""

    projects: IProjectRepository
    storeys: IStoreyRepository
    elements: IElementRepository
    spaces: ISpaceRepository

    async def __aenter__(self) -> "IUnitOfWork": ...
    async def __aexit__(
        self, exc_type: type[BaseException] | None,
        exc_val: BaseException | None, exc_tb: object,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
