"""Common Pydantic schemas for pagination, sorting, and metadata."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(..., description="Total items matching filter")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Page limit")
    total_pages: int = Field(..., description="Total available pages")
