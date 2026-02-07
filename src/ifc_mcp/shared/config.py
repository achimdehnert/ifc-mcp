"""Application configuration.

Managed with pydantic-settings, supporting environment variable overrides.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All settings can be overridden via environment variables
    with the IFC_MCP_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="IFC_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = "postgresql+asyncpg://ifc_mcp:ifc_mcp@localhost:5432/ifc_mcp"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle: int = 3600

    # =========================================================================
    # IFC Import
    # =========================================================================
    ifc_import_batch_size: int = 500
    ifc_import_max_file_size_mb: int = 500
    ifc_import_timeout_seconds: int = 600
    ifc_import_temp_dir: str = "/tmp/ifc_imports"

    # =========================================================================
    # Pagination
    # =========================================================================
    default_page_size: int = 50
    max_page_size: int = 1000

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "console"
    log_file: str | None = None

    # =========================================================================
    # Server
    # =========================================================================
    server_name: str = "ifc-mcp"
    server_version: str = "0.1.0"
    server_host: str = "0.0.0.0"
    server_port: int = 8003

    # =========================================================================
    # Export
    # =========================================================================
    export_dir: str = "/tmp/ifc_exports"
    svg_output_dir: str = "/tmp/ifc_svg"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure async driver is used."""
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = {"json", "console"}
        lower = v.lower()
        if lower not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of {valid_formats}")
        return lower


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance (cached)
    """
    return Settings()


# Module-level convenience
settings = get_settings()
