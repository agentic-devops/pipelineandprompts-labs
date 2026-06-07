from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

from app.db.session import check_db_connection
from app.routers import shipments

SLOT    = os.getenv("SLOT", "blue")
VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(
    title="Waybill API",
    description="Shipment tracking and waybill management for logistics operations.",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(shipments.router)


@app.get("/health", tags=["ops"])
def health():
    """
    Health check used by smoke tests and load balancer.
    Returns 200 if app is running and DB is reachable.
    Returns 503 if DB connection fails — triggers DEGRADED alert tier.
    """
    db_ok = check_db_connection()
    payload = {
        "status":  "ok" if db_ok else "degraded",
        "slot":    SLOT,
        "version": VERSION,
        "db":      "connected" if db_ok else "unreachable",
    }
    return JSONResponse(
        content=payload,
        status_code=200 if db_ok else 503,
    )


@app.get("/", include_in_schema=False)
def root():
    return {"service": "waybill-api", "slot": SLOT, "version": VERSION}
