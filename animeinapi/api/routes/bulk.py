from __future__ import annotations

from fastapi import APIRouter

from ...models import AnimeDetail, BulkRequest, BulkResult, Episode, StreamResponse
from .dependencies import Svc

router = APIRouter(tags=["bulk"])


@router.post("/bulk/anime")
async def bulk_anime(
    service: Svc,
    body: BulkRequest,
) -> BulkResult[AnimeDetail]:
    return await service.get_anime_bulk(body.ids)


@router.post("/bulk/streams")
async def bulk_streams(
    service: Svc,
    body: BulkRequest,
) -> BulkResult[StreamResponse]:
    return await service.get_streams_bulk(body.ids)


@router.post("/bulk/episodes")
async def bulk_episodes(
    service: Svc,
    body: BulkRequest,
) -> BulkResult[list[Episode]]:
    return await service.get_episodes_bulk(body.ids)
