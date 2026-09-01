# Morva — User Data Quality / Import Note (1405-05)

Source reports supplied by the project owner:

- گزارش لیست حقوق.xlsx — 3,329 rows
- اکسل گزارش بیمه تکمیلی.xlsx — 2,193 rows
- اکسل گزارش کسر اقساط (1).xlsx — 20,671 rows
- گزارش احکام حقوقی.xlsx — 22,696 rows
- گزارش بیمه خدمات درمانی.xlsx — 2,197 rows
- گزارش لیست بیمه تامین اجتماعی.xlsx — 1,116 rows

## Join coverage

- Payroll ↔ supplementary insurance: 2,193 / 3,329 personnel codes
- Payroll ↔ installment deductions: 3,126 / 3,329 personnel codes
- Payroll ↔ personnel orders: 3,329 / 3,329 personnel codes
- Payroll ↔ health insurance by national ID: 2,169 / 3,329 payroll rows
- Payroll ↔ social security: 1,116 / 3,329 personnel codes

## Aggregate controls

- Payroll gross benefits: 971,405,814,240
- Payroll deductions: 247,897,427,588
- Payroll employer commitments: 156,081,256,435
- Payroll net pay: 723,508,386,652
- Supplementary employee share: 32,685,000,000
- Supplementary total: 32,722,500,000
- Health insurance premium: 40,874,971,084
- Social employee premium: 15,492,415,986
- Social employer premium: 45,669,023,616

## Import policy

The first Morva fixture is intentionally anonymized. Raw names and national IDs are not committed to GitHub. Surrogate identifiers are derived from SHA-256 hashes.

The fixture contains representative cross-source records for integration/regression work. It is not an assertion that Morva's legal Rule Packs are already approved or that the supplied values are themselves authoritative legal calculations.
