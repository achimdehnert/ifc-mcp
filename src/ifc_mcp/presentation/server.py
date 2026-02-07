"""IFC MCP Server.

Main MCP server setup using FastMCP.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp.server import Server
from mcp.server.stdio import stdio_server

from ifc_mcp.infrastructure.database.connection import close_database, init_database
from ifc_mcp.presentation.tools import register_all_tools
from ifc_mcp.shared.config import settings
from ifc_mcp.shared.logging import get_logger, setup_logging

logger = get_logger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server.

    Returns:
        Configured MCP Server instance
    """
    server = Server(settings.app_name)

    # Register all tools
    register_all_tools(server)

    return server


@asynccontextmanager
async def lifespan() -> AsyncGenerator[None, None]:
    """Manage server lifecycle.

    Initializes database on startup and closes on shutdown.
    """
    logger.info("Starting IFC MCP Server", version=settings.app_version)

    # Initialize database
    try:
        await init_database()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    try:
        yield
    finally:
        # Cleanup
        await close_database()
        logger.info("Database connection closed")
        logger.info("IFC MCP Server stopped")


async def run_server() -> None:
    """Run the MCP server."""
    setup_logging()
    server = create_server()

    async with lifespan():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )


def main() -> None:
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
