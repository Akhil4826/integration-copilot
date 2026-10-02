"""Product data-access repository."""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product


class ProductRepository:
    """Encapsulates database operations for Product entity."""

    def get_by_product_id(self, db: Session, product_id: str) -> Optional[Product]:
        stmt = select(Product).where(Product.product_id == product_id.strip().upper())
        return db.execute(stmt).scalar_one_or_none()

    def list_products(
        self, db: Session, category: Optional[str] = None, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Product], int]:
        stmt = select(Product)
        if category:
            stmt = stmt.where(Product.category.ilike(category.strip()))

        all_matches = db.execute(stmt).scalars().all()
        total = len(all_matches)

        paginated_stmt = stmt.order_by(Product.name.asc()).offset(offset).limit(limit)
        items = list(db.execute(paginated_stmt).scalars().all())
        return items, total

    def get_top_products_by_sales(self, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """Calculate top products by total sales revenue excluding cancelled orders."""
        stmt = (
            select(
                Product.product_id,
                Product.name,
                Product.category,
                func.sum(OrderItem.quantity).label("total_units_sold"),
                func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
            )
            .join(OrderItem, Product.product_id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.order_id)
            .where(Order.status != OrderStatus.CANCELLED)
            .group_by(Product.product_id, Product.name, Product.category)
            .order_by(desc("total_revenue"))
            .limit(limit)
        )

        rows = db.execute(stmt).all()
        return [
            {
                "product_id": r.product_id,
                "name": r.name,
                "category": r.category,
                "total_units_sold": int(r.total_units_sold or 0),
                "total_revenue": round(float(r.total_revenue or 0.0), 2),
            }
            for r in rows
        ]

    def create(self, db: Session, product: Product) -> Product:
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
