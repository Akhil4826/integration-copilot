from app.db.database import get_db
from app.services.analytics_service import AnalyticsService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.ticket_service import TicketService

__all__ = [
    "get_db",
    "get_customer_service",
    "get_order_service",
    "get_ticket_service",
    "get_analytics_service",
]


def get_customer_service() -> CustomerService:
    return CustomerService()


def get_order_service() -> OrderService:
    return OrderService()


def get_ticket_service() -> TicketService:
    return TicketService()


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()
