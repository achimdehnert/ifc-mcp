"""SQLAlchemy ORM Models.

Maps domain entities to database tables.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func


# =============================================================================
# Base Class
# =============================================================================


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# =============================================================================
# Enum Types (matching PostgreSQL enums)
# =============================================================================


class IfcSchemaVersionEnum(str, Enum):
    """IFC Schema versions."""

    IFC2X3 = "IFC2X3"
    IFC4 = "IFC4"
    IFC4X1 = "IFC4X1"
    IFC4X2 = "IFC4X2"
    IFC4X3 = "IFC4X3"


class ElementCategoryEnum(str, Enum):
    """Element categories."""

    wall = "wall"
    wall_standard_case = "wall_standard_case"
    door = "door"
    window = "window"
    slab = "slab"
    roof_slab = "roof_slab"
    column = "column"
    beam = "beam"
    stair = "stair"
    ramp = "ramp"
    curtain_wall = "curtain_wall"
    covering = "covering"
    space = "space"
    opening = "opening"
    railing = "railing"
    furniture = "furniture"
    equipment = "equipment"
    distribution_element = "distribution_element"
    other = "other"


class ExZoneEnum(str, Enum):
    """Ex-Zone classifications."""

    zone_0 = "zone_0"
    zone_1 = "zone_1"
    zone_2 = "zone_2"
    zone_20 = "zone_20"
    zone_21 = "zone_21"
    zone_22 = "zone_22"
    none = "none"


class PropertyDataTypeEnum(str, Enum):
    """Property data types."""

    string = "string"
    integer = "integer"
    real = "real"
    boolean = "boolean"
    logical = "logical"
    identifier = "identifier"
    label = "label"
    text = "text"


# =============================================================================
# ORM Models
# =============================================================================


class ProjectORM(Base):
    """IFC Project table."""

    __tablename__ = "ifc_projects"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    original_file_path: Mapped[str | None] = mapped_column(String(1024))
    original_file_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    authoring_app: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    storeys: Mapped[list["StoreyORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="StoreyORM.elevation",
    )
    elements: Mapped[list["BuildingElementORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    spaces: Mapped[list["SpaceORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    element_types: Mapped[list["ElementTypeORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    materials: Mapped[list["MaterialORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    pset_definitions: Mapped[list["PropertySetDefinitionORM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class StoreyORM(Base):
    """Building storey table."""

    __tablename__ = "storeys"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    global_id: Mapped[str] = mapped_column(String(22), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    long_name: Mapped[str | None] = mapped_column(String(255))
    elevation: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="storeys")
    elements: Mapped[list["BuildingElementORM"]] = relationship(
        back_populates="storey"
    )
    spaces: Mapped[list["SpaceORM"]] = relationship(back_populates="storey")

    __table_args__ = (
        UniqueConstraint("project_id", "global_id", name="storeys_uk_global_id"),
        Index("idx_storeys_project", "project_id"),
        Index("idx_storeys_elevation", "project_id", "elevation"),
    )


class ElementTypeORM(Base):
    """Element type table (IfcWallType, etc.)."""

    __tablename__ = "element_types"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    global_id: Mapped[str] = mapped_column(String(22), nullable=False)
    ifc_class: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="element_types")
    elements: Mapped[list["BuildingElementORM"]] = relationship(
        back_populates="element_type"
    )
    properties: Mapped[list["TypePropertyORM"]] = relationship(
        back_populates="element_type",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "global_id", name="types_uk_global_id"),
        Index("idx_types_project_class", "project_id", "ifc_class"),
    )


class BuildingElementORM(Base):
    """Building element table."""

    __tablename__ = "building_elements"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    storey_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("storeys.id", ondelete="SET NULL"),
    )
    type_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("element_types.id", ondelete="SET NULL"),
    )

    global_id: Mapped[str] = mapped_column(String(22), nullable=False)
    ifc_class: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str | None] = mapped_column(String(255))
    tag: Mapped[str | None] = mapped_column(String(100))

    # Geometry (denormalized)
    length_m: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))
    width_m: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))
    height_m: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))
    area_m2: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    volume_m3: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))

    # Position
    position_x: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    position_y: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    position_z: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))

    # Flags
    is_external: Mapped[bool | None] = mapped_column(Boolean)
    is_load_bearing: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="elements")
    storey: Mapped["StoreyORM | None"] = relationship(back_populates="elements")
    element_type: Mapped["ElementTypeORM | None"] = relationship(
        back_populates="elements"
    )
    properties: Mapped[list["ElementPropertyORM"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
    )
    quantities: Mapped[list["ElementQuantityORM"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
    )
    materials: Mapped[list["ElementMaterialORM"]] = relationship(
        back_populates="element",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "global_id", name="elements_uk_global_id"),
        Index("idx_elements_project_class", "project_id", "ifc_class"),
        Index("idx_elements_project_category", "project_id", "category"),
        Index("idx_elements_storey", "storey_id"),
        Index("idx_elements_type", "type_id"),
        Index("idx_elements_name", "project_id", "name"),
    )


class SpaceORM(Base):
    """Space/room table."""

    __tablename__ = "spaces"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    storey_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("storeys.id", ondelete="SET NULL"),
    )
    element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )

    global_id: Mapped[str] = mapped_column(String(22), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    long_name: Mapped[str | None] = mapped_column(String(255))
    space_number: Mapped[str | None] = mapped_column(String(50))

    # Geometry
    net_floor_area: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    gross_floor_area: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    net_volume: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    gross_volume: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 4))
    net_height: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))

    # Usage
    occupancy_type: Mapped[str | None] = mapped_column(String(100))

    # Ex-Protection
    ex_zone: Mapped[str] = mapped_column(String(20), default="none")
    hazardous_area: Mapped[bool] = mapped_column(Boolean, default=False)

    # Fire Safety
    fire_compartment: Mapped[str | None] = mapped_column(String(100))

    # Finishes
    finish_floor: Mapped[str | None] = mapped_column(String(255))
    finish_wall: Mapped[str | None] = mapped_column(String(255))
    finish_ceiling: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="spaces")
    storey: Mapped["StoreyORM | None"] = relationship(back_populates="spaces")
    boundaries: Mapped[list["SpaceBoundaryORM"]] = relationship(
        back_populates="space",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "global_id", name="spaces_uk_global_id"),
        Index("idx_spaces_project", "project_id"),
        Index("idx_spaces_storey", "storey_id"),
        Index("idx_spaces_ex_zone", "project_id", "ex_zone"),
        Index("idx_spaces_number", "project_id", "space_number"),
    )


# =============================================================================
# Property/Quantity Tables
# =============================================================================


class PropertySetDefinitionORM(Base):
    """Property set definition table."""

    __tablename__ = "property_set_definitions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ifc_class: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="pset_definitions")
    element_properties: Mapped[list["ElementPropertyORM"]] = relationship(
        back_populates="pset_definition"
    )
    type_properties: Mapped[list["TypePropertyORM"]] = relationship(
        back_populates="pset_definition"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="pset_def_uk_name"),
    )


class ElementPropertyORM(Base):
    """Element property table (EAV pattern)."""

    __tablename__ = "element_properties"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    pset_definition_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property_set_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )

    property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    property_value: Mapped[str | None] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(20), default="string")
    unit: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    element: Mapped["BuildingElementORM"] = relationship(back_populates="properties")
    pset_definition: Mapped["PropertySetDefinitionORM"] = relationship(
        back_populates="element_properties"
    )

    __table_args__ = (
        UniqueConstraint(
            "element_id", "pset_definition_id", "property_name",
            name="props_uk_element_pset_prop"
        ),
        Index("idx_props_element", "element_id"),
        Index("idx_props_pset", "pset_definition_id"),
        Index("idx_props_name_value", "property_name", "property_value"),
    )


class TypePropertyORM(Base):
    """Type property table."""

    __tablename__ = "type_properties"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    type_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("element_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    pset_definition_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("property_set_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )

    property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    property_value: Mapped[str | None] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(20), default="string")
    unit: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    element_type: Mapped["ElementTypeORM"] = relationship(back_populates="properties")
    pset_definition: Mapped["PropertySetDefinitionORM"] = relationship(
        back_populates="type_properties"
    )

    __table_args__ = (
        UniqueConstraint(
            "type_id", "pset_definition_id", "property_name",
            name="type_props_uk"
        ),
        Index("idx_type_props_type", "type_id"),
    )


class ElementQuantityORM(Base):
    """Element quantity table."""

    __tablename__ = "element_quantities"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )

    qto_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity_value: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 6))
    unit: Mapped[str | None] = mapped_column(String(50))
    formula: Mapped[str | None] = mapped_column(Text)

    # Relationships
    element: Mapped["BuildingElementORM"] = relationship(back_populates="quantities")

    __table_args__ = (
        UniqueConstraint(
            "element_id", "qto_name", "quantity_name",
            name="qtos_uk_element_qto_qty"
        ),
        Index("idx_qtos_element", "element_id"),
    )


# =============================================================================
# Material Tables
# =============================================================================


class MaterialORM(Base):
    """Material table."""

    __tablename__ = "materials"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ifc_projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    project: Mapped["ProjectORM"] = relationship(back_populates="materials")
    element_materials: Mapped[list["ElementMaterialORM"]] = relationship(
        back_populates="material"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="materials_uk_name"),
        Index("idx_materials_project", "project_id"),
        Index("idx_materials_category", "project_id", "category"),
    )


class ElementMaterialORM(Base):
    """Element-Material association table."""

    __tablename__ = "element_materials"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )

    layer_order: Mapped[int | None] = mapped_column(Integer)
    layer_thickness: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))
    is_ventilated: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    element: Mapped["BuildingElementORM"] = relationship(back_populates="materials")
    material: Mapped["MaterialORM"] = relationship(back_populates="element_materials")

    __table_args__ = (
        Index("idx_elem_mat_element", "element_id"),
        Index("idx_elem_mat_material", "material_id"),
    )


# =============================================================================
# Relationship Tables
# =============================================================================


class SpaceBoundaryORM(Base):
    """Space boundary table."""

    __tablename__ = "space_boundaries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    space_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )

    boundary_type: Mapped[str | None] = mapped_column(String(50))
    physical_or_virtual: Mapped[str | None] = mapped_column(String(20))
    internal_or_external: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    space: Mapped["SpaceORM"] = relationship(back_populates="boundaries")

    __table_args__ = (
        Index("idx_space_bound_space", "space_id"),
        Index("idx_space_bound_element", "element_id"),
    )


class ElementOpeningORM(Base):
    """Element opening association (doors/windows in walls)."""

    __tablename__ = "element_openings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    host_element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )
    filling_element_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("building_elements.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "host_element_id", "filling_element_id",
            name="openings_uk"
        ),
        Index("idx_openings_host", "host_element_id"),
        Index("idx_openings_filling", "filling_element_id"),
    )
