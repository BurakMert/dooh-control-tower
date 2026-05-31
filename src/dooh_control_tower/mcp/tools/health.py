from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import text

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.mcp.server import mcp


class ComponentStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None


class HealthCheck(BaseModel):
    status: Literal["ok", "degraded", "down"]
    timestamp: datetime
    components: list[ComponentStatus]


async def _check_postgres() -> ComponentStatus:
    # PostGIS_full_version() proves connectivity AND that the extension
    # actually loaded (the new thing M0.6 introduced). A plain SELECT 1 would
    # pass even if PostGIS weren't installed.
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT PostGIS_full_version()"))
            version = result.scalar_one()
        return ComponentStatus(name="postgres", status="ok", detail=version)
    except Exception as e:
        return ComponentStatus(
            name="postgres",
            status="down",
            detail=f"{type(e).__name__}: {e}",
        )


@mcp.tool()
async def health_check() -> HealthCheck:
    """Report the operational health of the DOOH Control Tower MCP server.

    Returns the overall status, current UTC timestamp, and a list of
    component statuses (MCP runtime, Postgres + PostGIS). Use this to verify
    the server is responsive and to identify which subsystem (if any) is
    degraded.
    """
    postgres = await _check_postgres()
    components: list[ComponentStatus] = [
        ComponentStatus(name="mcp", status="ok"),
        postgres,
    ]
    overall: Literal["ok", "degraded", "down"] = (
        "ok" if all(c.status == "ok" for c in components) else "degraded"
    )
    return HealthCheck(
        status=overall,
        timestamp=datetime.now(UTC),
        components=components,
    )
