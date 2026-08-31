# Morva Payroll Platform

**مروا** یک پلتفرم جامع، قانون‌محور و قابل حسابرسی برای مدیریت پرسنل، احکام و حقوق و دستمزد است که با تمرکز بر نیازهای آموزش‌وپرورش ایران طراحی می‌شود.

> وضعیت فعلی: **Foundation / MVP قابل توسعه**. قواعد قانونی واقعی فقط پس از ورود به کاتالوگ مقررات، بازبینی کارشناسی و ثبت نسخه مؤثر در سیستم باید فعال شوند.

## Core capabilities

- پرونده و وضعیت استخدامی کارکنان
- احکام مؤثر بر تاریخ و حفظ تاریخچه
- Rule Engine نسخه‌بندی‌شده با توضیح محاسبه
- Payroll deterministic با fingerprint بازتولیدپذیر
- مبانی مالیات، بیمه و بازنشستگی به‌صورت policy
- محاسبه معوقات و تفاوت ماهانه
- PostgreSQL/SQLAlchemy persistence
- Audit trail پایه
- API نسخه‌دار FastAPI
- داشبورد RTL فارسی React

## Architecture

Morva starts as a modular monolith. Domain boundaries are explicit so high-volume or independently scaled components can later become services without changing the domain contracts.

```text
Web / Admin / Employee Portal
            |
         FastAPI
            |
  +---------+----------+
  |         |          |
Personnel  Rules     Payroll
  |         |          |
Orders   Legal Data  Tax/Pension/Insurance
  |         |          |
  +---------+----------+
            |
        PostgreSQL
            |
      Audit / Integrations
```

## Non-negotiable principles

1. Rules are versioned data; legal logic is not scattered through application code.
2. Effective dates are first-class; corrections create history instead of overwriting it.
3. Every payroll result is explainable, fingerprinted and reproducible.
4. Retroactive recalculation is a core payroll operation.
5. External government systems are adapters around Morva, not the domain core.
6. AI may identify anomalies or assist analysis, but never becomes the source of legal payroll truth.

## Development

```bash
pip install -e '.[dev]'
uvicorn morva.api.app:app --reload
pytest -q
ruff check .
```

For PostgreSQL-backed local development:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000` and OpenAPI documentation at `/docs`.

## Web dashboard

```bash
cd web
npm install
npm run dev
```

## API examples

`POST /api/v1/payroll/calculate` calculates a deterministic payroll result from supplied lines.

`POST /api/v1/rules/evaluate` evaluates a persisted-safe expression with an effective date and returns an explanation plus legal reference.

## Safety and legal data

The repository currently contains development/demo policy examples only. Before production use, each Iranian payroll rule must be loaded from a reviewed legal source with effective dates, scope, prerequisites, tax/insurance/pension flags and an audit reference.
