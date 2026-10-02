"""Support ticket business service layer."""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.errors import NotFoundException, ValidationException
from app.models.ticket import SupportTicket, TicketPriority, TicketStatus
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import SupportTicketCreate, SupportTicketUpdate, TicketFilterParams


class TicketService:
    def __init__(
        self,
        ticket_repo: Optional[TicketRepository] = None,
        customer_repo: Optional[CustomerRepository] = None,
        order_repo: Optional[OrderRepository] = None,
    ):
        self.ticket_repo = ticket_repo or TicketRepository()
        self.customer_repo = customer_repo or CustomerRepository()
        self.order_repo = order_repo or OrderRepository()

    def get_ticket(self, db: Session, ticket_id: str) -> SupportTicket:
        if not ticket_id or not ticket_id.strip():
            raise ValidationException("ticket_id cannot be empty")
        ticket = self.ticket_repo.get_by_ticket_id(db, ticket_id)
        if not ticket:
            raise NotFoundException("SupportTicket", ticket_id)
        return ticket

    def filter_tickets(
        self,
        db: Session,
        filters: TicketFilterParams,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[SupportTicket], int]:
        return self.ticket_repo.filter_tickets(db, filters, offset=offset, limit=limit)

    def create_ticket(self, db: Session, data: SupportTicketCreate) -> SupportTicket:
        # 1. Validate customer exists
        customer = self.customer_repo.get_by_customer_id(db, data.customer_id)
        if not customer:
            raise NotFoundException("Customer", data.customer_id)

        # 2. If order_id is specified, validate order exists
        order_id_clean = None
        if data.order_id and data.order_id.strip():
            order_id_clean = data.order_id.strip().upper()
            order = self.order_repo.get_by_order_id(db, order_id_clean)
            if not order:
                raise NotFoundException("Order", order_id_clean)

        ticket_id = self.ticket_repo.get_next_ticket_id(db)

        ticket = SupportTicket(
            ticket_id=ticket_id,
            customer_id=customer.customer_id,
            order_id=order_id_clean,
            title=data.title.strip(),
            description=data.description.strip(),
            priority=data.priority or TicketPriority.MEDIUM,
            status=TicketStatus.OPEN,
        )

        return self.ticket_repo.create_ticket(db, ticket)

    def update_ticket(
        self, db: Session, ticket_id: str, data: SupportTicketUpdate
    ) -> SupportTicket:
        ticket = self.ticket_repo.get_by_ticket_id(db, ticket_id)
        if not ticket:
            raise NotFoundException("SupportTicket", ticket_id)

        update_fields = data.model_dump(exclude_unset=True)
        updated = self.ticket_repo.update_ticket(db, ticket_id, update_fields)
        if not updated:
            raise NotFoundException("SupportTicket", ticket_id)
        return updated
