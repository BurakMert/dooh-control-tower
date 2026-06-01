"""ORM models. Importing this package registers all tables on Base.metadata.

Alembic's env.py imports this package so that autogenerate sees every model.
"""

from dooh_control_tower.models.base import Base
from dooh_control_tower.models.screen import Screen

__all__ = ["Base", "Screen"]
