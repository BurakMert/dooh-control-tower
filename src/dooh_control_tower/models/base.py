"""Declarative base for all ORM models.

Alembic discovers tables via Base.metadata, so every model must inherit from
this Base and the model's module must be imported before alembic runs (see
src/dooh_control_tower/models/__init__.py for side-effect imports).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
