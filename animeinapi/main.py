from __future__ import annotations

import asyncio
import contextlib
import logging
import statistics
import time
from collections import deque

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from . import __version__
from .api.routes import router
from .config import get_settings
from .core.cache import Cache
from .core.client import HttpClient
from .core.service import AnimeinService

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


class Metrics:
    WINDOW = 500

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.durations: dict[str, deque] = {}
        self.upstream_total: int = 0
        self.upstream_success: int = 0
        self.upstream_failed: int = 0
        self.upstream_durations: deque = deque(maxlen=self.WINDOW)

    def record(self, path: str, seconds: float) -> None:
        self.counts[path] = self.counts.get(path, 0) + 1
        bucket = self.durations.setdefault(path, deque(maxlen=self.WINDOW))
        bucket.append(seconds)

    def record_upstream(self, success: bool, seconds: float) -> None:
        self.upstream_total += 1
        if success:
            self.upstream_success += 1
        else:
            self.upstream_failed += 1
        self.upstream_durations.append(seconds)

    def snapshot(self) -> dict:
        out: dict = {}
        rate = (
            round((self.upstream_success / self.upstream_total * 100), 2)
            if self.upstream_total > 0
            else 100.0
        )
        out["_upstream"] = {
            "total_calls": self.upstream_total,
            "success_calls": self.upstream_success,
            "failed_calls": self.upstream_failed,
            "success_rate_percent": rate,
            "meets_target_92_5": rate >= 92.5,
        }
        for path, bucket in self.durations.items():
            samples = sorted(bucket)
            n = len(samples)
            out[path] = {
                "count": self.counts.get(path, 0),
                "avg_ms": round(statistics.mean(samples) * 1000, 2),
                "p50_ms": round(samples[n // 2] * 1000, 2),
                "p95_ms": round(samples[min(int(n * 0.95), n - 1)] * 1000, 2),
                "max_ms": round(samples[-1] * 1000, 2),
            }
        return out


async def timing(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    metrics = request.app.state.metrics
    path = request.scope.get("route")
    path_label = getattr(path, "path", request.url.path) if path else request.url.path
    metrics.record(path_label, duration)
    response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.2f}"
    return response


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
