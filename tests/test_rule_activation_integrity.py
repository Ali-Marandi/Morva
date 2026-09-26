from datetime import date, datetime
from uuid import uuid4

import pytest

from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import Base, RulePackRecord
from morva.rules.activation import RuleActivationBlocked, require_authoritative_pack, require_production_rule_pack


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


def _production_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()

def _production_fixture(session):
    pack = RulePackRecord(version="GATE1-1.0", status="approved", legal_source_hash="c" * 64, rules_hash="d" * 64, effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31))
    source = LegalSourceRecord(citation="source", issuer="issuer", adoption_date="2026-01-01", effective_from="2026-01-01", effective_to="2026-12-31", document_hash="a" * 64, status="approved")
    session.add_all([pack, source]); session.flush()
    evidence = RuleEvidenceRecord(rule_pack_version=pack.version, component_code="TAX", legal_source_id=source.id, issuer=source.issuer, article="1", population_scope="public-sector", source_hash=source.document_hash, regression_suite_hash="b" * 64, status="approved", reviewed_by="legal-reviewer", approved_by="finance-approver", approved_at=datetime(2026, 1, 3))
    entry = CalculationMatrixRecord(rule_pack_version=pack.version, component_code="TAX", population_scope="public-sector", treatment="deduction", expression={"op": "value", "name": "taxable"}, effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31), legal_source_id=source.id, legal_article="1", taxable=False, pensionable=False, insurable=False, regression_suite_hash="b" * 64, status="approved", reviewed_by="matrix-reviewer", reviewed_at=datetime(2026, 1, 4), approved_by="matrix-approver", approved_at=datetime(2026, 1, 5))
    session.add_all([evidence, entry]); session.commit()
    return pack

def test_production_activation_requires_effective_pack_and_matrix_readiness() -> None:
    with _production_session() as session:
        pack = _production_fixture(session)
        require_production_rule_pack(session, pack=pack, as_of=date(2026, 9, 1), component_codes={"TAX"})

def test_production_activation_blocks_outside_rule_pack_effective_period() -> None:
    with _production_session() as session:
        pack = _production_fixture(session)
        with pytest.raises(RuleActivationBlocked, match="not effective"):
            require_production_rule_pack(session, pack=pack, as_of=date(2027, 1, 1), component_codes={"TAX"})
