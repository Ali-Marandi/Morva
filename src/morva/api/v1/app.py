from fastapi import FastAPI

from .cases import router as cases_router
from .imports import router as imports_router
from .payroll import router as payroll_router
from .self_service import router as self_service_router

app = FastAPI(title="Morva Payroll API", version="1.0.0")
app.include_router(payroll_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")
app.include_router(self_service_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "morva-payroll-api"}
