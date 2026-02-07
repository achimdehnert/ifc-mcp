"""Domain Models.

Core domain entities representing the IFC building model.
"""
from __future__ import annotations

from ifc_mcp.domain.models.element import (
    BuildingElement,
    ElementCategory,
    MaterialLayer,
    PropertyValue,
    QuantityValue,
)
from ifc_mcp.domain.models.project import (
    IfcSchemaVersion,
    Project,
    Storey,
)
from ifc_mcp.domain.models.space import (
    Space,
    SpaceBoundary,
)

__all__ = [
    # Project
    "Project",
    "Storey",
    "IfcSchemaVersion",
    # Element
    "BuildingElement",
    "ElementCategory",
    "PropertyValue",
    "QuantityValue",
    "MaterialLayer",
    # Space
    "Space",
    "SpaceBoundary",
]
