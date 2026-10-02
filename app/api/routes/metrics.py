"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from app.core.metrics import get_metrics_data

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
def metrics():
    """Prometheus-compatible scraping endpoint."""
    data, content_type = get_metrics_data()
    return Response(content=data, media_type=content_type)
