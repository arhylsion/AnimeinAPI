from __future__ import annotations

import asyncio

from ...models import AnimeDetail, BulkResult, Episode, StreamResponse


class BulkServiceMixin:
    async def get_anime_bulk(self, anime_ids: list[str]) -> BulkResult[AnimeDetail]:
        tasks = [self.get_anime(aid) for aid in anime_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: dict[str, AnimeDetail] = {}
        errors: dict[str, str] = {}
        for aid, res in zip(anime_ids, results, strict=False):
            if isinstance(res, Exception):
                errors[aid] = str(res)
            else:
                items[aid] = res
        return BulkResult(
            items=items,
            errors=errors,
            total_requested=len(anime_ids),
            total_success=len(items),
            total_failed=len(errors),
        )

    async def get_streams_bulk(self, episode_ids: list[str]) -> BulkResult[StreamResponse]:
        tasks = [self.get_streams(eid) for eid in episode_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: dict[str, StreamResponse] = {}
        errors: dict[str, str] = {}
        for eid, res in zip(episode_ids, results, strict=False):
            if isinstance(res, Exception):
                errors[eid] = str(res)
            else:
                items[eid] = res
        return BulkResult(
            items=items,
            errors=errors,
            total_requested=len(episode_ids),
            total_success=len(items),
            total_failed=len(errors),
        )

    async def get_episodes_bulk(self, anime_ids: list[str]) -> BulkResult[list[Episode]]:
        tasks = [self.get_episodes(aid) for aid in anime_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: dict[str, list[Episode]] = {}
        errors: dict[str, str] = {}
        for aid, res in zip(anime_ids, results, strict=False):
            if isinstance(res, Exception):
                errors[aid] = str(res)
            else:
                items[aid] = res
        return BulkResult(
            items=items,
            errors=errors,
            total_requested=len(anime_ids),
            total_success=len(items),
            total_failed=len(errors),
        )
