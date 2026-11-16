# P1 — Import → Personnel Snapshot → PayrollRun

## Trust chain

`source file` → `ImportBatch` → `ImportRecord` → `EmployeeRecord.source_employee_key` → immutable `PersonnelSnapshot` → explicit source projection → `PayrollLine` → `PayrollRun`.

The source layer is immutable and retains SHA-256 provenance. Duplicate batches with the same period, source and digest are rejected.

## Quarantine rules

A critical reconciliation exception, missing master employee, missing personnel snapshot, or unmapped source payroll component prevents the batch from becoming ready for calculation.

Projected payroll lines are created with `mapping_status=review_required`. They are not calculator inputs until the mapping and treatment have been explicitly approved.

## Calendar invariant

Payroll periods such as `1405-05` are canonical Jalali period keys. They are never converted by constructing a Gregorian `date` from the year/month digits.

## Production boundary

The implementation does not activate an external payment adapter and does not infer legal treatment for unmapped or unreviewed components. Those remain explicit approval gates.


## Effective-date conversion boundary

A payroll period key (for example, `1405-05`) and a Jalali effective-date source value are source-calendar data, not Gregorian dates. The source string must remain unchanged until an independently governed calendar adapter resolves it.

The Golden Case calendar boundary is defined in `morva.rules.calendar_adapter`:

- An injected Jalali adapter receives the original source value verbatim and returns a structured `CalendarDateResolution`.
- The resolution identifies source/target calendars, adapter/version, the resolved date, authority reference, evidence SHA-256 and separate review/approval provenance.
- An independent evidence verifier must approve the referenced evidence before the resolved date can be used by the matrix-to-RuleDefinition resolver.
- The contract rejects missing approval metadata, reviewer/approver identity reuse, placeholder or malformed hashes, mismatched source values and datetime/string results.
- No default converter or Jalali arithmetic implementation is shipped in this tranche. Without a separately governed adapter and verifier, date resolution fails closed.

This is an interface and metadata-validation contract only. It does not independently certify that an authority reference is official or that a given algorithm is legally authoritative. A trusted evidence verifier and the official calendar implementation must be separately supplied and reviewed before production use. Issue date, effective date, arrears date and end date remain separate fields and must each be resolved according to their source semantics.
