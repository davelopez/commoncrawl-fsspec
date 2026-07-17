# commoncrawl-fsspec

> An `fsspec` filesystem plugin that turns the [Common Crawl](https://commoncrawl.org/) web archive into a browseable and searchable virtual filesystem.

[![Python >=3.10](https://img.shields.io/badge/python->=3.10-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ Features

- **Browse** the Common Crawl archive like a filesystem — crawls, segments, and WARC files
- **Search** for URLs across any crawl using the CDX API or DuckDB/Parquet
- **Read** individual WARC records via HTTP byte-range requests
- **Download** files to disk with standard `fsspec` operations
- **Interactive CLI** with a rich terminal browser for exploration
- **Pluggable search backends** — CDX API (default) or DuckDB/Parquet

## 📦 Installation

```bash
pip install commoncrawl-fsspec
```

### Optional extras

| Extra      | Description                       |
| ---------- | --------------------------------- |
| `examples` | Interactive CLI (`click`, `rich`) |
| `duckdb`   | Parquet-based search backend      |
| `warcio`   | WARC record payload extraction    |
| `all`      | Everything above                  |

```bash
pip install commoncrawl-fsspec[all]
```

## 🚀 Quick Start

### Python API

```python
import fsspec

# Create the filesystem
fs = fsspec.filesystem("cc")

# List top-level directories
fs.ls("/")
# ['/crawls', '/search']

# Browse available crawls
crawls = fs.ls("/crawls")
# ['/crawls/CC-MAIN-2026-25', '/crawls/CC-MAIN-2026-21', ...]

# Navigate into a crawl
segments = fs.ls("/crawls/CC-MAIN-2026-25/segments")
# ['/crawls/CC-MAIN-2026-25/segments/1780687572080.85', ...]

# List WARC files in a segment
files = fs.ls("/crawls/CC-MAIN-2026-25/segments/1780687572080.85/warc")
# ['/crawls/CC-MAIN-2026-25/segments/1780687572080.85/warc/CC-MAIN-20260605214811-00000.warc.gz', ...]

# Get file metadata
info = fs.info("/crawls/CC-MAIN-2026-25/segments/1780687572080.85/warc/CC-MAIN-20260605214811-00000.warc.gz")
# {'name': '...', 'type': 'file', 'size': 940246254, 'mtime': ...}
```

### Search URLs

```python
import fsspec

fs = fsspec.filesystem("cc")

# Search for URLs matching a pattern
results = fs.glob("/search/CC-MAIN-2024-33/*https://example.com/*")
for record in results:
    print(record["url"], record["mime"], record["size"])
```

### Interactive CLI

```bash
# Launch the interactive browser
python -m examples.cc interactive

# Or search directly from the command line
python -m examples.cc search CC-MAIN-2024-33 "https://example.com/*"

# List a path
python -m examples.cc ls /crawls
```

## 📂 Virtual Filesystem

The plugin exposes a virtual filesystem with two namespaces:

### Archive Browser (`/crawls`)

Navigate the Common Crawl archive structure:

```
/
├── /crawls/                          → List of crawls (from collinfo.json)
│   └── /crawls/{crawl-id}/
│       └── /crawls/{crawl-id}/segments/
│           └── /crawls/{crawl-id}/segments/{segment-id}/
│               ├── /crawls/.../warc/   → WARC files
│               ├── /crawls/.../wet/    → WET files
│               └── /crawls/.../wat/    → WAT files
└── /search/                          → Search entry point
    └── /search/{crawl-id}/            → Query via glob
```

### Search (`/search`)

The `/search` namespace is a query entry point, not a browsable folder. Use `glob` to search:

```python
# Search for URLs in a crawl
results = fs.glob("/search/CC-MAIN-2024-33/*https://example.com/*")

# Each result is a virtual file representing a captured web page
for record in results:
    print(record["url"])
    print(record["timestamp"])
    print(record["mime"])
```

**Important:** CDX search expects URL patterns, not free text:

| ✅ Works                | ❌ Doesn't work |
| ----------------------- | --------------- |
| `*.wikipedia.org/*`     | `wikipedia`     |
| `https://example.com/*` | `example`       |
| `*.gov/*`               | `government`    |

## 🔍 Search Backends

### CDX API (default)

The default backend uses the Common Crawl CDX Index API:

```python
fs = fsspec.filesystem("cc", search_backend="cdx")
```

### DuckDB/Parquet

Query the Parquet index directly with DuckDB:

```python
fs = fsspec.filesystem("cc", search_backend="parquet")
```

Requires the `duckdb` extra: `pip install commoncrawl-fsspec[duckdb]`

## 📖 API Reference

### `CommonCrawlFileSystem`

| Method                       | Description                           |
| ---------------------------- | ------------------------------------- |
| `ls(path, detail=True)`      | List directory contents               |
| `info(path)`                 | Get file/directory metadata           |
| `glob(pattern, detail=True)` | Search URLs (via `/search` namespace) |
| `open(path, mode="rb")`      | Open a file for reading               |
| `cat_file(path, start, end)` | Read bytes from a file                |
| `get_file(rpath, lpath)`     | Download a file to disk               |

### Constructor Options

| Parameter            | Default | Description                             |
| -------------------- | ------- | --------------------------------------- |
| `search_backend`     | `"cdx"` | Search backend (`"cdx"` or `"parquet"`) |
| `max_search_results` | `1000`  | Maximum search results to return        |
| `cache_ttl`          | `86400` | Cache TTL in seconds (24 hours)         |

## 🏗️ Architecture

```
commoncrawl-fsspec/
├── filesystem.py          # CommonCrawlFileSystem (fsspec orchestrator)
├── paths.py               # Virtual path parsing and building
├── models.py              # Data models (CrawlInfo, SearchRecord, etc.)
├── caching.py             # TTL and record caches
├── clients/
│   ├── http_client.py     # HTTP client with retries
│   ├── crawl_index_client.py  # Crawl discovery (collinfo.json)
│   ├── s3_listing_client.py   # Crawl manifest browsing
│   └── warc_fetcher.py    # WARC record byte-range fetching
└── search/
    ├── base.py            # SearchBackend abstract class
    ├── cdx.py             # CDX API backend
    ├── parquet.py         # DuckDB/Parquet backend
    └── factory.py         # Backend factory
```

## 🧪 Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run mypy src

# Linting
uv run ruff check src
```

## 📝 License

MIT
