"""Orders API endpoints."""

import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_order_service
from app.core.security import UserPrincipal, get_current_user
from app.models.order import OrderStatus
from app.schemas.common import PaginatedResponse
from app.schemas.order import (
    OrderCreate,
    OrderFilterParams,
    OrderResponse,
    OrderUpdate,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    start_date: Optional[datetime] = Query(
        None, description="Filter orders created on or after date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter orders created on or before date"
    ),
    minimum_amount: Optional[float] = Query(None, ge=0, description="Minimum order total amount"),
    maximum_amount: Optional[float] = Query(None, ge=0, description="Maximum order total amount"),
    sort_by: str = Query("created_at", pattern="^(created_at|total_amount|status|order_id)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve filtered and paginated list of orders."""
    filters = OrderFilterParams(
        status=status,
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
        minimum_amount=minimum_amount,
        maximum_amount=maximum_amount,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    offset = (page - 1) * limit
    items, total = service.filter_orders(db, filters, offset=offset, limit=limit)
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve order details by order ID."""
    order = service.get_order(db, order_id)
    return OrderResponse.model_validate(order)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Create a new order with line items."""
    order = service.create_order(db, data)
    return OrderResponse.model_validate(order)


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Update status of an existing order."""
    if data.status is None:
        return OrderResponse.model_validate(service.get_order(db, order_id))
    order = service.update_order_status(db, order_id, data.status)
    return OrderResponse.model_validate(order)
