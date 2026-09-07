from __future__ import annotations

# Coverage manifest only. No legal rates, thresholds, or statutory treatments are
# asserted here. Those values must arrive through the governed legal-source/evidence flow.
REQUIRED_1405_COMPONENTS: tuple[str, ...] = (
    "JOB_RIGHT",
    "INCUMBENT_RIGHT",
    "JOB_ALLOWANCE",
    "RANK_ALLOWANCE",
    "FAMILY_ALLOWANCE",
    "CHILD_ALLOWANCE",
    "OVERTIME",
    "TEACHING_FEE",
    "TAX",
    "PENSION",
    "INSURANCE",
    "LOAN",
    "COURT_ORDER",
)


def is_1405_rule_pack(version: str) -> bool:
    return version.strip().startswith("1405.")
