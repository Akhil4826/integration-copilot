"""Support ticket data-access repository."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.ticket import SupportTicket
from app.schemas.ticket import TicketFilterParams


class TicketRepository:
    """Encapsulates database operations for SupportTicket entity."""

    def get_by_ticket_id(self, db: Session, ticket_id: str) -> Optional[SupportTicket]:
        stmt = select(SupportTicket).where(SupportTicket.ticket_id == ticket_id.strip().upper())
        return db.execute(stmt).scalar_one_or_none()

    def filter_tickets(
        self,
        db: Session,
        filters: TicketFilterParams,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[SupportTicket], int]:
        stmt = select(SupportTicket)

        if filters.customer_id:
            stmt = stmt.where(SupportTicket.customer_id == filters.customer_id.strip().upper())
        if filters.order_id:
            stmt = stmt.where(SupportTicket.order_id == filters.order_id.strip().upper())
        if filters.status:
            stmt = stmt.where(SupportTicket.status == filters.status)
        if filters.priority:
            stmt = stmt.where(SupportTicket.priority == filters.priority)

        # Count total
        count_stmt = select(func.count(SupportTicket.id))
        if filters.customer_id:
            count_stmt = count_stmt.where(
                SupportTicket.customer_id == filters.customer_id.strip().upper()
            )
        if filters.order_id:
            count_stmt = count_stmt.where(
                SupportTicket.order_id == filters.order_id.strip().upper()
            )
        if filters.status:
            count_stmt = count_stmt.where(SupportTicket.status == filters.status)
        if filters.priority:
            count_stmt = count_stmt.where(SupportTicket.priority == filters.priority)

        total = db.execute(count_stmt).scalar() or 0

        # Sort
        sort_col = getattr(SupportTicket, filters.sort_by, SupportTicket.created_at)
        if filters.sort_order.lower() == "desc":
            stmt = stmt.order_by(desc(sort_col))
        else:
            stmt = stmt.order_by(sort_col.asc())

        stmt = stmt.offset(offset).limit(limit)
        items = list(db.execute(stmt).scalars().all())
        return items, total

    def create_ticket(self, db: Session, ticket: SupportTicket) -> SupportTicket:
        try:
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            return ticket
        except Exception:
            db.rollback()
            raise

    def update_ticket(
        self, db: Session, ticket_id: str, update_fields: Dict[str, Any]
    ) -> Optional[SupportTicket]:
        ticket = self.get_by_ticket_id(db, ticket_id)
        if not ticket:
            return None

        for field, value in update_fields.items():
            if value is not None and hasattr(ticket, field):
                setattr(ticket, field, value)

        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
        return ticket

    def get_next_ticket_id(self, db: Session) -> str:
        """Generate next ticket ID (e.g. TCK-1031)."""
        stmt = select(func.count(SupportTicket.id))
        count = db.execute(stmt).scalar() or 0
        return f"TCK-{1001 + count}"
