from __future__ import annotations

from fastapi import APIRouter, Query

from ...core.client import UpstreamError
from ...core.constants import SORTS
from ...models import AnimeDetail, Episode, SearchResult, Trailer
from .dependencies import Svc, handle_upstream_error

router = APIRouter(tags=["anime"])


@router.get("/search")
async def search(
    service: Svc,
    q: str = Query(""),
    page: int = Query(0, ge=0),
    sort: str = Query("views", pattern=f"^({'|'.join(SORTS)})$"),
    genre: str = Query(""),
) -> SearchResult:
    try:
        return await service.search(q, page=page, sort=sort, genre=genre)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/anime/{anime_id}")
async def anime_detail(service: Svc, anime_id: str) -> AnimeDetail:
    try:
        return await service.get_anime(anime_id)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/anime/{anime_id}/episodes")
async def anime_episodes(
    service: Svc,
    anime_id: str,
    page: int = Query(0, ge=0),
) -> list[Episode]:
    try:
        return await service.get_episodes(anime_id, page=page)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/anime/{anime_id}/trailers")
async def anime_trailers(service: Svc, anime_id: str) -> list[Trailer]:
    try:
        return await service.get_trailers(anime_id)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc
