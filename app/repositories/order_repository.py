"""Order data-access repository."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.schemas.order import OrderFilterParams


class OrderRepository:
    """Encapsulates database operations for Order and OrderItem entities."""

    def get_by_order_id(self, db: Session, order_id: str) -> Optional[Order]:
        stmt = (
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.order_id == order_id.strip().upper())
        )
        return db.execute(stmt).unique().scalar_one_or_none()

    def get_customer_orders(self, db: Session, customer_id: str, limit: int = 10) -> List[Order]:
        stmt = (
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.customer_id == customer_id.strip().upper())
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(db.execute(stmt).unique().scalars().all())

    def filter_orders(
        self,
        db: Session,
        filters: OrderFilterParams,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        stmt = select(Order).options(joinedload(Order.items))

        if filters.status:
            stmt = stmt.where(Order.status == filters.status)
        if filters.customer_id:
            stmt = stmt.where(Order.customer_id == filters.customer_id.strip().upper())
        if filters.start_date:
            stmt = stmt.where(Order.created_at >= filters.start_date)
        if filters.end_date:
            stmt = stmt.where(Order.created_at <= filters.end_date)
        if filters.minimum_amount is not None:
            stmt = stmt.where(Order.total_amount >= filters.minimum_amount)
        if filters.maximum_amount is not None:
            stmt = stmt.where(Order.total_amount <= filters.maximum_amount)

        # Count total matches
        count_stmt = select(func.count(Order.id))
        if filters.status:
            count_stmt = count_stmt.where(Order.status == filters.status)
        if filters.customer_id:
            count_stmt = count_stmt.where(Order.customer_id == filters.customer_id.strip().upper())
        if filters.start_date:
            count_stmt = count_stmt.where(Order.created_at >= filters.start_date)
        if filters.end_date:
            count_stmt = count_stmt.where(Order.created_at <= filters.end_date)
        if filters.minimum_amount is not None:
            count_stmt = count_stmt.where(Order.total_amount >= filters.minimum_amount)
        if filters.maximum_amount is not None:
            count_stmt = count_stmt.where(Order.total_amount <= filters.maximum_amount)

        total = db.execute(count_stmt).scalar() or 0

        # Apply sorting
        sort_col = getattr(Order, filters.sort_by, Order.created_at)
        if filters.sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_col))
        else:
            stmt = stmt.order_by(sort_col.asc())

        stmt = stmt.offset(offset).limit(limit)
        items = list(db.execute(stmt).unique().scalars().all())
        return items, total

    def create_order(self, db: Session, order: Order, items: List[OrderItem]) -> Order:
        try:
            db.add(order)
            db.flush()
            for item in items:
                db.add(item)
            db.commit()
            return self.get_by_order_id(db, order.order_id) or order
        except Exception:
            db.rollback()
            raise

    def update_order_status(
        self, db: Session, order_id: str, new_status: OrderStatus
    ) -> Optional[Order]:
        order = self.get_by_order_id(db, order_id)
        if not order:
            return None
        order.status = new_status
        db.commit()
        db.refresh(order)
        return order

    def get_order_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate summary metrics across orders."""
        stmt = select(Order)
        if start_date:
            stmt = stmt.where(Order.created_at >= start_date)
        if end_date:
            stmt = stmt.where(Order.created_at <= end_date)

        orders = list(db.execute(stmt).scalars().all())
        total_orders = len(orders)
        successful_orders = sum(
            1 for o in orders if o.status in (OrderStatus.DELIVERED, OrderStatus.SHIPPED)
        )
        failed_orders = sum(1 for o in orders if o.status == OrderStatus.FAILED)
        cancelled_orders = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        pending_orders = sum(
            1 for o in orders if o.status in (OrderStatus.PENDING, OrderStatus.PROCESSING)
        )

        # Revenue calculated for non-cancelled orders
        valid_orders = [o for o in orders if o.status != OrderStatus.CANCELLED]
        total_revenue = sum(o.total_amount for o in valid_orders)
        avg_order_value = total_revenue / len(valid_orders) if valid_orders else 0.0

        return {
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "failed_orders": failed_orders,
            "cancelled_orders": cancelled_orders,
            "pending_orders": pending_orders,
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(avg_order_value, 2),
        }

    def get_next_order_id(self, db: Session) -> str:
        """Generate next deterministic order ID."""
        stmt = select(func.count(Order.id))
        count = db.execute(stmt).scalar() or 0
        return f"ORD-{1001 + count}"
