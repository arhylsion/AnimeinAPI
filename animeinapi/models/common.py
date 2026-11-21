from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    detail: str


class BulkRequest(BaseModel):
    ids: list[str] = Field(..., description="List of IDs to fetch in bulk")


class BulkResult(BaseModel, Generic[T]):
    items: dict[str, T] = Field(
        default_factory=dict, description="Map of successfully fetched items keyed by ID"
    )
    errors: dict[str, str] = Field(
        default_factory=dict, description="Map of error messages keyed by failed ID"
    )
    total_requested: int = Field(0, description="Total number of requested IDs")
    total_success: int = Field(0, description="Total number of succeeded IDs")
    total_failed: int = Field(0, description="Total number of failed IDs")
