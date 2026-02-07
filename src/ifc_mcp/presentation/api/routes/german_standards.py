"""German Standards API Routes (DIN 277, WoFlV, GAEB)."""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ifc_mcp.application.services.din277_service import DIN277Service
from ifc_mcp.application.services.gaeb_service import GAEBService
from ifc_mcp.application.services.woflv_service import WoFlVService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork

router = APIRouter()


class DIN277Request(BaseModel):
    """DIN 277 calculation request."""

    project_id: str
    bgf: float | None = None
    floor_height: float = 3.0


class WoFlVRequest(BaseModel):
    """WoFlV calculation request."""

    project_id: str
    default_hoehe: float = 2.5


class GAEBRequest(BaseModel):
    """GAEB generation request."""

    project_id: str
    projekt_nummer: str = ""
    format: str = "xml"  # "xml" or "excel"


@router.post("/din277/calculate")
async def calculate_din277(request: DIN277Request) -> dict:
    """Calculate DIN 277 areas.

    Args:
        request: DIN277Request

    Returns:
        Calculated areas according to DIN 277:2021
    """
    try:
        project_id = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = DIN277Service(uow)
        result = await service.calculate(
            project_id=project_id,
            bgf=request.bgf if request.bgf else None,
            floor_height=request.floor_height,
        )

    return result.to_dict()


@router.post("/woflv/calculate")
async def calculate_woflv(request: WoFlVRequest) -> dict:
    """Calculate WoFlV residential area.

    Args:
        request: WoFlVRequest

    Returns:
        Calculated residential area according to WoFlV
    """
    try:
        project_id = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = WoFlVService(uow)
        result = await service.calculate(
            project_id=project_id,
            default_hoehe=request.default_hoehe,
        )

    return result.to_dict()


@router.post("/gaeb/generate")
async def generate_gaeb(request: GAEBRequest) -> StreamingResponse:
    """Generate GAEB bill of quantities.

    Args:
        request: GAEBRequest

    Returns:
        GAEB XML or Excel file
    """
    try:
        project_id = UUID(request.project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        service = GAEBService(uow)
        lv = await service.generate_from_project(
            project_id=project_id,
            projekt_nummer=request.projekt_nummer,
        )

    # Generate requested format
    if request.format == "xml":
        output = service.generate_xml(lv)
        content_type = "application/xml"
        filename = f"LV_{lv.projekt_name}.x84"
    elif request.format == "excel":
        output = service.generate_excel(lv)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"LV_{lv.projekt_name}.xlsx"
    else:
        raise HTTPException(status_code=400, detail="Invalid format (xml or excel)")

    return StreamingResponse(
        output,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
