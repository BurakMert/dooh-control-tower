"""DOOH campaign — an advertiser's buy against the network."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dooh_control_tower.models.base import Base

if TYPE_CHECKING:
    from dooh_control_tower.models.creative import Creative
    from dooh_control_tower.models.targeting import Targeting


class Campaign(Base):
    """A buy from a single advertiser, with a flight window and a daily budget.

    Money is stored as integer cents — Postgres `numeric` is more precise but
    pacing math (M6.1) is all integer arithmetic and `int` keeps the wire
    simpler. We can switch to `numeric(12, 2)` if/when actual currency
    conversion lands.

    `state` is a free string — closed set is `{draft, active, paused, completed}`
    once M5.5 (`change_state`) settles it; promoting to a Postgres ENUM is a
    later migration.

    Spatial targeting and creatives are modelled as separate tables.
    `creatives` is 1:N (one campaign, many creatives). `targeting` is 1:1
    (every campaign has at most one targeting row — see `targeting.py`).
    """

    __tablename__ = "campaign"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    external_id: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    advertiser: Mapped[str]
    state: Mapped[str] = mapped_column(server_default=text("'draft'"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    daily_budget_cents: Mapped[int]
    pacing_strategy: Mapped[str] = mapped_column(server_default=text("'even'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creatives: Mapped[list["Creative"]] = relationship(
        "Creative",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    targeting: Mapped["Targeting | None"] = relationship(
        "Targeting",
        back_populates="campaign",
        cascade="all, delete-orphan",
        uselist=False,
    )
