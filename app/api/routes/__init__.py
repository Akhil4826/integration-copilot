"""API routes package."""

from app.api.routes.agent import router as agent_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.customers import router as customers_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.orders import router as orders_router
from app.api.routes.tickets import router as tickets_router

__all__ = [
    "health_router",
    "metrics_router",
    "customers_router",
    "orders_router",
    "tickets_router",
    "analytics_router",
    "agent_router",
]
