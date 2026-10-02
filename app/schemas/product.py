"""Product Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    category: str = Field(..., min_length=2, max_length=64)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    product_id: Optional[str] = Field(
        None, description="Optional custom product ID (e.g. PROD-1051)"
    )


class ProductResponse(ProductBase):
    id: int
    product_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
