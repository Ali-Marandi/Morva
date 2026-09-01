# Morva — Full Source Reconciliation (1405-05)

This report was generated from the six owner-supplied XLSX reports for the 1405-05 payroll period.

## Source population

| Source | Rows |
|---|---:|
| Payroll | 3,329 |
| Supplementary insurance | 2,193 |
| Installment deductions | 20,671 |
| Personnel orders | 22,696 |
| Health insurance | 2,197 |
| Social Security | 1,116 |

## Employee coverage

- Payroll employees: 3,329 unique personnel codes.
- Every payroll employee has at least one personnel order record: 3,329/3,329.
- 231 personnel codes occur in the order history but not in the 1405-05 payroll population; these are retained as historical HR population and are not silently discarded.
- Supplementary insurance links to 2,193 payroll employees.
- Loan records link to 3,126 payroll employees.
- Social Security links to 1,116 payroll employees.
- Health-insurance rows link to 2,169 payroll employees through national-identifier matching.

## Payroll arithmetic controls

- Gross benefits: 971,405,814,240.
- Reported deductions: 247,897,427,588.
- Net pay: 723,508,386,652.
- Employer commitments: 156,081,256,435.
- Gross component reconciliation mismatches: **0**.
- Net arithmetic mismatches (`gross - deductions != net`): **0**.

## Deduction bridge

The ten deduction columns in the payroll report do not exhaust all deductions when installment-loan deductions are considered. The Morva importer therefore reconciles:

`reported payroll deductions - listed payroll deduction columns - loan installments`

This produced 9 residual exceptions totaling 55,625,337. These are retained as explicit reconciliation exceptions and are not force-balanced.

## Duplicate keys

Duplicate `شماره وام` and `شماره حکم` values are expected to occur because one employee may have multiple installment/order rows over time. They are therefore not treated as uniqueness failures. Payroll personnel codes, supplementary personnel codes, social-security personnel codes, and health national identifiers were unique in their respective reports.

## Temporal controls

There are 15,749 order rows where issue date occurs after effective date. This is an **indicator**, not an automatic error: retroactive/corrective orders can legitimately have an effective date earlier than their issue date. Morva preserves both dates and leaves policy-level validation to the order/rule governance layer.

## Privacy

Raw names and national identifiers are not stored in this GitHub QA artifact. Any employee-level exception references use SHA-256-derived surrogate keys.

## Release gate

This reconciliation establishes a source-data baseline for Morva. It does **not** prove legal correctness of tax, pension, insurance, or ranking rules and does not authorize production payroll. Those require separately approved Rule Packs and official integration validation.
