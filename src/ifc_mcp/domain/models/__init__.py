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
    "Project", "Storey", "IfcSchemaVersion",
    "BuildingElement", "ElementCategory", "PropertyValue", "QuantityValue", "MaterialLayer",
    "Space", "SpaceBoundary",
]
