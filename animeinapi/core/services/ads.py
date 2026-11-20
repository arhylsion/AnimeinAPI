from __future__ import annotations

from ...models import Ad
from ..constants import TTL_ADS


class AdsServiceMixin:
    async def get_ads(self, tag: str = "") -> Ad | None:
        cached = await self._cached(("ads", tag), TTL_ADS, lambda: self._get_ads(tag))
        return cached.data

    async def _get_ads(self, tag: str) -> Ad | None:
        payload = await self._get("data/ads/show", tag=tag)
        ad = (payload.get("data") or {}).get("ad")
        return Ad.model_validate(ad) if ad else None
