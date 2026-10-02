"""Customer tools for MCP server."""

from typing import Any, Dict, Optional

from app.core.errors import NotFoundException, ValidationException
from app.db.database import SessionLocal
from app.services.customer_service import CustomerService

customer_service = CustomerService()


def register_customer_tools(server):
    @server.tool(
        name="get_customer",
        description=(
            "Retrieve a customer using their unique customer ID (e.g. 'CUST-1004'). "
            "Use this tool when the user asks for customer details or when customer information "
            "is required before performing another customer-specific operation."
        ),
    )
    def get_customer(customer_id: str) -> Dict[str, Any]:
        """Fetch customer record by customer_id."""
        db = SessionLocal()
        try:
            customer = customer_service.get_customer(db, customer_id)
            return {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "created_at": customer.created_at.isoformat(),
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="search_customers",
        description=(
            "Search for customers by name, customer ID, email, or phone query. "
            "Use this tool when the user wants to locate customer accounts without an exact ID."
        ),
    )
    def search_customers(query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Search customers matching query."""
        db = SessionLocal()
        try:
            clamped_limit = max(1, min(limit, 50))
            items, total = customer_service.search_customers(db, query=query, limit=clamped_limit)
            return {
                "total_matches": total,
                "count": len(items),
                "customers": [
                    {
                        "customer_id": c.customer_id,
                        "name": c.name,
                        "email": c.email,
                        "phone": c.phone,
                    }
                    for c in items
                ],
            }
        finally:
            db.close()
