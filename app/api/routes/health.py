"""Health and readiness checks."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: verifies service process is running."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check(
    response: Response,
    db: Session = Depends(get_db),
):
    """Readiness probe: verifies database connectivity and core subsystems."""
    checks = {
        "status": "ready",
        "database": "unknown",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"error: {str(exc)}"
        checks["status"] = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return checks
