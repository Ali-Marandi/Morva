# M3.11 — Legal Component Matrix and 1405 Rule Pack Governance

## هدف

این tranche ماتریس کامل اجزای محاسبه حقوق سال ۱۴۰۵ را به یک manifest ماشین‌خوان تبدیل می‌کند و آن را به Rule Pack سالانه متصل می‌کند.

## اصل ایمنی

این manifest به‌تنهایی هیچ قاعده‌ای را برای پرداخت واقعی فعال نمی‌کند. همه اجزا عمداً `review_required` هستند تا منبع اولیه، تاریخ اثر، دامنه مشمولان، نحوه برخورد مالیات/بیمه/بازنشستگی، شواهد regression و تأیید مستقل حقوقی/مالی ثبت شود.

## پوشش

ماتریس `docs/legal/rule-packs/1405/component-matrix-1405.yml` تمام اجزای الزامی تعریف‌شده در `REQUIRED_1405_COMPONENTS` را پوشش می‌دهد:

`JOB_RIGHT`, `INCUMBENT_RIGHT`, `JOB_ALLOWANCE`, `RANK_ALLOWANCE`, `FAMILY_ALLOWANCE`, `CHILD_ALLOWANCE`, `OVERTIME`, `TEACHING_FEE`, `REGION_WEATHER`, `TAX`, `PENSION`, `INSURANCE`, `LOAN`, `COURT_ORDER`.

## قواعد انتشار

- تفاوت سال‌های ۱۴۰۴ و ۱۴۰۵ باید با نسخه مستقل Rule Pack حفظ شود.
- منبع اولیه و وضعیت تأیید آن باید پیش از activation ثبت شود.
- treatment و سه پرچم `taxable/pensionable/insurable` نباید از fixture یا مشاهده منبع به‌صورت ضمنی استنتاج شوند.
- reviewer و approver باید مستقل باشند.
- هر تغییر حقوقی باید با Rule Pack جدید و regression evidence منتشر شود؛ نسخه قبلی برای historical replay حفظ می‌شود.

## شواهد CI

`tests/test_legal_component_matrix_1405.py` پوشش اجزا، fail-closed بودن و وجود فیلدهای حقوقی/درمانی هر جزء را کنترل می‌کند. گیت مستقل `M3.11 legal component matrix gate` همین کنترل‌ها را در CI اجرا می‌کند.

## دامنه این tranche

این تغییر، زیرساخت و پوشش ساختاری ماتریس را کامل می‌کند؛ «تأیید قانونی نهایی» همچنان وابسته به بارگذاری متن منابع اولیه و تأیید رسمی کارشناسان حقوقی و مالی است و تا آن زمان هیچ Rule تولیدی فعال محسوب نمی‌شود.
