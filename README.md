# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

## وضعیت نسخه

**Morva 1.0.0-rc1 — Production Release Candidate**

نسخه وب عمومی برای GitHub Pages آماده شده و با هر push به `main` از طریق GitHub Actions build/deploy می‌شود.

هسته سامانه، مدل دامنه، موتور قوانین، Payroll، احکام، رتبه‌بندی، معوقات، ledgerها، validation، audit، integration ports، self-service، analytics، security و عملیات PostgreSQL در repository پیاده شده‌اند.

## Web

Public web deployment target:

`https://ali-marandi.github.io/Morva/`

## معماری

```text
Personnel -> Orders -> Rule Set -> Payroll -> Tax/Pension/Insurance
                         |              |
                         v              v
                    Audit Trail      Retro/Validation
                         |
                         v
       SINA / Accounting / Treasury / Bank Adapters
                         |
                         v
                 Employee / Finance / Management UI
```

## اصول حیاتی

- Rules are versioned and effective-dated data.
- Personnel orders preserve history.
- Payroll calculations are deterministic, explainable and fingerprinted.
- Retroactive recalculation is first-class.
- Legal references travel with rules and payroll evidence.
- AI is advisory only and cannot alter legal truth or release payment.
- Real employee/payroll data never belongs in Git.

## اجرا

```bash
pip install -e '.[dev]'
uvicorn morva.api.main:app --reload
```

`GET /health` برای liveness و `GET /ready` برای readiness استفاده می‌شود.

## وب محلی

```bash
cd web
npm install
npm run dev
```

## تست Backend

```bash
python -m compileall -q src tests
ruff check .
pytest -q
```

## Build وب

```bash
cd web
npm install
npm run build
```

## Production gate

برای استفاده واقعی، همه Ruleهای فعال باید منبع اولیه، ماده/بند، تاریخ اثر، بازبین و تست رگرسیون داشته باشند؛ نمونه واقعی هر population باید line-by-line با خروجی مروا reconcile شود؛ endpoint و credential سامانه‌های بیرونی باید در محیط غیرتولیدی تست شوند؛ و backup/PITR، load، امنیت و SoD باید تأیید شده باشند.

Rule Packهای 1405 که هنوز `review_required` هستند عمداً فعال نمی‌شوند.

## مستندات

- `docs/IMPLEMENTATION_MATRIX.md`
- `docs/PRODUCTION_READINESS.md`
- `docs/RELEASE_1_0.md`
- `docs/ops/PRODUCTION_RUNBOOK.md`
- `docs/legal/LAW_CATALOG.md`
