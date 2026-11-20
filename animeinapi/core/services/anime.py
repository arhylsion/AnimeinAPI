from __future__ import annotations

from ...models import AnimeDetail, AnimeSummary, Episode, SearchResult, Trailer
from ..client import UpstreamError
from ..constants import TTL_DETAIL, TTL_EPISODES, TTL_SEARCH, TTL_TRAILERS


class AnimeServiceMixin:
    async def search(
        self, query: str, page: int = 0, sort: str = "views", genre: str = ""
    ) -> SearchResult:
        cached = await self._cached(
            ("search", page, sort, query, genre),
            TTL_SEARCH,
            lambda: self._search(query, page, sort, genre),
        )
        return cached.data

    async def _search(self, query: str, page: int, sort: str, genre: str) -> SearchResult:
        payload = await self._get(
            "3/2/explore/movie", page=page, sort=sort, keyword=query, genre_in=genre
        )
        data = payload.get("data", {})
        movies = (
            data if isinstance(data, list) else (data.get("movies") or data.get("movie") or [])
        )
        items = [AnimeSummary.model_validate(m) for m in movies]
        total = None
        if isinstance(data, dict):
            total = data.get("total_movies") or data.get("total")
        return SearchResult(page=page, total=total or len(items), items=items)

    async def get_anime(self, anime_id: str) -> AnimeDetail:
        cached = await self._cached(
            ("anime", anime_id), TTL_DETAIL, lambda: self._get_anime(anime_id)
        )
        return cached.data

    async def _get_anime(self, anime_id: str) -> AnimeDetail:
        payload = await self._get(f"3/2/movie/detail/{anime_id}")
        data = payload.get("data") or {}
        movie = data.get("movie") if isinstance(data, dict) else None
        if not movie:
            raise UpstreamError("Detail movie kosong dari upstream")
        return AnimeDetail.model_validate(movie)

    async def get_episodes(self, anime_id: str, page: int = 0) -> list[Episode]:
        cached = await self._cached(
            ("episodes", anime_id, page),
            TTL_EPISODES,
            lambda: self._get_episodes(anime_id, page),
        )
        return cached.data

    async def _get_episodes(self, anime_id: str, page: int) -> list[Episode]:
        payload = await self._get(f"3/2/movie/episode/{anime_id}", page=page)
        data = payload.get("data") or []
        episodes = data if isinstance(data, list) else data.get("episode") or []
        items = [Episode.model_validate(ep) for ep in episodes]

        def sort_key(ep: Episode) -> int:
            try:
                return int(ep.index)
            except ValueError:
                return 0

        return sorted(items, key=sort_key)

    async def get_trailers(self, anime_id: str) -> list[Trailer]:
        cached = await self._cached(
            ("trailers", anime_id), TTL_TRAILERS, lambda: self._get_trailers(anime_id)
        )
        return cached.data

    async def _get_trailers(self, anime_id: str) -> list[Trailer]:
        payload = await self._get("data/movie/trailer/list", id_movie=anime_id)
        data = payload.get("data") or {}
        trailers = data.get("trailer") if isinstance(data, dict) else data or []
        return [Trailer.model_validate(t) for t in trailers]
