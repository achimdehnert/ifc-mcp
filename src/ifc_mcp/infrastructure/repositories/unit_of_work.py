"""Unit of Work Implementation.

Coordinates repository operations within a single database transaction.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ifc_mcp.infrastructure.database.connection import get_session_factory


if TYPE_CHECKING:
    from ifc_mcp.infrastructure.repositories.element_repository import ElementRepository
    from ifc_mcp.infrastructure.repositories.project_repository import ProjectRepository
    from ifc_mcp.infrastructure.repositories.space_repository import SpaceRepository
    from ifc_mcp.infrastructure.repositories.storey_repository import StoreyRepository


class UnitOfWork:
    """Unit of Work pattern implementation.

    Manages a single database transaction across multiple repositories.

    Usage:
        async with UnitOfWork() as uow:
            project = await uow.projects.get_by_id(project_id)
            elements = await uow.elements.find_by_project(project_id)
            await uow.commit()

    On exception, the transaction is automatically rolled back.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize Unit of Work.

        Args:
            session: Optional existing session (for testing)
        """
        self._session = session
        self._owns_session = session is None

        # Lazy-loaded repositories
        self._projects: ProjectRepository | None = None
        self._storeys: StoreyRepository | None = None
        self._elements: ElementRepository | None = None
        self._spaces: SpaceRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        """Enter async context, create session if needed."""
        if self._owns_session:
            factory = get_session_factory()
            self._session = factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context, rollback on exception."""
        if exc_type is not None:
            await self.rollback()

        if self._owns_session and self._session is not None:
            await self._session.close()

    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered. Use 'async with UnitOfWork() as uow:'")
        return self._session

    @property
    def projects(self) -> "ProjectRepository":
        """Get project repository."""
        if self._projects is None:
            from ifc_mcp.infrastructure.repositories.project_repository import (
                ProjectRepository,
            )
            self._projects = ProjectRepository(self.session)
        return self._projects

    @property
    def storeys(self) -> "StoreyRepository":
        """Get storey repository."""
        if self._storeys is None:
            from ifc_mcp.infrastructure.repositories.storey_repository import (
                StoreyRepository,
            )
            self._storeys = StoreyRepository(self.session)
        return self._storeys

    @property
    def elements(self) -> "ElementRepository":
        """Get element repository."""
        if self._elements is None:
            from ifc_mcp.infrastructure.repositories.element_repository import (
                ElementRepository,
            )
            self._elements = ElementRepository(self.session)
        return self._elements

    @property
    def spaces(self) -> "SpaceRepository":
        """Get space repository."""
        if self._spaces is None:
            from ifc_mcp.infrastructure.repositories.space_repository import (
                SpaceRepository,
            )
            self._spaces = SpaceRepository(self.session)
        return self._spaces

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.session.rollback()

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        await self.session.flush()
