"""Schemas package exports."""

from app.schemas.analytics import (
    OrderStatisticsResponse,
    RevenueSummaryResponse,
    TopProductResponse,
)
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.customer import CustomerBase, CustomerCreate, CustomerResponse
from app.schemas.order import (
    OrderBase,
    OrderCreate,
    OrderFilterParams,
    OrderItemBase,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
    OrderUpdate,
)
from app.schemas.product import ProductBase, ProductCreate, ProductResponse
from app.schemas.ticket import (
    SupportTicketBase,
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketUpdate,
    TicketFilterParams,
)

__all__ = [
    "PaginationParams",
    "PaginatedResponse",
    "CustomerBase",
    "CustomerCreate",
    "CustomerResponse",
    "ProductBase",
    "ProductCreate",
    "ProductResponse",
    "OrderItemBase",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderBase",
    "OrderCreate",
    "OrderUpdate",
    "OrderResponse",
    "OrderFilterParams",
    "SupportTicketBase",
    "SupportTicketCreate",
    "SupportTicketUpdate",
    "SupportTicketResponse",
    "TicketFilterParams",
    "OrderStatisticsResponse",
    "TopProductResponse",
    "RevenueSummaryResponse",
]
