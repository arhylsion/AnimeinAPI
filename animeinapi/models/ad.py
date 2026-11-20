from __future__ import annotations

from pydantic import BaseModel


class Ad(BaseModel):
    id: str | int
    name: str | None = None
    tag: str | None = None
    url_content_video: str | None = None
    url_content_image: str | None = None
    url_redirect: str | None = None
    count_view: str | int | None = None
    count_click: str | int | None = None
