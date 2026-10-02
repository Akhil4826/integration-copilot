"""Analytics tools for MCP server."""

from datetime import datetime
from typing import Any, Dict, Optional

from app.db.database import SessionLocal
from app.services.analytics_service import AnalyticsService

analytics_service = AnalyticsService()


def register_analytics_tools(server):
    @server.tool(
        name="get_order_statistics",
        description=(
            "Calculate aggregate order statistics and revenue metrics. "
            "Returns total orders, successful orders, failed orders, cancelled orders, "
            "total revenue, and average order value. Optional start_date and end_date in ISO format. "
            "Use when the user asks for summaries of order activity, revenue figures, or performance stats."
        ),
    )
    def get_order_statistics(
        start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aggregate order statistics."""
        db = SessionLocal()
        try:
            s_date = None
            if start_date:
                try:
                    s_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except ValueError:
                    return {"error": f"Invalid start_date '{start_date}'", "code": "INVALID_DATE"}

            e_date = None
            if end_date:
                try:
                    e_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                except ValueError:
                    return {"error": f"Invalid end_date '{end_date}'", "code": "INVALID_DATE"}

            return analytics_service.get_order_statistics(db, start_date=s_date, end_date=e_date)
        finally:
            db.close()

    @server.tool(
        name="get_top_products",
        description=(
            "Retrieve the top selling products ranked by revenue. "
            "Returns product ID, name, category, total units sold, and total revenue. "
            "Use when asked about top products, best sellers, or highest grossing items."
        ),
    )
    def get_top_products(limit: int = 5) -> Dict[str, Any]:
        """Retrieve top products by sales."""
        db = SessionLocal()
        try:
            clamped = max(1, min(limit, 20))
            products = analytics_service.get_top_products(db, limit=clamped)
            return {"count": len(products), "top_products": products}
        finally:
            db.close()
