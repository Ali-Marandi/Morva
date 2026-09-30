from __future__ import annotations

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_68_verification_history_integrity_m4_69 import (
    HistoricalM468VerificationHistoryIntegrityRepository,
    HistoricalM468VerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_67_verification_persistence_m4_68 import (
    IndependentHistoricalM466VerificationPersistenceReceiptRecord,
    IndependentHistoricalM466VerificationPersistenceReceiptRepository,
)
from morva.runtime.independent_historical_m4_69_verification_m4_70 import (
    IndependentHistoricalM469VerificationError,
    independently_verify_historical_m4_69_verification_history_integrity,
)
from tests.test_historical_m4_68_verification_history_integrity_m4_69 import (
    _persist_m4_68_result,
    _session_m4_69,
)


def test_m4_70_independently_verifies_m4_69_snapshot():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_records = list(
            session.scalars(
                select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
            ).all()
        )
        verification = independently_verify_historical_m4_69_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is True
        assert verification.snapshot_id == snapshot.id
        assert verification.persisted_fingerprint == verification.reconstructed_fingerprint
        assert len(verification.verification_fingerprint) == 64
    finally:
        session.close()
        engine.dispose()


def test_m4_70_honors_point_in_time_boundary():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session, "a" * 64)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_68_result(session, "b" * 64)
        source_records = list(
            session.scalars(
                select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
            ).all()
        )
        verification = independently_verify_historical_m4_69_verification_history_integrity(
            snapshot=first,
            source_records=source_records,
        )
        assert verification.valid is True
        assert verification.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_70_detects_tampered_source_result():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        source = session.scalars(
            select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        source_records = list(
            session.scalars(
                select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM469VerificationError,
            match="M4.68 source verification result is structurally invalid",
        ):
            independently_verify_historical_m4_69_verification_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_70_emits_deterministic_mismatch_blockers():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        snapshot.record_count = 2
        snapshot.valid_count = 2
        session.flush()
        source_records = list(
            session.scalars(
                select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
            ).all()
        )
        verification = independently_verify_historical_m4_69_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is False
        assert verification.blockers == (
            "M470_RECORD_COUNT_MISMATCH",
            "M470_VALID_COUNT_MISMATCH",
        )
    finally:
        session.close()
        engine.dispose()
