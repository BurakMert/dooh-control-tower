"""DOOH targeting — geo + daypart eligibility rules for a campaign."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dooh_control_tower.models.base import Base

if TYPE_CHECKING:
    from dooh_control_tower.models.campaign import Campaign


class Targeting(Base):
    """Eligibility rules for one campaign — modelled 1:1.

    `geom` is `MULTIPOLYGON` (not `POLYGON`) so a single coverage area can
    be disconnected — e.g. a chain with Manhattan + Brooklyn footprint but
    skipping the East River. The seed wraps single bbox polygons as
    single-element multipolygons; M5.4 (polygon paste-in) will use this
    column natively.

    Daypart is two integer hours (UTC, 0-23). End is exclusive — so 6-22
    means "active 06:00 through 21:59:59". A full 24h flight uses 0-24,
    same-hour means inactive (handy as a "draft" sentinel until M5.3).

    JSONB-vs-table — we chose this column-shape because M3.3 (`ST_Contains`
    against screen points) is the hot read path; PostGIS spatial indexes
    over a typed geometry column beat JSONB-extracted GeoJSON for both
    speed and ergonomics.
    """

    __tablename__ = "targeting"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        unique=True,
    )
    geom: Mapped[WKBElement] = mapped_column(
        Geometry("MULTIPOLYGON", srid=4326, spatial_index=True),
    )
    daypart_start_hour: Mapped[int]
    daypart_end_hour: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="targeting"
    )
