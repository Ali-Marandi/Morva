from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from morva.rules import RuleContext, RuleDefinition, RuleEngine

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    effective_from: date
    effective_to: date | None = None
    expression: dict[str, Any] | None = None
    legal_reference: str | None = None
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False


class EvaluateIn(BaseModel):
    rule: RuleIn
    effective_date: date
    values: dict[str, str] = Field(default_factory=dict)


@router.post("/evaluate")
def evaluate(payload: EvaluateIn) -> dict[str, object]:
    if payload.rule.expression is None:
        raise HTTPException(status_code=422, detail="evaluate requires a persisted-safe expression")
    try:
        values = {key: Decimal(value) for key, value in payload.values.items()}
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail="all rule values must be decimal strings") from exc
    engine = RuleEngine([
        RuleDefinition(
            code=payload.rule.code,
            title=payload.rule.title,
            effective_from=payload.rule.effective_from,
            effective_to=payload.rule.effective_to,
            taxable=payload.rule.taxable,
            pensionable=payload.rule.pensionable,
            insurable=payload.rule.insurable,
            expression=payload.rule.expression,
            legal_reference=payload.rule.legal_reference,
        )
    ])
    result = engine.calculate(payload.rule.code, RuleContext(payload.effective_date, values))
    return {
        "code": result.code,
        "amount": str(result.amount),
        "explanation": result.explanation,
        "legal_reference": result.legal_reference,
    }
