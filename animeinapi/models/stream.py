from __future__ import annotations

from pydantic import BaseModel, Field

from .episode import Episode


class StreamInfo(BaseModel):
    id: str
    link: str
    quality: str
    key_file_size: str | float | None = None
    name: str | None = None
    type: str | None = None
    domain: str | None = None
    username: str | None = None
    server_id: str | None = None

    @property
    def is_rapsodi(self) -> bool:
        return (self.name or "").upper() == "RAPSODI" or (self.type or "") == "direct"


class StreamResponse(BaseModel):
    episode: Episode
    episode_next: Episode | None = None
    streams: dict[str, list[StreamInfo]] = Field(default_factory=dict)
