from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from ...core.client import UpstreamError, UpstreamNotFound
from ...core.constants import WEEKDAY_INDONESIAN
from ...core.service import AnimeinService

DAY_PATTERN = "^(MINGGU|SENIN|SELASA|RABU|KAMIS|JUMAT|SABTU|RANDOM)$"


def get_service(request: Request) -> AnimeinService:
    return request.app.state.service


Svc = Annotated[AnimeinService, Depends(get_service)]


def handle_upstream_error(exc: UpstreamError) -> HTTPException:
    if isinstance(exc, UpstreamNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=f"Upstream error: {exc}")


def today_wib() -> str:
    wib = datetime.now(timezone(timedelta(hours=7)))
    return WEEKDAY_INDONESIAN[wib.weekday()]
