# Morva Payroll Domain Snapshot — 1405-05

## Scope

This snapshot is built from the anonymized canonical bundle generated from the six owner-supplied reports. It is a source-data domain snapshot, not an activation of legal calculation rules.

## Population

| Dataset | Count |
|---|---:|
| Payroll employees | 3,329 |
| Personnel-order employee keys | 3,560 |
| Historical-only order keys | 231 |
| Loan employee keys | 3,126 |
| Supplementary-insurance employee keys | 2,193 |
| Health-insurance employee keys | 2,170 |
| Social-security employee keys | 1,116 |

## Payroll joins

| Join | Matched |
|---|---:|
| Payroll → Personnel orders | 3,329 / 3,329 |
| Payroll → Loan ledger | 3,126 / 3,329 |
| Payroll → Supplementary insurance | 2,193 / 3,329 |
| Payroll → Health insurance | 2,169 / 3,329 |
| Payroll → Social security | 1,116 / 3,329 |

The one health-insurance record not linked to a payroll employee is retained as an orphan-source record and must not be silently discarded.

## Arithmetic controls

- 27 payroll earning components reconcile exactly to reported `جمع مزایا` for all 3,329 payroll rows.
- Reported gross less reported deductions reconciles exactly to reported net for all 3,329 payroll rows.
- Nine payroll rows retain a non-zero deduction residual after listed payroll deduction components plus loan installments. Aggregate residual is 55,625,337. These are explicit reconciliation exceptions; Morva does not auto-balance them.

## Effective order policy

For a payroll snapshot, Morva selects the latest personnel order by effective date, then issue date as a tie-breaker. Issue date being later than effective date is not itself classified as an error because retroactive/corrective orders are valid business scenarios. Orders outside the current payroll population remain in the historical HR domain.

## Order-type coverage

The full order history contains 22,696 rows. The most frequent order types are:

1. تغییر حقوق و مزایا — 10,665
2. شاغل — 3,191
3. انتصاب — 1,602
4. ارتقاءطبقه شغلي — 1,037
5. برقراري فوق العاده رتبه بندي معلمان — 912
6. ارتقاء رتبه نظام رتبه بندي معلمان — 458
7. اصلاحیه حق شاغل — 413
8. برقراري رتبه بندي معلمان — 373
9. استخدام پيماني — 364
10. تطبيق نظام رتبه بندي معلمان — 356
11. اصلاح اطلاعات اوليه مستخدم — 341
12. افزايش امتيازات فصل دهم قانون م . خ . ك — 338
13. برقراری فوق العاده مشاغل خدماتی — 337
14. استخدام آزمايشي — 219
15. بازنشستگي — 216

## Domain invariant

Every imported payroll employee must have one or more historical personnel orders. Every payroll component must remain traceable to its source label. No legal rate is inferred merely from the presence of a source column.
