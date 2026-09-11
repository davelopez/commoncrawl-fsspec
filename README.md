# commoncrawl-fsspec

> An `fsspec` filesystem plugin that turns the [Common Crawl](https://commoncrawl.org/) web archive into a browseable virtual filesystem.

[![Python >=3.10](https://img.shields.io/badge/python->=3.10-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ Features

- **Browse** the Common Crawl archive like a filesystem — crawls, segments, and WARC files
- **Read** individual WARC records via HTTP byte-range requests
- **Download** files to disk with standard `fsspec` operations
- **Interactive CLI** with a rich terminal browser for exploration

## 📦 Installation

```bash
pip install commoncrawl-fsspec
```

### Optional extras

| Extra      | Description                       |
| ---------- | --------------------------------- |
| `examples` | Interactive CLI (`click`, `rich`) |

```bash
pip install commoncrawl-fsspec[examples]
```

## 🚀 Quick Start

### Python API

```python
import fsspec

# Create the filesystem
fs = fsspec.filesystem("cc")

# List top-level directories
fs.ls("/")
# ['/crawls']

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

### Interactive CLI

```bash
# Launch the interactive browser
python -m examples.cc interactive

# List a path
python -m examples.cc ls /crawls
```

## 📂 Virtual Filesystem

The plugin exposes a virtual filesystem for navigating the archive:

### Archive Browser (`/crawls`)

Navigate the Common Crawl archive structure:

```
/
└── /crawls/                          → List of crawls (from collinfo.json)
    └── /crawls/{crawl-id}/
        └── /crawls/{crawl-id}/segments/
            └── /crawls/{crawl-id}/segments/{segment-id}/
                ├── /crawls/.../warc/   → WARC files
                ├── /crawls/.../wet/    → WET files
                └── /crawls/.../wat/    → WAT files
```

## 📖 API Reference

### `CommonCrawlFileSystem`

| Method                       | Description                     |
| ---------------------------- | ------------------------------- |
| `ls(path, detail=True)`      | List directory contents         |
| `info(path)`                 | Get file/directory metadata     |
| `glob(pattern, detail=True)` | Glob for files matching pattern |
| `open(path, mode="rb")`      | Open a file for reading         |
| `cat_file(path, start, end)` | Read bytes from a file          |
| `get_file(rpath, lpath)`     | Download a file to disk         |

### Constructor Options

| Parameter   | Default | Description                     |
| ----------- | ------- | ------------------------------- |
| `cache_ttl` | `86400` | Cache TTL in seconds (24 hours) |

## 🏗️ Architecture

```
commoncrawl-fsspec/
├── filesystem.py          # CommonCrawlFileSystem (fsspec orchestrator)
├── paths.py               # Virtual path parsing and building
├── models.py              # Data models (CrawlInfo, WarcFileInfo)
├── caching.py             # TTL cache for crawl list
├── clients/
│   ├── http_client.py     # HTTP client with retries
│   ├── crawl_index_client.py  # Crawl discovery (collinfo.json)
│   ├── s3_listing_client.py   # Crawl manifest browsing
│   └── warc_fetcher.py    # WARC record byte-range fetching
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
