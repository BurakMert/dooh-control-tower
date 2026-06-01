"""DOOH screen — a physical placement in a network."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import DateTime, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from dooh_control_tower.models.base import Base


class Screen(Base):
    """A physical DOOH screen — a placement in a network.

    Keyed primarily by `external_id` (the network's identifier — e.g.
    'screen_001'); `id` is the internal UUID used for foreign keys.

    `geom` is the screen's point in WGS 84 / SRID 4326, GiST-indexed for
    spatial containment queries (used from M3 onward for geo targeting).

    `screen_type` is a free string for now — we'll tighten to a Postgres ENUM
    once M1.2 (synthetic generator) and M3 (targeting) settle the closed set.
    """

    __tablename__ = "screen"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    external_id: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    geom: Mapped[WKBElement] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=True),
    )
    screen_type: Mapped[str]
    resolution_width: Mapped[int]
    resolution_height: Mapped[int]
    market: Mapped[str]
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
