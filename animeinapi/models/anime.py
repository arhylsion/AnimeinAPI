from __future__ import annotations

from pydantic import BaseModel


class AnimeSummary(BaseModel):
    id: str
    slug: str | None = None
    title: str
    synopsis: str | None = None
    synonyms: str | None = None
    image_poster: str | None = None
    image_cover: str | None = None
    type: str | None = None
    year: str | None = None
    day: str | None = None
    status: str | None = None
    views: str | None = None
    favorites: str | None = None
    genre: str | None = None
    time: str | None = None
    key_time: str | None = None


class AnimeDetail(AnimeSummary):
    day: str | None = None
    aired_start: str | None = None
    aired_end: str | None = None
    studio: str | None = None
    time: str | None = None
    key_status: str | None = None


class SearchResult(BaseModel):
    page: int
    total: int | None = None
    items: list[AnimeSummary]


class Slider(BaseModel):
    id: str
    link: str | None = None
    image: str | None = None
    type: str | None = None


class Trailer(BaseModel):
    id: str
    name: str | None = None
    url_youtube: str | None = None
    thumbnail: str | None = None
    time: str | None = None
    is_new: bool | str | None = None
