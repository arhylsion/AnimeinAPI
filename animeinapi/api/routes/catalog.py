from __future__ import annotations

from fastapi import APIRouter, Query

from ...core.client import UpstreamError
from ...models import AnimeSummary, CatalogStats, Genre, HomeData
from .dependencies import DAY_PATTERN, Svc, handle_upstream_error, today_wib

router = APIRouter(tags=["catalog"])


@router.get("/genres")
async def genres(service: Svc) -> list[Genre]:
    try:
        return await service.get_genres()
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/home")
async def home(
    service: Svc,
    day: str | None = Query(None, pattern=DAY_PATTERN),
    limit: int = Query(16, ge=1, le=100),
) -> HomeData:
    try:
        return await service.get_home(day=day or today_wib(), limit=limit)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/schedule")
async def schedule(
    service: Svc,
    day: str | None = Query(None, pattern=DAY_PATTERN),
) -> list[AnimeSummary]:
    try:
        return await service.get_schedule(day=day or today_wib())
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/stats", tags=["meta"])
async def catalog_stats(service: Svc) -> CatalogStats:
    try:
        return await service.get_catalog_stats()
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc
