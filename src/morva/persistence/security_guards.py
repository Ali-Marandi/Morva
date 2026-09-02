from __future__ import annotations

from sqlalchemy import event

from morva.persistence.models import EmployeeRecord


@event.listens_for(EmployeeRecord, "before_insert")
@event.listens_for(EmployeeRecord, "before_update")
def reject_plaintext_sensitive_identity(_mapper, _connection, target: EmployeeRecord) -> None:
    from morva.runtime.config import settings
    if settings.production and target.national_id:
        raise ValueError("plaintext national_id writes are forbidden in production; use SensitiveIdentityRecord")
