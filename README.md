# AnimeinAPI

High-performance API gateway for the community-driven Animein media streaming platform and the **RAPSODI** storage cluster. Provides catalog metadata, episode listings, sanitized character slug indexing, catalog statistics, bulk scraping, and **multi-resolution direct MP4 streams (360p/480p/720p/1080p)** with sub-200ms latency and high upstream reliability (>= 92.5%).

## Architecture & Ecosystem

Animein operates as a community-driven media streaming platform:
- Community contributors upload anime episodes from various sources via the **`teman.animein.net`** upload portal.
- Uploaded video files are stored and served through Animein's internal storage engine and database named **RAPSODI** (`storages.animein.net`) as multi-resolution direct MP4 streams.
- **AnimeinAPI** acts as a fast API gateway featuring HTTP/2 multiplexing, persistent connection pooling, bidirectional character slug indexing (`slug <-> numeric_id`), and an in-memory Stale-While-Revalidate (SWR) cache to serve single and bulk requests under 200ms.

## Verified Catalog Statistics

- **4,896** anime titles
- **78,000+** episodes
- **33** genres & themes (Genre, Theme, Demographic)

## Endpoints

| Method | Path | Description | Status |
|---|---|---|---|
| GET | `/api/search?q=&page=&sort=&genre=` | Search anime catalog | OK |
| GET | `/api/genres` | List all genres and themes (33) | OK |
| GET | `/api/home?day=&limit=` | Homepage data (slider, hot, new, today, popular, waiting, random, trailer) | OK |
| GET | `/api/schedule?day=` | Release schedule by day (`SENIN`..`MINGGU` / `RANDOM`) | OK |
| GET | `/api/anime/{id_or_slug}` | Full anime metadata (accepts numeric ID or character slug) | OK |
| GET | `/api/anime/{id_or_slug}/episodes` | Episode list in ascending order (accepts numeric ID or slug) | OK |
| GET | `/api/anime/{id_or_slug}/trailers` | YouTube trailers (accepts numeric ID or slug) | OK |
| GET | `/api/anime/{id_or_slug}/episode/{index}/streams` | Stream servers by anime ID/slug and episode number | OK |
| GET | `/api/episode/{id_or_slug}/streams` | Stream servers by numeric episode ID or flat episode slug | OK |
| POST | `/api/bulk/anime` | Bulk fetch anime details by array of numeric IDs or slugs | OK |
| POST | `/api/bulk/streams` | Bulk fetch episode streams by array of numeric IDs or slugs | OK |
| POST | `/api/bulk/episodes` | Bulk fetch episode lists by array of anime IDs or slugs | OK |
| GET | `/api/stats` | Cached realtime catalog statistics | OK |
| GET | `/api/chat?highest_id=&lowest_id=` | Global community chat (polling, 100-message window) | OK |
| GET | `/api/episode/{id_or_slug}/comments?sort=&page=` | Episode comments (30/page) + cover/poster | OK |
| GET | `/api/ads?tag=` | Structured ads (video/image/redirect) | OK |
| GET | `/metrics` | Per-path latency (avg/p50/p95/max) & upstream reliability rate (>= 92.5%) | OK |
| GET | `/healthz` | Health check | OK |
| GET | `/docs` | Swagger UI (FastAPI) | OK |

## Character Slug Indexing & Resolution

Every `AnimeSummary`, `AnimeDetail`, and `Episode` object includes a sanitized ASCII kebab-case `slug` alongside its upstream numeric `id`:
- **Anime Slug**: e.g. `"title": "Naruto: Shippuuden"` -> `"slug": "naruto-shippuuden"` (resolves to upstream ID `341`).
- **Collision Disambiguation**: If two different anime share the same title slug, the second is automatically disambiguated with `-{year}` (e.g. `hunter-x-hunter-2011`), falling back to `-{id}`.
- **Flat Episode Slug**: `{anime_slug}-episode-{index}`, e.g. `naruto-shippuuden-episode-25` (resolves to upstream episode ID `35969`).
- **Nested Episode Route**: `GET /api/anime/naruto-shippuuden/episode/25/streams`.
- **Cold Miss Fallback**: If a slug is requested before it has been seen in `home`, `schedule`, or `search`, AnimeinAPI automatically queries upstream search, indexes the result, and resolves the numeric ID transparently.

## API Reference

### Search / Catalog
```http
GET /api/search?q=naruto&page=0&sort=views&genre=14,43
```
- `q`: title keyword
- `page`: 0-based page index
- `sort`: `views` (default) | `newest` | `year` | `rating`
- `genre`: comma-separated genre IDs (from `/api/genres`)

### Anime Detail & Episodes (by Slug or Numeric ID)
```http
GET /api/anime/naruto-shippuuden
GET /api/anime/341
GET /api/anime/naruto-shippuuden/episodes
```

### Multi-Resolution Streams (RAPSODI Cluster)
```http
GET /api/episode/35969/streams
GET /api/episode/haikyuu-second-season-episode-25/streams
GET /api/anime/haikyuu-second-season/episode/25/streams
```
```json
{
  "episode": {
    "id": "35969",
    "slug": "haikyuu-second-season-episode-25",
    "index": "25",
    "title": "Episode 25"
  },
  "episode_next": {
    "id": "35970",
    "slug": "haikyuu-second-season-episode-26",
    "index": "26"
  },
  "streams": {
    "360p": [
      {
        "id": "599380",
        "link": "https://storages.animein.net/...25-360p-....mp4",
        "quality": "360p",
        "type": "direct",
        "name": "RAPSODI",
        "key_file_size": "25.78"
      }
    ],
    "480p": [...],
    "720p": [...]
  }
}
```
- `name: "RAPSODI"` with `type: "direct"` serves direct MP4 streams from Animein's storage cluster and is automatically prioritized first.

### Bulk Scraping
Fetch multiple items concurrently over HTTP/2 stream multiplexing using numeric IDs, character slugs, or a mix of both:

```http
POST /api/bulk/anime
Content-Type: application/json

{
  "ids": ["naruto-shippuuden", "2073"]
}
```
Response:
```json
{
  "items": {
    "naruto-shippuuden": { "id": "341", "slug": "naruto-shippuuden", "title": "Naruto: Shippuuden" },
    "2073": { "id": "2073", "slug": "haikyuu-second-season", "title": "Haikyuu!! Second Season" }
  },
  "errors": {},
  "total_requested": 2,
  "total_success": 2,
  "total_failed": 0
}
```

Other bulk endpoints:
- `POST /api/bulk/streams` with body `{"ids": ["haikyuu-second-season-episode-25", "5017"]}`
- `POST /api/bulk/episodes` with body `{"ids": ["naruto-shippuuden", "2073"]}`

### Catalog Statistics
```http
GET /api/stats
```
Response:
```json
{
  "total_anime": 4896,
  "total_episodes": "78.000+",
  "total_genres": 33,
  "last_updated": "2026-11-21 06:57:36 WIB"
}
```

### Metrics & Upstream Reliability
```http
GET /metrics
```
Returns per-endpoint latency percentiles (`avg_ms`, `p50_ms`, `p95_ms`, `max_ms`) and upstream reliability stats (`meets_target_92_5` is `true` when success rate >= 92.5%).

## Project Structure

```text
animeinapi/
├── __init__.py
├── config.py                  # Settings via pydantic-settings
├── main.py                    # FastAPI app, lifespan, warmup
├── models/                    # Atomic domain models
│   ├── __init__.py
│   ├── ad.py
│   ├── anime.py
│   ├── catalog.py
│   ├── common.py
│   ├── community.py
│   ├── episode.py
│   └── stream.py
├── core/
│   ├── cache.py               # In-memory TTL cache (single-flight + SWR + negative cache)
│   ├── client.py              # Async HTTP/2 client with pooling & retry/backoff
│   ├── constants.py           # TTLs and shared constants
│   ├── index.py               # Bidirectional slug <-> numeric ID index
│   ├── metrics.py             # Request latency & upstream reliability metrics
│   ├── service.py             # Unified AnimeinService facade
│   ├── slug.py                # Sanitization & slug parsing utilities
│   └── services/              # Atomic domain service mixins
│       ├── __init__.py
│       ├── ads.py
│       ├── anime.py
│       ├── base.py
│       ├── bulk.py
│       ├── catalog.py
│       ├── community.py
│       └── stream.py
└── api/
    └── routes/                # Modular FastAPI routers
        ├── __init__.py
        ├── ads.py
        ├── anime.py
        ├── bulk.py
        ├── catalog.py
        ├── community.py
        ├── dependencies.py
        └── stream.py
scripts/
└── benchmark.py               # Live latency (<200ms) & reliability (>=92.5%) benchmark
tests/                         # pytest + respx test suite (25 tests)
```

## Installation & Running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m uvicorn animeinapi.main:app --host 0.0.0.0 --port 8000
# or
animein
```

## Configuration (.env)

Copy `.env.example` to `.env` to override defaults:

| Variable | Default | Description |
|---|---|---|
| `ANIMEIN_BASE_URL` | `https://animeinweb.com` | Upstream source URL |
| `ANIMEIN_PROXY_SECRET` | `animein-secure-proxy-key-123` | `x-proxy-secret` header value |
| `ANIMEIN_TIMEOUT` | `15` | Upstream request timeout (seconds) |
| `ANIMEIN_RETRIES` | `2` | Retry count for network/5xx errors |
| `ANIMEIN_LOG_LEVEL` | `INFO` | Log level (`DEBUG` / `INFO` / `WARNING`) |

## Testing & Benchmark

```bash
# Run unit & integration tests
pytest

# Run latency (<200ms) & upstream reliability (>=92.5%) benchmark
python scripts/benchmark.py
```
