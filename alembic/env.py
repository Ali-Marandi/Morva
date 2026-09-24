from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import (
    Column,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    engine_from_config,
    inspect,
    pool,
)

from morva.persistence.models import Base
from morva.persistence import acceptance_records  # noqa: F401
from morva.persistence import approval_records  # noqa: F401
from morva.persistence import calculation_matrix_records  # noqa: F401
from morva.persistence import core_hr_employment  # noqa: F401
from morva.persistence import core_hr_records  # noqa: F401
from morva.persistence import domain_extensions  # noqa: F401
from morva.persistence import enterprise_models  # noqa: F401
from morva.persistence import masterdata_records  # noqa: F401
from morva.persistence import evidence_submission_records  # noqa: F401
from morva.persistence import evidence_lifecycle_records  # noqa: F401
from morva.persistence import evidence_role_binding_records  # noqa: F401
from morva.persistence import integration_execution_readiness_records  # noqa: F401
from morva.persistence import independent_historical_freshness_receipt_verifications_m4_46  # noqa: F401
from morva.persistence import historical_freshness_verification_history_integrity_m4_47  # noqa: F401
from morva.persistence import payment_exception_records  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return os.getenv("MORVA_DATABASE_URL", "sqlite:///./morva.db")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _ensure_version_table_capacity(connection) -> None:
    """Keep Alembic revision storage wide enough for long revision identifiers."""
    inspector = inspect(connection)
    if not inspector.has_table("alembic_version"):
        table = Table(
            "alembic_version",
            MetaData(),
            Column("version_num", String(length=128), nullable=False),
            PrimaryKeyConstraint("version_num", name="alembic_version_pkc"),
        )
        table.create(connection)
        return

    if connection.dialect.name == "postgresql":
        for column in inspector.get_columns("alembic_version"):
            if column["name"] == "version_num":
                length = getattr(column.get("type"), "length", None)
                if length is not None and length < 128:
                    connection.exec_driver_sql(
                        "ALTER TABLE alembic_version "
                        "ALTER COLUMN version_num TYPE VARCHAR(128)"
                    )
                break


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_version_table_capacity(connection)
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
