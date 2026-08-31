from fastapi import FastAPI

from morva.api.v1.payroll import router as payroll_router
from morva.api.v1.rules import router as rules_router

app = FastAPI(
    title="Morva Payroll Platform",
    version="0.3.0",
    description="Rule-driven payroll foundation for Iranian public-sector education payroll.",
)
app.include_router(payroll_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "morva-payroll", "version": "0.3.0"}
