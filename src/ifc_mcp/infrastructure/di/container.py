"""Dependency Injection Container.

Manages service lifecycle and dependencies.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ifc_mcp.application.services.din277_service import DIN277Service
    from ifc_mcp.application.services.ex_protection_service import ExProtectionService
    from ifc_mcp.application.services.gaeb_service import GAEBService
    from ifc_mcp.application.services.import_service import ImportService
    from ifc_mcp.application.services.schedule_service import ScheduleService
    from ifc_mcp.application.services.woflv_service import WoFlVService
    from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork


class Container:
    """Dependency Injection Container.

    Singleton container for managing service instances.
    """

    _instance: Container | None = None
    _initialized: bool = False

    def __new__(cls) -> Container:
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize container (only once)."""
        if self._initialized:
            return

        self._initialized = True

        # Services will be lazily initialized
        self._import_service: ImportService | None = None
        self._schedule_service: ScheduleService | None = None
        self._ex_protection_service: ExProtectionService | None = None
        self._din277_service: DIN277Service | None = None
        self._woflv_service: WoFlVService | None = None
        self._gaeb_service: GAEBService | None = None

    def get_import_service(self, uow: UnitOfWork) -> ImportService:
        """Get ImportService instance.

        Args:
            uow: Unit of Work

        Returns:
            ImportService instance
        """
        from ifc_mcp.application.services.import_service import ImportService

        return ImportService(uow)

    def get_schedule_service(self, uow: UnitOfWork) -> ScheduleService:
        """Get ScheduleService instance.

        Args:
            uow: Unit of Work

        Returns:
            ScheduleService instance
        """
        from ifc_mcp.application.services.schedule_service import ScheduleService

        return ScheduleService(uow)

    def get_ex_protection_service(self, uow: UnitOfWork) -> ExProtectionService:
        """Get ExProtectionService instance.

        Args:
            uow: Unit of Work

        Returns:
            ExProtectionService instance
        """
        from ifc_mcp.application.services.ex_protection_service import (
            ExProtectionService,
        )

        return ExProtectionService(uow)

    def get_din277_service(self, uow: UnitOfWork) -> DIN277Service:
        """Get DIN277Service instance.

        Args:
            uow: Unit of Work

        Returns:
            DIN277Service instance
        """
        from ifc_mcp.application.services.din277_service import DIN277Service

        return DIN277Service(uow)

    def get_woflv_service(self, uow: UnitOfWork) -> WoFlVService:
        """Get WoFlVService instance.

        Args:
            uow: Unit of Work

        Returns:
            WoFlVService instance
        """
        from ifc_mcp.application.services.woflv_service import WoFlVService

        return WoFlVService(uow)

    def get_gaeb_service(self, uow: UnitOfWork) -> GAEBService:
        """Get GAEBService instance.

        Args:
            uow: Unit of Work

        Returns:
            GAEBService instance
        """
        from ifc_mcp.application.services.gaeb_service import GAEBService

        return GAEBService(uow)


# Global container instance
container = Container()
