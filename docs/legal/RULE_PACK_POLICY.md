# Morva Rule Pack Policy

Rule Packها نسخه‌شده و تاریخ‌دار هستند. نمونه زیر فقط یک fixture توسعه‌ای است و قانون جاری محسوب نمی‌شود.

## Lifecycle

`draft -> reviewed -> approved -> published -> retired`

## Production requirements

برای publish شدن یک Rule Pack:

1. legal source ثبت شده باشد.
2. effective dates مشخص باشد.
3. scope/eligibility مشخص باشد.
4. formula/DSL اعتبارسنجی شده باشد.
5. آثار مالیات/بیمه/بازنشستگی مشخص باشد.
6. تست رگرسیون داشته باشد.
7. نمونه واقعی یا مستقل برای reconciliation داشته باشد.
8. reviewer و timestamp ثبت شده باشد.
9. hash مجموعه قوانین و نمونه‌های خروجی ثبت شود.

## 1405 note

جدول مالیات حقوق ۱۴۰۵ و سایر ضرایب سالانه باید در یک Rule Pack مستقل بارگذاری شوند؛ تغییر سال نباید کد محاسبه را تغییر دهد.

مقادیر مالیاتی موجود در fixtureهای توسعه‌ای تنها برای تست موتور هستند و نباید در محیط واقعی پرداخت استفاده شوند.
