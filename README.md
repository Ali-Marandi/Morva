# Morva Payroll Platform

سامانه جامع، قانون‌محور و قابل حسابرسی حقوق و دستمزد کارکنان آموزش‌وپرورش.

## وضعیت

نسخه توسعه فعلی: **0.4.0 Foundation/MVP Core**

مروا از یک Modular Monolith شروع می‌کند تا منطق حقوق، احکام، قوانین، کسورات، معوقات، حسابرسی و اتصال‌ها یک هسته تراکنشی منسجم داشته باشند.

## معماری

```text
Personnel -> Orders -> Rule Set -> Payroll -> Tax/Pension/Insurance
                         |              |
                         v              v
                    Audit Trail      Retro/Validation
                         |
                         v
                External Adapters (SINA/Accounting/Treasury)
```

## اصول

- Rules are versioned and effective-dated data.
- Personnel orders preserve issue/effective history.
- Payroll calculations are deterministic, explainable and fingerprinted.
- Retroactive recalculation is first-class.
- Legal references are stored alongside rules and payroll evidence.
- External systems are adapters, never the domain core.
- Demo tax/contribution policies are development fixtures only.

## اجرای API

```bash
pip install -e '.[dev]'
uvicorn morva.api.main:app --reload
```

سپس: `GET /health`

مستندات OpenAPI در `/docs` در دسترس است.

## تست

```bash
pytest -q
ruff check .
```

## توجه تولیدی

تا زمانی که Rule Pack هر سال از منابع رسمی بررسی و تأیید نشده، مروا نباید برای محاسبه حقوق واقعی استفاده شود. داده‌های قانونی باید شامل منبع، تاریخ اثر، نسخه، وضعیت بررسی و تست‌های بازگشتی باشند.
