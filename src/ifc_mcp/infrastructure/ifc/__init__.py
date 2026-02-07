"""IFC Infrastructure.

IfcOpenShell-based parsing and import services.
"""
from __future__ import annotations

from ifc_mcp.infrastructure.ifc.import_service import (
    IfcImportService,
    ImportResult,
    import_ifc_file,
)
from ifc_mcp.infrastructure.ifc.parser import (
    IfcParser,
    ParsedElement,
    ParsedMaterial,
    ParsedProject,
    ParsedProperty,
    ParsedQuantity,
    ParsedSpace,
    ParsedStorey,
    ParsedType,
)

__all__ = [
    # Parser
    "IfcParser",
    "ParsedProject",
    "ParsedStorey",
    "ParsedType",
    "ParsedElement",
    "ParsedSpace",
    "ParsedProperty",
    "ParsedQuantity",
    "ParsedMaterial",
    # Import Service
    "IfcImportService",
    "ImportResult",
    "import_ifc_file",
]
