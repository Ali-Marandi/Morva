# M3.35 — Target-scale, concurrency, mutation and financial properties

## Implemented evidence

M3.35 adds a repeatable engineering gate around the existing payroll calculator and batch boundary. It does not alter legal treatment logic or claim production capacity certification.

### Financial property-based tests

`tests/test_m3_35_financial_properties.py` uses Hypothesis to exercise generated payroll lines and validates:

- gross equals the sum of earning lines;
- deductions equal the sum of deduction lines;
- net equals gross minus deductions;
- taxable, pensionable and insurable bases remain bounded by gross;
- replaying identical inputs produces identical output and fingerprint;
- a non-taxable earning changes gross/net without changing taxable income;
- contribution bases use only pensionable earnings;
- contribution rate and ceiling behavior are exact to two decimal places.

These are domain invariants of the current software model, not substitutes for authoritative legal treatment certification.

### Concurrency evidence

`tests/test_m3_35_concurrency.py` replays the same calculation across 16 worker threads and runs 512 distinct employee calculations in parallel. The gate checks deterministic fingerprints, identical results for identical inputs, and fingerprint separation for distinct employee inputs.

This validates thread-safe use of the current pure calculation boundary. It is not a substitute for production database/queue contention testing.

### Target-scale evidence

`tests/performance/test_m3_35_target_scale.py` runs the existing deterministic batch executor with a configurable population. The default gate population is 10,000 employees and can be increased with `MORVA_M3_35_EMPLOYEES`.

The test injects deterministic replay duplicates and verifies that processing, gross, net and difference totals remain exact. It prints throughput evidence without imposing a machine-specific latency threshold.

### Mutation gate

`tools/m3_35_mutation_gate.py` makes a clean temporary copy of the source and intentionally applies four targeted financial mutations:

1. remove the taxable-line filter from the calculator;
2. remove the pensionable-line filter from the calculator;
3. invert the net calculation sign;
4. ignore the contribution ceiling.

The selected regression/property tests must fail for every mutant. A surviving mutant fails the gate. This provides explicit evidence that the critical financial assertions are sensitive to representative implementation faults.

## CI gate

`.github/workflows/m3-35-target-scale-property-mutation.yml` runs Ruff, the M3.35 property/concurrency/scale suite and the mutation gate on pushes to `main` and pull requests targeting `main`.

## Certification boundary

M3.35 is software-test evidence only. Production certification still requires a representative environment, approved workload targets and service-level objectives, database/queue/integration contention tests, mutation coverage beyond the targeted financial mutants, independent performance review, and formal operational approval.
