# M3.27 — Three-Way Reconciliation Release Boundary

## هدف

M3.27 مرز fail-closed بین خروجی حقوق Morva، دستور/دفترداری سازمانی و settlement پرداخت را صریح می‌کند. یک batch فقط زمانی releaseable است که سه snapshot مستقل از نظر شناسه batch، تعداد کارکنان و مبالغ gross/deductions/net دقیقاً منطبق باشند.

## قرارداد

- منبع Morva مبنای مقایسه است و accounting و payment باید دقیقاً با آن match شوند.
- هر اختلاف batch، employee count یا هر مبلغ، reconciliation را مردود می‌کند.
- وضعیت reconciliation باید پیش از release به تصمیم عملیاتی/تأیید انسانی برسد؛ این گیت خودش مجوز پرداخت ایجاد نمی‌کند.
- محاسبات با `Decimal` انجام می‌شوند و هیچ نرخ، مبلغ قانونی یا دادهٔ واقعی جدیدی در این tranche اضافه نمی‌شود.

## مرز release

`ThreeWayReconciliation.assert_releaseable()` در اولین mismatch خطای سخت ایجاد می‌کند. بنابراین پرداخت یا settlement نمی‌تواند صرفاً با عبور ظاهری از یکی از سه سیستم آزاد شود.

## شواهد

تست‌های focused سناریوهای تطابق کامل، اختلاف مبلغ و اختلاف batch را پوشش می‌دهند. این tranche صرفاً integrity/reconciliation boundary نرم‌افزاری است؛ اتصال واقعی Treasury/PFM/Bank و evidence رسمی staging/pilot همچنان در صف تولید باقی می‌ماند.
