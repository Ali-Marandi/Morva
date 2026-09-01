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
