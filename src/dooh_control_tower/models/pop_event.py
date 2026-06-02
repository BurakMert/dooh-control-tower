"""Proof-of-Play impression event — one row per creative render.

Design locked in ADR-0001 (docs/adr/0001-pop-event-natural-pk-and-
denormalized-h3.md). Summary: natural composite PK, h3_r8/r9 denormalized
onto the row, daily PARTITION BY RANGE(event_date).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from dooh_control_tower.models.base import Base


class PopEvent(Base):
    """One impression. Natural-key identity (when, where, what).

    `event_date` is the partition key. Set Python-side to `event_ts.date()`;
    we don't use a generated column because the `(event_ts AT TIME ZONE
    'UTC')::date` incantation is more migration noise than the one-line
    insert-side convention is worth at this stage.

    `h3_r8` / `h3_r9` are NULL until M1.6 backfills + indexes them.
    """

    __tablename__ = "pop_event"

    event_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    event_date: Mapped[date] = mapped_column(Date, primary_key=True)
    screen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("screen.id", ondelete="CASCADE"),
        primary_key=True,
    )
    creative_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative.id", ondelete="CASCADE"),
        primary_key=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
    )
    duration_seconds: Mapped[int]
    h3_r8: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    h3_r9: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_pop_event_campaign_id_event_date_ts",
            "campaign_id",
            "event_date",
            "event_ts",
        ),
        Index(
            "ix_pop_event_screen_id_event_date",
            "screen_id",
            "event_date",
        ),
        {"postgresql_partition_by": "RANGE (event_date)"},
    )
