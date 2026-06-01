from pydantic import BaseModel
from sqlalchemy import func, select

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.mcp.server import mcp
from dooh_control_tower.models import Screen


class ScreenCount(BaseModel):
    count: int


@mcp.tool()
async def count_screens() -> ScreenCount:
    """Count the number of screens currently in the network.

    Will be 0 until M1.2 (synthetic generator) populates the table. Use this
    to verify the agent can reach the screen table through the connection
    pool, and to gut-check what's been generated after seeding.
    """
    async with async_session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Screen))
        return ScreenCount(count=result.scalar_one())
