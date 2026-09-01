# Morva Legal Rule Governance

## Purpose

No payroll rule becomes active merely because it sounds correct. Every production rule must be traceable to a reviewed legal source and a regression case.

## Lifecycle

`draft -> source_review -> legal_review -> finance_review -> regression_tested -> approved -> active -> superseded -> archived`

## Required metadata

- `rule_code`
- `title`
- `source_document`
- `authority`
- `document_date`
- `publication_reference`
- `effective_from`
- `effective_to`
- `scope`
- `formula`
- `eligibility`
- `tax_treatment`
- `insurance_treatment`
- `pension_treatment`
- `minimum`
- `maximum`
- `exceptions`
- `review_status`
- `reviewed_by`
- `reviewed_at`
- `regression_case_ids`

## 1405 findings incorporated during research

1. Law on Civil Service Management: Articles 64-68 establish the broad structure of job points, employee points and allowances. Article 65 also has a specific 1.1 multiplier for full-time educational jobs in the Ministry of Education.
2. Teacher Ranking Law: five ranks exist and Article 6 defines minimum ranking allowances of 45%, 55%, 65%, 75% and 90% of the specified base.
3. The 1404 executive regulation of teacher ranking replaced the 1401 regulation. Morva therefore treats the 1401 regulation as superseded historical source data, not an active rule pack.
4. Current ranking regulation includes electronic case collection, evidence, assessment, committee approval and appeal workflows. It also provides specific authority levels for district/region, provincial and central committees.
5. 1405 budget execution rules require monthly personnel/order updates through the SINA platform and describe SINA FISH and SINA ORDER web services. Morva models these as external adapters.
6. 1405 payroll tax rules reported in current sources use a 4.8 billion IRR annual exemption and progressive bands. Until the primary law artifact is imported and reviewed, these values remain `review_required` fixtures.

## Safety gate

The repository may contain research fixtures and draft rule packs. Only rules marked `approved` can be used by a production payroll run.
