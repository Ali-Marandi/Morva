from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
from morva.runtime.release_certification import CertificationSignoff, ReleaseCertification
from morva.runtime.release_gate import ReleaseGate
from morva.runtime.security_assessment import SecurityAssessment, SecurityFinding


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed


def load_release_gate(path: Path) -> ReleaseGate:
    payload = json.loads(path.read_text(encoding="utf-8"))
    security_payload = payload["security_assessment"]
    security = SecurityAssessment(
        assessment_id=security_payload["assessment_id"],
        assessed_at=_dt(security_payload["assessed_at"]),
        scope_hash=security_payload["scope_hash"],
        required_controls=tuple(security_payload["required_controls"]),
        verified_controls=tuple(security_payload["verified_controls"]),
        findings=tuple(
            SecurityFinding(**finding) for finding in security_payload.get("findings", ())
        ),
        independent_assessor=security_payload.get("independent_assessor"),
        independent_report_uri=security_payload.get("independent_report_uri"),
        independent_signed_at=(
            _dt(security_payload["independent_signed_at"])
            if security_payload.get("independent_signed_at")
            else None
        ),
    )

    certification_payload = payload["certification"]
    certification = ReleaseCertification(
        release_id=certification_payload["release_id"],
        candidate_sha=certification_payload["candidate_sha"],
        required_evidence=tuple(certification_payload["required_evidence"]),
        verified_evidence=tuple(certification_payload["verified_evidence"]),
        security_signoff_complete=bool(
            certification_payload.get("security_signoff_complete", False)
        ),
        disaster_recovery_signoff_complete=bool(
            certification_payload.get("disaster_recovery_signoff_complete", False)
        ),
        load_signoff_complete=bool(certification_payload.get("load_signoff_complete", False)),
        reconciliation_signoff_complete=bool(
            certification_payload.get("reconciliation_signoff_complete", False)
        ),
        signoffs=tuple(
            CertificationSignoff(
                role=item["role"],
                signer=item["signer"],
                signed_at=_dt(item["signed_at"]),
                evidence_uri=item["evidence_uri"],
            )
            for item in certification_payload.get("signoffs", ())
        ),
    )

    attestation_payload = payload["attestation"]
    attestation = ReleaseAttestation(
        release_id=attestation_payload["release_id"],
        tag=attestation_payload["tag"],
        candidate_sha=attestation_payload["candidate_sha"],
        certification_fingerprint=attestation_payload["certification_fingerprint"],
        evidence_bundle_fingerprint=attestation_payload["evidence_bundle_fingerprint"],
        artifacts=tuple(
            ArtifactAttestation(**artifact) for artifact in attestation_payload["artifacts"]
        ),
        signer=attestation_payload.get("signer"),
        signed_at=(
            _dt(attestation_payload["signed_at"])
            if attestation_payload.get("signed_at")
            else None
        ),
        signature_uri=attestation_payload.get("signature_uri"),
        release_uri=attestation_payload.get("release_uri"),
    )
    return ReleaseGate(payload["candidate_sha"], security, certification, attestation)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the aggregate Morva release gate")
    parser.add_argument("evidence_file", type=Path)
    args = parser.parse_args()

    gate = load_release_gate(args.evidence_file)
    gate.assert_release_ready()
    print("M3.40 release gate passed")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"fingerprint={gate.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
