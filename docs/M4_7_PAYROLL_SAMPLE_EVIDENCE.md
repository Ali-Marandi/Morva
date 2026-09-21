# M4.7 — Authoritative Payroll Sample Evidence

M4.7 creates a fail-closed boundary for approved payroll reference samples.

A sample is bound to:
- an exact employee-population scope;
- an exact Jalali payroll period;
- an M4.1 `payroll_sample` evidence item;
- an input-manifest SHA-256;
- an expected-output SHA-256;
- a line-by-line comparison fingerprint;
- reviewer/approver provenance.

The implementation stores identifiers and hashes only. No payroll amount, national identifier or real employee record is included.

Reference samples remain external authoritative inputs and must be independently supplied and approved before they can satisfy production acceptance gates.
