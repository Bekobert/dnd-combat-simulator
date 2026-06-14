"""FastAPI application entry point.

Run with: uvicorn backend.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import combat

app = FastAPI(
    title="D&D Combat Simulator API",
    description="LLM-driven D&D 5e combat simulator — backend service.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(combat.router, prefix="/api/combat", tags=["combat"])


@app.get("/health")
async def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "version": app.version}
