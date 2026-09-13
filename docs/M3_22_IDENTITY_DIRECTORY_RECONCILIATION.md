# M3.22 Identity Directory Reconciliation

M3.22 makes employee self-service identity resolution deterministic and fail-closed.

## Contract

An authenticated principal is resolved against `EmployeeRecord` using only these trusted directory keys:

- `employee_no`
- `source_employee_key`

The resolver trims surrounding whitespace, evaluates both keys, and orders candidates deterministically by `employee_no`.

## Safety rules

Exactly one distinct employee record must match. Zero matches remain unmapped and are rejected by self-service with `404`. Multiple distinct matches are treated as an identity-directory ambiguity and rejected with `409`.

The resolver does not perform fuzzy matching, name matching, national-ID fallback, directory mutation, or automatic conflict repair.

## Self-service integration

The `/api/v1/self/*` endpoints now consume the same reconciliation contract before loading profile, payslip, or personnel-order data. This removes the previous inline `employee_no OR source_employee_key` lookup that could silently select an arbitrary row when an external identity matched more than one record.

The result object is also suitable for audit and operational diagnostics without exposing sensitive national identity values.

## Non-goals

This tranche does not alter payroll formulas, legal numeric values, master-data authority, or authentication token validation. It only establishes a deterministic boundary between authenticated identity and the canonical employee directory.
