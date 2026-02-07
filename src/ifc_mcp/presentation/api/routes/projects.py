"""Project API Routes."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from ifc_mcp.application.services.import_service import ImportService
from ifc_mcp.infrastructure.repositories.unit_of_work import UnitOfWork

router = APIRouter()


class ProjectResponse(BaseModel):
    """Project response schema."""

    id: str
    name: str
    schema_version: str
    storey_count: int
    space_count: int
    element_count: int


@router.post("/projects/import")
async def import_ifc(file: UploadFile) -> dict:
    """Import IFC file.

    Args:
        file: Uploaded IFC file

    Returns:
        Import result with project ID
    """
    if not file.filename or not file.filename.endswith((".ifc", ".IFC")):
        raise HTTPException(status_code=400, detail="File must be IFC format")

    # Save uploaded file temporarily
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        async with UnitOfWork() as uow:
            import_service = ImportService(uow)
            project = await import_service.import_file(tmp_path)
            await uow.commit()

        # Get counts
        async with UnitOfWork() as uow:
            storeys = await uow.storeys.find_by_project(project.id)
            spaces = await uow.spaces.find_by_project(project.id)
            elements = await uow.elements.find_by_project(project.id)

        return {
            "project_id": str(project.id),
            "name": project.name,
            "schema": project.schema_version.value,
            "storey_count": len(storeys),
            "space_count": len(spaces),
            "element_count": len(elements),
        }
    finally:
        tmp_path.unlink()


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> ProjectResponse:
    """Get project details.

    Args:
        project_id: Project UUID

    Returns:
        Project details
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        project = await uow.projects.get(pid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        storeys = await uow.storeys.find_by_project(pid)
        spaces = await uow.spaces.find_by_project(pid)
        elements = await uow.elements.find_by_project(pid)

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        schema_version=project.schema_version.value,
        storey_count=len(storeys),
        space_count=len(spaces),
        element_count=len(elements),
    )


@router.get("/projects")
async def list_projects() -> list[ProjectResponse]:
    """List all projects.

    Returns:
        List of projects
    """
    async with UnitOfWork() as uow:
        projects = await uow.projects.list_all()

        result = []
        for project in projects:
            if project.deleted_at:
                continue

            storeys = await uow.storeys.find_by_project(project.id)
            spaces = await uow.spaces.find_by_project(project.id)
            elements = await uow.elements.find_by_project(project.id)

            result.append(
                ProjectResponse(
                    id=str(project.id),
                    name=project.name,
                    schema_version=project.schema_version.value,
                    storey_count=len(storeys),
                    space_count=len(spaces),
                    element_count=len(elements),
                )
            )

    return result


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str) -> dict:
    """Delete project (soft delete).

    Args:
        project_id: Project UUID

    Returns:
        Deletion confirmation
    """
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    async with UnitOfWork() as uow:
        project = await uow.projects.get(pid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project.soft_delete()
        await uow.projects.add(project)
        await uow.commit()

    return {"status": "deleted", "project_id": str(pid)}
