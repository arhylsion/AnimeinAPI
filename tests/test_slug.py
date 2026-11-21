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
    assert (
        make_episode_slug("naruto-shippuuden", "25", disambiguator="999")
        == "naruto-shippuuden-episode-25-999"
    )
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
    assert idx.get_anime_id("hunter-x-hunter-100") == "100"


def test_slug_index_collision_disambiguation_with_aid():
    idx = SlugIndex()
    s1 = idx.register_anime("400", "Bleach", year=None)
    s2 = idx.register_anime("500", "Bleach", year=None)
    assert s1 == "bleach"
    assert s2 == "bleach-500"
    assert idx.get_anime_id("bleach") == "400"
    assert idx.get_anime_id("bleach-500") == "500"


def test_slug_index_alias_does_not_shadow_existing_entry():
    idx = SlugIndex()
    # Anime 10 has title "Foo 20", so its canonical slug is "foo-20"
    first = idx.register_anime("10", "Foo 20")
    assert first == "foo-20"
    # Anime 20 has title "Foo", so its synthetic alias would be "foo-20"
    second = idx.register_anime("20", "Foo")
    assert second == "foo"
    # "foo-20" must still resolve to anime "10", not be overwritten by anime "20"'s synthetic alias
    assert idx.get_anime_id("foo-20") == "10"
    assert idx.get_anime_id("foo") == "20"


def test_register_episode_none_and_collision_disambiguation():
    idx = SlugIndex()
    idx.register_anime("2073", "Haikyuu")
    assert idx.register_episode("1", None, anime_id="2073") is None
    assert idx.register_episode("10", 5, anime_id="2073") == "haikyuu-episode-5"
    # Colliding episode ID for the same anime + episode index is disambiguated with -{eid}
    assert idx.register_episode("11", 5, anime_id="2073") == "haikyuu-episode-5-11"
    assert idx.get_episode_id("haikyuu-episode-5") == "10"
    assert idx.get_episode_id("haikyuu-episode-5-11") == "11"


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


async def test_get_episode_streams_by_index_pagination_and_not_found(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        # Page 0 has 30 episodes (indices 1..30), page 1 has episode 31 (id 90031)
        page0_episodes = [
            {"id": str(80000 + i), "index": str(i), "title": f"Episode {i}", "id_movie": "2073"}
            for i in range(1, 31)
        ]
        page1_episodes = [
            {"id": "90031", "index": "31", "title": "Episode 31", "id_movie": "2073"}
        ]
        mock.get("/3/2/movie/episode/2073", params={"page": 0}).mock(
            return_value=Response(
                200, json={"status": 200, "error": False, "data": {"episode": page0_episodes}}
            )
        )
        mock.get("/3/2/movie/episode/2073", params={"page": 1}).mock(
            return_value=Response(
                200, json={"status": 200, "error": False, "data": {"episode": page1_episodes}}
            )
        )
        mock.get("/3/2/episode/streamnew/90031").mock(
            return_value=Response(200, json=load("streams.json"))
        )

        # Resolves episode 31 from page 1 (0-based pagination: page=0 -> page=1)
        res = await service.get_episode_streams_by_index("2073", "31")
        assert res.episode.id == "35969"

        # Non-existent episode index stops after page 1 (len < 30) and raises UpstreamNotFound
        with pytest.raises(UpstreamNotFound):
            await service.get_episode_streams_by_index("2073", "999")


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
            return_value=Response(
                200, json={"status": 200, "error": False, "data": {"movies": []}}
            )
        )
        with pytest.raises(UpstreamNotFound):
            await service.get_anime("nonexistent-anime-slug")
