from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ...config import Settings
from ..cache import Cache, Cached
from ..client import HttpClient, UpstreamError, UpstreamNotFound


class BaseService:
    def __init__(self, http: HttpClient, cache: Cache, settings: Settings) -> None:
        self._http = http
        self._cache = cache
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            "x-proxy-secret": self._settings.proxy_secret,
            "Referer": self._settings.base_url + "/",
            "Accept": "application/json",
        }

    async def _get(self, path: str, **params: str | int) -> dict:
        url = f"{self._settings.proxy_url}/{path}"
        payload = await self._http.get_json(url, params=params, headers=self._headers())
        if not isinstance(payload, dict):
            raise UpstreamError("Payload upstream bukan objek JSON")
        if payload.get("error") is True or payload.get("status", 200) != 200:
            if payload.get("status") == 404:
                raise UpstreamNotFound(str(payload.get("data", "Not found")))
            raise UpstreamError(f"Upstream error: {payload.get('data')}")
        return payload

    async def _cached(
        self,
        parts: tuple[str | int, ...],
        ttl: float,
        fetch: Callable[[], Awaitable[Any]],
    ) -> Cached:
        key = ":".join(map(str, parts))
        return await self._cache.get(key, ttl, fetch, stale_ttl=ttl)
