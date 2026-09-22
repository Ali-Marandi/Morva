from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.evidence_lifecycle import (
    EvidenceLifecycleError,
    build_lifecycle_assessment,
    build_lifecycle_link,
)


NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")


def _item(
    evidence_id: str,
    *,
    source_type: str = "legal_rule",
    population_scope: str = "teachers",
    effective_from: str = "2026-01-01T00:00:00+00:00",
    approved_at: str = "2026-09-01T00:00:00+00:00",
    status: str = "accepted",
) -> AuthoritativeEvidenceItem:
    return AuthoritativeEvidenceItem(
        intake_version=1,
        evidence_id=evidence_id,
        source_type=source_type,
        source_uri=f"https://authority.example/{evidence_id}",
        source_sha256="a" * 64,
        issuer="authority",
        population_scope=population_scope,
        effective_from=effective_from,
        effective_to="2027-01-01T00:00:00+00:00",
        status=status,
        approved_by="approver",
        approved_at=approved_at,
        expires_at="2026-12-31T00:00:00+00:00",
    )


def _registry(*items: AuthoritativeEvidenceItem):
    return build_registry(items, registered_at=NOW)


def test_build_link_is_self_verifying():
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="lifecycle-admin",
        linked_at=NOW,
        reason="renewed authority",
    )
    link.verify()
    assert link.fingerprint == link.expected_fingerprint


def test_valid_supersession_produces_new_head():
    old = _item("E-OLD")
    new = _item(
        "E-NEW",
        effective_from="2026-09-02T00:00:00+00:00",
    )
    registry = _registry(old, new)
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="lifecycle-admin",
        linked_at=NOW,
        reason="renewed authority",
    )

    assessment = build_lifecycle_assessment(
        registry,
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        links=(link,),
    )

    assert assessment.head_evidence_ids == ("E-NEW",)
    assert assessment.superseded_evidence_ids == ("E-OLD",)
    assert assessment.link_fingerprints == (link.fingerprint,)


def test_no_links_keep_all_accepted_items_as_heads():
    registry = _registry(_item("E-001"), _item("E-002"))
    assessment = build_lifecycle_assessment(
        registry,
        repository="Ali-Marandi/Morva",
        checked_at=NOW,
        links=(),
    )
    assert assessment.head_evidence_ids == ("E-001", "E-002")
    assert assessment.superseded_evidence_ids == ()


def test_source_type_mismatch_is_rejected():
    registry = _registry(
        _item("E-OLD"),
        _item("E-NEW", source_type="security_assessment", effective_from="2026-09-02T00:00:00+00:00"),
    )
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="admin",
        linked_at=NOW,
        reason="changed source family",
    )
    with pytest.raises(EvidenceLifecycleError, match="source_type"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=(link,))


def test_population_scope_mismatch_is_rejected():
    registry = _registry(
        _item("E-OLD"),
        _item("E-NEW", population_scope="administrators", effective_from="2026-09-02T00:00:00+00:00"),
    )
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="admin",
        linked_at=NOW,
        reason="changed population",
    )
    with pytest.raises(EvidenceLifecycleError, match="population_scope"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=(link,))


def test_multiple_successors_are_rejected():
    old = _item("E-OLD")
    new_a = _item("E-NEW-A", effective_from="2026-09-02T00:00:00+00:00")
    new_b = _item("E-NEW-B", effective_from="2026-09-03T00:00:00+00:00")
    registry = _registry(old, new_a, new_b)
    links = (
        build_lifecycle_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW-A",
            linked_by="admin",
            linked_at=NOW,
            reason="renewed",
        ),
        build_lifecycle_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW-B",
            linked_by="admin",
            linked_at=NOW,
            reason="renewed again",
        ),
    )
    with pytest.raises(EvidenceLifecycleError, match="multiple successors"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=links)


def test_cycle_is_rejected():
    first = _item("E-001", effective_from="2026-01-01T00:00:00+00:00")
    second = _item("E-002", effective_from="2026-02-01T00:00:00+00:00")
    third = _item("E-003", effective_from="2026-03-01T00:00:00+00:00")
    registry = _registry(first, second, third)
    links = (
        build_lifecycle_link(
            predecessor_evidence_id="E-001",
            successor_evidence_id="E-002",
            linked_by="admin",
            linked_at=NOW,
            reason="1 to 2",
        ),
        build_lifecycle_link(
            predecessor_evidence_id="E-002",
            successor_evidence_id="E-003",
            linked_by="admin",
            linked_at=NOW,
            reason="2 to 3",
        ),
        build_lifecycle_link(
            predecessor_evidence_id="E-003",
            successor_evidence_id="E-001",
            linked_by="admin",
            linked_at=NOW,
            reason="bad reverse link",
        ),
    )
    with pytest.raises(EvidenceLifecycleError, match="effective_from|cycle"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=links)


def test_future_link_is_rejected():
    registry = _registry(
        _item("E-OLD"),
        _item("E-NEW", effective_from="2026-09-02T00:00:00+00:00"),
    )
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="admin",
        linked_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
        reason="future",
    )
    with pytest.raises(EvidenceLifecycleError, match="future"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=(link,))


def test_successor_approval_in_future_is_rejected():
    registry = _registry(
        _item("E-OLD"),
        _item(
            "E-NEW",
            effective_from="2026-09-02T00:00:00+00:00",
            approved_at="2026-09-23T00:00:00+00:00",
        ),
    )
    link = build_lifecycle_link(
        predecessor_evidence_id="E-OLD",
        successor_evidence_id="E-NEW",
        linked_by="admin",
        linked_at=NOW,
        reason="future approval",
    )
    with pytest.raises(EvidenceLifecycleError, match="future"):
        build_lifecycle_assessment(registry, repository="repo", checked_at=NOW, links=(link,))


def test_input_order_does_not_change_assessment_identity():
    old = _item("E-OLD")
    new = _item("E-NEW", effective_from="2026-09-02T00:00:00+00:00")
    third = _item("E-THIRD", effective_from="2026-10-01T00:00:00+00:00")
    registry = _registry(old, new, third)
    links = (
        build_lifecycle_link(
            predecessor_evidence_id="E-OLD",
            successor_evidence_id="E-NEW",
            linked_by="admin",
            linked_at=NOW,
            reason="renewed",
        ),
    )
    one = build_lifecycle_assessment(
        registry, repository="repo", checked_at=NOW, links=links
    )
    two = build_lifecycle_assessment(
        registry, repository="repo", checked_at=NOW, links=tuple(reversed(links))
    )
    assert one.fingerprint == two.fingerprint
