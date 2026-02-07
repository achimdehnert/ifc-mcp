"""Initial schema creation

Revision ID: 001
Revises: 
Create Date: 2024-12-01

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # ==========================================================================
    # PROJECTS
    # ==========================================================================
    op.create_table(
        "ifc_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("schema_version", sa.String(20), nullable=False),
        sa.Column("original_file_path", sa.String(1024), nullable=True),
        sa.Column("original_file_hash", sa.String(64), nullable=True, unique=True),
        sa.Column("authoring_app", sa.String(255), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("organization", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ==========================================================================
    # STOREYS
    # ==========================================================================
    op.create_table(
        "storeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("global_id", sa.String(22), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("long_name", sa.String(255), nullable=True),
        sa.Column("elevation", sa.DECIMAL(10, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "global_id", name="storeys_uk_global_id"),
    )
    op.create_index("idx_storeys_project", "storeys", ["project_id"])
    op.create_index("idx_storeys_elevation", "storeys", ["project_id", "elevation"])

    # ==========================================================================
    # ELEMENT TYPES
    # ==========================================================================
    op.create_table(
        "element_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("global_id", sa.String(22), nullable=False),
        sa.Column("ifc_class", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "global_id", name="types_uk_global_id"),
    )
    op.create_index("idx_types_project_class", "element_types", ["project_id", "ifc_class"])

    # ==========================================================================
    # BUILDING ELEMENTS
    # ==========================================================================
    op.create_table(
        "building_elements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "storey_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storeys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("element_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("global_id", sa.String(22), nullable=False),
        sa.Column("ifc_class", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("object_type", sa.String(255), nullable=True),
        sa.Column("tag", sa.String(100), nullable=True),
        # Geometry
        sa.Column("length_m", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("width_m", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("height_m", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("area_m2", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("volume_m3", sa.DECIMAL(12, 4), nullable=True),
        # Position
        sa.Column("position_x", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("position_y", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("position_z", sa.DECIMAL(12, 4), nullable=True),
        # Flags
        sa.Column("is_external", sa.Boolean, nullable=True),
        sa.Column("is_load_bearing", sa.Boolean, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "global_id", name="elements_uk_global_id"),
    )
    op.create_index("idx_elements_project_class", "building_elements", ["project_id", "ifc_class"])
    op.create_index("idx_elements_project_category", "building_elements", ["project_id", "category"])
    op.create_index("idx_elements_storey", "building_elements", ["storey_id"])
    op.create_index("idx_elements_type", "building_elements", ["type_id"])
    op.create_index("idx_elements_name", "building_elements", ["project_id", "name"])

    # ==========================================================================
    # SPACES
    # ==========================================================================
    op.create_table(
        "spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "storey_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storeys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("global_id", sa.String(22), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("long_name", sa.String(255), nullable=True),
        sa.Column("space_number", sa.String(50), nullable=True),
        # Geometry
        sa.Column("net_floor_area", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("gross_floor_area", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("net_volume", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("gross_volume", sa.DECIMAL(12, 4), nullable=True),
        sa.Column("net_height", sa.DECIMAL(10, 4), nullable=True),
        # Usage
        sa.Column("occupancy_type", sa.String(100), nullable=True),
        # Ex-Protection
        sa.Column("ex_zone", sa.String(20), server_default="none", nullable=False),
        sa.Column("hazardous_area", sa.Boolean, server_default="false", nullable=False),
        # Fire Safety
        sa.Column("fire_compartment", sa.String(100), nullable=True),
        # Finishes
        sa.Column("finish_floor", sa.String(255), nullable=True),
        sa.Column("finish_wall", sa.String(255), nullable=True),
        sa.Column("finish_ceiling", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("project_id", "global_id", name="spaces_uk_global_id"),
    )
    op.create_index("idx_spaces_project", "spaces", ["project_id"])
    op.create_index("idx_spaces_storey", "spaces", ["storey_id"])
    op.create_index("idx_spaces_ex_zone", "spaces", ["project_id", "ex_zone"])
    op.create_index("idx_spaces_number", "spaces", ["project_id", "space_number"])

    # ==========================================================================
    # PROPERTY SET DEFINITIONS
    # ==========================================================================
    op.create_table(
        "property_set_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ifc_class", sa.String(100), nullable=True),
        sa.UniqueConstraint("project_id", "name", name="pset_def_uk_name"),
    )

    # ==========================================================================
    # ELEMENT PROPERTIES
    # ==========================================================================
    op.create_table(
        "element_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pset_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("property_set_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("property_name", sa.String(255), nullable=False),
        sa.Column("property_value", sa.Text, nullable=True),
        sa.Column("data_type", sa.String(20), server_default="string", nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.UniqueConstraint(
            "element_id", "pset_definition_id", "property_name",
            name="props_uk_element_pset_prop"
        ),
    )
    op.create_index("idx_props_element", "element_properties", ["element_id"])
    op.create_index("idx_props_pset", "element_properties", ["pset_definition_id"])
    op.create_index("idx_props_name_value", "element_properties", ["property_name", "property_value"])

    # ==========================================================================
    # TYPE PROPERTIES
    # ==========================================================================
    op.create_table(
        "type_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("element_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pset_definition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("property_set_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("property_name", sa.String(255), nullable=False),
        sa.Column("property_value", sa.Text, nullable=True),
        sa.Column("data_type", sa.String(20), server_default="string", nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.UniqueConstraint(
            "type_id", "pset_definition_id", "property_name",
            name="type_props_uk"
        ),
    )
    op.create_index("idx_type_props_type", "type_properties", ["type_id"])

    # ==========================================================================
    # ELEMENT QUANTITIES
    # ==========================================================================
    op.create_table(
        "element_quantities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qto_name", sa.String(255), nullable=False),
        sa.Column("quantity_name", sa.String(255), nullable=False),
        sa.Column("quantity_value", sa.DECIMAL(18, 6), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("formula", sa.Text, nullable=True),
        sa.UniqueConstraint(
            "element_id", "qto_name", "quantity_name",
            name="qtos_uk_element_qto_qty"
        ),
    )
    op.create_index("idx_qtos_element", "element_quantities", ["element_id"])

    # ==========================================================================
    # MATERIALS
    # ==========================================================================
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ifc_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.UniqueConstraint("project_id", "name", name="materials_uk_name"),
    )
    op.create_index("idx_materials_project", "materials", ["project_id"])
    op.create_index("idx_materials_category", "materials", ["project_id", "category"])

    # ==========================================================================
    # ELEMENT MATERIALS
    # ==========================================================================
    op.create_table(
        "element_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("layer_order", sa.Integer, nullable=True),
        sa.Column("layer_thickness", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("is_ventilated", sa.Boolean, server_default="false", nullable=False),
    )
    op.create_index("idx_elem_mat_element", "element_materials", ["element_id"])
    op.create_index("idx_elem_mat_material", "element_materials", ["material_id"])

    # ==========================================================================
    # SPACE BOUNDARIES
    # ==========================================================================
    op.create_table(
        "space_boundaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "space_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("spaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("boundary_type", sa.String(50), nullable=True),
        sa.Column("physical_or_virtual", sa.String(20), nullable=True),
        sa.Column("internal_or_external", sa.String(20), nullable=True),
    )
    op.create_index("idx_space_bound_space", "space_boundaries", ["space_id"])
    op.create_index("idx_space_bound_element", "space_boundaries", ["element_id"])

    # ==========================================================================
    # ELEMENT OPENINGS
    # ==========================================================================
    op.create_table(
        "element_openings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "host_element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "filling_element_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("building_elements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "host_element_id", "filling_element_id",
            name="openings_uk"
        ),
    )
    op.create_index("idx_openings_host", "element_openings", ["host_element_id"])
    op.create_index("idx_openings_filling", "element_openings", ["filling_element_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("element_openings")
    op.drop_table("space_boundaries")
    op.drop_table("element_materials")
    op.drop_table("materials")
    op.drop_table("element_quantities")
    op.drop_table("type_properties")
    op.drop_table("element_properties")
    op.drop_table("property_set_definitions")
    op.drop_table("spaces")
    op.drop_table("building_elements")
    op.drop_table("element_types")
    op.drop_table("storeys")
    op.drop_table("ifc_projects")
