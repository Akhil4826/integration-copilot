"""Support Tickets API endpoints."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_ticket_service
from app.core.security import UserPrincipal, get_current_user
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.common import PaginatedResponse
from app.schemas.ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketUpdate,
    TicketFilterParams,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


@router.get("", response_model=PaginatedResponse[SupportTicketResponse])
def list_tickets(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
    status: Optional[TicketStatus] = Query(None, description="Filter by ticket status"),
    priority: Optional[TicketPriority] = Query(None, description="Filter by priority"),
    sort_by: str = Query("created_at", pattern="^(created_at|priority|status|ticket_id)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    service: TicketService = Depends(get_ticket_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve filtered and paginated support tickets."""
    filters = TicketFilterParams(
        customer_id=customer_id,
        order_id=order_id,
        status=status,
        priority=priority,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    offset = (page - 1) * limit
    items, total = service.filter_tickets(db, filters, offset=offset, limit=limit)
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse(
        items=[SupportTicketResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    service: TicketService = Depends(get_ticket_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve support ticket details by ticket ID."""
    ticket = service.get_ticket(db, ticket_id)
    return SupportTicketResponse.model_validate(ticket)


@router.post("", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: SupportTicketCreate,
    db: Session = Depends(get_db),
    service: TicketService = Depends(get_ticket_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Create a new support ticket."""
    ticket = service.create_ticket(db, data)
    return SupportTicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=SupportTicketResponse)
def update_ticket(
    ticket_id: str,
    data: SupportTicketUpdate,
    db: Session = Depends(get_db),
    service: TicketService = Depends(get_ticket_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Update support ticket fields (e.g. status or priority)."""
    ticket = service.update_ticket(db, ticket_id, data)
    return SupportTicketResponse.model_validate(ticket)
