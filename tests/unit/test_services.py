"""Unit tests for Customer, Order, Ticket, and Analytics business services."""

import pytest

from app.core.errors import NotFoundException
from app.models.order import OrderStatus
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.customer import CustomerCreate
from app.schemas.order import OrderCreate, OrderFilterParams, OrderItemCreate
from app.schemas.ticket import SupportTicketCreate, SupportTicketUpdate
from app.services.analytics_service import AnalyticsService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.ticket_service import TicketService


class TestCustomerService:
    def test_get_existing_customer(self, db_session):
        service = CustomerService()
        cust = service.get_customer(db_session, "CUST-1004")
        assert cust.customer_id == "CUST-1004"
        assert "Brown" in cust.name

    def test_get_nonexistent_customer_raises_404(self, db_session):
        service = CustomerService()
        with pytest.raises(NotFoundException) as exc:
            service.get_customer(db_session, "CUST-9999")
        assert exc.value.status_code == 404
        assert "CUST-9999" in exc.value.message

    def test_search_customers(self, db_session):
        service = CustomerService()
        items, total = service.search_customers(db_session, query="James")
        assert total >= 1
        assert any("James" in c.name for c in items)

    def test_create_customer(self, db_session):
        service = CustomerService()
        data = CustomerCreate(
            name="Alice Newcomer",
            email="alice.newcomer99@example.com",
            phone="+1-555-999-8888",
        )
        new_cust = service.create_customer(db_session, data)
        assert new_cust.customer_id.startswith("CUST-")
        assert new_cust.email == "alice.newcomer99@example.com"


class TestOrderService:
    def test_get_order(self, db_session):
        service = OrderService()
        order = service.get_order(db_session, "ORD-1004")
        assert order.order_id == "ORD-1004"
        assert order.customer_id == "CUST-1004"
        assert order.status == OrderStatus.FAILED
        assert len(order.items) >= 1

    def test_filter_failed_orders(self, db_session):
        service = OrderService()
        filters = OrderFilterParams(status=OrderStatus.FAILED)
        items, total = service.filter_orders(db_session, filters)
        assert total >= 10
        assert all(o.status == OrderStatus.FAILED for o in items)

    def test_create_order_calculates_total(self, db_session):
        service = OrderService()
        order_data = OrderCreate(
            customer_id="CUST-1001",
            items=[
                OrderItemCreate(
                    product_id="PROD-1001", quantity=2
                ),  # Ultra Wireless Mouse 49.99 * 2 = 99.98
            ],
        )
        order = service.create_order(db_session, order_data)
        assert order.customer_id == "CUST-1001"
        assert order.total_amount == 99.98
        assert len(order.items) == 1

    def test_create_order_nonexistent_customer_raises_404(self, db_session):
        service = OrderService()
        order_data = OrderCreate(
            customer_id="CUST-9999",
            items=[OrderItemCreate(product_id="PROD-1001", quantity=1)],
        )
        with pytest.raises(NotFoundException):
            service.create_order(db_session, order_data)


class TestTicketService:
    def test_get_ticket(self, db_session):
        service = TicketService()
        ticket = service.get_ticket(db_session, "TCK-1001")
        assert ticket.ticket_id == "TCK-1001"
        assert ticket.customer_id == "CUST-1004"
        assert ticket.priority == TicketPriority.HIGH

    def test_create_ticket(self, db_session):
        service = TicketService()
        data = SupportTicketCreate(
            customer_id="CUST-1004",
            order_id="ORD-1004",
            title="Order investigation",
            description="Investigate payment decline during checkout",
            priority=TicketPriority.CRITICAL,
        )
        t = service.create_ticket(db_session, data)
        assert t.ticket_id.startswith("TCK-")
        assert t.priority == TicketPriority.CRITICAL
        assert t.status == TicketStatus.OPEN

    def test_update_ticket(self, db_session):
        service = TicketService()
        update_data = SupportTicketUpdate(status=TicketStatus.RESOLVED)
        updated = service.update_ticket(db_session, "TCK-1001", update_data)
        assert updated.status == TicketStatus.RESOLVED


class TestAnalyticsService:
    def test_order_statistics(self, db_session):
        service = AnalyticsService()
        stats = service.get_order_statistics(db_session)
        assert stats["total_orders"] >= 100
        assert stats["failed_orders"] >= 10
        assert stats["total_revenue"] > 0
        assert stats["average_order_value"] > 0

    def test_top_products(self, db_session):
        service = AnalyticsService()
        prods = service.get_top_products(db_session, limit=5)
        assert len(prods) == 5
        assert prods[0]["total_revenue"] >= prods[1]["total_revenue"]
