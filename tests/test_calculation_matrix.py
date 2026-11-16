from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import Base, RulePackRecord
from morva.rules.calculation_matrix import (
    MatrixResolutionError,
    _select_active_matrix_entry,
    approve_matrix_entry,
    create_matrix_entry,
    matrix_readiness,
    resolve_rule_definition_for_case,
    validate_matrix_payload,
)
from morva.rules.calendar_adapter import CalendarDateResolution
from morva.rules.engine import RuleContext, RuleEngine
from morva.rules.regression import fingerprint_expected_result_payload, fingerprint_values
from morva.rules.regression_cases import RegressionCase, verify_expected_result


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _setup(
    session,
    *,
    source_status="approved",
    evidence_status="approved",
    pack_status="reviewed",
):
    pack = RulePackRecord(
        version="TEST-MATRIX-1.0",
        status=pack_status,
        legal_source_hash="a" * 64,
        rules_hash="c" * 64,
        reviewed_by="legal-reviewer",
        reviewed_at=datetime(2026, 1, 2),
        approved_by="pack-approver" if pack_status in {"approved", "published"} else None,
        approved_at=datetime(2026, 1, 3) if pack_status in {"approved", "published"} else None,
    )
    source = LegalSourceRecord(
        citation="Synthetic authority source",
        issuer="Synthetic issuer",
        adoption_date="2026-01-01",
        effective_from="2026-01-01",
        document_hash="a" * 64,
        status=source_status,
    )
    session.add_all([pack, source])
    session.flush()
    evidence = RuleEvidenceRecord(
        rule_pack_version=pack.version,
        component_code="TEST_EARNING",
        legal_source_id=source.id,
        issuer=source.issuer,
        article="1",
        population_scope="all",
        source_hash=source.document_hash,
        regression_suite_hash="b" * 64,
        status=evidence_status,
        reviewed_by="evidence-reviewer" if evidence_status != "review_required" else None,
        approved_by="evidence-approver" if evidence_status == "approved" else None,
        approved_at=datetime(2026, 1, 3) if evidence_status == "approved" else None,
    )
    session.add(evidence)
    session.commit()
    return pack, source, evidence


def test_matrix_payload_rejects_unknown_expression_operation():
    try:
        validate_matrix_payload(
            treatment="earning",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            regression_suite_hash="b" * 64,
            expression={"op": "pow", "args": [{"op": "const", "value": "2"}]},
            legal_article="1",
            population_scope="all",
            taxable=True,
            pensionable=False,
            insurable=False,
        )
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unknown expression operation must be rejected")


def test_matrix_payload_requires_explicit_treatment_flags():
    try:
        validate_matrix_payload(
            treatment="earning",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            regression_suite_hash="b" * 64,
            expression={"op": "value", "name": "base"},
            legal_article="1",
            population_scope="all",
        )
    except ValueError as exc:
        assert "explicitly provided" in str(exc)
    else:
        raise AssertionError("treatment flags must not be implicit")


def test_matrix_requires_approved_source_and_evidence():
    with _session() as session:
        _setup(session, source_status="review_required")
        try:
            create_matrix_entry(
                session,
                {
                    "rule_pack_version": "TEST-MATRIX-1.0",
                    "component_code": "TEST_EARNING",
                    "population_scope": "all",
                    "treatment": "earning",
                    "expression": {"op": "value", "name": "base"},
                    "effective_from": date(2026, 1, 1),
                    "effective_to": None,
                    "legal_source_id": session.query(LegalSourceRecord).first().id,
                    "legal_article": "1",
                    "legal_clause": None,
                    "taxable": True,
                    "pensionable": False,
                    "insurable": False,
                    "regression_suite_hash": "b" * 64,
                    "notes": None,
                },
                "matrix-user",
            )
        except ValueError as exc:
            assert "approved" in str(exc)
        else:
            raise AssertionError("unapproved legal evidence must block matrix creation")


def test_matrix_entry_review_approval_and_readiness():
    with _session() as session:
        pack, source, evidence = _setup(session)
        entry = create_matrix_entry(
            session,
            {
                "rule_pack_version": pack.version,
                "component_code": evidence.component_code,
                "population_scope": "all",
                "treatment": "earning",
                "expression": {"op": "mul", "args": [{"op": "value", "name": "base"}, {"op": "value", "name": "rate"}]},
                "effective_from": date(2026, 1, 1),
                "effective_to": None,
                "legal_source_id": source.id,
                "legal_article": "1",
                "legal_clause": None,
                "taxable": True,
                "pensionable": False,
                "insurable": False,
                "regression_suite_hash": evidence.regression_suite_hash,
                "notes": None,
            },
            "matrix-creator",
        )
        session.commit()
        entry = session.get(CalculationMatrixRecord, entry.id)
        entry.reviewed_by = "matrix-reviewer"
        entry.reviewed_at = datetime(2026, 1, 4)
        entry.status = "reviewed"
        session.commit()
        approve_matrix_entry(entry, "matrix-approver")
        session.commit()
        readiness = matrix_readiness(session, pack.version)
        assert readiness.ready is True
        assert readiness.entry_count == 1


def test_matrix_readiness_blocks_missing_approval_provenance():
    with _session() as session:
        pack, source, evidence = _setup(session)
        entry = CalculationMatrixRecord(
            rule_pack_version=pack.version,
            component_code=evidence.component_code,
            population_scope="all",
            treatment="earning",
            expression={"op": "value", "name": "base"},
            effective_from=date(2026, 1, 1),
            legal_source_id=source.id,
            legal_article="1",
            taxable=True,
            pensionable=False,
            insurable=False,
            regression_suite_hash=evidence.regression_suite_hash,
            status="approved",
            reviewed_by="matrix-reviewer",
            reviewed_at=datetime(2026, 1, 4),
        )
        session.add(entry)
        session.commit()
        readiness = matrix_readiness(session, pack.version)
        assert readiness.ready is False
        assert any("approval provenance is incomplete" in item for item in readiness.blockers)


def test_empty_matrix_is_blocking():
    with _session() as session:
        session.add(RulePackRecord(version="1405.empty", status="approved"))
        session.commit()
        readiness = matrix_readiness(session, "1405.empty")
        assert readiness.ready is False
        assert "no calculation-matrix entries" in readiness.blockers[0]


def _resolver_case(pack, source, evidence):
    input_values = {"base": Decimal("2"), "rate": Decimal("3")}
    expected_output = {
        "code": evidence.component_code,
        "amount": "6.00",
        "legal_reference": source.citation,
        "rule_version": pack.version,
        "taxable": True,
        "pensionable": False,
        "insurable": True,
    }
    return RegressionCase(
        case_id="synthetic-matrix-case-001",
        rule_pack_version=pack.version,
        component_code=evidence.component_code,
        population_scope=evidence.population_scope,
        effective_date="jalali-source:1405-01-01",
        status="approved",
        input_values=input_values,
        expected_output=expected_output,
        input_fingerprint=fingerprint_values(input_values),
        expected_output_fingerprint=fingerprint_expected_result_payload(expected_output),
        legal_source_hash=source.document_hash,
        legal_article=evidence.article,
        legal_clause=evidence.clause,
    )


def _bind_case_to_test_repository(monkeypatch, case):
    monkeypatch.setattr(
        "morva.rules.calculation_matrix.load_cases",
        lambda _version: (case,),
    )
    monkeypatch.setattr(
        "morva.rules.calculation_matrix.regression_suite_hash",
        lambda _version: "b" * 64,
    )


def _calendar_dependencies(effective_on, *, source_override=None, verified=True):
    class _SyntheticCalendarAdapter:
        def resolve_jalali_date(self, source_value: str) -> CalendarDateResolution:
            return CalendarDateResolution(
                source_calendar="jalali",
                target_calendar="gregorian",
                source_value=source_override if source_override is not None else source_value,
                effective_on=effective_on,
                adapter_id="synthetic-calendar-adapter",
                adapter_version="test-1",
                authority_reference="synthetic-test-calendar-evidence",
                evidence_sha256="d" * 64,
                approval_status="approved",
                reviewed_by="synthetic-reviewer",
                reviewed_at=datetime(2030, 1, 1),
                approved_by="synthetic-approver",
                approved_at=datetime(2030, 1, 2),
            )

    class _SyntheticCalendarVerifier:
        def verify(self, resolution: CalendarDateResolution) -> bool:
            return verified and resolution.adapter_id == "synthetic-calendar-adapter"

    return _SyntheticCalendarAdapter(), _SyntheticCalendarVerifier()


def _resolve_rule_definition(session, case, *, effective_on, source_override=None, verified=True):
    adapter, verifier = _calendar_dependencies(
        effective_on,
        source_override=source_override,
        verified=verified,
    )
    return resolve_rule_definition_for_case(
        session,
        case,
        calendar_adapter=adapter,
        calendar_evidence_verifier=verifier,
    )


def _approved_matrix_entry(session, pack, source, evidence):
    entry = create_matrix_entry(
        session,
        {
            "rule_pack_version": pack.version,
            "component_code": evidence.component_code,
            "population_scope": evidence.population_scope,
            "treatment": "earning",
            "expression": {
                "op": "mul",
                "args": [
                    {
                        "op": "add",
                        "args": [
                            {"op": "value", "name": "base"},
                            {"op": "const", "value": "0"},
                        ],
                    },
                    {"op": "value", "name": "rate"},
                ],
            },
            "effective_from": date(2030, 1, 1),
            "effective_to": date(2030, 12, 31),
            "legal_source_id": source.id,
            "legal_article": evidence.article,
            "legal_clause": evidence.clause,
            "taxable": True,
            "pensionable": False,
            "insurable": True,
            "regression_suite_hash": evidence.regression_suite_hash,
            "notes": None,
        },
        "matrix-creator",
    )
    entry.reviewed_by = "matrix-reviewer"
    entry.reviewed_at = datetime(2030, 1, 2)
    entry.status = "reviewed"
    session.commit()
    entry = session.get(CalculationMatrixRecord, entry.id)
    approve_matrix_entry(entry, "matrix-approver")
    session.commit()
    return session.get(CalculationMatrixRecord, entry.id)


def test_resolver_maps_approved_golden_case_to_rule_engine_without_parsing_source_date(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        definition = _resolve_rule_definition(
            session,
            case,
            effective_on=date(2030, 12, 31),
        )
        result = RuleEngine([definition]).calculate(
            definition.code,
            RuleContext(date(2030, 12, 31), case.input_values),
            production=True,
            rule_pack_version=pack.version,
        )

        assert case.effective_date == "jalali-source:1405-01-01"
        assert definition.code == case.component_code
        assert definition.regression_case_ids == (case.case_id,)
        verify_expected_result(case, result)

def test_resolver_rejects_raw_date_bypass():
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)

        with pytest.raises(TypeError):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_calendar_source_value_mismatch(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(
            MatrixResolutionError,
            match="calendar source/evidence resolution is not trusted",
        ):
            _resolve_rule_definition(
                session,
                case,
                effective_on=date(2030, 6, 1),
                source_override="1405-01-02",
            )


def test_resolver_rejects_unverified_calendar_evidence(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(
            MatrixResolutionError,
            match="calendar source/evidence resolution is not trusted",
        ):
            _resolve_rule_definition(
                session,
                case,
                effective_on=date(2030, 6, 1),
                verified=False,
            )

def test_resolver_requires_exact_population_scope(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        case = replace(case, population_scope="not-the-approved-population")
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="no calculation-matrix mapping"):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_date_outside_matrix_effective_window(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="no calculation-matrix entry is effective"):
            _resolve_rule_definition(session, case, effective_on=date(2031, 1, 1))


def test_resolver_rejects_unapproved_rule_pack(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="reviewed")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="not activation-ready"):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_unapproved_matrix_entry(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        create_matrix_entry(
            session,
            {
                "rule_pack_version": pack.version,
                "component_code": evidence.component_code,
                "population_scope": evidence.population_scope,
                "treatment": "earning",
                "expression": {"op": "value", "name": "base"},
                "effective_from": date(2030, 1, 1),
                "effective_to": None,
                "legal_source_id": source.id,
                "legal_article": evidence.article,
                "legal_clause": evidence.clause,
                "taxable": True,
                "pensionable": False,
                "insurable": True,
                "regression_suite_hash": evidence.regression_suite_hash,
                "notes": None,
            },
            "matrix-creator",
        )
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="not approved"):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_matrix_selector_fails_closed_when_two_entries_overlap():
    with _session() as session:
        pack, source, evidence = _setup(session)
        entry = _approved_matrix_entry(session, pack, source, evidence)

        with pytest.raises(MatrixResolutionError, match="ambiguous calculation-matrix mapping"):
            _select_active_matrix_entry(
                [entry, entry],
                rule_pack_version=pack.version,
                component_code=evidence.component_code,
                population_scope=evidence.population_scope,
                effective_on=date(2030, 6, 1),
            )


def test_resolver_rejects_expected_output_metadata_that_disagrees_with_matrix(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        changed = dict(case.expected_output or {})
        changed["legal_reference"] = "different-source"
        case = replace(
            case,
            expected_output=changed,
            expected_output_fingerprint=fingerprint_expected_result_payload(changed),
        )
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="legal reference does not match"):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_golden_case_source_hash_mismatch(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = replace(_resolver_case(pack, source, evidence), legal_source_hash="d" * 64)
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(MatrixResolutionError, match="legal-source hash"):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


@pytest.mark.parametrize("missing_name", ["base", "rate"])
def test_resolver_rejects_missing_names_from_nested_rule_expressions(missing_name, monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        remaining_inputs = dict(case.input_values)
        remaining_inputs.pop(missing_name)
        case = replace(
            case,
            input_values=remaining_inputs,
            input_fingerprint=fingerprint_values(remaining_inputs),
        )
        _bind_case_to_test_repository(monkeypatch, case)

        with pytest.raises(
            MatrixResolutionError,
            match="missing required rule inputs",
        ):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_case_not_registered_in_canonical_repository(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        monkeypatch.setattr(
            "morva.rules.calculation_matrix.load_cases",
            lambda _version: (),
        )

        with pytest.raises(
            MatrixResolutionError,
            match="must occur exactly once in the canonical repository",
        ):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_case_payload_drift_from_canonical_repository(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        canonical_case = _resolver_case(pack, source, evidence)
        changed_values = {**canonical_case.input_values, "base": Decimal("999")}
        supplied_case = replace(
            canonical_case,
            input_values=changed_values,
            input_fingerprint=fingerprint_values(changed_values),
        )
        _bind_case_to_test_repository(monkeypatch, canonical_case)

        with pytest.raises(
            MatrixResolutionError,
            match="does not match its canonical repository entry",
        ):
            _resolve_rule_definition(session, supplied_case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_duplicate_case_ids_in_canonical_repository(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        monkeypatch.setattr(
            "morva.rules.calculation_matrix.load_cases",
            lambda _version: (case, case),
        )

        with pytest.raises(
            MatrixResolutionError,
            match="must occur exactly once in the canonical repository",
        ):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))


def test_resolver_rejects_stale_rule_evidence_suite_hash(monkeypatch):
    with _session() as session:
        pack, source, evidence = _setup(session, pack_status="approved")
        _approved_matrix_entry(session, pack, source, evidence)
        case = _resolver_case(pack, source, evidence)
        _bind_case_to_test_repository(monkeypatch, case)
        monkeypatch.setattr(
            "morva.rules.calculation_matrix.regression_suite_hash",
            lambda _version: "c" * 64,
        )

        with pytest.raises(
            MatrixResolutionError,
            match="regression suite hash does not match the canonical repository",
        ):
            _resolve_rule_definition(session, case, effective_on=date(2030, 6, 1))
