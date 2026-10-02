"""Analytics Pydantic schemas."""

from typing import List

from pydantic import BaseModel, Field


class OrderStatisticsResponse(BaseModel):
    total_orders: int = Field(..., description="Total orders in the queried period")
    successful_orders: int = Field(..., description="Orders DELIVERED or SHIPPED")
    failed_orders: int = Field(..., description="Orders FAILED")
    cancelled_orders: int = Field(..., description="Orders CANCELLED")
    pending_orders: int = Field(..., description="Orders PENDING or PROCESSING")
    total_revenue: float = Field(..., description="Total revenue from all valid orders")
    average_order_value: float = Field(..., description="Average value per order")


class TopProductResponse(BaseModel):
    product_id: str
    name: str
    category: str
    total_units_sold: int
    total_revenue: float


class RevenueSummaryResponse(BaseModel):
    total_revenue: float
    delivered_revenue: float
    lost_revenue_failed: float
    total_orders: int
    top_categories: List[dict] = []
