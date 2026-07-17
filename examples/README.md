# Common Crawl CLI

A command-line tool to browse, search, and download data from the Common Crawl archive using the `commoncrawl-fsspec` plugin.

## Features

- **Interactive browser** — navigate the virtual filesystem with numbered entries
- **Search** for URLs within a crawl using the CDX API
- **Download** WARC records to local files
- **Rich console output** with colors, tables, and status indicators

## Installation

Install the package with all extras:

```bash
pip install commoncrawl-fsspec[all]
```

Or install from source:

```bash
pip install -e "../.[all]"
```

## Usage

### Interactive mode (recommended)

Launch the interactive browser:

```bash
python cc.py interactive
```

This opens a shell where you can navigate the filesystem by typing entry numbers:

```
📂 /
  №  Name      Type       Size
  ─────────────────────────────
  1  /crawls   📁 Dir        —
  2  /search   📁 Dir        —

Type a number to navigate, or use commands below
cc:/// > 1

📂 /crawls
  №  Name                          Type       Size
  ─────────────────────────────────────────────────
  1  /crawls/CC-MAIN-2024-10       📁 Dir        —
  2  /crawls/CC-MAIN-2024-08       📁 Dir        —
...
```

#### Interactive commands

| Command            | Description                   |
| ------------------ | ----------------------------- |
| `1, 2, 3...`       | Navigate to entry by number   |
| `..`               | Go up one level               |
| `/`                | Go to root                    |
| `back`             | Go back in history            |
| `cd <path>`        | Change to absolute path       |
| `search <pattern>` | Search URLs in current crawl  |
| `cat <num>`        | Display file contents         |
| `dl <num> <file>`  | Download file to disk         |
| `info <num>`       | Show file metadata            |
| `ls <path>`        | List a path (non-interactive) |
| `clear`            | Clear screen                  |
| `quit` / `exit`    | Exit                          |

### Command-line mode

List top-level directories:

```bash
python cc.py ls /
```

List available crawls:

```bash
python cc.py ls /crawls
```

List segments for a specific crawl:

```bash
python cc.py ls /crawls/CC-MAIN-2024-10/segments
```

List WARC files in a segment:

```bash
python cc.py ls /crawls/CC-MAIN-2024-10/segments/141.19/warc
```

Search for URLs matching a pattern in a crawl:

```bash
python cc.py search CC-MAIN-2024-10 "example.com"
```

Search with a limit on results:

```bash
python cc.py search CC-MAIN-2024-10 "github.com" --limit 10
```

Read the contents of a search result:

```bash
python cc.py cat /search/CC-MAIN-2024-10/<token>
```

Download a WARC record to a local file:

```bash
python cc.py download /search/CC-MAIN-2024-10/<token> output.warc
```

Get metadata about a file:

```bash
python cc.py info /crawls/CC-MAIN-2024-10/segments/141.19/warc/example.warc
```

## Commands Reference

| Command                    | Description                  |
| -------------------------- | ---------------------------- |
| `ls <path>`                | List contents of a directory |
| `search <crawl> <pattern>` | Search for URLs in a crawl   |
| `cat <path>`               | Display file contents        |
| `download <path> <output>` | Download a file to disk      |
| `info <path>`              | Show file metadata           |

## Examples

### Find all pages from a domain

```bash
python cc.py search CC-MAIN-2024-10 "docs.python.org" --limit 20
```

### Browse the latest crawl

```bash
python cc.py ls /crawls | tail -1
```

### Download and inspect a record

```bash
python cc.py search CC-MAIN-2024-10 "wikipedia.org" --limit 1
python cc.py download /search/CC-MAIN-2024-10/<token> record.warc
cat record.warc
```
