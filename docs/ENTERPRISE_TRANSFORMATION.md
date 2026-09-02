# Morva Enterprise Payroll Transformation

## هدف

این سند معیار فنی تبدیل Morva به یک سامانه حقوق و دستمزد Enterprise است. پیاده‌سازی نرم‌افزاری هرگز به‌تنهایی معادل مجوز پرداخت واقعی نیست.

## زنجیره authoritative

`Source -> ImportBatch -> MasterData -> EffectivePersonnelSnapshot -> ApprovedRulePack -> PayrollRun -> EmployeePayrollArtifact -> PayslipLines -> Validation -> Review -> Approval -> Freeze -> PaymentBatch -> Outbox -> ExternalReceipt -> BankSettlement -> Reconciliation -> ImmutableAudit`

## سه سطح وضعیت

| وضعیت | معنی |
|---|---|
| `implemented` | کد قابلیت وجود دارد و مسیر اصلی آن پیاده‌سازی شده است. |
| `validated` | تست‌های لازم و شواهد کنترل برای محیط هدف با موفقیت ثبت شده است. |
| `production_certified` | علاوه بر validation، مدارک حقوقی/مالی، امنیت عملیاتی، DR، integration و sign-off رسمی تکمیل شده است. |

## قواعد non-negotiable

- Rule بدون primary source و approval هرگز active نمی‌شود.
- Payroll line بدون provenance و mapping approval وارد authoritative calculation نمی‌شود.
- نتیجه هر employee به‌عنوان artifact مستقل با snapshot hash و rule-pack hash نگهداری می‌شود.
- payment batch بدون freeze، artifacts کامل، Rule Pack approved/published و SoD معتبر ایجاد نمی‌شود.
- پیام بیرونی فقط از طریق Outbox با idempotency key ارسال می‌شود.
- acknowledgement از طریق Inbox و external receipt ثبت می‌شود.
- retry نباید payment duplication ایجاد کند.
- production بدون PostgreSQL، MFA، OIDC، managed keys و migrated schema fail-closed است.
- demo data و demo policies در production ممنوع‌اند.

## وضعیت این release

در این مرحله، زیرساخت Enterprise زیر پیاده‌سازی شده است:

1. persistent employee payroll artifacts;
2. persistent payslip lines;
3. lifecycle audit records;
4. encrypted sensitive-field primitives with keyed lookup;
5. hierarchical organization-scope authorization primitive;
6. transactional outbox/inbox records;
7. payment-batch creation gate;
8. mandatory idempotency and correlation headers for payment-batch creation;
9. immutable rule-pack hash evidence on authoritative calculation.

## blockers قبل از پرداخت واقعی

این موارد عمداً توسط کد به‌صورت fail-closed حفظ می‌شوند و نمی‌توان آنها را بدون شواهد خارجی جعل کرد:

- تأیید رسمی تمام Rule Packهای فعال توسط امور مالی/حقوقی؛
- قرارداد و endpoint رسمی SINA، حسابداری، خزانه، بانک، مالیات و بیمه؛
- نمونه‌های authoritative و golden reconciliation واقعی؛
- key management و rotation عملیاتی؛
- encrypted backup، WAL/PITR و restore-drill evidence؛
- load/concurrency/security/DR evidence در محیط هدف؛
- approval و separation-of-duties واقعی در IAM سازمان؛
- certification نهایی گزارش مغایرت و خروجی پرداخت.

Until all blockers are evidenced, Morva MUST NOT be declared ready for real payment.
