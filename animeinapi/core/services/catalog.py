from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ...models import AnimeSummary, CatalogStats, Genre, HomeData
from ..constants import TTL_GENRES, TTL_HOME, TTL_SCHEDULE, TTL_STATS


class CatalogServiceMixin:
    async def get_genres(self) -> list[Genre]:
        cached = await self._cached(("genres",), TTL_GENRES, self._get_genres)
        return cached.data

    async def _get_genres(self) -> list[Genre]:
        payload = await self._get("3/2/explore/genre")
        data = payload.get("data") or {}
        genres = data.get("genre") if isinstance(data, dict) else data or []
        return [Genre.model_validate(g) for g in genres]

    async def get_home(self, day: str = "RANDOM", limit: int = 16) -> HomeData:
        cached = await self._cached(
            ("home", day, limit), TTL_HOME, lambda: self._get_home(day, limit)
        )
        return cached.data

    async def _get_home(self, day: str, limit: int) -> HomeData:
        payload = await self._get("3/2/home/data", day=day, limit=limit)
        home = HomeData.model_validate(payload.get("data") or {})
        for section in (
            home.hot,
            home.new,
            home.today,
            home.popular,
            home.waiting,
            home.random,
            home.trailer,
        ):
            self._index_anime_list(section)
        return home

    async def get_schedule(self, day: str = "RANDOM") -> list[AnimeSummary]:
        cached = await self._cached(
            ("schedule", day), TTL_SCHEDULE, lambda: self._get_schedule(day)
        )
        return cached.data

    async def _get_schedule(self, day: str) -> list[AnimeSummary]:
        payload = await self._get("3/2/schedule/data", day=day)
        data = payload.get("data") or {}
        movies = data.get("movie") if isinstance(data, dict) else data or []
        return self._index_anime_list([AnimeSummary.model_validate(m) for m in movies])

    async def get_catalog_stats(self) -> CatalogStats:
        cached = await self._cached(("catalog_stats",), TTL_STATS, self._get_catalog_stats)
        return cached.data

    async def _get_catalog_stats(self) -> CatalogStats:
        genres = await self.get_genres()
        total_movies = 4896
        try:
            p81 = await self._get("3/2/explore/movie", page=81, sort="views")
            movies = (p81.get("data") or {}).get("movie") or []
            if movies:
                total_movies = 81 * 60 + len(movies)
        except Exception:
            pass
        wib = datetime.now(timezone(timedelta(hours=7)))
        return CatalogStats(
            total_anime=total_movies,
            total_episodes="78.000+",
            total_genres=len(genres),
            last_updated=wib.strftime("%Y-%m-%d %H:%M:%S WIB"),
        )
