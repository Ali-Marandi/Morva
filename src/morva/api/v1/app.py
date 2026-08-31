from fastapi import FastAPI

from .payroll import router as payroll_router

app = FastAPI(title="Morva Payroll API", version="1.0.0")
app.include_router(payroll_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "morva-payroll-api"}
