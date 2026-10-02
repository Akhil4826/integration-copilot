"""Order business service layer."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.errors import NotFoundException, ValidationException
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate, OrderFilterParams


class OrderService:
    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
        product_repo: Optional[ProductRepository] = None,
    ):
        self.order_repo = order_repo or OrderRepository()
        self.customer_repo = customer_repo or CustomerRepository()
        self.product_repo = product_repo or ProductRepository()

    def get_order(self, db: Session, order_id: str) -> Order:
        if not order_id or not order_id.strip():
            raise ValidationException("order_id cannot be empty")
        order = self.order_repo.get_by_order_id(db, order_id)
        if not order:
            raise NotFoundException("Order", order_id)
        return order

    def get_customer_orders(self, db: Session, customer_id: str, limit: int = 10) -> List[Order]:
        if not customer_id or not customer_id.strip():
            raise ValidationException("customer_id cannot be empty")
        # Verify customer exists
        customer = self.customer_repo.get_by_customer_id(db, customer_id)
        if not customer:
            raise NotFoundException("Customer", customer_id)
        return self.order_repo.get_customer_orders(db, customer_id, limit=limit)

    def filter_orders(
        self,
        db: Session,
        filters: OrderFilterParams,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        return self.order_repo.filter_orders(db, filters, offset=offset, limit=limit)

    def create_order(self, db: Session, data: OrderCreate) -> Order:
        # 1. Verify customer exists
        customer = self.customer_repo.get_by_customer_id(db, data.customer_id)
        if not customer:
            raise NotFoundException("Customer", data.customer_id)

        if not data.items:
            raise ValidationException("Order must have at least one line item")

        # 2. Verify all products and calculate total amount
        order_id = self.order_repo.get_next_order_id(db)
        total_amount = 0.0
        order_items: List[OrderItem] = []

        for item_data in data.items:
            product = self.product_repo.get_by_product_id(db, item_data.product_id)
            if not product:
                raise NotFoundException("Product", item_data.product_id)

            line_total = product.price * item_data.quantity
            total_amount += line_total

            order_items.append(
                OrderItem(
                    order_id=order_id,
                    product_id=product.product_id,
                    quantity=item_data.quantity,
                    unit_price=product.price,
                )
            )

        order = Order(
            order_id=order_id,
            customer_id=customer.customer_id,
            status=data.status or OrderStatus.PENDING,
            total_amount=round(total_amount, 2),
        )

        return self.order_repo.create_order(db, order, order_items)

    def update_order_status(self, db: Session, order_id: str, new_status: OrderStatus) -> Order:
        order = self.order_repo.get_by_order_id(db, order_id)
        if not order:
            raise NotFoundException("Order", order_id)
        updated = self.order_repo.update_order_status(db, order_id, new_status)
        if not updated:
            raise NotFoundException("Order", order_id)
        return updated

    def get_order_statistics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return self.order_repo.get_order_statistics(db, start_date=start_date, end_date=end_date)
