from __future__ import annotations

from fastapi import APIRouter, Query

from ...core.client import UpstreamError
from ...models import ChatData, CommentList
from .dependencies import Svc, handle_upstream_error

router = APIRouter(tags=["community"])


@router.get("/chat")
async def chat(
    service: Svc,
    highest_id: str = Query(""),
    lowest_id: str = Query(""),
) -> ChatData:
    try:
        return await service.get_chat(highest_id=highest_id, lowest_id=lowest_id)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc


@router.get("/episode/{episode_id}/comments")
async def episode_comments(
    service: Svc,
    episode_id: str,
    sort: str = Query("new", pattern="^(top|new)$"),
    page: int = Query(0, ge=0),
) -> CommentList:
    try:
        return await service.get_comments(episode_id, sort=sort, page=page)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc
