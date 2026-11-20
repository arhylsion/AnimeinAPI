# AnimeinAPI

API media stream anime berbasis platform komunitas Animein dan storage cluster **RAPSODI**. Mengambil metadata, daftar episode, statistik katalog, dan **stream multi-resolusi (360p/480p/720p/1080p)** dengan latensi cepat (<200ms) dan keandalan upstream tinggi (≥92,5%).

## Arsitektur & Ekosistem Animein

Animein memposisikan diri sebagai platform media streaming berbasis komunitas:
- Kontributor dan komunitas mengunggah episode anime dari berbagai sumber melalui portal **`teman.animein.net`**.
- File-file video yang diunggah dikelola dan didistribusikan melalui database & storage engine internal Animein bernama **RAPSODI** (disajikan via `storages.animein.net` sebagai stream direct MP4 multi-resolusi).
- **AnimeinAPI** bertindak sebagai API gateway performa tinggi dengan dukungan HTTP/2 multiplexing, persistent connection pooling, dan In-Memory SWR Cache untuk melayani konsumsi data single maupun bulk request di bawah 200ms.

## Statistik Katalog (Terverifikasi)

- **4.896** judul anime
- **78.000+** episode
- **33** genre & tema (Genre, Theme, Demographic)

## Daftar Endpoint

| Method | Path | Deskripsi | Status |
|---|---|---|---|
| GET | `/api/search?q=&page=&sort=&genre=` | Cari anime (pageSize 18/60) | ✓ |
| GET | `/api/genres` | Daftar genre (33 grup Genre/Theme) | ✓ |
| GET | `/api/home?day=&limit=` | Data homepage (8 section: slider, hot, new, today, popular, waiting, random, trailer) | ✓ |
| GET | `/api/schedule?day=` | Jadwal rilis per hari (SENIN..MINGGU/RANDOM) | ✓ |
| GET | `/api/anime/{id}` | Metadata lengkap anime | ✓ |
| GET | `/api/anime/{id}/episodes` | Daftar episode (urut naik) | ✓ |
| GET | `/api/anime/{id}/trailers` | Trailer YouTube | ✓ |
| GET | `/api/episode/{id}/streams` | Server stream per resolusi (prioritas RAPSODI direct MP4) + `episode_next` | ✓ |
| POST | `/api/bulk/anime` | Bulk scrape detail anime berdasarkan array of IDs | ✓ |
| POST | `/api/bulk/streams` | Bulk scrape stream episode berdasarkan array of IDs | ✓ |
| POST | `/api/bulk/episodes` | Bulk scrape episode list berdasarkan array of anime IDs | ✓ |
| GET | `/api/stats` | Statistik katalog realtime/cached | ✓ |
| GET | `/api/chat?highest_id=&lowest_id=` | Chat global komunitas (polling, window 100 pesan) | ✓ |
| GET | `/api/episode/{id}/comments?sort=&page=` | Komentar per episode (30/halaman) + cover/poster | ✓ |
| GET | `/api/ads?tag=` | Iklan terstruktur (video/image/redirect) | ✓ |
| GET | `/metrics` | Latency p50/p95/avg & Upstream Reliability Rate (≥92,5%) | ✓ |
| GET | `/healthz` | Health check | ✓ |
| GET | `/docs` | Swagger UI (FastAPI bawaan) | ✓ |

## Referensi API

### Search / Catalog
```http
GET /api/search?q=naruto&page=0&sort=views&genre=14,43
```
- `q`: kata kunci judul
- `page`: 0-based
- `sort`: `views` (default) | `newest` | `year` | `rating`
- `genre`: ID genre dipisah koma (dari `/api/genres`)

### Stream Multi-Resolusi (Cluster RAPSODI)
```http
GET /api/episode/35969/streams
```
```json
{
  "episode": {"id": "35969", "index": "25", "title": "Episode 25"},
  "episode_next": {"id": "35970", "index": "26"},
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
- Server `name: "RAPSODI"` bertipe `direct` (MP4 dari storage cluster Animein).

### Bulk Scraping
Mendukung pengambilan banyak data sekaligus secara paralel via HTTP/2 stream multiplexing:

```http
POST /api/bulk/anime
Content-Type: application/json

{
  "ids": ["341", "2073"]
}
```
Response:
```json
{
  "items": {
    "341": { "id": "341", "title": "Naruto: Shippuuden", ... },
    "2073": { "id": "2073", "title": "Haikyuu!!", ... }
  },
  "errors": {},
  "total_requested": 2,
  "total_success": 2,
  "total_failed": 0
}
```

Endpoint bulk lainnya:
- `POST /api/bulk/streams` dengan body `{"ids": ["35969", "5017"]}`
- `POST /api/bulk/episodes` dengan body `{"ids": ["341", "2073"]}`

### Statistik Katalog
```http
GET /api/stats
```
Response:
```json
{
  "total_anime": 4896,
  "total_episodes": "78.000+",
  "total_genres": 33,
  "last_updated": "2026-11-20 19:22:45 WIB"
}
```

### Metrik & Reliability Upstream
```http
GET /metrics
```
Mengembalikan statistik performa per-endpoint (avg, p50, p95, max) serta metrik upstream reliability (`meets_target_92_5` bernilai `true` jika success rate ≥ 92,5%).

## Instalasi & Menjalankan

```bash
# Setup virtual environment & dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Menjalankan server
python -m uvicorn animeinapi.main:app --host 0.0.0.0 --port 8000
# Atau menggunakan script entrypoint
animein
```

## Konfigurasi (.env)

Salin `.env.example` ke `.env` jika ingin menyesuaikan:

| Var | Default | Keterangan |
|---|---|---|
| `ANIMEIN_BASE_URL` | `https://animeinweb.com` | Situs sumber |
| `ANIMEIN_PROXY_SECRET` | `animein-secure-proxy-key-123` | Kunci proxy header `x-proxy-secret` |
| `ANIMEIN_TIMEOUT` | `15` | Timeout request upstream (detik) |
| `ANIMEIN_RETRIES` | `2` | Jumlah percobaan ulang untuk network error |
| `ANIMEIN_LOG_LEVEL` | `INFO` | Log level (`DEBUG` / `INFO` / `WARNING`) |

## Pengujian & Benchmark

```bash
# Menjalankan unit & integration tests
pytest

# Menjalankan latency benchmark (<200ms) & upstream success rate (≥92,5%)
python scripts/benchmark.py
```
