"""IFC Project Domain Entity.

Represents an imported IFC project/file in the domain.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4


if TYPE_CHECKING:
    from ifc_mcp.domain.models.element import BuildingElement
    from ifc_mcp.domain.models.space import Space


class IfcSchemaVersion(str, Enum):
    """Supported IFC Schema Versions."""

    IFC2X3 = "IFC2X3"
    IFC4 = "IFC4"
    IFC4X1 = "IFC4X1"
    IFC4X2 = "IFC4X2"
    IFC4X3 = "IFC4X3"

    @classmethod
    def from_string(cls, value: str) -> IfcSchemaVersion:
        """Parse schema version from string.

        Args:
            value: Schema version string (e.g., "IFC4", "IFC2X3 TC1")

        Returns:
            Matching IfcSchemaVersion enum
        """
        normalized = value.upper().replace(" ", "").replace("_", "")

        # Handle common variations
        if "IFC4X3" in normalized:
            return cls.IFC4X3
        if "IFC4X2" in normalized:
            return cls.IFC4X2
        if "IFC4X1" in normalized:
            return cls.IFC4X1
        if "IFC4" in normalized:
            return cls.IFC4
        if "IFC2X3" in normalized or "IFC2" in normalized:
            return cls.IFC2X3

        # Default to IFC4 for unknown
        return cls.IFC4


@dataclass
class Storey:
    """Building storey/floor level.

    Attributes:
        id: Unique identifier
        project_id: Parent project ID
        global_id: IFC GlobalId
        name: Storey name (e.g., "Ground Floor", "Level 1")
        long_name: Long/descriptive name
        elevation: Height above origin in meters
    """

    id: UUID
    project_id: UUID
    global_id: str
    name: str | None = None
    long_name: str | None = None
    elevation: float | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        project_id: UUID,
        global_id: str,
        name: str | None = None,
        long_name: str | None = None,
        elevation: float | None = None,
    ) -> Storey:
        """Factory method to create a new Storey.

        Args:
            project_id: Parent project ID
            global_id: IFC GlobalId
            name: Storey name
            long_name: Long name
            elevation: Height in meters

        Returns:
            New Storey instance
        """
        return cls(
            id=uuid4(),
            project_id=project_id,
            global_id=global_id,
            name=name,
            long_name=long_name,
            elevation=elevation,
        )


@dataclass
class Project:
    """IFC Project Aggregate Root.

    Represents an imported IFC file with its metadata.
    This is an Aggregate Root in DDD terms - it controls
    access to its child entities.

    Attributes:
        id: Unique identifier
        name: Project name
        description: Project description
        schema_version: IFC schema version
        original_file_path: Path to original IFC file
        original_file_hash: SHA-256 hash for deduplication
        authoring_app: Application that created the IFC
        author: Author name
        organization: Organization name
        created_at: Record creation timestamp
        imported_at: Import timestamp
    """

    id: UUID
    name: str
    schema_version: IfcSchemaVersion
    description: str | None = None
    original_file_path: str | None = None
    original_file_hash: str | None = None
    authoring_app: str | None = None
    author: str | None = None
    organization: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    imported_at: datetime = field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None

    # Aggregate children (loaded lazily)
    _storeys: list[Storey] = field(default_factory=list, repr=False)
    _element_count: int | None = field(default=None, repr=False)
    _space_count: int | None = field(default=None, repr=False)

    @classmethod
    def create(
        cls,
        name: str,
        schema_version: IfcSchemaVersion | str,
        *,
        description: str | None = None,
        original_file_path: str | None = None,
        original_file_hash: str | None = None,
        authoring_app: str | None = None,
        author: str | None = None,
        organization: str | None = None,
    ) -> Project:
        """Factory method to create a new Project.

        Args:
            name: Project name
            schema_version: IFC schema version
            description: Optional description
            original_file_path: Path to IFC file
            original_file_hash: File hash
            authoring_app: Authoring application
            author: Author name
            organization: Organization name

        Returns:
            New Project instance
        """
        if isinstance(schema_version, str):
            schema_version = IfcSchemaVersion.from_string(schema_version)

        return cls(
            id=uuid4(),
            name=name,
            schema_version=schema_version,
            description=description,
            original_file_path=original_file_path,
            original_file_hash=original_file_hash,
            authoring_app=authoring_app,
            author=author,
            organization=organization,
        )

    @property
    def storeys(self) -> list[Storey]:
        """Get project storeys."""
        return self._storeys

    @storeys.setter
    def storeys(self, value: list[Storey]) -> None:
        """Set project storeys."""
        self._storeys = value

    @property
    def element_count(self) -> int | None:
        """Get total element count (if loaded)."""
        return self._element_count

    @element_count.setter
    def element_count(self, value: int) -> None:
        """Set element count."""
        self._element_count = value

    @property
    def space_count(self) -> int | None:
        """Get total space count (if loaded)."""
        return self._space_count

    @space_count.setter
    def space_count(self, value: int) -> None:
        """Set space count."""
        self._space_count = value

    @property
    def is_deleted(self) -> bool:
        """Check if project is soft-deleted."""
        return self.deleted_at is not None

    def add_storey(self, storey: Storey) -> None:
        """Add a storey to the project.

        Args:
            storey: Storey to add
        """
        storey.project_id = self.id
        self._storeys.append(storey)

    def get_storey_by_name(self, name: str) -> Storey | None:
        """Find storey by name.

        Args:
            name: Storey name to find

        Returns:
            Matching Storey or None
        """
        for storey in self._storeys:
            if storey.name == name:
                return storey
        return None

    def get_storey_by_elevation(self, elevation: float, tolerance: float = 0.01) -> Storey | None:
        """Find storey by elevation.

        Args:
            elevation: Target elevation in meters
            tolerance: Matching tolerance

        Returns:
            Matching Storey or None
        """
        for storey in self._storeys:
            if storey.elevation is not None:
                if abs(storey.elevation - elevation) <= tolerance:
                    return storey
        return None

    def mark_deleted(self) -> None:
        """Soft-delete the project."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted project."""
        self.deleted_at = None

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
