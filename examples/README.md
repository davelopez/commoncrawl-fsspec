# Common Crawl CLI

A command-line tool to browse and download data from the Common Crawl archive using the `commoncrawl-fsspec` plugin.

## Features

- **Interactive browser** — navigate the virtual filesystem with numbered entries
- **Download** WARC files to local files
- **Rich console output** with colors, tables, and status indicators

## Installation

All commands below are run from the repository root (the directory containing `pyproject.toml`).
The environment is managed with [uv](https://docs.astral.sh/uv/) — install it first if you haven't
already — and the CLI needs the `examples` extra:

```bash
uv sync --extra examples
```

That installs the `examples` extra dependencies, which the CLI requires. If you consume the
plugin from another project instead, add it with the extra:

```bash
uv add "commoncrawl-fsspec[examples]"
```

> **Tip:** adding `--extra examples` to any `uv run` command resolves the extra on the fly, e.g.
> `uv run --extra examples python -m examples.cc ls /`. Without it (and without the `uv sync`
> above) you will get `ModuleNotFoundError: No module named 'rich'`.

## Usage

### Interactive mode (recommended)

Launch the interactive browser:

```bash
uv run python -m examples.cc interactive
```

This opens a shell where you can navigate the filesystem by typing entry numbers:

```
📂 /
  №  Name      Type       Size
  ─────────────────────────────
  1  /crawls   📁 Dir        —

Type a number to navigate, or use commands below
cc:/// > 1

📂 /crawls
  №  Name                          Type       Size
  ─────────────────────────────────────────────────
  1  /crawls/CC-MAIN-2026-34       📁 Dir        —
  2  /crawls/CC-MAIN-2026-30       📁 Dir        —
...
```

#### Interactive commands

| Command           | Description                   |
| ----------------- | ----------------------------- |
| `1, 2, 3...`      | Navigate to entry by number   |
| `..`              | Go up one level               |
| `/`               | Go to root                    |
| `back`            | Go back in history            |
| `cd <path>`       | Change to absolute path       |
| `cat <num>`       | Display file contents         |
| `dl <num> <file>` | Download file to disk         |
| `info <num>`      | Show file metadata            |
| `ls <path>`       | List a path (non-interactive) |
| `clear`           | Clear screen                  |
| `quit` / `exit`   | Exit                          |

### Command-line mode

List top-level directories:

```bash
uv run python -m examples.cc ls /
```

List available crawls (newest first):

```bash
uv run python -m examples.cc ls /crawls
```

List segments for a specific crawl:

```bash
uv run python -m examples.cc ls /crawls/CC-MAIN-2026-34/segments
```

List WARC files in a segment:

```bash
uv run python -m examples.cc ls /crawls/CC-MAIN-2026-34/segments/1786091384908.68/warc
```

Read the contents of a file:

```bash
uv run python -m examples.cc cat \
  /crawls/CC-MAIN-2026-34/segments/1786091384908.68/wet/CC-MAIN-20260807101845-20260807131845-00000.warc.wet.gz
```

Download a file to a local file:

```bash
uv run python -m examples.cc download \
  /crawls/CC-MAIN-2026-34/segments/1786091384908.68/warc/CC-MAIN-20260807101845-20260807131845-00000.warc.gz \
  record.warc.gz
```

Get metadata about a file:

```bash
uv run python -m examples.cc info \
  /crawls/CC-MAIN-2026-34/segments/1786091384908.68/warc/CC-MAIN-20260807101845-20260807131845-00000.warc.gz
```

> The crawl, segment and file names above are examples — run `ls /crawls` to discover the current
> ones. WARC files are roughly 1 GB each, WET/WAT files are smaller (~60 MB / ~150 MB), so prefer
> those for a quick test.

> `cat` loads the whole file into memory and WARC/WET/WAT files are gzip-compressed, so it reports
> "binary content". Use `download` plus `gzip -dc` to inspect the records.

## Commands Reference

| Command                    | Description                  |
| -------------------------- | ---------------------------- |
| `ls <path>`                | List contents of a directory |
| `cat <path>`               | Display file contents        |
| `download <path> <output>` | Download a file to disk      |
| `info <path>`              | Show file metadata           |

## Examples

### Browse the latest crawl

```bash
uv run python -m examples.cc ls /crawls
```

### Download and inspect a WET file

WET files are much smaller than WARC files, which makes them handy for a quick test:

```bash
uv run python -m examples.cc download \
  /crawls/CC-MAIN-2026-34/segments/1786091384908.68/wet/CC-MAIN-20260807101845-20260807131845-00000.warc.wet.gz \
  record.warc.wet.gz

gzip -dc record.warc.wet.gz | head -n 1
```

### Keep long paths when piping

Rich truncates long paths to fit the output width. When piping the output somewhere else, set
`COLUMNS` so full paths survive:

```bash
COLUMNS=200 uv run python -m examples.cc ls \
  /crawls/CC-MAIN-2026-34/segments/1786091384908.68/warc | head
```
