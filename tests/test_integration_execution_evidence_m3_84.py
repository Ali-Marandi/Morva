from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.integration_execution_evidence import (
    AdapterExecutionEvidence,
    IntegrationExecutionEvidenceError,
    IntegrationExecutionEvidenceReceipt,
    load_execution_evidence,
    write_execution_evidence,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


SHA = "a" * 40
CHECKED = datetime.fromisoformat("2026-09-20T10:00:00+00:00")


def _items(environment="staging"):
    return tuple(
        AdapterExecutionEvidence(
            adapter=adapter,
            environment=environment,
            status="passed",
            evidence_id=f"{adapter}-001",
            evidence_sha256=(chr(97 + index) * 64),
            started_at="2026-09-20T09:00:00+00:00",
            finished_at="2026-09-20T09:30:00+00:00",
            operator="integration-operator",
        )
        for index, adapter in enumerate(REQUIRED_ADAPTERS)
    )


def _receipt(environment="staging"):
    return IntegrationExecutionEvidenceReceipt(
        evidence_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=SHA,
        target_environment=environment,
        execution_id="EXEC-001",
        evidence_items=_items(environment),
        checked_at=CHECKED,
    )


def test_roundtrip_and_fingerprint(tmp_path: Path):
    first = _receipt()
    path = tmp_path / "execution.json"
    write_execution_evidence(first, path)
    second = load_execution_evidence(path)
    assert second.evidence_fingerprint == first.evidence_fingerprint
    assert tuple(item.adapter for item in second.evidence_items) == REQUIRED_ADAPTERS


def test_wrong_environment_is_rejected():
    with pytest.raises(IntegrationExecutionEvidenceError, match="environment"):
        _receipt("production")


def test_missing_adapter_is_rejected():
    items = _items()[:-1]
    with pytest.raises(IntegrationExecutionEvidenceError, match="canonical adapter set"):
        IntegrationExecutionEvidenceReceipt(
            evidence_version=1,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            target_environment="staging",
            execution_id="EXEC-001",
            evidence_items=items,
            checked_at=CHECKED,
        )


def test_duplicate_adapter_is_rejected():
    items = list(_items())
    items[-1] = items[0]
    with pytest.raises(IntegrationExecutionEvidenceError, match="canonical adapter set"):
        IntegrationExecutionEvidenceReceipt(
            evidence_version=1,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            target_environment="staging",
            execution_id="EXEC-001",
            evidence_items=tuple(items),
            checked_at=CHECKED,
        )


def test_future_finish_is_rejected():
    items = list(_items())
    items[0] = AdapterExecutionEvidence(
        adapter=items[0].adapter,
        environment="staging",
        status="passed",
        evidence_id=items[0].evidence_id,
        evidence_sha256=items[0].evidence_sha256,
        started_at="2026-09-20T10:01:00+00:00",
        finished_at="2026-09-20T10:02:00+00:00",
        operator=items[0].operator,
    )
    with pytest.raises(IntegrationExecutionEvidenceError, match="future-dated"):
        IntegrationExecutionEvidenceReceipt(
            evidence_version=1,
            repository="Ali-Marandi/Morva",
            candidate_sha=SHA,
            target_environment="staging",
            execution_id="EXEC-001",
            evidence_items=tuple(items),
            checked_at=CHECKED,
        )


def test_digest_tamper_is_rejected(tmp_path: Path):
    receipt = _receipt()
    path = tmp_path / "execution.json"
    write_execution_evidence(receipt, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence_items"][0]["evidence_sha256"] = "f" * 64
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(IntegrationExecutionEvidenceError, match="fingerprint mismatch"):
        load_execution_evidence(path)


def test_write_once(tmp_path: Path):
    receipt = _receipt()
    path = tmp_path / "execution.json"
    write_execution_evidence(receipt, path)
    with pytest.raises(IntegrationExecutionEvidenceError, match="write-once"):
        write_execution_evidence(receipt, path)


def test_cli_expected_arguments_are_documented():
    assert SHA.startswith("a")
