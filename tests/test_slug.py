"""Tests for sanitized character slug indexing, collision disambiguation, and resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from animeinapi.config import Settings
from animeinapi.core.cache import Cache
from animeinapi.core.client import HttpClient, UpstreamNotFound
from animeinapi.core.index import SlugIndex
from animeinapi.core.service import AnimeinService
from animeinapi.core.slug import (
    is_numeric_id,
    make_episode_slug,
    parse_episode_slug,
    slugify,
)

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


def test_slugify_and_episode_helpers():
    assert slugify("Naruto: Shippuuden") == "naruto-shippuuden"
    assert slugify("Haikyuu!! Second Season") == "haikyuu-second-season"
    assert slugify("  Pokémon: Horizons (2023) ") == "pokemon-horizons-2023"
    assert is_numeric_id("4039") is True
    assert is_numeric_id("naruto-shippuuden") is False

    ep_slug = make_episode_slug("naruto-shippuuden", "25")
    assert ep_slug == "naruto-shippuuden-episode-25"
    assert parse_episode_slug(ep_slug) == ("naruto-shippuuden", "25")
    assert parse_episode_slug("invalid-slug-without-marker") is None


def test_slug_index_collision_disambiguation():
    idx = SlugIndex()
    s1 = idx.register_anime("100", "Hunter x Hunter", year="1999")
    s2 = idx.register_anime("200", "Hunter x Hunter", year="2011")
    s3 = idx.register_anime("300", "Hunter x Hunter", year="2011")

    assert s1 == "hunter-x-hunter"
    assert s2 == "hunter-x-hunter-2011"
    assert s3 == "hunter-x-hunter-300"

    assert idx.get_anime_id("hunter-x-hunter") == "100"
    assert idx.get_anime_id("hunter-x-hunter-2011") == "200"
    assert idx.get_anime_id("hunter-x-hunter-300") == "300"
    # Direct ID alias also resolves
    assert idx.get_anime_id("hunter-x-hunter-100") == "100"


async def test_passive_indexing_and_warm_slug_lookup(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/movie", params={"keyword": "haikyuu"}).mock(
            return_value=Response(200, json=load("explore.json"))
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
                            "title": "Haikyuu!! Second Season",
                            "year": "2016",
                        }
                    },
                },
            )
        )

        search_res = await service.search("haikyuu")
        assert search_res.items[0].slug == "haikyuu-second-season"
        assert search_res.items[1].slug == "tsue-to-tsurugi-no-wistoria"

        # Warm lookup by character slug hits numeric detail endpoint /3/2/movie/detail/2073
        detail = await service.get_anime("haikyuu-second-season")
        assert detail.id == "2073"
        assert detail.slug == "haikyuu-second-season"


async def test_cold_anime_slug_search_fallback(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get(
            "/3/2/explore/movie",
            params={"keyword": "haikyuu second season"},
        ).mock(return_value=Response(200, json=load("explore.json")))
        mock.get("/3/2/movie/detail/2073").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {
                        "movie": {
                            "id": "2073",
                            "title": "Haikyuu!! Second Season",
                        }
                    },
                },
            )
        )

        # Cold lookup with empty index triggers search fallback and resolves to ID 2073
        detail = await service.get_anime("haikyuu-second-season")
        assert detail.id == "2073"
        assert detail.slug == "haikyuu-second-season"


async def test_episode_slug_and_nested_stream_resolution(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get(
            "/3/2/explore/movie",
            params={"keyword": "haikyuu second season"},
        ).mock(return_value=Response(200, json=load("explore.json")))
        mock.get("/3/2/movie/episode/2073").mock(
            return_value=Response(200, json=load("episodes.json"))
        )
        mock.get("/3/2/episode/streamnew/35969").mock(
            return_value=Response(200, json=load("streams.json"))
        )

        # 1. Flat episode slug resolution (cold -> search -> episodes -> streamnew/35969)
        stream_res = await service.get_streams("haikyuu-second-season-episode-25")
        assert stream_res.episode.id == "35969"
        assert stream_res.episode.slug == "haikyuu-second-season-episode-25"
        assert "720p" in stream_res.streams

        # 2. Nested resolution by anime slug + episode index
        nested_res = await service.get_episode_streams_by_index(
            "haikyuu-second-season", "25"
        )
        assert nested_res.episode.id == "35969"


async def test_bulk_mixed_slugs_and_numeric_ids(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get(
            "/3/2/explore/movie",
            params={"keyword": "haikyuu second season"},
        ).mock(return_value=Response(200, json=load("explore.json")))
        mock.get("/3/2/movie/detail/2073").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {
                        "movie": {
                            "id": "2073",
                            "title": "Haikyuu!! Second Season",
                        }
                    },
                },
            )
        )
        mock.get("/3/2/movie/detail/5018").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "error": False,
                    "data": {
                        "movie": {
                            "id": "5018",
                            "title": "Tsue to Tsurugi no Wistoria",
                        }
                    },
                },
            )
        )

        bulk = await service.get_anime_bulk(["haikyuu-second-season", "5018"])
        assert bulk.total_requested == 2
        assert bulk.total_success == 2
        assert bulk.items["haikyuu-second-season"].id == "2073"
        assert bulk.items["5018"].slug == "tsue-to-tsurugi-no-wistoria"


async def test_unknown_slug_raises_not_found(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/movie").mock(
            return_value=Response(200, json={"status": 200, "error": False, "data": {"movies": []}})
        )
        with pytest.raises(UpstreamNotFound):
            await service.get_anime("nonexistent-anime-slug")
