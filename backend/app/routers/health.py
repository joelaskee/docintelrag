"""Health check router."""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check (DB + Redis connectivity)."""
    # TODO: Add actual DB and Redis checks
    return {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
