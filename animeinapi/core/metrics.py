from __future__ import annotations

import statistics
import time
from collections import deque

from fastapi import Request


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
