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
