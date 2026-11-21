from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    user_pokemon: str | None = None
    image_masukotto: str | None = None
    image_url: str | None = None
    image_url_replay: str | None = None
    user_name_replay: str | None = None
    text: str | None = None
    text_replay: str | None = None
    time: str | None = None
    time_hour: str | None = None
    time_iso: str | None = None
    time_updated: str | None = None
    id_chat_replay: str | None = None
    type: str | None = None
    pro: int | None = None
    rank: int | None = None
    movie: Any = None


class ChatData(BaseModel):
    chat: list[ChatMessage] = Field(default_factory=list)
    chat_update: list[ChatMessage] = Field(default_factory=list)
    news: Any = None
    refresh: str | None = None


class Comment(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    user_pokemon: str | None = None
    text: str | None = None
    time: str | None = None
    time_updated: str | None = None
    like: str | None = None
    dislike: str | None = None
    score: str | None = None
    replay: Any = None
    is_like: str | None = None
    pro: int | None = None
    rank: int | None = None


class CommentList(BaseModel):
    comment: list[Comment] = Field(default_factory=list)
    cover: list[Any] = Field(default_factory=list)
    poster: list[Any] = Field(default_factory=list)
    count: str | int | None = None
    id_movie: str | None = None
