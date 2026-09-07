from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class MasterDataAcceptanceRecord(Base):
    __tablename__ = "master_data_acceptance"
    __table_args__ = (UniqueConstraint("dataset_name", "dataset_sha256", name="uq_master_data_acceptance_dataset_hash"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_name: Mapped[str] = mapped_column(String(120), index=True)
    schema_version: Mapped[str] = mapped_column(String(50))
    source_system: Mapped[str] = mapped_column(String(120))
    source_uri: Mapped[str] = mapped_column(String(500))
    authoritative_source_reference: Mapped[str] = mapped_column(String(300))
    dataset_period: Mapped[str] = mapped_column(String(7), index=True)
    dataset_sha256: Mapped[str] = mapped_column(String(64), index=True)
    row_count: Mapped[int] = mapped_column()
    duplicate_key_count: Mapped[int] = mapped_column(default=0)
    rejected_row_count: Mapped[int] = mapped_column(default=0)
    schema_valid: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(30), default="blocked", index=True)
    integrity_blocking: Mapped[bool] = mapped_column(default=True)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    submitted_by: Mapped[str] = mapped_column(String(100), index=True)
    accepted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    authority_confirmation_reference: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
