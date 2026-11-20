from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    detail: str


class BulkRequest(BaseModel):
    ids: list[str] = Field(..., description="Daftar ID yang ingin diambil secara bulk")


class BulkResult(BaseModel, Generic[T]):
    items: dict[str, T] = Field(
        default_factory=dict, description="Dictionary hasil sukses per ID"
    )
    errors: dict[str, str] = Field(
        default_factory=dict, description="Dictionary pesan error per ID yang gagal"
    )
    total_requested: int = Field(0, description="Total ID yang diminta")
    total_success: int = Field(0, description="Total ID yang berhasil")
    total_failed: int = Field(0, description="Total ID yang gagal")
