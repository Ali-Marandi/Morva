# Morva Personnel Dictionary

## Core entities

- `Person`: هویت پایه فرد
- `Employee`: رابطه استخدامی جاری/تاریخی
- `Employment`: نوع استخدام، تاریخ‌ها و وضعیت
- `OrganizationUnit`: واحد سازمانی
- `Position`: پست/شغل
- `Assignment`: انتصاب فرد به پست و محل خدمت
- `Education`: سوابق تحصیلی
- `Experience`: سابقه خدمت
- `Dependent`: افراد تحت تکفل
- `BankAccount`: حساب پرداخت
- `TaxProfile`: مشخصات مالیاتی
- `InsuranceProfile`: مشخصات بیمه
- `PensionProfile`: مشخصات صندوق/بازنشستگی
- `PersonnelOrder`: حکم کارگزینی
- `RankCase`: پرونده رتبه‌بندی

## Employment lifecycle

`candidate -> active -> suspended -> retired/terminated/deceased`

هیچ transition نباید بدون تاریخ و actor معتبر ثبت شود.

## Effective dating

برای هر وضعیت مؤثر بر حقوق، حداقل این فیلدها نگهداری می‌شوند:

- effective_from
- effective_to
- source_event_id
- source_order_id در صورت وجود
- version

## Rank values

رتبه‌ها به‌عنوان داده دامنه‌ای مستقل مدل می‌شوند:

1. آموزشیار معلم
2. مربی معلم
3. استادیار معلم
4. دانشیار معلم
5. استاد معلم

این فهرست از سند پژوهشی مروا گرفته شده و قبل از فعال‌سازی Ruleهای مالی باید با متن قانونی/آیین‌نامه جاری تطبیق و تأیید شود.
