from contextlib import asynccontextmanager

from fastapi import FastAPI

from morva.api.v1.payroll import router as payroll_router
from morva.api.v1.rules import router as rules_router
from morva.api.v1.validation import router as validation_router
from morva.persistence.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Morva Payroll Platform",
    version="0.4.0",
    description="Rule-driven payroll platform for Iranian public-sector education.",
    lifespan=lifespan,
)
app.include_router(payroll_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(validation_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "morva-payroll", "version": "0.4.0"}
