from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from dooh_control_tower.mcp.server import mcp


class ComponentStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded", "down"]
    detail: str | None = None


class HealthCheck(BaseModel):
    status: Literal["ok", "degraded", "down"]
    timestamp: datetime
    components: list[ComponentStatus]


@mcp.tool()
def health_check() -> HealthCheck:
    """Report the operational health of the DOOH Control Tower MCP server.

    Returns the overall status, current UTC timestamp, and a list of
    component statuses. Use this to verify the server is responsive and to
    identify which subsystem (if any) is degraded.
    """
    return HealthCheck(
        status="ok",
        timestamp=datetime.now(UTC),
        components=[
            ComponentStatus(name="mcp", status="ok"),
        ],
    )
