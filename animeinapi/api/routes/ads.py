from __future__ import annotations

from fastapi import APIRouter, Query

from ...core.client import UpstreamError
from ...models import Ad
from .dependencies import Svc, handle_upstream_error

router = APIRouter(tags=["ads"])


@router.get("/ads")
async def ads(
    service: Svc,
    tag: str = Query(""),
) -> Ad | None:
    try:
        return await service.get_ads(tag=tag)
    except UpstreamError as exc:
        raise handle_upstream_error(exc) from exc
