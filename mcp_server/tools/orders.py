"""Order tools for MCP server."""

from datetime import datetime
from typing import Any, Dict, Optional

from app.core.errors import NotFoundException, ValidationException
from app.db.database import SessionLocal
from app.models.order import OrderStatus
from app.schemas.order import OrderCreate, OrderFilterParams, OrderItemCreate
from app.services.order_service import OrderService

order_service = OrderService()


def register_order_tools(server):
    @server.tool(
        name="get_order",
        description=(
            "Retrieve details of a specific order using its order ID (e.g. 'ORD-1004'). "
            "Returns status, total amount, customer ID, timestamps, and line items. "
            "Use when the user asks about a specific order."
        ),
    )
    def get_order(order_id: str) -> Dict[str, Any]:
        """Fetch order record by order_id."""
        db = SessionLocal()
        try:
            order = order_service.get_order(db, order_id)
            return {
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "status": order.status.value,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                    }
                    for item in order.items
                ],
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="search_orders",
        description=(
            "Search and filter orders by status (PENDING, PROCESSING, SHIPPED, DELIVERED, FAILED, CANCELLED), "
            "customer_id, or date range. "
            "Use this tool when the user asks to see failed orders, recent orders, or orders matching specific criteria."
        ),
    )
    def search_orders(
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search orders matching filters."""
        db = SessionLocal()
        try:
            order_status = None
            if status:
                try:
                    order_status = OrderStatus(status.strip().upper())
                except ValueError:
                    return {
                        "error": f"Invalid order status '{status}'. Valid statuses: {[s.value for s in OrderStatus]}",
                        "code": "INVALID_STATUS",
                    }

            s_date = None
            if start_date:
                try:
                    s_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                except ValueError:
                    return {
                        "error": f"Invalid start_date format '{start_date}'. Use ISO format (YYYY-MM-DD)",
                        "code": "INVALID_DATE",
                    }

            e_date = None
            if end_date:
                try:
                    e_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                except ValueError:
                    return {
                        "error": f"Invalid end_date format '{end_date}'. Use ISO format (YYYY-MM-DD)",
                        "code": "INVALID_DATE",
                    }

            clamped_limit = max(1, min(limit, 50))
            filters = OrderFilterParams(
                status=order_status,
                customer_id=customer_id,
                start_date=s_date,
                end_date=e_date,
            )
            items, total = order_service.filter_orders(db, filters, limit=clamped_limit)

            return {
                "total_matches": total,
                "count": len(items),
                "orders": [
                    {
                        "order_id": o.order_id,
                        "customer_id": o.customer_id,
                        "status": o.status.value,
                        "total_amount": o.total_amount,
                        "created_at": o.created_at.isoformat(),
                    }
                    for o in items
                ],
            }
        finally:
            db.close()

    @server.tool(
        name="get_customer_orders",
        description=(
            "Retrieve orders placed by a specific customer using their customer ID (e.g. 'CUST-1004'). "
            "Use when the user asks to see orders for a specific customer."
        ),
    )
    def get_customer_orders(customer_id: str, limit: int = 10) -> Dict[str, Any]:
        """Fetch all orders for a specific customer."""
        db = SessionLocal()
        try:
            clamped_limit = max(1, min(limit, 50))
            orders = order_service.get_customer_orders(db, customer_id, limit=clamped_limit)
            return {
                "customer_id": customer_id.upper(),
                "count": len(orders),
                "orders": [
                    {
                        "order_id": o.order_id,
                        "status": o.status.value,
                        "total_amount": o.total_amount,
                        "created_at": o.created_at.isoformat(),
                        "items_count": len(o.items),
                    }
                    for o in orders
                ],
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="create_order",
        description=(
            "Place a new order for a customer with a specified product ID and quantity. "
            "IMPORTANT: This is a WRITE operation that creates financial commitments. "
            "User confirmation is required before execution."
        ),
    )
    def create_order(customer_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Create new order with line items."""
        db = SessionLocal()
        try:
            order_data = OrderCreate(
                customer_id=customer_id,
                items=[OrderItemCreate(product_id=product_id, quantity=quantity)],
            )
            order = order_service.create_order(db, order_data)
            return {
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "status": order.status.value,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "message": f"Successfully created order {order.order_id}",
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="update_order_status",
        description=(
            "Update the status of an existing order (e.g. CANCELLED, PROCESSING, SHIPPED). "
            "IMPORTANT: This is a WRITE operation modifying business state. "
            "Requires user confirmation."
        ),
    )
    def update_order_status(order_id: str, status: str) -> Dict[str, Any]:
        """Update order status."""
        db = SessionLocal()
        try:
            try:
                new_status = OrderStatus(status.strip().upper())
            except ValueError:
                return {
                    "error": f"Invalid order status '{status}'. Valid: {[s.value for s in OrderStatus]}",
                    "code": "INVALID_STATUS",
                }
            order = order_service.update_order_status(db, order_id, new_status)
            return {
                "order_id": order.order_id,
                "status": order.status.value,
                "updated_at": order.updated_at.isoformat(),
                "message": f"Order {order.order_id} updated to status {order.status.value}",
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()
