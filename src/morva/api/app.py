from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from morva.api.v1.imports import router as imports_router
from morva.api.v1.payroll import router as payroll_router
from morva.api.v1.reconciliation import router as reconciliation_router
from morva.api.v1.rules import router as rules_router
from morva.api.v1.validation import router as validation_router
from morva.persistence.database import init_db
from morva.runtime.config import settings
from morva.security.auth import get_current_principal


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate()
    init_db()
    yield


app = FastAPI(title="Morva Payroll Platform", version="1.0.0-rc1", description="Production-oriented payroll platform for Iranian public-sector education.", lifespan=lifespan)
protected_dependencies = [Depends(get_current_principal)]
app.include_router(payroll_router, prefix="/api/v1", dependencies=protected_dependencies)
app.include_router(imports_router, prefix="/api/v1", dependencies=protected_dependencies)
app.include_router(reconciliation_router, prefix="/api/v1", dependencies=protected_dependencies)
app.include_router(rules_router, prefix="/api/v1", dependencies=protected_dependencies)
app.include_router(validation_router, prefix="/api/v1", dependencies=protected_dependencies)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "morva-payroll", "version": "1.0.0-rc1"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, object]:
    settings.validate()
    return {"status": "ready", "environment": settings.environment, "database": "configured", "integrations_enabled": settings.integrations_enabled, "mfa_required": settings.require_mfa}
