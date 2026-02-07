"""Ex-Protection API Routes (ATEX)."""
from uuid import UUID

from fastapi import APIRouter, HTTPException

from ifc_mcp.application.services.ex_protection_service import ExProtectionService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork

router = APIRouter()


@router.get("/projects/{project_id}/ex-zones")
async def analyze_ex_zones(project_id: str) -> dict:
    """Analyze Ex-Zones (ATEX compliance).

    Args:
        project_id: Project UUID

    Returns:
        Ex-Zone analysis result
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.analyze_zones(pid)

    return {
        "project_id": str(result.project_id),
        "total_spaces": result.total_spaces,
        "hazardous_spaces": result.hazardous_spaces,
        "zones": [
            {
                "space_id": str(z.space_id),
                "space_name": z.space_name,
                "space_number": z.space_number,
                "storey_name": z.storey_name,
                "zone_type": z.zone_type,
                "is_gas_zone": z.is_gas_zone,
                "is_dust_zone": z.is_dust_zone,
                "hazard_level": z.hazard_level,
                "required_equipment_category": z.required_equipment_category,
                "volume_m3": float(z.volume_m3) if z.volume_m3 else None,
                "area_m2": float(z.area_m2) if z.area_m2 else None,
            }
            for z in result.zones
        ],
        "zone_summary": result.zone_summary,
        "volume_by_zone": {k: float(v) for k, v in result.volume_by_zone.items()},
    }


@router.get("/projects/{project_id}/fire-rating")
async def analyze_fire_rating(project_id: str) -> dict:
    """Analyze fire rating of building elements.

    Args:
        project_id: Project UUID

    Returns:
        Fire rating analysis
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        result = await service.analyze_fire_rating(pid)

    return {
        "project_id": str(result.project_id),
        "total_elements": result.total_elements,
        "elements_with_rating": result.elements_with_rating,
        "elements": [
            {
                "element_id": str(e.element_id),
                "element_name": e.element_name,
                "ifc_class": e.ifc_class,
                "storey_name": e.storey_name,
                "fire_rating": e.fire_rating,
                "fire_rating_minutes": e.fire_rating_minutes,
            }
            for e in result.elements
        ],
        "rating_summary": result.rating_summary,
        "elements_without_rating": result.elements_without_rating,
    }


@router.get("/projects/{project_id}/room-volumes")
async def get_room_volumes(project_id: str) -> dict:
    """Get room volumes for Ex-Protection calculations.

    Args:
        project_id: Project UUID

    Returns:
        Room volume data
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = ExProtectionService(uow)
        volumes = await service.calculate_room_volumes(pid)

    return {
        "project_id": str(project_id),
        "rooms": [
            {
                "space_id": str(v.space_id),
                "space_name": v.space_name,
                "space_number": v.space_number,
                "storey_name": v.storey_name,
                "net_volume_m3": float(v.net_volume_m3) if v.net_volume_m3 else None,
                "gross_volume_m3": float(v.gross_volume_m3)
                if v.gross_volume_m3
                else None,
                "net_floor_area_m2": float(v.net_floor_area_m2)
                if v.net_floor_area_m2
                else None,
                "net_height_m": float(v.net_height_m) if v.net_height_m else None,
                "ex_zone": v.ex_zone,
            }
            for v in volumes
        ],
    }
