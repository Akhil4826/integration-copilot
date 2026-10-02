"""Customer Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=32)


class CustomerCreate(CustomerBase):
    customer_id: Optional[str] = Field(None, description="Optional custom ID (e.g. CUST-1031)")


class CustomerResponse(CustomerBase):
    id: int
    customer_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
