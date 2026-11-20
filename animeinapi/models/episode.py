from __future__ import annotations

from pydantic import BaseModel


class Episode(BaseModel):
    id: str
    index: str
    title: str
    views: str | None = None
    id_movie: str | None = None
    key_time: str | None = None
    image: str | None = None
    is_new: bool | str | None = None
