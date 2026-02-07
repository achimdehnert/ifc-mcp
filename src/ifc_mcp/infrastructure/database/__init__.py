"""Database Infrastructure.

SQLAlchemy ORM models and connection management.
"""
from __future__ import annotations

from ifc_mcp.infrastructure.database.connection import (
    close_database,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    get_session_factory,
    init_database,
)
from ifc_mcp.infrastructure.database.models import (
    Base,
    BuildingElementORM,
    ElementMaterialORM,
    ElementOpeningORM,
    ElementPropertyORM,
    ElementQuantityORM,
    ElementTypeORM,
    MaterialORM,
    ProjectORM,
    PropertySetDefinitionORM,
    SpaceBoundaryORM,
    SpaceORM,
    StoreyORM,
    TypePropertyORM,
)

__all__ = [
    # Connection
    "get_engine",
    "get_session",
    "get_session_factory",
    "init_database",
    "close_database",
    "create_tables",
    "drop_tables",
    # Models
    "Base",
    "ProjectORM",
    "StoreyORM",
    "ElementTypeORM",
    "BuildingElementORM",
    "SpaceORM",
    "PropertySetDefinitionORM",
    "ElementPropertyORM",
    "TypePropertyORM",
    "ElementQuantityORM",
    "MaterialORM",
    "ElementMaterialORM",
    "SpaceBoundaryORM",
    "ElementOpeningORM",
]
