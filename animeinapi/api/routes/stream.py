from __future__ import annotations

from fastapi import APIRouter

from ...core.client import UpstreamError
from ...models import StreamResponse
from .dependencies import Svc, handle_upstream_error

router = APIRouter(tags=["stream"])


@router.get("/episode/{episode_id}/streams")
async def episode_streams(service: Svc, episode_id: str) -> StreamResponse:
    try:
        return await service.get_streams(episode_id)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/anime/{anime_id}/episode/{episode_index}/streams")
async def anime_episode_streams(
    service: Svc, anime_id: str, episode_index: str
) -> StreamResponse:
    try:
        return await service.get_episode_streams_by_index(anime_id, episode_index)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc
