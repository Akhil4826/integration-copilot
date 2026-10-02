"""Customers API endpoints."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_customer_service, get_db
from app.core.security import UserPrincipal, get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    query: Optional[str] = Query(None, description="Search term for name, ID, or email"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    service: CustomerService = Depends(get_customer_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """List or search customers with pagination."""
    offset = (page - 1) * limit
    items, total = service.search_customers(db, query=query, offset=offset, limit=limit)
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    service: CustomerService = Depends(get_customer_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Retrieve customer details by customer ID."""
    customer = service.get_customer(db, customer_id)
    return CustomerResponse.model_validate(customer)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    service: CustomerService = Depends(get_customer_service),
    current_user: UserPrincipal = Depends(get_current_user),
):
    """Create a new customer."""
    customer = service.create_customer(db, data)
    return CustomerResponse.model_validate(customer)
