"""Support ticket tools for MCP server."""

from typing import Any, Dict, Optional

from app.core.errors import NotFoundException, ValidationException
from app.db.database import SessionLocal
from app.models.ticket import TicketPriority, TicketStatus
from app.schemas.ticket import (
    SupportTicketCreate,
    SupportTicketUpdate,
    TicketFilterParams,
)
from app.services.ticket_service import TicketService

ticket_service = TicketService()


def register_ticket_tools(server):
    @server.tool(
        name="get_support_ticket",
        description=(
            "Retrieve details of a specific support ticket by ticket ID (e.g. 'TCK-1001'). "
            "Returns customer ID, title, description, priority, status, and associated order ID. "
            "Use when checking ticket progress or details."
        ),
    )
    def get_support_ticket(ticket_id: str) -> Dict[str, Any]:
        """Fetch ticket by ticket_id."""
        db = SessionLocal()
        try:
            ticket = ticket_service.get_ticket(db, ticket_id)
            return {
                "ticket_id": ticket.ticket_id,
                "customer_id": ticket.customer_id,
                "order_id": ticket.order_id,
                "title": ticket.title,
                "description": ticket.description,
                "priority": ticket.priority.value,
                "status": ticket.status.value,
                "created_at": ticket.created_at.isoformat(),
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="list_support_tickets",
        description=(
            "List and filter support tickets by customer ID, order ID, status (OPEN, IN_PROGRESS, RESOLVED, CLOSED), "
            "or priority (LOW, MEDIUM, HIGH, CRITICAL). "
            "Use when asked to view open tickets, customer tickets, or high-priority issues."
        ),
    )
    def list_support_tickets(
        customer_id: Optional[str] = None,
        order_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """List tickets matching criteria."""
        db = SessionLocal()
        try:
            prio = None
            if priority:
                try:
                    prio = TicketPriority(priority.strip().upper())
                except ValueError:
                    return {
                        "error": f"Invalid priority '{priority}'. Valid: {[p.value for p in TicketPriority]}",
                        "code": "INVALID_PRIORITY",
                    }

            stat = None
            if status:
                try:
                    stat = TicketStatus(status.strip().upper())
                except ValueError:
                    return {
                        "error": f"Invalid status '{status}'. Valid: {[s.value for s in TicketStatus]}",
                        "code": "INVALID_STATUS",
                    }

            clamped_limit = max(1, min(limit, 50))
            filters = TicketFilterParams(
                customer_id=customer_id,
                order_id=order_id,
                status=stat,
                priority=prio,
            )
            items, total = ticket_service.filter_tickets(db, filters, limit=clamped_limit)
            return {
                "total_matches": total,
                "count": len(items),
                "tickets": [
                    {
                        "ticket_id": t.ticket_id,
                        "customer_id": t.customer_id,
                        "order_id": t.order_id,
                        "title": t.title,
                        "priority": t.priority.value,
                        "status": t.status.value,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in items
                ],
            }
        finally:
            db.close()

    @server.tool(
        name="create_support_ticket",
        description=(
            "Create a new support ticket for a customer, optionally linking an order ID. "
            "Inputs: customer_id (e.g. 'CUST-1004'), title, description, priority (LOW, MEDIUM, HIGH, CRITICAL), order_id (optional). "
            "IMPORTANT: This is a WRITE operation modifying business state. "
            "User confirmation is required before execution."
        ),
    )
    def create_support_ticket(
        customer_id: str,
        title: str,
        description: str,
        priority: str = "MEDIUM",
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create new support ticket."""
        db = SessionLocal()
        try:
            try:
                ticket_prio = TicketPriority(priority.strip().upper())
            except ValueError:
                return {
                    "error": f"Invalid priority '{priority}'. Valid: {[p.value for p in TicketPriority]}",
                    "code": "INVALID_PRIORITY",
                }

            ticket_data = SupportTicketCreate(
                customer_id=customer_id,
                order_id=order_id,
                title=title,
                description=description,
                priority=ticket_prio,
            )
            ticket = ticket_service.create_ticket(db, ticket_data)
            return {
                "ticket_id": ticket.ticket_id,
                "customer_id": ticket.customer_id,
                "order_id": ticket.order_id,
                "title": ticket.title,
                "priority": ticket.priority.value,
                "status": ticket.status.value,
                "created_at": ticket.created_at.isoformat(),
                "message": f"Successfully created support ticket {ticket.ticket_id}",
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()

    @server.tool(
        name="update_support_ticket",
        description=(
            "Update an existing support ticket's status, priority, or description. "
            "IMPORTANT: This is a WRITE operation. User confirmation is required before execution."
        ),
    )
    def update_support_ticket(
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update support ticket fields."""
        db = SessionLocal()
        try:
            ticket_prio = None
            if priority:
                try:
                    ticket_prio = TicketPriority(priority.strip().upper())
                except ValueError:
                    return {"error": f"Invalid priority '{priority}'", "code": "INVALID_PRIORITY"}

            ticket_stat = None
            if status:
                try:
                    ticket_stat = TicketStatus(status.strip().upper())
                except ValueError:
                    return {"error": f"Invalid status '{status}'", "code": "INVALID_STATUS"}

            update_data = SupportTicketUpdate(
                status=ticket_stat,
                priority=ticket_prio,
                description=description,
            )
            ticket = ticket_service.update_ticket(db, ticket_id, update_data)
            return {
                "ticket_id": ticket.ticket_id,
                "status": ticket.status.value,
                "priority": ticket.priority.value,
                "updated_at": ticket.updated_at.isoformat(),
                "message": f"Successfully updated support ticket {ticket.ticket_id}",
            }
        except (NotFoundException, ValidationException) as exc:
            return {"error": exc.message, "code": exc.code}
        finally:
            db.close()
