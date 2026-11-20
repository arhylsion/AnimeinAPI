from __future__ import annotations

from .services import (
    AdsServiceMixin,
    AnimeServiceMixin,
    BaseService,
    BulkServiceMixin,
    CatalogServiceMixin,
    CommunityServiceMixin,
    StreamServiceMixin,
)


class AnimeinService(
    BaseService,
    AnimeServiceMixin,
    StreamServiceMixin,
    CatalogServiceMixin,
    CommunityServiceMixin,
    AdsServiceMixin,
    BulkServiceMixin,
):
    """Unified gateway service composing all atomic domain services."""
