from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class ReplayCertificationRequest:
    artifact_id: str
    period: str
    personnel_snapshot_id: str
    personnel_snapshot_hash: str
    rule_pack_version: str
    rule_pack_hash: str
    input_hash: str
    expected_output_hash: str
    replay_output_hash: str
    replay_fingerprint: str
    certified_at: datetime
    reviewer_id: str
    approver_id: str
    status: str = "review_required"

    def validate(self) -> None:
        fields = (
            ("artifact_id", self.artifact_id), ("period", self.period),
            ("personnel_snapshot_id", self.personnel_snapshot_id),
            ("personnel_snapshot_hash", self.personnel_snapshot_hash),
            ("rule_pack_version", self.rule_pack_version), ("rule_pack_hash", self.rule_pack_hash),
            ("input_hash", self.input_hash), ("expected_output_hash", self.expected_output_hash),
            ("replay_output_hash", self.replay_output_hash), ("replay_fingerprint", self.replay_fingerprint),
            ("reviewer_id", self.reviewer_id), ("approver_id", self.approver_id),
        )
        for name, value in fields:
            if not value.strip():
                raise ValueError(f"{name} is required")
        for name, value in (
            ("personnel_snapshot_hash", self.personnel_snapshot_hash),
            ("rule_pack_hash", self.rule_pack_hash), ("input_hash", self.input_hash),
            ("expected_output_hash", self.expected_output_hash), ("replay_output_hash", self.replay_output_hash),
            ("replay_fingerprint", self.replay_fingerprint),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
                raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
        if self.certified_at.tzinfo is None:
            raise ValueError("certified_at must be timezone-aware")
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise ValueError("reviewer and approver must be distinct")
        if self.status not in {"review_required", "certified"}:
            raise ValueError("status must be review_required or certified")

    def execution_ready(self) -> bool:
        try:
            self.validate()
        except ValueError:
            return False
        return self.status == "certified" and self.expected_output_hash.lower() == self.replay_output_hash.lower()

    def certification_fingerprint(self) -> str:
        self.validate()
        canonical = "|".join((
            self.artifact_id.strip(), self.period.strip(), self.personnel_snapshot_id.strip(),
            self.personnel_snapshot_hash.lower(), self.rule_pack_version.strip(), self.rule_pack_hash.lower(),
            self.input_hash.lower(), self.expected_output_hash.lower(), self.replay_output_hash.lower(),
            self.replay_fingerprint.lower(), self.certified_at.isoformat(), self.reviewer_id.strip(),
            self.approver_id.strip(), self.status,
        ))
        return sha256(canonical.encode("utf-8")).hexdigest()
