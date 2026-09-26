from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_dr_runbook_and_script_are_present() -> None:
    runbook = (ROOT / "ops" / "DR_DRILL.md").read_text(encoding="utf-8")
    script = (ROOT / "ops" / "dr_drill.sh").read_text(encoding="utf-8")

    assert "MORVA_DATABASE_URL" in runbook
    assert "MORVA_DR_RESTORE_URL" in runbook
    assert "RTO" in runbook and "RPO" in runbook
    assert "pg_dump --format=custom" in script
    assert "pg_restore --list" in script
    assert "DRILL_OK" in script


def test_dr_operational_files_contain_no_literal_database_credentials() -> None:
    for path in (ROOT / "ops" / "DR_DRILL.md", ROOT / "ops" / "dr_drill.sh", ROOT / "ops" / "docker-compose.production.yml"):
        content = path.read_text(encoding="utf-8")
        assert "postgresql://morva:morva@" not in content
        assert "postgresql+psycopg://morva:morva@" not in content
