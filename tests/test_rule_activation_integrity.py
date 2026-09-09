from datetime import datetime
from uuid import uuid4

import pytest

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import RulePackRecord
from morva.rules.activation import RuleActivationBlocked, require_authoritative_pack


class _ScalarResult:
    def __init__(self, values: list[RuleEvidenceRecord]) -> None:
        self._values = values

    def all(self) -> list[RuleEvidenceRecord]:
        return self._values


class _SessionStub:
    def __init__(self, evidence: list[RuleEvidenceRecord], source: LegalSourceRecord | None) -> None:
        self._evidence = evidence
        self._source = source

    def scalars(self, _query: object) -> _ScalarResult:
        return _ScalarResult(self._evidence)

    def get(self, _model: type[LegalSourceRecord], _source_id: object) -> LegalSourceRecord | None:
        return self._source


def _fixture(
    *,
    source_status: str = "approved",
    evidence_source_hash: str = "a" * 64,
    source_hash: str = "a" * 64,
    reviewed_by: str | None = "legal-reviewer",
    approved_by: str | None = "finance-approver",
    approved_at: datetime | None = datetime(2026, 9, 9, 10, 0),
) -> tuple[RulePackRecord, RuleEvidenceRecord, LegalSourceRecord]:
    source_id = uuid4()
    source = LegalSourceRecord(
        id=source_id,
        citation="test source",
        issuer="test issuer",
        adoption_date="2026-01-01",
        effective_from="2026-01-01",
        document_hash=source_hash,
        status=source_status,
    )
    evidence = RuleEvidenceRecord(
        id=uuid4(),
        rule_pack_version="1405-test-1.0",
        component_code="TAX",
        legal_source_id=source_id,
        issuer="test issuer",
        article="1",
        population_scope="test population",
        source_hash=evidence_source_hash,
        regression_suite_hash="b" * 64,
        status="approved",
        reviewed_by=reviewed_by,
        approved_by=approved_by,
        approved_at=approved_at,
    )
    pack = RulePackRecord(
        id=uuid4(),
        version="1405-test-1.0",
        status="approved",
        legal_source_hash="c" * 64,
        rules_hash="d" * 64,
    )
    return pack, evidence, source


def test_activation_accepts_complete_provenance() -> None:
    pack, evidence, source = _fixture()

    require_authoritative_pack(
        _SessionStub([evidence], source),
        pack=pack,
        component_codes={"TAX"},
    )


def test_activation_blocks_source_hash_mismatch() -> None:
    pack, evidence, source = _fixture(evidence_source_hash="e" * 64)

    with pytest.raises(RuleActivationBlocked, match="source hash mismatch"):
        require_authoritative_pack(
            _SessionStub([evidence], source),
            pack=pack,
            component_codes={"TAX"},
        )


def test_activation_blocks_unapproved_source() -> None:
    pack, evidence, source = _fixture(source_status="reviewed")

    with pytest.raises(RuleActivationBlocked, match="legal source is not approved"):
        require_authoritative_pack(
            _SessionStub([evidence], source),
            pack=pack,
            component_codes={"TAX"},
        )


def test_activation_requires_distinct_review_and_approval_actors() -> None:
    pack, evidence, source = _fixture(reviewed_by="same-user", approved_by="same-user")

    with pytest.raises(RuleActivationBlocked, match="must be distinct"):
        require_authoritative_pack(
            _SessionStub([evidence], source),
            pack=pack,
            component_codes={"TAX"},
        )


def test_activation_requires_approval_timestamp() -> None:
    pack, evidence, source = _fixture(approved_at=None)

    with pytest.raises(RuleActivationBlocked, match="approval timestamp"):
        require_authoritative_pack(
            _SessionStub([evidence], source),
            pack=pack,
            component_codes={"TAX"},
        )
