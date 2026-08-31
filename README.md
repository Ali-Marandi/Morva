# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

## Architecture

Morva starts as a modular monolith. Personnel, organization, orders, rules, payroll, taxation, pension, insurance, budgeting, workflow, audit and integrations are explicit domain modules.

## Principles

- Rules are versioned data, not hard-coded business logic.
- Effective-dated orders preserve history.
- Every payroll result is explainable and reproducible.
- Retroactive recalculation is a first-class capability.
- External systems are adapters, never the domain core.

## Initial stack

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL, pytest and Ruff.

## Development

```bash
pip install -e '.[dev]'
uvicorn morva.api.main:app --reload
pytest
```
