"""Application services.

All business logic services for IFC analysis.
"""
from __future__ import annotations

# Re-export services for convenient imports
# These will be available as:
#   from ifc_mcp.application.services import MaterialTakeoffService

__all__ = [
    "AccessibilityCheckService",
    "DIN277Service",
    "ExcelExportService",
    "ExProtectionService",
    "FireCompartmentMapService",
    "FireEscapePlanService",
    "GAEBService",
    "MaterialTakeoffService",
    "ModelCheckService",
    "ScheduleService",
    "WoFlVService",
]


def __getattr__(name: str):
    """Lazy imports for services."""
    if name == "AccessibilityCheckService":
        from ifc_mcp.application.services.accessibility_check_service import AccessibilityCheckService
        return AccessibilityCheckService
    elif name == "DIN277Service":
        from ifc_mcp.application.services.din277_service import DIN277Service
        return DIN277Service
    elif name == "ExcelExportService":
        from ifc_mcp.application.services.excel_export_service import ExcelExportService
        return ExcelExportService
    elif name == "ExProtectionService":
        from ifc_mcp.application.services.ex_protection_service import ExProtectionService
        return ExProtectionService
    elif name == "FireCompartmentMapService":
        from ifc_mcp.application.services.fire_compartment_service import FireCompartmentMapService
        return FireCompartmentMapService
    elif name == "FireEscapePlanService":
        from ifc_mcp.application.services.fire_escape_plan_service import FireEscapePlanService
        return FireEscapePlanService
    elif name == "GAEBService":
        from ifc_mcp.application.services.gaeb_service import GAEBService
        return GAEBService
    elif name == "MaterialTakeoffService":
        from ifc_mcp.application.services.material_takeoff_service import MaterialTakeoffService
        return MaterialTakeoffService
    elif name == "ModelCheckService":
        from ifc_mcp.application.services.model_check_service import ModelCheckService
        return ModelCheckService
    elif name == "ScheduleService":
        from ifc_mcp.application.services.schedule_service import ScheduleService
        return ScheduleService
    elif name == "WoFlVService":
        from ifc_mcp.application.services.woflv_service import WoFlVService
        return WoFlVService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
