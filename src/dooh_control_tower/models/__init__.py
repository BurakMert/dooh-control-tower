"""ORM models. Importing this package registers all tables on Base.metadata.

Alembic's env.py imports this package so that autogenerate sees every model.
"""

from dooh_control_tower.models.base import Base
from dooh_control_tower.models.campaign import Campaign
from dooh_control_tower.models.creative import Creative
from dooh_control_tower.models.screen import Screen
from dooh_control_tower.models.targeting import Targeting

__all__ = ["Base", "Campaign", "Creative", "Screen", "Targeting"]
