from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base


class OrganizationUnitRecord(Base):
    __tablename__ = "organization_units"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30), index=True)
    parent_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LegalSourceRecord(Base):
    __tablename__ = "legal_sources"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    citation: Mapped[str] = mapped_column(String(300), index=True)
    issuer: Mapped[str] = mapped_column(String(200))
    adoption_date: Mapped[str] = mapped_column(String(10))
    effective_from: Mapped[str] = mapped_column(String(10))
    effective_to: Mapped[str | None] = mapped_column(String(10), nullable=True)
    document_hash: Mapped[str] = mapped_column(String(64))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)


class RuleEvidenceRecord(Base):
    __tablename__ = "rule_evidence"
    __table_args__ = (UniqueConstraint("rule_pack_version", "component_code", name="uq_rule_evidence_pack_component"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_pack_version: Mapped[str] = mapped_column(String(80), index=True)
    component_code: Mapped[str] = mapped_column(String(80), index=True)
    legal_source_id: Mapped[UUID] = mapped_column(index=True)
    issuer: Mapped[str] = mapped_column(String(200))
    article: Mapped[str] = mapped_column(String(100))
    clause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    population_scope: Mapped[str] = mapped_column(String(200))
    source_hash: Mapped[str] = mapped_column(String(64))
    regression_suite_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="review_required", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PayrollArtifactRecord(Base):
    __tablename__ = "payroll_artifacts"
    __table_args__ = (UniqueConstraint("payroll_run_id", "employee_no", name="uq_payroll_artifact_run_employee"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    personnel_snapshot_id: Mapped[UUID] = mapped_column(index=True)
    personnel_snapshot_hash: Mapped[str] = mapped_column(String(64))
    rule_pack_version: Mapped[str] = mapped_column(String(80))
    rule_pack_hash: Mapped[str] = mapped_column(String(64))
    input_hash: Mapped[str] = mapped_column(String(64))
    output_hash: Mapped[str] = mapped_column(String(64), index=True)
    gross: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    deductions: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    net: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    status: Mapped[str] = mapped_column(String(30), default="calculated", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PayslipLineRecord(Base):
    __tablename__ = "payslip_lines"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    kind: Mapped[str] = mapped_column(String(20))
    taxable: Mapped[bool] = mapped_column(Boolean, default=False)
    pensionable: Mapped[bool] = mapped_column(Boolean, default=False)
    insurable: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    legal_source_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    source_record_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)


class LifecycleEventRecord(Base):
    __tablename__ = "payroll_lifecycle_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    sequence_no: Mapped[int] = mapped_column(index=True)
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str] = mapped_column(String(100), index=True)
    organization_unit_id: Mapped[str] = mapped_column(String(50), index=True)
    reason: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(150), index=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("payroll_run_id", "sequence_no", name="uq_payroll_lifecycle_sequence"), UniqueConstraint("payroll_run_id", "idempotency_key", name="uq_payroll_lifecycle_idempotency"))


class SensitiveIdentityRecord(Base):
    __tablename__ = "sensitive_identities"
    __table_args__ = (UniqueConstraint("employee_id", name="uq_sensitive_identity_employee"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(index=True)
    national_id_ciphertext: Mapped[str] = mapped_column(Text)
    national_id_lookup_hmac: Mapped[str] = mapped_column(String(128), index=True)
    bank_account_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_account_lookup_hmac: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    key_version: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OutboxMessageRecord(Base):
    __tablename__ = "outbox_messages"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operation: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(150), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InboxMessageRecord(Base):
    __tablename__ = "inbox_messages"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_inbox_provider_external"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(150))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="received", index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IntegrationReceiptRecord(Base):
    __tablename__ = "integration_receipts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    operation: Mapped[str] = mapped_column(String(100))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(150), index=True)
    external_id: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentBatchRecord(Base):
    __tablename__ = "payment_batches"
    __table_args__ = (UniqueConstraint("payroll_run_id", name="uq_payment_batch_run"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payroll_run_id: Mapped[UUID] = mapped_column(index=True)
    batch_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="IRR")
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    beneficiary_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentItemRecord(Base):
    __tablename__ = "payment_items"
    __table_args__ = (UniqueConstraint("payment_batch_id", "employee_no", name="uq_payment_item_batch_employee"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_batch_id: Mapped[UUID] = mapped_column(index=True)
    employee_no: Mapped[str] = mapped_column(String(50), index=True)
    artifact_id: Mapped[UUID] = mapped_column(index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    currency_code: Mapped[str] = mapped_column(String(3))
    bank_account_ciphertext: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    external_payment_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BankReconciliationRecord(Base):
    __tablename__ = "bank_reconciliations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_batch_id: Mapped[UUID] = mapped_column(index=True)
    external_id: Mapped[str] = mapped_column(String(150), index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    settled_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    status: Mapped[str] = mapped_column(String(30), default="unreconciled", index=True)
    difference: Mapped[Decimal] = mapped_column(Numeric(24, 4), default=Decimal("0"))
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
