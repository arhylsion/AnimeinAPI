from __future__ import annotations

from fastapi import APIRouter

from ...models import ErrorResponse
from .ads import router as ads_router
from .anime import router as anime_router
from .bulk import router as bulk_router
from .catalog import router as catalog_router
from .community import router as community_router
from .stream import router as stream_router

router = APIRouter(prefix="/api", responses={502: {"model": ErrorResponse}})

router.include_router(catalog_router)
router.include_router(anime_router)
router.include_router(stream_router)
router.include_router(bulk_router)
router.include_router(community_router)
router.include_router(ads_router)

__all__ = ["router"]
