from __future__ import annotations

from fastapi import APIRouter, Depends

from morva.masterdata.validation import validate_master_data
from morva.persistence.database import SessionLocal
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import has_permission, authorize

router = APIRouter(prefix="/master-data", tags=["master-data-validation"])


def _authorize_read(principal: Principal) -> None:
    if not has_permission(principal, "personnel.read"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="required permission not granted")
    authorize(principal, "personnel.read", principal.scope)


@router.get("/integrity")
def get_master_data_integrity(
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize_read(principal)
    with SessionLocal() as session:
        return validate_master_data(session).as_dict()
