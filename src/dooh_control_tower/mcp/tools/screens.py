from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func, select

from dooh_control_tower.db import async_session_factory
from dooh_control_tower.mcp.server import mcp
from dooh_control_tower.models import Screen


class ScreenCount(BaseModel):
    count: int


class ScreenSummary(BaseModel):
    """Compact projection of a screen for tabular + map consumption.

    `lat` / `lon` are derived from the PostGIS POINT geometry via ST_Y/ST_X so
    the client doesn't need to parse WKB. Shared with `show_screen_map`.
    """

    id: UUID
    external_id: str
    name: str
    lat: float
    lon: float
    screen_type: str
    market: str


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


@mcp.tool()
async def list_screens() -> list[ScreenSummary]:
    """List every screen in the network with its position and metadata.

    Returns id, external_id, name, lat/lon (derived from the PostGIS POINT
    geometry via ST_Y/ST_X), screen_type, and market — ordered by external_id.
    Currently unfiltered; M2.3 will add geo and attribute filter parameters
    here.
    """
    async with async_session_factory() as session:
        stmt = select(
            Screen.id,
            Screen.external_id,
            Screen.name,
            func.ST_Y(Screen.geom).label("lat"),
            func.ST_X(Screen.geom).label("lon"),
            Screen.screen_type,
            Screen.market,
        ).order_by(Screen.external_id)
        result = await session.execute(stmt)
        return [ScreenSummary(**row._mapping) for row in result.all()]
