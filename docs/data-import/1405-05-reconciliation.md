# Morva 1405-05 Reconciliation Results

Source period: **1405-05 (Mordad 1405)**

## Source row counts

- Payroll: 3,329
- Supplementary insurance: 2,193
- Installment ledger: 20,671
- Personnel orders: 22,696
- Health insurance: 2,197
- Social security: 1,116

## Join results

- Payroll → supplementary insurance: 2,193 / 2,193
- Payroll → installment ledger: 3,126 / 3,126 personnel
- Payroll → personnel orders: 3,329 / 3,329 current personnel; the source contains 231 additional historical-only personnel keys
- Payroll → social security: 1,116 / 1,116
- Payroll → health insurance by national ID: 2,169 / 2,197; 28 health rows have no payroll national-ID match

## Payroll controls

- Gross benefits: 971,405,814,240
- Deductions: 247,897,427,588
- Net pay: 723,508,386,652
- Employer commitments: 156,081,256,435
- Gross components reconcile to `جمع مزایا` for 3,329 / 3,329 rows.
- `جمع مزایا - جمع کسور = خالص پرداختی` for 3,329 / 3,329 rows.

## Deduction bridge

`جمع کسور` must be reconciled as:

`10 explicit payroll deduction columns + installment ledger deductions`

For 3,320 / 3,329 payroll rows this bridge reconciles exactly. Nine rows retain a non-zero residual and are therefore recorded as exceptions rather than silently balanced.

| Personnel key | Residual | Severity |
|---|---:|---|
| 11785141 | 2,000,000 | review |
| 18002928 | -21,135,278 | critical review |
| 18982494 | 6,000,000 | review |
| 33228515 | 37,260,615 | review |
| 51310595 | 500,000 | review |
| 52215190 | 1,000,000 | review |
| 93957948 | 10,000,000 | review |
| 93969477 | 10,000,000 | review |
| 93969483 | 10,000,000 | review |

Total residual across these nine rows: **55,625,337**.

## Data quality conclusions

1. The payroll report is internally consistent for gross, deductions and net arithmetic.
2. The gross component mapping is exact and includes `بازگشت بیمه تکمیلی-160`.
3. Loan installments explain almost all of the deduction gap and must be treated as ledger deductions, not payroll component columns.
4. The nine residuals require business-source investigation before they can become automated Rule Pack behavior.
5. The 28 health-insurance unmatched rows and 231 historical-only order personnel keys are join exceptions, not reasons to fabricate data.

The repository fixture is anonymized; raw names, national IDs and other direct identifiers are never committed.
