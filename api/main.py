"""
main.py — FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import advisers, changes

app = FastAPI(
    title="SEC Investment Adviser Monitor API",
    description="Track month-over-month changes in SEC-registered investment advisers.",
    version="1.0.0",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(advisers.router, prefix="/api")
app.include_router(changes.router, prefix="/api")


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}


@app.get("/api", tags=["meta"])
async def api_root() -> dict[str, str]:
    """API root with version info."""
    return {
        "name": "SEC Investment Adviser Monitor API",
        "version": "1.0.0",
        "docs": "/docs",
    }
