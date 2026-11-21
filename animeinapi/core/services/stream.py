from __future__ import annotations

from ...models import Episode, StreamInfo, StreamResponse
from ..client import UpstreamError
from ..constants import TTL_STREAMS


class StreamServiceMixin:
    async def get_streams(self, episode_id: str) -> StreamResponse:
        cached = await self._cached(
            ("streams", episode_id), TTL_STREAMS, lambda: self._get_streams(episode_id)
        )
        return cached.data

    async def _get_streams(self, episode_id: str) -> StreamResponse:
        payload = await self._get(f"3/2/episode/streamnew/{episode_id}")
        data = payload.get("data", {})
        episode_raw = data.get("episode")
        if not episode_raw:
            raise UpstreamError("Empty episode data from upstream")
        episode = Episode.model_validate(episode_raw)

        streams: dict[str, list[StreamInfo]] = {}
        for server in data.get("server") or []:
            info = StreamInfo.model_validate(server)
            streams.setdefault(info.quality, []).append(info)

        for q in streams:
            streams[q].sort(key=lambda s: 0 if s.is_rapsodi else 1)

        episode_next = data.get("episode_next")
        return StreamResponse(
            episode=episode,
            episode_next=Episode.model_validate(episode_next) if episode_next else None,
            streams=streams,
        )
