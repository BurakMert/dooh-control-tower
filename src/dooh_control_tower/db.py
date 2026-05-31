"""Async SQLAlchemy 2.0 engine, session factory, and lifespan.

One AsyncEngine per process — created at import time so both transports
(stdio via mcp.run() and streamable-http via uvicorn) share the same module-
level singleton. Connections are opened lazily by the pool on first checkout.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Default targets the local docker-compose stack (matches .env). Override via
# `uvicorn --env-file .env` for HTTP, or via the `env` block in Claude
# Desktop's config for stdio.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://dooh:dooh-dev-only@localhost:5433/dooh_control_tower",
)


def make_engine(url: str = DATABASE_URL) -> AsyncEngine:
    return create_async_engine(
        url,
        # 5 baseline + 5 overflow = 10 max concurrent connections per worker.
        # Phase 1 single-worker dev sits far below this. Revisit at M3 (ad
        # serve) when the synthetic PoP simulator pushes real load.
        pool_size=5,
        max_overflow=5,
        # Cheap round-trip on checkout — catches connections silently killed
        # by docker restarts or postgres-side idle timeouts.
        pool_pre_ping=True,
    )


engine: AsyncEngine = make_engine()
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


@contextlib.asynccontextmanager
async def lifespan() -> AsyncIterator[None]:
    """Dispose the engine's pool on shutdown. Idempotent — safe to call twice."""
    try:
        yield
    finally:
        await engine.dispose()
