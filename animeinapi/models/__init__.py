from __future__ import annotations

from .ad import Ad
from .anime import AnimeDetail, AnimeSummary, SearchResult, Slider, Trailer
from .catalog import CatalogStats, Genre, HomeData
from .common import BulkRequest, BulkResult, ErrorResponse
from .community import ChatData, ChatMessage, Comment, CommentList
from .episode import Episode
from .stream import StreamInfo, StreamResponse

__all__ = [
    "Ad",
    "AnimeDetail",
    "AnimeSummary",
    "BulkRequest",
    "BulkResult",
    "CatalogStats",
    "ChatData",
    "ChatMessage",
    "Comment",
    "CommentList",
    "Episode",
    "ErrorResponse",
    "Genre",
    "HomeData",
    "SearchResult",
    "Slider",
    "StreamInfo",
    "StreamResponse",
    "Trailer",
]
