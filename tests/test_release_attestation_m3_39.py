from datetime import datetime, timezone

import pytest

from morva.runtime.release_attestation import (
    ArtifactAttestation,
    ReleaseAttestation,
    ReleaseAttestationError,
)


NOW = datetime(2026, 9, 17, 18, 0, tzinfo=timezone.utc)


def artifacts():
    return (
        ArtifactAttestation("dist/morva-1.0.1.whl", "a" * 64),
        ArtifactAttestation("dist/morva-1.0.1.tar.gz", "b" * 64),
    )


def complete_attestation():
    return ReleaseAttestation(
        release_id="morva-1.0.1",
        tag="v1.0.1",
        candidate_sha="c" * 40,
        certification_fingerprint="d" * 64,
        evidence_bundle_fingerprint="e" * 64,
        artifacts=artifacts(),
        signer="release-signer",
        signed_at=NOW,
        signature_uri="evidence://signature/v1.0.1",
        release_uri="https://github.com/Ali-Marandi/Morva/releases/tag/v1.0.1",
    )


def test_release_attestation_fails_closed_without_signing_or_release_evidence():
    attestation = ReleaseAttestation(
        release_id="morva-1.0.1",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        certification_fingerprint="b" * 64,
        evidence_bundle_fingerprint="c" * 64,
        artifacts=(),
    )

    assert attestation.release_ready is False
    with pytest.raises(ReleaseAttestationError, match="release signing evidence is incomplete"):
        attestation.assert_release_ready()


def test_complete_release_attestation_is_ready_and_deterministic():
    first = complete_attestation()
    second = complete_attestation()

    assert first.release_ready is True
    first.assert_release_ready()
    assert first.fingerprint == second.fingerprint


def test_release_attestation_rejects_duplicate_artifacts():
    duplicate = ArtifactAttestation("dist/morva.whl", "a" * 64)
    with pytest.raises(ReleaseAttestationError, match="artifact paths must be unique"):
        ReleaseAttestation(
            release_id="morva-1.0.1",
            tag="v1.0.1",
            candidate_sha="a" * 40,
            certification_fingerprint="b" * 64,
            evidence_bundle_fingerprint="c" * 64,
            artifacts=(duplicate, duplicate),
        )


def test_release_attestation_rejects_invalid_hashes_and_naive_timestamps():
    with pytest.raises(ReleaseAttestationError, match="SHA-256"):
        ArtifactAttestation("dist/morva.whl", "not-a-hash")

    with pytest.raises(ReleaseAttestationError, match="timezone-aware"):
        ReleaseAttestation(
            release_id="morva-1.0.1",
            tag="v1.0.1",
            candidate_sha="a" * 40,
            certification_fingerprint="b" * 64,
            evidence_bundle_fingerprint="c" * 64,
            artifacts=artifacts(),
            signer="release-signer",
            signed_at=datetime(2026, 9, 17, 18, 0),
            signature_uri="evidence://signature/v1.0.1",
            release_uri="evidence://release/v1.0.1",
        )
