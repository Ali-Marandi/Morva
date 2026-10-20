# Statutory Fund Integration Architecture Review

**Review date:** 2026-10-18

**Scope:** evidence available in this repository and official public sources reviewed on the date above. This is an engineering assessment, not legal advice, provider approval, or authorization to process payroll or submit contributions.

## Executive finding

The repository has useful provider-neutral domain boundaries for the Central Civil Servants Pension Fund and the Social Security Organization. The reviewed official public material confirms that employer-facing electronic services exist and that employers submit employee lists and contributions through those services. The material reviewed does **not** provide a machine-readable integration contract (such as an accepted API schema, file specification, authentication profile, or sandbox agreement).

Consequently, Morva can safely prepare contract-intake and evidence plumbing, but cannot implement or activate either provider submission from the public information reviewed. No endpoint, field, calculation rule, retry behavior, or acknowledgement semantics should be inferred from the public service descriptions.

## Evidence reviewed

| Source | What it supports | What it does not establish |
|---|---|---|
| [Central Civil Servants Pension Fund public site](https://www.cspf.ir/) and the fund’s publicly linked electronic services at [eservices.cspf.ir](https://eservices.cspf.ir/) | The fund operates an official public website and electronic service portal. | No public employer API schema, integration endpoint contract, authentication specification, sandbox, or contribution acknowledgement format was identified in the reviewed public pages. A portal's existence is not evidence of an API. |
| [Social Security Organization official information channel](https://t.me/s/tamin_media) and its published employer-service notices | The organization directs employers to [es.tamin.ir](https://es.tamin.ir/) to submit payroll lists and pay contributions. | These operational notices do not specify an API/file contract, provider-side idempotency, response codes, retry rules, or a supported software integration method. |
| Morva source and readiness documentation at `src/morva/integrations/`, `src/morva/runtime/`, `src/morva/payroll/`, `docs/integrations/STATUTORY_FUNDS.md`, and `docs/PRODUCTION_READINESS.md` | Current domain boundaries, evidence gates, fail-closed behavior, and reconciliation checks. | Repository abstractions are not provider approval or proof that a live connection works. |

The search was limited to publicly accessible material. “No contract identified” means none was found in those reviewed sources; it does not prove that a private, authenticated, or formally supplied contract does not exist.

## What the current code supports

- `src/morva/integrations/statutory_funds.py` defines distinct `StatutoryFund` identities, ports, and treatment catalogs for the two funds. Catalog validation prevents one fund’s treatment metadata from being used for the other.
- Both ports currently accept the generic `IntegrationPayload` and return the generic `IntegrationReceipt` from `src/morva/integrations/ports.py`. The payload body is an untyped dictionary and the receipt has only provider, external ID, correlation ID, and status. These types do not encode either provider’s actual contract.
- `FailClosedStatutoryFundAdapter` refuses external submission by default. Preserve that behavior until evidence and independent approvals exist.
- `src/morva/runtime/official_adapter_evidence.py` currently governs six adapter identifiers: `sina`, `accounting`, `treasury`, `bank`, `tax`, and `insurance`. The statutory fund ports are not separate identifiers in that activation list. The generic `insurance` identity must not be assumed to mean either statutory fund; it must be clarified and mapped only through an approved decision.
- `src/morva/payroll/statutory_reconciliation.py` checks a nonblank batch ID, nonnegative employee count, and equality of expected and settled totals. It has no provider source, accepted/rejected population, provider receipt reference, or contract-backed status semantics. It is a narrow consistency check, not evidence of full provider reconciliation.

## Contract-led target seam

Keep the internal payroll and legal-treatment model provider-neutral. Add provider-specific request/response models and adapters only after an authoritative provider contract has been received and reviewed. The intended boundary is:

1. A separately approved internal contribution batch is frozen and assigned an immutable correlation/idempotency identity.
2. A provider-specific mapper validates the batch against a versioned, approved provider schema. It must not calculate legal amounts or silently discard unsupported fields.
3. A provider-specific transport sends only through an authorized non-production endpoint or channel documented by that provider. Authentication, signing, encryption, rate limits, and timeouts follow that contract.
4. The raw request/response evidence is stored under the project’s approved privacy and retention controls, with sensitive values redacted from ordinary logs. The adapter records the contract version/digest and the provider’s acknowledgement or rejection reference.
5. Retries, resubmissions, corrections, reversals, and idempotency behavior follow explicit provider semantics. If the contract does not define a safe retry rule, ambiguous outcomes require manual reconciliation rather than blind resubmission.
6. Reconciliation compares the exact contract-backed identifiers, population counts, amounts, and statuses returned by the provider. Missing provider evidence remains unmatched; it is never treated as success.

This is a boundary proposal, not a claim about either provider’s actual protocol. Do not implement guessed fields or endpoints.

## Minimum evidence to accept a provider contract

For each fund independently, collect and approve:

- Named provider owner and authorized Morva integration owner, including the written basis for access.
- Authoritative source document and version: API specification, WSDL, file layout, or other formally supported contract; source URL or transmittal, retrieval date, and SHA-256 digest.
- Authentication and authorization profile, credential issuance/rotation/revocation procedure, network restrictions, and data classification/retention requirements.
- Required request fields, code dictionaries, effective-date rules, validation rules, and provider-defined rejection messages.
- Acknowledgement, status polling, correction, reversal, duplicate, timeout, and partial-acceptance semantics.
- Contract-defined correlation/idempotency mechanism, retry limits, service limits, maintenance/error behavior, and escalation/SLA.
- Provider-authorized sandbox, synthetic fixtures, known expected results, and evidence that tests cannot reach production or move money.
- A field-by-field reconciliation map from Morva batch identity and totals to provider receipts and final settlement evidence.
- Independent legal, payroll/data, security, integration, reconciliation, and disaster-recovery reviews with named approvers and dated evidence.

Keep this intake evidence versioned and expiring. A changed contract invalidates dependent mapping and test evidence until re-reviewed.

## The referenced “six-layer” study

The repository’s earlier notes refer to a six-layer feasibility study, but no identifiable study document, title, issuing owner, or authoritative source is present in the reviewed repository. Public service material reviewed here does not establish that six layers are a provider requirement. Do not invent six layers or treat an unverified phrase as an external technical contract.

The readiness item should be resolved by finding the study or obtaining a written answer from its accountable owner on whether it is binding. If it is binding, add its approved version and map each layer to code, evidence, and accountable owner. If it is not authoritative or no longer applicable, record the decision and approver before changing the gate. This review alone does not clear the item.

## Readiness decision

**Gate 3 remains BLOCKED.** Public workflows and existing interfaces are insufficient to authorize an integration. Both fund adapters remain fail-closed. There is no production activation, real payroll processing, or payment authorization in this review. All six production-readiness gates remain blocked until their independent evidence is complete and approved.

## Next practical steps

1. Ask the accountable project/provider owner for the six-layer study and for the official integration contract for each fund separately.
2. Resolve whether the existing `insurance` adapter is intended to represent a specific statutory fund or another insurance integration; do not silently reuse it.
3. After contract receipt, write provider-specific contract fixtures and schema-validation tests before implementing transport.
4. Extend evidence records and reconciliation only to fields and states actually guaranteed by those contracts.
5. Obtain independent reviews and authorized synthetic staging evidence; keep production execution disabled until the existing readiness gates are independently satisfied.
