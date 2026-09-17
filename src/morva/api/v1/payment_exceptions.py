from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.payment_exception_records import (
    PaymentExceptionEventRecord,
    PaymentExceptionRecord,
    PaymentExceptionRepository,
)
from morva.payroll.payment_exceptions import PaymentException, PaymentExceptionStatus, PaymentExceptionType
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import authorize

router = APIRouter(prefix="/payment-exceptions", tags=["payment-exceptions"])


class PaymentExceptionCreate(BaseModel):
    exception_id: str = Field(min_length=1, max_length=100)
    payment_item_id: str = Field(min_length=1, max_length=100)
    exception_type: PaymentExceptionType
    reason: str = Field(min_length=3, max_length=4000)


class PaymentExceptionResolve(BaseModel):
    actor: str | None = Field(default=None, min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=4000)
    evidence_ref: str = Field(min_length=1, max_length=4000)


class PaymentExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exception_id: str
    payment_item_id: str
    exception_type: str
    reason: str
    status: str
    opened_at: datetime
    resolved_at: datetime | None = None
    resolution_actor: str | None = None
    resolution_reason: str | None = None
    evidence_ref: str | None = None
    resolution_fingerprint: str | None = None


class PaymentExceptionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exception_id: str
    status: str
    actor: str
    reason: str
    evidence_ref: str
    occurred_at: datetime
    idempotency_key: str
    fingerprint: str


def _authorize(principal: Principal, permission: str) -> None:
    authorize(principal, permission, principal.scope)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PaymentExceptionResponse)
def create_payment_exception(
    payload: PaymentExceptionCreate,
    principal: Principal = Depends(get_current_principal),
) -> PaymentExceptionResponse:
    _authorize(principal, "payroll.payment.reconcile")
    with SessionLocal() as session:
        existing = session.scalar(
            select(PaymentExceptionRecord).where(PaymentExceptionRecord.exception_id == payload.exception_id.strip())
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="payment exception already exists")

        exception = PaymentException(
            exception_id=payload.exception_id.strip(),
            payment_item_id=payload.payment_item_id.strip(),
            exception_type=payload.exception_type,
            reason=payload.reason.strip(),
        )
        try:
            record = PaymentExceptionRepository(session).create(exception)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        append_audit_event(
            event_type="payment.exception.created",
            entity_type="payment_exception",
            entity_id=record.exception_id,
            actor_id=principal.user_id,
            payload={
                "payment_item_id": record.payment_item_id,
                "exception_type": record.exception_type,
            },
            reason=record.reason,
            session=session,
        )
        session.commit()
        return PaymentExceptionResponse.model_validate(record)


@router.get("", response_model=list[PaymentExceptionResponse])
def list_payment_exceptions(
    payment_item_id: str | None = None,
    include_resolved: bool = False,
    principal: Principal = Depends(get_current_principal),
) -> list[PaymentExceptionResponse]:
    _authorize(principal, "payroll.payment.reconcile")
    with SessionLocal() as session:
        query = select(PaymentExceptionRecord)
        if not include_resolved:
            query = query.where(PaymentExceptionRecord.status != PaymentExceptionStatus.RESOLVED.value)
        if payment_item_id is not None:
            query = query.where(PaymentExceptionRecord.payment_item_id == payment_item_id.strip())
        records = session.scalars(query.order_by(PaymentExceptionRecord.opened_at.asc())).all()
        return [PaymentExceptionResponse.model_validate(record) for record in records]


@router.get("/{exception_id}/events", response_model=list[PaymentExceptionEventResponse])
def list_payment_exception_events(
    exception_id: str,
    principal: Principal = Depends(get_current_principal),
) -> list[PaymentExceptionEventResponse]:
    _authorize(principal, "payroll.payment.reconcile")
    with SessionLocal() as session:
        exists = session.scalar(
            select(PaymentExceptionRecord.id).where(PaymentExceptionRecord.exception_id == exception_id.strip())
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="payment exception not found")
        events = session.scalars(
            select(PaymentExceptionEventRecord)
            .where(PaymentExceptionEventRecord.exception_id == exception_id.strip())
            .order_by(PaymentExceptionEventRecord.occurred_at.asc())
        ).all()
        return [PaymentExceptionEventResponse.model_validate(event) for event in events]


@router.post("/{exception_id}/resolve", response_model=PaymentExceptionEventResponse)
def resolve_payment_exception(
    exception_id: str,
    payload: PaymentExceptionResolve,
    idempotency_key: Annotated[str, Header(min_length=12, max_length=150, alias="Idempotency-Key")],
    principal: Principal = Depends(get_current_principal),
) -> PaymentExceptionEventResponse:
    _authorize(principal, "payroll.payment.reconcile")
    actor = (payload.actor or principal.user_id).strip()
    if actor != principal.user_id and principal.role != "admin":
        raise HTTPException(status_code=403, detail="resolution actor must match authenticated principal")

    with SessionLocal() as session:
        repository = PaymentExceptionRepository(session)
        try:
            event = repository.resolve(
                exception_id,
                actor=actor,
                reason=payload.reason,
                evidence_ref=payload.evidence_ref,
                idempotency_key=idempotency_key,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        append_audit_event(
            event_type="payment.exception.resolved",
            entity_type="payment_exception",
            entity_id=event.exception_id,
            actor_id=principal.user_id,
            payload={
                "status": event.status,
                "evidence_ref": event.evidence_ref,
                "fingerprint": event.fingerprint,
                "idempotency_key": event.idempotency_key,
            },
            reason=event.reason,
            session=session,
        )
        session.commit()
        return PaymentExceptionEventResponse.model_validate(event)
