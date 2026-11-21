from __future__ import annotations

from ...models import Episode, StreamInfo, StreamResponse
from ..client import UpstreamError, UpstreamNotFound
from ..constants import TTL_STREAMS


class StreamServiceMixin:
    async def get_streams(self, episode_id: str) -> StreamResponse:
        resolved_id = await self.resolve_episode_id(episode_id)
        cached = await self._cached(
            ("streams", resolved_id), TTL_STREAMS, lambda: self._get_streams(resolved_id)
        )
        return cached.data

    async def get_episode_streams_by_index(
        self, anime_id_or_slug: str, episode_index: str
    ) -> StreamResponse:
        anime_id = await self.resolve_anime_id(anime_id_or_slug)
        ep_id = self._slug_index.get_episode_id_by_index(anime_id, episode_index)
        if not ep_id:
            for page in range(0, 20):
                episodes = await self.get_episodes(anime_id, page=page)
                if not episodes:
                    break
                ep_id = self._slug_index.get_episode_id_by_index(anime_id, episode_index)
                if ep_id:
                    break
                if len(episodes) < 30:
                    break
        if not ep_id:
            raise UpstreamNotFound(
                f"Episode index {episode_index} not found for anime {anime_id_or_slug}"
            )
        return await self.get_streams(ep_id)

    async def _get_streams(self, episode_id: str) -> StreamResponse:
        payload = await self._get(f"3/2/episode/streamnew/{episode_id}")
        data = payload.get("data", {})
        episode_raw = data.get("episode")
        if not episode_raw:
            raise UpstreamError("Empty episode data from upstream")
        episode = self._index_episode(Episode.model_validate(episode_raw))

        streams: dict[str, list[StreamInfo]] = {}
        for server in data.get("server") or []:
            info = StreamInfo.model_validate(server)
            streams.setdefault(info.quality, []).append(info)

        for q in streams:
            streams[q].sort(key=lambda s: 0 if s.is_rapsodi else 1)

        episode_next_raw = data.get("episode_next")
        episode_next = (
            self._index_episode(Episode.model_validate(episode_next_raw))
            if episode_next_raw
            else None
        )
        return StreamResponse(
            episode=episode,
            episode_next=episode_next,
            streams=streams,
        )
