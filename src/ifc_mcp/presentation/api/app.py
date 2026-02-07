"""FastAPI Application.

REST API layer for IFC MCP Server.
Provides HTTP endpoints for all services.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ifc_mcp.infrastructure.database import init_database, close_database
from ifc_mcp.presentation.api import routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan.

    Initializes database on startup, closes on shutdown.
    """
    # Startup
    await init_database()

    yield

    # Shutdown
    await close_database()


def create_app() -> FastAPI:
    """Create FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="IFC MCP API",
        description="REST API for IFC Model Context Protocol Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS - Allow cad_hub and other frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",  # Django cad_hub
            "http://127.0.0.1:8000",
            "http://localhost:3000",  # React dev
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API v1 - Current stable version
    app.include_router(routes.projects.router, prefix="/api/v1", tags=["v1-projects"])
    app.include_router(routes.schedules.router, prefix="/api/v1", tags=["v1-schedules"])
    app.include_router(
        routes.ex_protection.router, prefix="/api/v1", tags=["v1-ex-protection"]
    )
    app.include_router(routes.german_standards.router, prefix="/api/v1", tags=["v1-german-standards"])
    
    # Legacy routes (backwards compatibility) - redirect to v1
    app.include_router(routes.projects.router, prefix="/api", tags=["projects"])
    app.include_router(routes.schedules.router, prefix="/api", tags=["schedules"])
    app.include_router(
        routes.ex_protection.router, prefix="/api", tags=["ex-protection"]
    )
    app.include_router(routes.german_standards.router, prefix="/api", tags=["german-standards"])

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "service": "ifc-mcp-api"}

    return app


# Create app instance
app = create_app()
