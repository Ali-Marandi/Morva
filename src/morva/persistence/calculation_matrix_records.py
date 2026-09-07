from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class CalculationMatrixRecord(Base):
    __tablename__ = "calculation_matrix"
    __table_args__ = (
        UniqueConstraint(
            "rule_pack_version",
            "component_code",
            "population_scope",
            name="uq_calculation_matrix_pack_component_population",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_pack_version: Mapped[str] = mapped_column(String(80), index=True)
    component_code: Mapped[str] = mapped_column(String(80), index=True)
    population_scope: Mapped[str] = mapped_column(String(200), index=True)
    treatment: Mapped[str] = mapped_column(String(20))
    expression: Mapped[dict] = mapped_column(JSON, default=dict)
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    legal_source_id: Mapped[UUID] = mapped_column(index=True)
    legal_article: Mapped[str] = mapped_column(String(100))
    legal_clause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    taxable: Mapped[bool] = mapped_column(Boolean, default=False)
    pensionable: Mapped[bool] = mapped_column(Boolean, default=False)
    insurable: Mapped[bool] = mapped_column(Boolean, default=False)
    regression_suite_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
