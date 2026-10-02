"""Order and OrderItem Pydantic schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus


class OrderItemBase(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: str

    model_config = {"from_attributes": True}


class OrderBase(BaseModel):
    customer_id: str
    status: OrderStatus = OrderStatus.PENDING


class OrderCreate(BaseModel):
    customer_id: str
    items: List[OrderItemCreate] = Field(..., min_length=1)
    status: Optional[OrderStatus] = OrderStatus.PENDING


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None


class OrderResponse(OrderBase):
    id: int
    order_id: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderFilterParams(BaseModel):
    status: Optional[OrderStatus] = None
    customer_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    minimum_amount: Optional[float] = Field(default=None, ge=0)
    maximum_amount: Optional[float] = Field(default=None, ge=0)
    sort_by: str = Field(
        default="created_at", pattern="^(created_at|total_amount|status|order_id)$"
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
