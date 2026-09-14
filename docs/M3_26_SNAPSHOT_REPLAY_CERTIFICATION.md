# M3.26 — Snapshot-Driven Replay Certification

## هدف

M3.26 مرز بین replay فنی و replay قابل‌استناد برای retro را مشخص می‌کند. بازاجرای یک Payroll Artifact باید همان Personnel Snapshot، همان Rule Pack، همان ورودی canonical و همان خروجی fingerprinted را مبنا قرار دهد.

## قرارداد fail-closed

صدور certification فقط با مجموعه‌ای کامل از شناسه‌ها و SHA-256های immutable مجاز است:

- Payroll Artifact و دوره؛
- Personnel Snapshot شناسه/هش؛
- Rule Pack نسخه/هش؛
- input hash؛
- expected output hash و replay output hash؛
- replay calculation fingerprint؛
- timestamp دارای timezone؛
- reviewer و approver مستقل.

هر mismatch در snapshot، Rule Pack، ورودی یا خروجی باید replay را غیرقابل‌تأیید نگه دارد. وضعیت `review_required` هرگز execution-ready نیست.

## Retro boundary

این tranche هنوز هیچ دادهٔ تاریخی واقعی، نتیجهٔ retro، مبلغ قانونی یا corpus تأییدشده‌ای را وارد مخزن نمی‌کند. certification فقط بر مبنای artifact و شواهدی که قبلاً واقعاً persisted شده‌اند ممکن است.

## خروجی قطعی

`certification_fingerprint()` از metadata کامل certification یک fingerprint deterministic می‌سازد تا گواهی replay قابل تطبیق و audit باشد.

## گیت

`M3.26 snapshot replay certification gate` با Ruff و تست‌های focused اجرا می‌شود. این گیت به‌تنهایی تأیید حقوقی یا صدور مجوز پرداخت واقعی نیست.
