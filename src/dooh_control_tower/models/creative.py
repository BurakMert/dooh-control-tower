"""DOOH creative — a single ad asset belonging to one campaign."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dooh_control_tower.models.base import Base

if TYPE_CHECKING:
    from dooh_control_tower.models.campaign import Campaign


class Creative(Base):
    """An ad asset — image or video — that a campaign can serve.

    Modelled 1:N (one campaign, many creatives). Real DOOH platforms reuse
    creatives across campaigns (N:N), but for this portfolio project the
    extra join table isn't justified yet — we'll promote to N:N if M5
    actually needs it.

    `asset_url` is a placeholder URL — we don't store/serve real asset bytes;
    the lite adserver (M3) just round-robins creative metadata.
    """

    __tablename__ = "creative"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    external_id: Mapped[str] = mapped_column(unique=True)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str]
    creative_type: Mapped[str]
    duration_seconds: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    asset_url: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="creatives"
    )
