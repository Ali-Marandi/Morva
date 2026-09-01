# Morva 1405-05 Import Contract

## Sources

| Source | Canonical domain | Primary key | Join key |
|---|---|---|---|
| گزارش لیست حقوق.xlsx | payroll | employee_key | کد پرسنلی |
| اکسل گزارش بیمه تکمیلی.xlsx | supplementary_insurance | employee_key | کد پرسنلی |
| اکسل گزارش کسر اقساط (1).xlsx | deduction_loan_ledger | employee_key + loan_code + row | کد پرسنلی |
| گزارش احکام حقوقی.xlsx | personnel_orders | employee_key + order_number | کد پرسنلی |
| گزارش بیمه خدمات درمانی.xlsx | health_insurance | national_key | شماره ملی |
| گزارش لیست بیمه تامین اجتماعی.xlsx | social_security | employee_key + insurance_code | کد پرسنلی |

## Payroll component boundary

`جمع مزایا` is reconciled against the 27 earning/return components from `حق شغل-1` through `بازگشت بیمه تکمیلی-160` (E:AE in the source report).

`جمع کسور` is reconciled against the 10 explicit payroll deduction components (AF:AO) **plus** installment amounts from the loan/deduction ledger. This boundary is essential because loan deductions are not columns in the payroll report.

## Privacy

Raw names, national IDs and other direct identifiers must not be committed to GitHub. Canonical fixtures use deterministic SHA-256 surrogate IDs. Source workbooks remain outside the repository.

## Import policy

- Reject malformed monetary values.
- Preserve Persian/Jalali dates as source values until an authoritative calendar conversion step is applied.
- Preserve effective/issue/arrears/end dates independently.
- Never overwrite historical orders or ledger rows.
- Record reconciliation exceptions rather than silently balancing them.
- Production activation requires an approved legal Rule Pack and authoritative reconciliation sample.
