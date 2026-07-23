"""
Health check router — GET /health

Used by Docker health checks and load balancers to verify the service is up.
"""

from fastapi import APIRouter, HTTPException

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import HealthResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="Service health check")
def health_check() -> HealthResponse:
    """
    Return service health status and active model name.

    Returns:
        HealthResponse: Status, model name, and current timestamp.

    Raises:
        HTTPException: 500 if health check encounters an unexpected error.
    """
    try:
        logger.info("Health check called")
        return HealthResponse(status="ok", model=settings.groq_model)
    except Exception as exc:
        logger.error("Health check failed | error=%s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Health check error: {exc}")
