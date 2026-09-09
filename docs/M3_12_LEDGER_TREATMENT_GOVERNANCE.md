# M3.12 — Ledger Treatment Governance

## هدف

این tranche مرز ایمن بین «طبقه‌بندی حقوقی/مالی» و «محاسبه مبلغ» را برای پنج حوزه تعریف می‌کند:

`TAX`, `PENSION`, `INSURANCE`, `LOAN`, `COURT_ORDER`.

## اصل fail-closed

این لایه هیچ نرخ، سقف، ضریب، معافیت یا فرمول قانونی را حدس نمی‌زند. هر treatment تا زمانی که منبع اولیه، ارجاع دقیق، تاریخ اثر، reviewer مستقل، approver مستقل و شواهد regression ثبت نشده باشد، در وضعیت `review_required` باقی می‌ماند.

اجرای treatment تأییدنشده با خطای صریح متوقف می‌شود و `LedgerTreatmentCatalog.execution_ready()` در این حالت `False` برمی‌گرداند.

## کنترل‌های پیاده‌سازی‌شده

- تعریف صریح componentهای مالیاتی، بازنشستگی، بیمه، وام و دستور قضایی؛
- پرچم‌های مستقل `taxable`, `pensionable`, `insurable` بدون استنتاج ضمنی؛
- منبع و reference اجباری؛
- تاریخ اثر اجباری؛
- تفکیک وظایف reviewer و approver؛
- الزام regression-suite hash برای approval؛
- جلوگیری از ثبت treatment تکراری برای یک component؛
- گیت CI مستقل برای تست‌های این قرارداد.

## مرز این tranche

این تغییر «زیرساخت governance» را تکمیل می‌کند، نه تأیید محتوای قانونی سال ۱۴۰۵. بارگذاری و تأیید رسمی منابع اولیه و سپس تعریف treatment جمعیتیِ دقیق، مرحله بعدی است. تا آن زمان هیچ treatment جدیدی مجاز به فعال‌سازی محاسبات واقعی نیست.
