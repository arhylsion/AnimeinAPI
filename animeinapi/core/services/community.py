from __future__ import annotations

from ...models import ChatData, CommentList
from ..constants import TTL_CHAT, TTL_COMMENTS


class CommunityServiceMixin:
    async def get_chat(self, highest_id: str = "", lowest_id: str = "") -> ChatData:
        cached = await self._cached(
            ("chat", highest_id, lowest_id),
            TTL_CHAT,
            lambda: self._get_chat(highest_id, lowest_id),
        )
        return cached.data

    async def _get_chat(self, highest_id: str, lowest_id: str) -> ChatData:
        payload = await self._get(
            "3/2/chat/data", highest_id=highest_id, lowest_id=lowest_id
        )
        return ChatData.model_validate(payload.get("data") or {})

    async def get_comments(
        self, episode_id: str, sort: str = "new", page: int = 0
    ) -> CommentList:
        resolved_id = await self.resolve_episode_id(episode_id)
        cached = await self._cached(
            ("comments", resolved_id, sort, page),
            TTL_COMMENTS,
            lambda: self._get_comments(resolved_id, sort, page),
        )
        return cached.data

    async def _get_comments(self, episode_id: str, sort: str, page: int) -> CommentList:
        payload = await self._get(
            "3/2/comment/data", id_episode=episode_id, sort=sort, page=page
        )
        return CommentList.model_validate(payload.get("data") or {})
