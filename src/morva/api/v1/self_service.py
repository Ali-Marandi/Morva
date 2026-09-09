from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import PayslipLineRecord, PayrollArtifactRecord
from morva.persistence.models import EmployeeRecord, PersonnelOrderRecord, PersonnelSnapshotRecord, PayrollRunRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import authorize

router = APIRouter(prefix="/self", tags=["employee-self-service"])

_VISIBLE_PAYROLL_STATUSES = {
    "approved",
    "frozen",
    "exported",
    "submitted",
    "payment_confirmed",
    "reconciled",
}


def _current_employee(session, principal: Principal) -> EmployeeRecord:
    employee = session.scalar(
        select(EmployeeRecord).where(
            (EmployeeRecord.employee_no == principal.user_id)
            | (EmployeeRecord.source_employee_key == principal.user_id)
        )
    )
    if employee is None:
        raise HTTPException(status_code=404, detail="employee identity is not mapped to a personnel record")
    authorize(principal, "self.read", principal.scope)
    return employee


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_payslip_pdf(
    *,
    employee_no: str,
    period: str,
    currency: str,
    gross: Decimal,
    deductions: Decimal,
    net: Decimal,
    lines: list[PayslipLineRecord],
) -> bytes:
    rows = [
        "Morva Payslip",
        f"Employee: {employee_no}",
        f"Period: {period}",
        f"Currency: {currency}",
        f"Gross: {gross}",
        f"Deductions: {deductions}",
        f"Net: {net}",
        "",
        "Code | Title | Amount | Kind",
    ]
    for line in sorted(lines, key=lambda item: item.line_sequence):
        rows.append(f"{line.code} | {line.title} | {line.amount} | {line.kind}")

    stream = BytesIO()
    stream.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>endobj\n")
    objects.append(b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    commands = [b"BT", b"/F1 9 Tf", b"40 800 Td"]
    for index, row in enumerate(rows):
        if index:
            commands.append(b"0 -14 Td")
        commands.append(f"({_pdf_escape(row[:110])}) Tj".encode("latin-1", errors="replace"))
    commands.append(b"ET")
    content = b"\n".join(commands)
    objects.append(f"5 0 obj<< /Length {len(content)} >>stream\n".encode() + content + b"\nendstream endobj\n")

    offsets: list[int] = [0]
    for obj in objects:
        offsets.append(stream.tell())
        stream.write(obj)
    xref = stream.tell()
    stream.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        stream.write(f"{offset:010d} 00000 n \n".encode())
    stream.write(f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return stream.getvalue()


@router.get("/profile")
def get_self_profile(principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _current_employee(session, principal)
        return {
            "employee_no": employee.employee_no,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "employment_type": employee.employment_type,
            "status": employee.status,
            "organization_unit_id": employee.organization_unit_id,
            "position_id": employee.position_id,
            "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
        }


@router.get("/payslips")
def list_self_payslips(
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    principal: Principal = Depends(get_current_principal),
) -> list[dict[str, object]]:
    with SessionLocal() as session:
        employee = _current_employee(session, principal)
        stmt = (
            select(PayrollArtifactRecord, PayrollRunRecord)
            .join(PayrollRunRecord, PayrollRunRecord.id == PayrollArtifactRecord.payroll_run_id)
            .where(
                PayrollArtifactRecord.employee_no == employee.employee_no,
                PayrollRunRecord.status.in_(_VISIBLE_PAYROLL_STATUSES),
            )
            .order_by(PayrollArtifactRecord.period.desc())
        )
        if period:
            stmt = stmt.where(PayrollArtifactRecord.period == period)
        rows = session.execute(stmt).all()
        return [
            {
                "artifact_id": str(artifact.id),
                "period": artifact.period,
                "currency_code": artifact.currency_code,
                "gross": str(artifact.gross),
                "deductions": str(artifact.deductions),
                "net": str(artifact.net),
                "status": run.status,
                "personnel_snapshot_hash": artifact.personnel_snapshot_hash,
                "rule_pack_version": artifact.rule_pack_version,
                "output_hash": artifact.output_hash,
            }
            for artifact, run in rows
        ]


@router.get("/payslips/{artifact_id}")
def get_self_payslip(artifact_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _current_employee(session, principal)
        row = session.execute(
            select(PayrollArtifactRecord, PayrollRunRecord)
            .join(PayrollRunRecord, PayrollRunRecord.id == PayrollArtifactRecord.payroll_run_id)
            .where(PayrollArtifactRecord.id == artifact_id)
        ).first()
        if row is None or row[0].employee_no != employee.employee_no:
            raise HTTPException(status_code=404, detail="payslip not found")
        artifact, run = row
        if run.status not in _VISIBLE_PAYROLL_STATUSES:
            raise HTTPException(status_code=409, detail="payslip is not yet available to the employee")
        snapshot = session.get(PersonnelSnapshotRecord, artifact.personnel_snapshot_id)
        if snapshot is None or snapshot.snapshot_hash != artifact.personnel_snapshot_hash:
            raise HTTPException(status_code=423, detail="payslip provenance verification failed")
        lines = session.scalars(
            select(PayslipLineRecord)
            .where(PayslipLineRecord.artifact_id == artifact.id)
            .order_by(PayslipLineRecord.line_sequence.asc())
        ).all()
        return {
            "artifact_id": str(artifact.id),
            "employee_no": artifact.employee_no,
            "period": artifact.period,
            "currency_code": artifact.currency_code,
            "gross": str(artifact.gross),
            "deductions": str(artifact.deductions),
            "net": str(artifact.net),
            "status": run.status,
            "personnel_snapshot_id": str(snapshot.id),
            "personnel_snapshot_hash": snapshot.snapshot_hash,
            "rule_pack_version": artifact.rule_pack_version,
            "rule_pack_hash": artifact.rule_pack_hash,
            "input_hash": artifact.input_hash,
            "output_hash": artifact.output_hash,
            "lines": [
                {
                    "sequence": line.line_sequence,
                    "code": line.code,
                    "title": line.title,
                    "amount": str(line.amount),
                    "kind": line.kind,
                    "taxable": line.taxable,
                    "pensionable": line.pensionable,
                    "insurable": line.insurable,
                    "rule_code": line.rule_code,
                    "legal_source_id": str(line.legal_source_id) if line.legal_source_id else None,
                    "explanation": line.explanation,
                }
                for line in lines
            ],
        }


@router.get("/payslips/{artifact_id}/pdf")
def download_self_payslip_pdf(artifact_id: UUID, principal: Principal = Depends(get_current_principal)) -> Response:
    with SessionLocal() as session:
        employee = _current_employee(session, principal)
        row = session.execute(
            select(PayrollArtifactRecord, PayrollRunRecord)
            .join(PayrollRunRecord, PayrollRunRecord.id == PayrollArtifactRecord.payroll_run_id)
            .where(PayrollArtifactRecord.id == artifact_id)
        ).first()
        if row is None or row[0].employee_no != employee.employee_no:
            raise HTTPException(status_code=404, detail="payslip not found")
        artifact, run = row
        if run.status not in _VISIBLE_PAYROLL_STATUSES:
            raise HTTPException(status_code=409, detail="payslip is not yet available to the employee")
        snapshot = session.get(PersonnelSnapshotRecord, artifact.personnel_snapshot_id)
        if snapshot is None or snapshot.snapshot_hash != artifact.personnel_snapshot_hash:
            raise HTTPException(status_code=423, detail="payslip provenance verification failed")
        lines = session.scalars(
            select(PayslipLineRecord)
            .where(PayslipLineRecord.artifact_id == artifact.id)
            .order_by(PayslipLineRecord.line_sequence.asc())
        ).all()
        append_audit_event(
            event_type="self.payslip.downloaded",
            entity_type="payroll_artifact",
            entity_id=str(artifact.id),
            actor_id=principal.user_id,
            payload={"employee_no": employee.employee_no, "period": artifact.period, "output_hash": artifact.output_hash},
            reason="employee self-service payslip download",
            session=session,
        )
        session.commit()
        pdf = build_payslip_pdf(
            employee_no=employee.employee_no,
            period=artifact.period,
            currency=artifact.currency_code,
            gross=artifact.gross,
            deductions=artifact.deductions,
            net=artifact.net,
            lines=lines,
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="payslip-{artifact.period}-{employee.employee_no}.pdf"'},
        )


@router.get("/orders")
def list_self_orders(principal: Principal = Depends(get_current_principal)) -> list[dict[str, object]]:
    with SessionLocal() as session:
        employee = _current_employee(session, principal)
        orders = session.scalars(
            select(PersonnelOrderRecord)
            .where(PersonnelOrderRecord.employee_no == employee.employee_no)
            .order_by(PersonnelOrderRecord.effective_date.desc())
        ).all()
        return [
            {
                "order_no": order.order_no,
                "order_type": order.order_type,
                "issue_date": order.issue_date.isoformat(),
                "effective_date": order.effective_date.isoformat(),
                "legal_reference": order.legal_reference,
                "reason": order.reason,
            }
            for order in orders
        ]
