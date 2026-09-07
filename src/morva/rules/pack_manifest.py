from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

from .rule_pack_1405 import REQUIRED_1405_COMPONENTS


class RulePackNotProductionReadyError(RuntimeError):
    """Raised when a rule pack cannot be used for production payroll."""


@dataclass(frozen=True, slots=True)
class RulePackManifest:
    version: str
    status: str
    authority: str
    source_documents: dict[str, str]
    components: tuple[str, ...]
    synthetic: bool = False

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "RulePackManifest":
        manifest = cls(
            version=str(payload.get("version", "")).strip(),
            status=str(payload.get("status", "")).strip().lower(),
            authority=str(payload.get("authority", "")).strip(),
            source_documents={str(k): str(v) for k, v in dict(payload.get("source_documents", {})).items()},
            components=tuple(str(item) for item in payload.get("components", ())),
            synthetic=bool(payload.get("synthetic", False)),
        )
        manifest.validate()
        return manifest

    @classmethod
    def load(cls, path: str | Path) -> "RulePackManifest":
        with Path(path).open(encoding="utf-8") as handle:
            return cls.from_mapping(json.load(handle))

    def validate(self) -> None:
        if not self.version or not self.version.startswith("1405."):
            raise ValueError("rule-pack manifest version must use the 1405.x format")
        if not self.authority:
            raise ValueError("rule-pack authority is required")
        missing = [code for code in REQUIRED_1405_COMPONENTS if code not in self.components]
        if missing:
            raise ValueError(f"rule-pack manifest is missing components: {', '.join(missing)}")
        if len(set(self.components)) != len(self.components):
            raise ValueError("rule-pack components must be unique")

    def assert_production_ready(self) -> None:
        if self.synthetic:
            raise RulePackNotProductionReadyError("synthetic rule packs are never production eligible")
        if self.status != "approved":
            raise RulePackNotProductionReadyError(
                f"rule pack {self.version} is not approved (status={self.status or 'unset'})"
            )
        missing = [code for code in REQUIRED_1405_COMPONENTS if not self.source_documents.get(code, "").strip()]
        if missing:
            raise RulePackNotProductionReadyError(
                f"authoritative source evidence is missing for: {', '.join(missing)}"
            )

    def component_coverage_hash(self) -> str:
        canonical = "|".join(sorted(self.components)).encode()
        return sha256(canonical).hexdigest()
