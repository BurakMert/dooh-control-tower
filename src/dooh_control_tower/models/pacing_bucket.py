"""Hourly per-campaign pacing aggregate — target vs actual."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from dooh_control_tower.models.base import Base


class PacingBucket(Base):
    """One row per (campaign, hour_ts) — the slot M6.1 rebalancer reads.

    `hour_ts` is UTC-aligned, the start of the hour. NYC-local prime-time
    framing is a render-side concern (M6.4 diagnosis panel) via
    `AT TIME ZONE 'America/New_York'`. We don't multi-region in scope, so
    no per-market timezone column.

    `target` is planned by a campaign-planner job (M6.1); `actual` is
    updated by the same rebalancer as it consumes pop_event aggregates.
    """

    __tablename__ = "pacing_bucket"

    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        primary_key=True,
    )
    hour_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    target: Mapped[int]
    actual: Mapped[int] = mapped_column(server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
