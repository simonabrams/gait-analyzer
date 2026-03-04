import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base

config = context.config
if config.config_file_name is not None:
    file_config = config.get_section(config.config_ini_section) or {}
    url = file_config.get("sqlalchemy.url")
    if not url or url == "driver://user:pass@localhost/dbname":
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/gait_analyzer",
        )
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
