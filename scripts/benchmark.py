#!/usr/bin/env python3
"""Benchmark AnimeinAPI performance (target <200ms) and upstream reliability (target >=92.5%)."""

from __future__ import annotations

import asyncio
import sys
import time

from animeinapi.config import Settings
from animeinapi.core.cache import Cache
from animeinapi.core.client import HttpClient
from animeinapi.core.service import AnimeinService
from animeinapi.main import Metrics


async def main() -> int:
    print("=" * 65)
    print("AnimeinAPI Performance & Upstream Reliability Benchmark")
    print("=" * 65)

    settings = Settings()
    metrics = Metrics()
    http = HttpClient(settings, on_upstream_result=metrics.record_upstream)
    cache = Cache()
    service = AnimeinService(http, cache, settings)

    # 1. Warmup
    print("\n[1/4] Warming up initial cache (genres & home)...")
    t0 = time.perf_counter()
    genres = await service.get_genres()
    home = await service.get_home()
    t_warm = (time.perf_counter() - t0) * 1000
    print(
        f"  [OK] Warmup complete in {t_warm:.2f}ms "
        f"(genres: {len(genres)}, hot items: {len(home.hot)})"
    )

    # Sample IDs from live home
    sample_anime_ids = [anime.id for anime in home.hot[:5]]
    print(f"  [OK] Sample Anime IDs: {sample_anime_ids}")

    # 2. Benchmark Single Requests (Cached & SWR)
    print("\n[2/4] Benchmarking Single Requests (Latency target: <200ms)...")
    single_results = []
    for aid in sample_anime_ids:
        await service.get_anime(aid)
        t_start = time.perf_counter()
        anime = await service.get_anime(aid)
        lat_ms = (time.perf_counter() - t_start) * 1000
        single_results.append(lat_ms)
        status = "[PASS]" if lat_ms < 200 else "[FAIL]"
        print(f"  - GET /api/anime/{aid} ('{anime.title[:25]}...'): {lat_ms:.2f}ms {status}")

    avg_single = sum(single_results) / len(single_results)
    print(f"  -> Single Requests Average Latency: {avg_single:.2f}ms (Target: <200ms)")

    # 3. Benchmark Bulk Scraping
    print("\n[3/4] Benchmarking Bulk Scraping (Concurrent target: <200ms)...")
    t_bulk_start = time.perf_counter()
    bulk_anime = await service.get_anime_bulk(sample_anime_ids)
    t_bulk_ms = (time.perf_counter() - t_bulk_start) * 1000
    bulk_status = "[PASS]" if t_bulk_ms < 200 else "[FAIL]"
    print(
        f"  - POST /api/bulk/anime ({bulk_anime.total_requested} IDs): {t_bulk_ms:.2f}ms "
        f"(Success: {bulk_anime.total_success}, Failed: {bulk_anime.total_failed}) {bulk_status}"
    )

    # Test Bulk Streams (Cold fetch then Warm/SWR fetch)
    episodes = await service.get_episodes(sample_anime_ids[0])
    sample_ep_ids = [ep.id for ep in episodes[:3]]
    t_stream_cold = time.perf_counter()
    bulk_streams_cold = await service.get_streams_bulk(sample_ep_ids)
    t_cold_ms = (time.perf_counter() - t_stream_cold) * 1000
    print(
        f"  - POST /api/bulk/streams (Cold upstream, {bulk_streams_cold.total_requested} IDs): "
        f"{t_cold_ms:.2f}ms (Success: {bulk_streams_cold.total_success})"
    )

    t_stream_start = time.perf_counter()
    bulk_streams = await service.get_streams_bulk(sample_ep_ids)
    t_stream_ms = (time.perf_counter() - t_stream_start) * 1000
    stream_status = "[PASS]" if t_stream_ms < 200 else "[FAIL]"
    print(
        f"  - POST /api/bulk/streams (Warm/SWR cache, {bulk_streams.total_requested} IDs): "
        f"{t_stream_ms:.2f}ms (Success: {bulk_streams.total_success}) {stream_status}"
    )

    # 4. Catalog Stats & Upstream Reliability
    print("\n[4/4] Verifying Catalog Stats & Upstream Reliability...")
    stats = await service.get_catalog_stats()
    print(f"  - Total Anime: {stats.total_anime}")
    print(f"  - Total Episodes: {stats.total_episodes}")
    print(f"  - Total Genres: {stats.total_genres}")
    print(f"  - Last Updated: {stats.last_updated}")

    snap = metrics.snapshot()
    upstream = snap["_upstream"]
    print("\nUpstream Reliability Metric:")
    print(f"  - Total Upstream Calls: {upstream['total_calls']}")
    print(f"  - Successful Calls:     {upstream['success_calls']}")
    print(f"  - Failed Calls:         {upstream['failed_calls']}")
    print(f"  - Success Rate:         {upstream['success_rate_percent']}% (Required: >=92.5%)")

    rate_pass = upstream["meets_target_92_5"]
    single_pass = avg_single < 200
    bulk_pass = t_bulk_ms < 200

    print("\n" + "=" * 65)
    if rate_pass and single_pass and bulk_pass:
        print("ALL BENCHMARKS & RELIABILITY TARGETS ACHIEVED")
        print(f"  [PASS] Single Scrap Latency: {avg_single:.2f}ms (< 200ms)")
        print(f"  [PASS] Bulk Scrap Latency:   {t_bulk_ms:.2f}ms (< 200ms)")
        print(f"  [PASS] Upstream Reliability: {upstream['success_rate_percent']}% (>= 92.5%)")
        print("=" * 65)
        await http.aclose()
        return 0
    else:
        print("SOME BENCHMARK CRITERIA WERE NOT MET")
        print(f"  Single pass: {single_pass}, Bulk pass: {bulk_pass}, Rate pass: {rate_pass}")
        print("=" * 65)
        await http.aclose()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
