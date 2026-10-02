"""Analytics API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_analytics_service, get_db
from app.core.security import UserPrincipal, get_current_user
from app.schemas.analytics import (
    OrderStatisticsResponse,
    RevenueSummaryResponse,
    TopProductResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/orders", response_model=OrderStatisticsResponse)
def get_order_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for order metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for order metrics"),
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve aggregated order metrics, breakdown by status, and average order value."""
    stats = service.get_order_statistics(db, start_date=start_date, end_date=end_date)
    return OrderStatisticsResponse(**stats)


@router.get("/revenue", response_model=RevenueSummaryResponse)
def get_revenue_summary(
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve comprehensive revenue metrics and category performance."""
    summary = service.get_revenue_summary(db)
    return RevenueSummaryResponse(**summary)


@router.get("/products", response_model=List[TopProductResponse])
def get_top_products(
    limit: int = Query(5, ge=1, le=50, description="Number of top products to retrieve"),
    db: Session = Depends(get_db),
    service: AnalyticsService = Depends(get_analytics_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve top selling products ranked by revenue."""
    top_prods = service.get_top_products(db, limit=limit)
    return [TopProductResponse(**p) for p in top_prods]
