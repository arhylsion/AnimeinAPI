from __future__ import annotations

import asyncio
import contextlib
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from . import __version__
from .api.routes import router
from .config import get_settings
from .core.cache import Cache
from .core.client import HttpClient
from .core.metrics import Metrics, timing
from .core.service import AnimeinService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    metrics = Metrics()
    http = HttpClient(settings, on_upstream_result=metrics.record_upstream)
    cache = Cache()
    service = AnimeinService(http, cache, settings)
    app.state.http = http
    app.state.cache = cache
    app.state.service = service
    app.state.metrics = metrics

    warmup = asyncio.create_task(warmup_jobs(service))
    yield
    warmup.cancel()
    await http.aclose()


async def warmup_jobs(service: AnimeinService) -> None:
    tasks = [
        asyncio.create_task(service.get_genres()),
        asyncio.create_task(service.get_home()),
        *[
            asyncio.create_task(service.get_schedule(day))
            for day in ("SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU", "MINGGU")
        ],
    ]
    for task in tasks:
        try:
            await task
        except Exception:
            logging.getLogger("animeinapi").debug("Warmup skip", exc_info=True)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.getLogger("animeinapi").setLevel(settings.log_level.upper())

    app = FastAPI(
        title="AnimeinAPI",
        version=__version__,
        description=(
            "Provider API media stream anime berbasis komunitas Animein "
            "dan storage cluster RAPSODI (direct MP4 multi-resolusi 360p-1080p)."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )
    app.middleware("http")(timing)
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"name": "AnimeinAPI", "version": __version__}

    @app.get("/healthz", tags=["meta"])
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/metrics", tags=["meta"])
    async def metrics() -> Response:
        return JSONResponse(app.state.metrics.snapshot())

    return app


app = create_app()


def run() -> None:
    uvicorn.run("animeinapi.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()

__all__ = ["Metrics", "app", "create_app", "run"]
