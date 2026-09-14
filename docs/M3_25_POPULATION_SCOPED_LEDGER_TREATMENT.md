# M3.25 — Population-Scoped Ledger Treatment Activation

## هدف

M3.25 مرز اجرای treatment را بعد از M3.24 مشخص می‌کند. یک treatment مالیاتی، بازنشستگی، بیمه، وام یا قضایی فقط زمانی می‌تواند برای اجرای payroll قابل‌استفاده باشد که به‌طور همزمان به جمعیت هدف، Rule Pack 1405 و evidence fingerprint همان Rule Pack متصل باشد.

## قرارداد fail-closed

هر رکورد باید این موارد را صریحاً داشته باشد:

- شناسه و دامنه جمعیت؛
- SHA-256 جمعیت هدف؛
- نسخه Rule Pack؛
- SHA-256 مجموعه evidence معتبر M3.24؛
- source و SHA-256 سند اولیه؛
- بازه اثر؛
- زمان دریافت دارای timezone؛
- reviewer و approver مستقل؛
- regression reference؛
- پرچم‌های صریح `taxable/pensionable/insurable`.

تا زمانی که وضعیت `approved` نباشد یا fingerprint جمعیت/Rule Pack با وضعیت مورد انتظار یکسان نباشد، `execution_ready()` مقدار `False` می‌دهد.

## اصل ایمنی

این tranche هیچ نرخ، سقف، درصد، ضریب، معافیت یا فرمول قانونی را ایجاد یا استنتاج نمی‌کند. حتی یک treatment تأییدشده بدون تطابق با evidence و جمعیت فعلی قابل اجرا نیست.

## اثر عملی

این مرحله زیرساخت را از «طبقه‌بندی governance» به «activation با دامنه مشخص» نزدیک می‌کند. داده‌های واقعی کارکنان، population fingerprintهای رسمی، اسناد اولیه و approvalهای واقعی همچنان خارج از کد و وابسته به فرآیند رسمی شواهد هستند.

## گیت

`M3.25 population-scoped ledger treatment gate` با Ruff و تست‌های treatment governance و activation اجرا می‌شود.
