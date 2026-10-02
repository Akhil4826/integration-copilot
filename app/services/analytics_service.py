"""Analytics business service layer."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository


class AnalyticsService:
    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        product_repo: Optional[ProductRepository] = None,
    ):
        self.order_repo = order_repo or OrderRepository()
        self.product_repo = product_repo or ProductRepository()

    def get_order_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return self.order_repo.get_order_statistics(db, start_date=start_date, end_date=end_date)

    def get_top_products(self, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        return self.product_repo.get_top_products_by_sales(db, limit=limit)

    def get_revenue_summary(self, db: Session) -> Dict[str, Any]:
        stats = self.order_repo.get_order_statistics(db)
        top_products = self.product_repo.get_top_products_by_sales(db, limit=10)

        # Category revenue breakdown
        cat_map: Dict[str, float] = {}
        for p in top_products:
            cat_map[p["category"]] = cat_map.get(p["category"], 0.0) + p["total_revenue"]

        categories = [
            {"category": cat, "revenue": round(rev, 2)}
            for cat, rev in sorted(cat_map.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "total_revenue": stats["total_revenue"],
            "delivered_revenue": stats["total_revenue"],
            "lost_revenue_failed": round(stats["failed_orders"] * stats["average_order_value"], 2),
            "total_orders": stats["total_orders"],
            "top_categories": categories,
        }
