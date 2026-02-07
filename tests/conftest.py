"""Pytest configuration and fixtures."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from ifc_mcp.shared.config import Settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with in-memory or test database."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/ifc_test",
        database_echo=False,
        log_level="DEBUG",
    )
