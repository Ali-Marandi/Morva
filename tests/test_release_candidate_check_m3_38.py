from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.m3_38_release_candidate_check import load_certification, main


NOW = datetime(2026, 9, 17, 17, 30, tzinfo=timezone.utc).isoformat()
REQUIRED = ("security-report", "dr-evidence", "load-evidence", "reconciliation-evidence")


def payload() -> dict[str, object]:
    return {
        "release_id": "morva-1.0.1",
        "candidate_sha": "a" * 40,
        "required_evidence": list(REQUIRED),
        "verified_evidence": list(REQUIRED),
        "security_signoff_complete": True,
        "disaster_recovery_signoff_complete": True,
        "load_signoff_complete": True,
        "reconciliation_signoff_complete": True,
        "signoffs": [
            {"role": "finance", "signer": "finance", "signed_at": NOW, "evidence_uri": "e://finance"},
            {"role": "legal", "signer": "legal", "signed_at": NOW, "evidence_uri": "e://legal"},
            {"role": "operations", "signer": "operations", "signed_at": NOW, "evidence_uri": "e://operations"},
        ],
    }


def test_load_certification_accepts_timezone_aware_json(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")

    certification = load_certification(path)

    assert certification.release_ready is True
    assert certification.candidate_sha == "a" * 40


def test_main_rejects_candidate_sha_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["m3_38_release_candidate_check", str(path), "--expected-sha", "b" * 40])

    with pytest.raises(SystemExit, match="candidate_sha does not match"):
        main()


def test_main_accepts_matching_release_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["m3_38_release_candidate_check", str(path), "--expected-sha", "a" * 40])

    assert main() == 0
    output = capsys.readouterr().out
    assert "release certification verified" in output
    assert "candidate_sha=" in output
    assert "fingerprint=" in output


def test_load_certification_keeps_release_fail_closed_when_evidence_missing(tmp_path: Path) -> None:
    data = payload()
    data["verified_evidence"] = list(REQUIRED[:-1])
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    certification = load_certification(path)

    assert certification.release_ready is False
    assert certification.missing_evidence == (REQUIRED[-1],)
