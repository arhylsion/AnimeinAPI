from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ...config import Settings
from ...models import AnimeSummary, Episode
from ..cache import Cache, Cached
from ..client import HttpClient, UpstreamError, UpstreamNotFound
from ..constants import TTL_EPISODES
from ..index import SlugIndex
from ..slug import is_numeric_id, parse_episode_slug, slugify

A = TypeVar("A", bound=AnimeSummary)


class BaseService:
    def __init__(
        self,
        http: HttpClient,
        cache: Cache,
        settings: Settings,
        slug_index: SlugIndex | None = None,
    ) -> None:
        self._http = http
        self._cache = cache
        self._settings = settings
        self._slug_index = slug_index if slug_index is not None else SlugIndex()

    @property
    def slug_index(self) -> SlugIndex:
        return self._slug_index

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
            raise UpstreamError("Upstream payload is not a JSON object")
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

    def _index_anime(self, item: A) -> A:
        item.slug = self._slug_index.register_anime(item.id, item.title, item.year)
        return item

    def _index_anime_list(self, items: list[A]) -> list[A]:
        for item in items:
            self._index_anime(item)
        return items

    def _index_episode(
        self,
        episode: Episode,
        anime_id: str | None = None,
        anime_slug: str | None = None,
    ) -> Episode:
        aid = anime_id or episode.id_movie
        episode.slug = self._slug_index.register_episode(
            episode.id, episode.index, anime_id=aid, anime_slug=anime_slug
        )
        return episode

    def _index_episode_list(
        self,
        episodes: list[Episode],
        anime_id: str | None = None,
        anime_slug: str | None = None,
    ) -> list[Episode]:
        for ep in episodes:
            self._index_episode(ep, anime_id=anime_id, anime_slug=anime_slug)
        return episodes

    async def _fetch_cached_episodes(self, resolved_anime_id: str, page: int = 0) -> list[Episode]:
        """Fetch cached episodes for an already-resolved numeric anime_id."""
        get_ep_fn = getattr(self, "_get_episodes", None)
        if get_ep_fn is None:
            return []
        cached = await self._cached(
            ("episodes", resolved_anime_id, page),
            TTL_EPISODES,
            lambda: get_ep_fn(resolved_anime_id, page),
        )
        return cached.data

    async def resolve_anime_id(self, id_or_slug: str) -> str:
        raw = id_or_slug.strip()
        if is_numeric_id(raw):
            return raw

        target_slug = slugify(raw)
        if not target_slug:
            raise UpstreamNotFound(f"Invalid anime slug: {id_or_slug}")

        hit = self._slug_index.get_anime_id(target_slug)
        if hit:
            return hit

        # Cold miss fallback: search upstream using keyword words
        words = target_slug.split("-")
        queries = [" ".join(words)]
        if len(words) > 1:
            queries.append(words[0])

        for q in dict.fromkeys(queries):
            search_fn = getattr(self, "search", None)
            if search_fn is None:
                break
            res = await search_fn(q, page=0)
            hit = self._slug_index.get_anime_id(target_slug)
            if hit:
                return hit
            for item in res.items:
                if slugify(item.title) == target_slug:
                    return item.id
                if item.synonyms and slugify(item.synonyms) == target_slug:
                    self._slug_index._anime_slug_to_id[target_slug] = item.id
                    return item.id

        raise UpstreamNotFound(f"Anime slug not found: {id_or_slug}")

    async def resolve_episode_id(self, id_or_slug: str) -> str:
        raw = id_or_slug.strip()
        if is_numeric_id(raw):
            return raw

        target_slug = slugify(raw)
        hit = self._slug_index.get_episode_id(target_slug)
        if hit:
            return hit

        parsed = parse_episode_slug(target_slug)
        if not parsed:
            raise UpstreamNotFound(f"Invalid episode slug: {id_or_slug}")

        anime_slug, ep_index = parsed
        anime_id = await self.resolve_anime_id(anime_slug)

        hit_by_slug = self._slug_index.get_episode_id(target_slug)
        if hit_by_slug:
            return hit_by_slug

        hit_by_idx = self._slug_index.get_episode_id_by_index(anime_id, ep_index)
        if hit_by_idx:
            return hit_by_idx

        for page in range(0, 20):
            episodes = await self._fetch_cached_episodes(anime_id, page=page)
            if not episodes:
                break
            hit_by_slug = self._slug_index.get_episode_id(target_slug)
            if hit_by_slug:
                return hit_by_slug
            hit_by_idx = self._slug_index.get_episode_id_by_index(anime_id, ep_index)
            if hit_by_idx:
                return hit_by_idx
            if len(episodes) < 30:
                break

        raise UpstreamNotFound(f"Episode slug not found: {id_or_slug}")
