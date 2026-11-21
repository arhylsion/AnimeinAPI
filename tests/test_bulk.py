"""Tests for Bulk Scraping, Catalog Stats, and Metrics in AnimeinAPI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from animeinapi.config import Settings
from animeinapi.core.cache import Cache
from animeinapi.core.client import HttpClient
from animeinapi.core.service import AnimeinService
from animeinapi.main import Metrics

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://animeinweb.com"
PROXY_URL = f"{BASE_URL}/api/proxy"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def settings() -> Settings:
    return Settings(base_url=BASE_URL, proxy_secret="test-secret", timeout=5.0, retries=1)


@pytest.fixture
def service(settings):
    return AnimeinService(HttpClient(settings), Cache(), settings)


async def test_get_anime_bulk_success(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        movie_detail_fixture = {
            "status": 200,
            "error": False,
            "data": {
                "movie": {
                    "id": "341",
                    "title": "Naruto",
                    "type": "TV",
                    "status": "Completed",
                }
            },
        }
        mock.get("/3/2/movie/detail/341").mock(
            return_value=Response(200, json=movie_detail_fixture)
        )
        mock.get("/3/2/movie/detail/2073").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {
                        "movie": {
                            "id": "2073",
                            "title": "Haikyuu",
                            "type": "TV",
                        }
                    },
                },
            )
        )

        bulk = await service.get_anime_bulk(["341", "2073"])
        assert bulk.total_requested == 2
        assert bulk.total_success == 2
        assert bulk.total_failed == 0
        assert bulk.items["341"].title == "Naruto"
        assert bulk.items["2073"].title == "Haikyuu"
        assert len(bulk.errors) == 0


async def test_get_anime_bulk_partial_failure(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/movie/detail/341").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {
                        "movie": {
                            "id": "341",
                            "title": "Naruto",
                        }
                    },
                },
            )
        )
        mock.get("/3/2/movie/detail/999").mock(return_value=Response(404, text="Not Found"))

        bulk = await service.get_anime_bulk(["341", "999"])
        assert bulk.total_requested == 2
        assert bulk.total_success == 1
        assert bulk.total_failed == 1
        assert "341" in bulk.items
        assert "999" in bulk.errors


async def test_get_streams_bulk(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/episode/streamnew/35969").mock(
            return_value=Response(200, json=load("streams.json"))
        )
        bulk = await service.get_streams_bulk(["35969"])
        assert bulk.total_requested == 1
        assert bulk.total_success == 1
        stream_res = bulk.items["35969"]
        assert stream_res.episode.title == "Episode 25"
        # Verify RAPSODI prioritization
        assert stream_res.streams["480p"][0].name == "RAPSODI"


async def test_get_episodes_bulk(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/movie/episode/2073").mock(
            return_value=Response(200, json=load("episodes.json"))
        )
        bulk = await service.get_episodes_bulk(["2073"])
        assert bulk.total_requested == 1
        assert bulk.total_success == 1
        assert len(bulk.items["2073"]) == 2


async def test_get_catalog_stats(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/genre").mock(return_value=Response(200, json=load("genres.json")))
        mock.get("/3/2/explore/movie", params={"page": 81, "sort": "views"}).mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {"movie": [{"id": f"{i}"} for i in range(36)]},
                },
            )
        )
        stats = await service.get_catalog_stats()
        assert stats.total_anime == 81 * 60 + 36  # 4896
        assert stats.total_episodes == "78.000+"
        assert stats.total_genres > 0
        assert "WIB" in stats.last_updated


def test_metrics_upstream_reliability():
    metrics = Metrics()
    # 95 successes, 5 failures = 95%
    for _ in range(95):
        metrics.record_upstream(True, 0.05)
    for _ in range(5):
        metrics.record_upstream(False, 0.5)

    snap = metrics.snapshot()
    upstream_data = snap["_upstream"]
    assert upstream_data["total_calls"] == 100
    assert upstream_data["success_calls"] == 95
    assert upstream_data["failed_calls"] == 5
    assert upstream_data["success_rate_percent"] == 95.0
    assert upstream_data["meets_target_92_5"] is True
