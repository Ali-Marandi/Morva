from datetime import datetime, timezone

from morva.rules.primary_source_evidence import (
    PrimarySourceEvidenceRequest,
    evidence_content_sha256,
    validate_primary_source_evidence,
)


def _request(**overrides):
    payload = {
        "source_id": "TAX-1405",
        "citation": "قانون بودجه سال 1405 کل کشور",
        "issuer": "مرجع قانونی صادرکننده",
        "source_uri": "https://example.gov.ir/document/1405",
        "document_hash": "a" * 64,
        "adoption_date": "1404-12-25",
        "effective_from": "1405-01-01",
        "effective_to": None,
        "retrieved_at": datetime(2026, 9, 13, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return PrimarySourceEvidenceRequest(**payload)


def test_valid_primary_source_evidence_is_accepted():
    result = validate_primary_source_evidence(_request())
    assert result.accepted is True
    assert result.blockers == ()


def test_source_uri_must_be_https():
    result = validate_primary_source_evidence(_request(source_uri="http://example.gov.ir/document"))
    assert result.accepted is False
    assert "source_uri must be an absolute HTTPS URI" in result.blockers


def test_hash_must_be_sha256_hex():
    result = validate_primary_source_evidence(_request(document_hash="not-a-hash"))
    assert result.accepted is False
    assert "document_hash must be a 64-character SHA-256 hex digest" in result.blockers


def test_retrieval_timestamp_is_required_for_provenance():
    result = validate_primary_source_evidence(_request(retrieved_at=None))
    assert result.accepted is False
    assert "retrieved_at is required for provenance" in result.blockers


def test_content_digest_is_deterministic_sha256():
    assert evidence_content_sha256(b"morva") == "90a93c6e4b688b674949dc7d8a0a3a4fb8fdd6d58183fe13fc6413d4dbc041bf"
