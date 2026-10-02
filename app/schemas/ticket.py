"""Support Ticket Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.ticket import TicketPriority, TicketStatus


class SupportTicketBase(BaseModel):
    customer_id: str = Field(..., min_length=3, max_length=32)
    order_id: Optional[str] = Field(None, max_length=32)
    title: str = Field(..., min_length=3, max_length=256)
    description: str = Field(..., min_length=5)
    priority: TicketPriority = TicketPriority.MEDIUM


class SupportTicketCreate(SupportTicketBase):
    pass


class SupportTicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=256)
    description: Optional[str] = Field(default=None, min_length=5)
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None


class SupportTicketResponse(SupportTicketBase):
    id: int
    ticket_id: str
    status: TicketStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketFilterParams(BaseModel):
    customer_id: Optional[str] = None
    order_id: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|priority|status|ticket_id)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
