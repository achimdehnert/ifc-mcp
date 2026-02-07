"""Application configuration.

Uses pydantic-settings for environment variable support.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be overridden via environment variables.
    Example: DATABASE_URL, DEBUG, LOG_LEVEL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Application
    # =========================================================================
    app_name: str = Field(default="ifc_mcp", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment name",
    )

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://ifc_user:changeme@localhost:5432/ifc_db",
        description="PostgreSQL connection URL (async)",
    )
    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Database connection pool size",
    )
    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Max overflow connections",
    )
    database_pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Pool timeout in seconds",
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)",
    )

    # =========================================================================
    # IFC Import
    # =========================================================================
    ifc_import_batch_size: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Batch size for IFC element import",
    )
    ifc_max_file_size_mb: int = Field(
        default=500,
        ge=10,
        le=2000,
        description="Maximum IFC file size in MB",
    )
    ifc_upload_dir: str = Field(
        default="/tmp/ifc_uploads",
        description="Directory for IFC file uploads",
    )

    # =========================================================================
    # Pagination
    # =========================================================================
    default_page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Default pagination page size",
    )
    max_page_size: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum pagination page size",
    )

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format",
    )

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if "postgresql" in v and "asyncpg" not in v:
            # Convert to async driver
            v = v.replace("postgresql://", "postgresql+asyncpg://")
            v = v.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        return v

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.database_url.replace("asyncpg", "psycopg")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
