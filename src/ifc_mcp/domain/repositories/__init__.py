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

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """Get project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project or None if not found
        """
        ...

    async def get_by_file_hash(self, file_hash: str) -> Project | None:
        """Get project by file hash (for deduplication).

        Args:
            file_hash: SHA-256 hash of original file

        Returns:
            Project or None
        """
        ...

    async def list_all(
        self,
        *,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """List all projects.

        Args:
            include_deleted: Include soft-deleted projects
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of projects
        """
        ...

    async def add(self, project: Project) -> Project:
        """Add a new project.

        Args:
            project: Project to add

        Returns:
            Added project with ID
        """
        ...

    async def update(self, project: Project) -> Project:
        """Update existing project.

        Args:
            project: Project to update

        Returns:
            Updated project
        """
        ...

    async def delete(self, project_id: UUID, *, hard: bool = False) -> bool:
        """Delete a project.

        Args:
            project_id: Project UUID
            hard: If True, permanently delete; else soft-delete

        Returns:
            True if deleted
        """
        ...

    async def count(self, *, include_deleted: bool = False) -> int:
        """Count projects.

        Args:
            include_deleted: Include soft-deleted

        Returns:
            Total count
        """
        ...


@runtime_checkable
class IStoreyRepository(Protocol):
    """Repository interface for Storey entities."""

    async def get_by_id(self, storey_id: UUID) -> Storey | None:
        """Get storey by ID."""
        ...

    async def get_by_project(self, project_id: UUID) -> list[Storey]:
        """Get all storeys for a project, ordered by elevation."""
        ...

    async def add(self, storey: Storey) -> Storey:
        """Add a storey."""
        ...

    async def add_batch(self, storeys: list[Storey]) -> int:
        """Batch add storeys."""
        ...


@runtime_checkable
class IElementRepository(Protocol):
    """Repository interface for BuildingElement entities."""

    async def get_by_id(self, element_id: UUID) -> BuildingElement | None:
        """Get element by ID with properties loaded.

        Args:
            element_id: Element UUID

        Returns:
            BuildingElement or None
        """
        ...

    async def get_by_global_id(
        self,
        project_id: UUID,
        global_id: str,
    ) -> BuildingElement | None:
        """Get element by IFC GlobalId.

        Args:
            project_id: Project UUID
            global_id: IFC GlobalId string

        Returns:
            BuildingElement or None
        """
        ...

    async def find_by_project(
        self,
        project_id: UUID,
        *,
        ifc_class: str | None = None,
        category: ElementCategory | None = None,
        storey_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BuildingElement]:
        """Find elements by criteria.

        Args:
            project_id: Project UUID
            ifc_class: Filter by IFC class
            category: Filter by category
            storey_id: Filter by storey
            limit: Max results
            offset: Pagination offset

        Returns:
            List of elements
        """
        ...

    async def find_by_property(
        self,
        project_id: UUID,
        pset_name: str,
        property_name: str,
        property_value: str,
    ) -> list[BuildingElement]:
        """Find elements by property value.

        Args:
            project_id: Project UUID
            pset_name: Property set name
            property_name: Property name
            property_value: Property value to match

        Returns:
            List of matching elements
        """
        ...

    async def find_by_material(
        self,
        project_id: UUID,
        material_keyword: str,
    ) -> list[BuildingElement]:
        """Find elements by material keyword.

        Args:
            project_id: Project UUID
            material_keyword: Material name keyword (case-insensitive)

        Returns:
            List of matching elements
        """
        ...

    async def add(self, element: BuildingElement) -> BuildingElement:
        """Add an element.

        Args:
            element: Element to add

        Returns:
            Added element
        """
        ...

    async def add_batch(self, elements: list[BuildingElement]) -> int:
        """Batch add elements for import performance.

        Args:
            elements: Elements to add

        Returns:
            Count of added elements
        """
        ...

    async def update(self, element: BuildingElement) -> BuildingElement:
        """Update an element.

        Args:
            element: Element to update

        Returns:
            Updated element
        """
        ...

    async def delete(self, element_id: UUID) -> bool:
        """Delete an element.

        Args:
            element_id: Element UUID

        Returns:
            True if deleted
        """
        ...

    async def count_by_project(
        self,
        project_id: UUID,
        *,
        ifc_class: str | None = None,
        category: ElementCategory | None = None,
    ) -> int:
        """Count elements by criteria.

        Args:
            project_id: Project UUID
            ifc_class: Filter by IFC class
            category: Filter by category

        Returns:
            Count
        """
        ...


@runtime_checkable
class ISpaceRepository(Protocol):
    """Repository interface for Space entities."""

    async def get_by_id(self, space_id: UUID) -> Space | None:
        """Get space by ID with boundaries loaded."""
        ...

    async def get_by_global_id(
        self,
        project_id: UUID,
        global_id: str,
    ) -> Space | None:
        """Get space by IFC GlobalId."""
        ...

    async def find_by_project(
        self,
        project_id: UUID,
        *,
        storey_id: UUID | None = None,
        ex_zone_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Space]:
        """Find spaces by criteria.

        Args:
            project_id: Project UUID
            storey_id: Filter by storey
            ex_zone_only: Only return spaces with Ex-Zone
            limit: Max results
            offset: Pagination offset

        Returns:
            List of spaces
        """
        ...

    async def find_by_ex_zone(
        self,
        project_id: UUID,
        zone_types: list[str] | None = None,
    ) -> list[Space]:
        """Find spaces by Ex-Zone classification.

        Args:
            project_id: Project UUID
            zone_types: Filter by specific zones (e.g., ["zone_0", "zone_1"])

        Returns:
            List of spaces with Ex-Zones
        """
        ...

    async def add(self, space: Space) -> Space:
        """Add a space."""
        ...

    async def add_batch(self, spaces: list[Space]) -> int:
        """Batch add spaces."""
        ...

    async def update(self, space: Space) -> Space:
        """Update a space."""
        ...

    async def count_by_project(
        self,
        project_id: UUID,
        *,
        ex_zone_only: bool = False,
    ) -> int:
        """Count spaces."""
        ...


@runtime_checkable
class IUnitOfWork(Protocol):
    """Unit of Work pattern for transaction management.

    Coordinates the work of multiple repositories within a single
    database transaction.
    """

    projects: IProjectRepository
    storeys: IStoreyRepository
    elements: IElementRepository
    spaces: ISpaceRepository

    async def __aenter__(self) -> "IUnitOfWork":
        """Enter async context."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context, rollback on exception."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
