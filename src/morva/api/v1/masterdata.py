from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import has_permission, authorize

router = APIRouter(prefix="/master-data", tags=["master-data"])


class OrganizationInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(min_length=1, max_length=30)
    parent_id: UUID | None = None
    active: bool = True


class PositionInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    occupational_group: str = Field(min_length=1, max_length=100)
    grade: int | None = None
    job_points: Decimal = Field(default=Decimal("0"), ge=0)
    full_time_educational: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    active: bool = True


def _authorize(principal: Principal, permission: str) -> None:
    if not has_permission(principal, permission):
        raise HTTPException(status_code=403, detail="required permission not granted")
    authorize(principal, permission, principal.scope, privileged=principal.role in {"admin", "auditor"})


def _org_response(row: OrganizationUnitRecord) -> dict[str, object]:
    return {
        "id": str(row.id),
        "code": row.code,
        "name": row.name,
        "kind": row.kind,
        "parent_id": str(row.parent_id) if row.parent_id else None,
        "active": row.active,
    }


def _position_response(row: PositionRecord) -> dict[str, object]:
    return {
        "id": str(row.id),
        "code": row.code,
        "title": row.title,
        "occupational_group": row.occupational_group,
        "grade": row.grade,
        "job_points": str(row.job_points),
        "full_time_educational": row.full_time_educational,
        "effective_from": row.effective_from.isoformat() if row.effective_from else None,
        "effective_to": row.effective_to.isoformat() if row.effective_to else None,
        "active": row.active,
    }


@router.get("/organizations")
def list_organizations(principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    _authorize(principal, "personnel.read")
    with SessionLocal() as session:
        rows = session.scalars(select(OrganizationUnitRecord).order_by(OrganizationUnitRecord.code)).all()
        return {"items": [_org_response(row) for row in rows]}


@router.post("/organizations", status_code=201)
def create_organization(payload: OrganizationInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    _authorize(principal, "personnel.write")
    if payload.parent_id:
        with SessionLocal() as session:
            parent = session.get(OrganizationUnitRecord, payload.parent_id)
            if parent is None:
                raise HTTPException(status_code=422, detail="parent organization not found")
            row = OrganizationUnitRecord(
                code=payload.code,
                name=payload.name,
                kind=payload.kind,
                parent_id=payload.parent_id,
                active=payload.active,
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(status_code=409, detail="organization code already exists") from exc
            append_audit_event(
                event_type="master_data.organization.created",
                entity_type="organization_unit",
                entity_id=str(row.id),
                actor_id=principal.user_id,
                payload={"code": row.code, "parent_id": str(row.parent_id)},
                reason="create organization master-data record",
                session=session,
            )
            session.commit()
            return _org_response(row)
    with SessionLocal() as session:
        row = OrganizationUnitRecord(code=payload.code, name=payload.name, kind=payload.kind, active=payload.active)
        session.add(row)
        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="organization code already exists") from exc
        append_audit_event(
            event_type="master_data.organization.created",
            entity_type="organization_unit",
            entity_id=str(row.id),
            actor_id=principal.user_id,
            payload={"code": row.code},
            reason="create organization master-data record",
            session=session,
        )
        session.commit()
        return _org_response(row)


@router.get("/positions")
def list_positions(
    principal: Principal = Depends(get_current_principal),
    effective_on: date | None = Query(default=None),
) -> dict[str, object]:
    _authorize(principal, "personnel.read")
    with SessionLocal() as session:
        statement = select(PositionRecord).order_by(PositionRecord.code)
        if effective_on is not None:
            statement = statement.where(
                PositionRecord.active.is_(True),
                or_(PositionRecord.effective_from.is_(None), PositionRecord.effective_from <= effective_on),
                or_(PositionRecord.effective_to.is_(None), PositionRecord.effective_to >= effective_on),
            )
        rows = session.scalars(statement).all()
        return {"effective_on": effective_on.isoformat() if effective_on else None, "items": [_position_response(row) for row in rows]}


@router.post("/positions", status_code=201)
def create_position(payload: PositionInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    _authorize(principal, "personnel.write")
    if payload.effective_to and payload.effective_from and payload.effective_to < payload.effective_from:
        raise HTTPException(status_code=422, detail="effective_to cannot precede effective_from")
    with SessionLocal() as session:
        row = PositionRecord(
            code=payload.code,
            title=payload.title,
            occupational_group=payload.occupational_group,
            grade=payload.grade,
            job_points=payload.job_points,
            full_time_educational=payload.full_time_educational,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            active=payload.active,
        )
        session.add(row)
        try:
            session.flush()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="position code already exists") from exc
        append_audit_event(
            event_type="master_data.position.created",
            entity_type="position",
            entity_id=str(row.id),
            actor_id=principal.user_id,
            payload={"code": row.code, "effective_from": row.effective_from.isoformat() if row.effective_from else None, "effective_to": row.effective_to.isoformat() if row.effective_to else None},
            reason="create position master-data record",
            session=session,
        )
        session.commit()
        return _position_response(row)
