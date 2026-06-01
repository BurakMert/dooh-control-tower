"""Alembic migration environment.

Sync mode under psycopg3 — psycopg3 is dual-mode (sync + async share one URL),
so Alembic (sync) and the FastAPI/MCP app (async) use the exact same
DATABASE_URL string. This was the deciding factor for picking psycopg3 over
asyncpg in M0.6b.

GeoAlchemy2's alembic_helpers handle:
  - skipping postgis-owned tables (spatial_ref_sys, ...) in autogenerate
  - rendering Geometry/Geography columns correctly in generated migrations
  - emitting spatial indexes as `CREATE INDEX ... USING gist (...)`
"""

from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import engine_from_config, pool

# Import every model module so Base.metadata sees all tables before autogen.
from dooh_control_tower.db import DATABASE_URL
from dooh_control_tower.models import Base

config = context.config

# Override the placeholder URL in alembic.ini with the one the app uses.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Filter for autogenerate.

    The postgis/postgis image ships a TIGER geocoder in the `tiger` schema and
    its own helper tables in `public` (spatial_ref_sys). Postgres' search_path
    pulls them into the inspector's view, and Alembic would otherwise treat
    them as "removed" because they don't appear in our metadata.

    Rule: if the object exists only in the DB and not in our models (i.e.,
    reflected with no match in our metadata), leave it alone — we don't own
    it. Combined with GeoAlchemy2's helper, this keeps autogenerate focused
    on tables we declared.
    """
    if not alembic_helpers.include_object(object, name, type_, reflected, compare_to):
        return False
    if reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout — useful for review or for applying via psql."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_item=alembic_helpers.render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Open a real connection and apply migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_item=alembic_helpers.render_item,
            process_revision_directives=alembic_helpers.writer,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
