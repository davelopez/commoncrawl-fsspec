"""Common Crawl CLI — browse, search, and download from Common Crawl."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import click

try:
    import fsspec
except ImportError:
    print("Error: fsspec is required. Install with: pip install commoncrawl-fsspec")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from commoncrawl_fsspec.search.base import SearchQuery
except ImportError:
    print(
        "Error: rich is required. Install with: pip install commoncrawl-fsspec[examples]"
    )
    sys.exit(1)

console = Console()


def get_fs():
    """Get a CommonCrawl filesystem instance."""
    return fsspec.filesystem("cc")


def format_size(size: float) -> str:
    """Format a file size in human-readable form."""
    if size == 0:
        return "—"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


def format_timestamp(ts) -> str:
    """Format a timestamp for display."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    return str(ts)


def render_entries(
    path: str,
    entries: list,
    show_numbers: bool = False,
) -> Tuple[List[str], List[str]]:
    """Render entries as a table. Returns (dir_paths, file_paths)."""
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")

    if show_numbers:
        table.add_column("№", style="bold yellow", width=4, justify="right")

    table.add_column("Name", style="white", no_wrap=True)
    table.add_column("Type", style="magenta", width=10)
    table.add_column("Size", style="green", justify="right")

    dir_paths: List[str] = []
    file_paths: List[str] = []

    for entry in entries:
        name = entry["name"]
        etype = entry.get("type", "file")
        size = entry.get("size", 0)

        if etype == "directory":
            dir_paths.append(name)
            table.add_row(
                f"{len(dir_paths)}" if show_numbers else "",
                name,
                "📁 Dir",
                "—",
            )
        else:
            file_paths.append(name)
            idx = len(dir_paths) + len(file_paths)
            table.add_row(
                f"{idx}" if show_numbers else "",
                name,
                "📄 File",
                format_size(size),
            )

    console.print(f"\n[bold]📂 {path}[/bold]")
    console.print(table)

    if show_numbers:
        console.print(f"\n[dim]Type a number to navigate, or use commands below[/dim]")
    else:
        console.print(
            f"\n[dim]{len(dir_paths)} dir(s), {len(file_paths)} file(s)[/dim]"
        )

    return dir_paths, file_paths


def run_search(fs, crawl_id: str, pattern: str, limit: int):
    """Run a URL-pattern search against the active crawl."""
    fs._get_crawl_list()
    query = SearchQuery(crawl_id=crawl_id, url_pattern=pattern, limit=limit)
    result = fs.search_backend.search(query)
    return result.records


def interactive_shell(start_path: str = "/") -> None:
    """Launch an interactive browsing shell."""
    fs = get_fs()
    cwd = start_path
    history: List[str] = [cwd]
    history_idx = 0

    console.print(
        Panel(
            "[bold cyan]Common Crawl Interactive Browser[/bold cyan]\n\n"
            "[dim]Navigation:[/dim]\n"
            "  [bold]1, 2, 3...[/bold]      Navigate to entry by number\n"
            "  [bold]..[/bold]                Go up one level\n"
            "  [bold]/[/bold]                 Go to root\n"
            "  [bold]back[/bold]              Go back in history\n"
            "  [bold]cd <path>[/bold]         Change to absolute path\n"
            "  [bold]search <pattern>[/bold]  Search URLs in current crawl\n"
            "                         Use URL patterns like https://example.com/*\n"
            "  [bold]cat <num>[/bold]         Display file contents\n"
            "  [bold]dl <num> <file>[/bold]   Download file to disk\n"
            "  [bold]info <num>[/bold]        Show file metadata\n"
            "  [bold]ls <path>[/bold]         List a path (non-interactive)\n"
            "  [bold]clear[/bold]             Clear screen\n"
            "  [bold]quit[/bold] / [bold]exit[/bold]    Exit\n",
            title="🌐 Welcome",
            border_style="cyan",
        )
    )

    while True:
        # Fetch entries
        try:
            entries = fs.ls(cwd, detail=True)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            entries = []

        dir_paths, file_paths = render_entries(cwd, entries, show_numbers=True)
        all_paths = dir_paths + file_paths

        # Prompt
        prompt = f"\n[cyan]cc://{cwd}[/cyan] [bold]>[/bold] "
        try:
            raw = console.input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # --- Navigation ---
        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        elif cmd == "clear":
            console.clear()
            continue

        elif cmd == "back":
            if history_idx > 0:
                history_idx -= 1
                cwd = history[history_idx]
            else:
                console.print("[dim]Already at start of history[/dim]")
            continue

        elif cmd == "..":
            parent = Path(cwd).parent
            cwd = str(parent) if parent != Path(".") else "/"
            history.append(cwd)
            history_idx = len(history) - 1
            continue

        elif cmd == "/":
            cwd = "/"
            history.append(cwd)
            history_idx = len(history) - 1
            continue

        elif cmd == "cd":
            if not args:
                console.print("[yellow]Usage: cd <path>[/yellow]")
                continue
            target = args.strip()
            if not target.startswith("/"):
                target = cwd.rstrip("/") + "/" + target
            try:
                fs.ls(target, detail=True)
                cwd = target
                history.append(cwd)
                history_idx = len(history) - 1
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            continue

        elif cmd == "ls":
            target = args.strip() if args else cwd
            try:
                entries = fs.ls(target, detail=True)
                render_entries(target, entries, show_numbers=False)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            continue

        # --- Search ---
        elif cmd == "search":
            if not args:
                console.print("[yellow]Usage: search <pattern>[/yellow]")
                continue
            # Try to extract crawl_id from current path
            if "/search/" in cwd:
                crawl_id = cwd.split("/search/")[1].split("/")[0]
            elif "/crawls/" in cwd:
                crawl_id = cwd.split("/crawls/")[1].split("/")[0]
            else:
                console.print(
                    "[yellow]Navigate to /crawls/<id> or /search/<id> first[/yellow]"
                )
                continue

            pattern = args.strip()
            with console.status(
                f"[cyan]Searching [bold]{crawl_id}[/bold] for [green]{pattern}[/green]..."
            ):
                try:
                    results = run_search(fs, crawl_id, pattern, fs.max_search_results)
                except Exception as e:
                    console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
                    continue

            if not results:
                console.print(
                    Panel(
                        f"No results for [green]'{pattern}'[/green]",
                        title="[yellow]Search[/yellow]",
                        border_style="yellow",
                    )
                )
                continue

            results = results[:50]
            table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
            table.add_column("№", style="bold yellow", width=4, justify="right")
            table.add_column("URL", style="cyan", no_wrap=True)
            table.add_column("MIME", style="magenta", width=20)
            table.add_column("Size", style="green", justify="right", width=10)

            for i, entry in enumerate(results, 1):
                url = getattr(entry, "url", "")
                mime = getattr(entry, "mime", "")
                size = format_size(getattr(entry, "length", 0))
                table.add_row(str(i), url, mime, size)

            console.print(
                Panel(
                    table,
                    title=f"[green]{len(results)} results[/green] for [bold]{pattern}[/bold]",
                    border_style="green",
                )
            )
            continue

        # --- File operations by number ---
        elif cmd in ("cat", "dl", "download", "info"):
            if not args:
                console.print(f"[yellow]Usage: {cmd} <number>[/yellow]")
                continue
            try:
                num = int(args.strip().split()[0]) - 1
            except (ValueError, IndexError):
                console.print(f"[yellow]Usage: {cmd} <number>[/yellow]")
                continue

            if num < 0 or num >= len(all_paths):
                console.print(f"[yellow]Invalid number: {num + 1}[/yellow]")
                continue

            target = all_paths[num]

            if cmd == "cat":
                with console.status(f"[cyan]Reading [bold]{target}[/bold]..."):
                    try:
                        with fs.open(target, "rb") as f:
                            data = f.read()
                    except Exception as e:
                        console.print(
                            f"[bold red]Error:[/bold red] {e}", soft_wrap=True
                        )
                        continue

                try:
                    text = data.decode("utf-8")
                    console.print(
                        Panel(
                            text[:4000],
                            title=f"[bold]📄 {target}[/bold] ([dim]{format_size(len(data))}[/dim])",
                            border_style="blue",
                            expand=False,
                        )
                    )
                    if len(data) > 4000:
                        console.print(
                            f"[dim]... truncated (showing first 4000 chars)[/dim]"
                        )
                except UnicodeDecodeError:
                    console.print(
                        Panel(
                            f"[yellow]Binary content[/yellow] — use [bold]dl[/bold] to save.\n\nSize: [green]{format_size(len(data))}[/green]",
                            title=f"[bold]📄 {target}[/bold]",
                            border_style="yellow",
                        )
                    )

            elif cmd in ("dl", "download"):
                dl_parts = args.strip().split()
                output = dl_parts[1] if len(dl_parts) > 1 else "download.warc"
                with console.status(f"[cyan]Downloading [bold]{target}[/bold]..."):
                    try:
                        with fs.open(target, "rb") as f:
                            data = f.read()
                    except Exception as e:
                        console.print(
                            f"[bold red]Error:[/bold red] {e}", soft_wrap=True
                        )
                        continue

                out = Path(output)
                out.write_bytes(data)
                console.print(
                    f"[bold green]✓ Downloaded[/bold green] [cyan]{format_size(len(data))}[/cyan] → [bold]{out}[/bold]"
                )

            elif cmd == "info":
                with console.status(f"[cyan]Getting info for [bold]{target}[/bold]..."):
                    try:
                        entry = fs.info(target)
                    except Exception as e:
                        console.print(
                            f"[bold red]Error:[/bold red] {e}", soft_wrap=True
                        )
                        continue

                table = Table(box=box.ROUNDED, show_header=False)
                table.add_column("Field", style="bold cyan", width=14)
                table.add_column("Value", style="white")

                for label, key in [
                    ("Path", "name"),
                    ("Type", "type"),
                    ("Size", "size"),
                    ("Modified", "mtime"),
                    ("URL", "url"),
                    ("Timestamp", "timestamp"),
                ]:
                    val = entry.get(key)
                    if val is not None:
                        if key == "size":
                            val = format_size(val)
                        elif key == "mtime":
                            val = format_timestamp(val)
                        table.add_row(label, str(val))

                console.print(
                    Panel(table, title="[bold]📋 File Info[/bold]", border_style="blue")
                )
            continue

        # --- Try to parse as a number (navigation) ---
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(all_paths):
                target = all_paths[idx]
                # Check if it's a directory
                try:
                    entry = fs.info(target)
                    if entry.get("type") == "file":
                        console.print(
                            f"[dim]'{target}' is a file. Use[/dim] [bold]cat {idx + 1}[/bold] [dim]to view it.[/dim]"
                        )
                        continue
                except Exception:
                    pass
                cwd = target
                history.append(cwd)
                history_idx = len(history) - 1
                continue
            else:
                console.print(f"[yellow]No entry #{idx + 1}[/yellow]")
                continue
        except ValueError:
            console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            continue


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option()
def cli(ctx):
    """🌐 Browse, search, and download data from [bold cyan]Common Crawl[/].

    \\b
    Run with [bold]interactive[/bold] for an interactive browser.

    Examples:
      [bold]cc interactive[/bold]                     Interactive browser
      [bold]cc ls /[/]                              List top-level directories
      [bold]cc ls /crawls[/]                        List available crawls
      [bold]cc search CC-MAIN-2024-10 "example.com"[/]  Search URLs
      [bold]cc cat /search/.../token[/]             Read a record
      [bold]cc download /search/.../token out.warc[/]   Download a record
    """
    if ctx.invoked_subcommand is None:
        ctx.get_help()


@cli.command(name="interactive")
@click.argument("path", default="/")
def interactive_cmd(path: str):
    """Launch an interactive browser shell."""
    interactive_shell(path)


@cli.command(name="shell")
@click.argument("path", default="/")
def shell_cmd(path: str):
    """Launch an interactive browser shell (alias for interactive)."""
    interactive_shell(path)


@cli.command(name="ls")
@click.argument("path", default="/")
def ls_cmd(path: str):
    """List contents of a directory."""
    fs = get_fs()
    with console.status(f"[cyan]Listing [bold]{path}[/bold]..."):
        try:
            entries = fs.ls(path, detail=True)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            sys.exit(1)

    if not entries:
        console.print(f"[dim](empty: {path})[/dim]")
        return

    render_entries(path, entries, show_numbers=False)


@cli.command()
@click.argument("crawl_id")
@click.argument("pattern")
@click.option("--limit", "-n", default=20, help="Maximum number of results.")
def search(crawl_id: str, pattern: str, limit: int):
    """Search for URLs in a crawl using a CDX URL pattern."""
    fs = get_fs()

    with console.status(
        f"[cyan]Searching [bold]{crawl_id}[/bold] for [green]{pattern}[/green]..."
    ):
        try:
            entries = run_search(fs, crawl_id, pattern, limit)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            sys.exit(1)

    if not entries:
        console.print(
            Panel(
                f"No results found for [green]'{pattern}'[/green] in [bold]{crawl_id}[/bold]",
                title="[yellow]Search Results[/yellow]",
                border_style="yellow",
            )
        )
        return

    results = entries[:limit]

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("URL", style="cyan", no_wrap=True)
    table.add_column("MIME", style="magenta", width=20)
    table.add_column("Status", style="yellow", width=6)
    table.add_column("Size", style="green", justify="right", width=10)
    table.add_column("Timestamp", style="dim", width=14)

    for entry in results:
        url = getattr(entry, "url", "")
        mime = getattr(entry, "mime", "")
        status = getattr(entry, "status", "")
        size = format_size(getattr(entry, "length", 0))
        ts = getattr(entry, "timestamp", "")

        table.add_row(url, mime, status, size, ts)

    title = f"[bold green]Found {len(results)} result(s)[/bold green] for [green]'{pattern}'[/green] in [bold]{crawl_id}[/bold]"
    console.print(Panel(table, title=title, border_style="green"))


@cli.command()
@click.argument("path")
def cat(path: str):
    """Display file contents."""
    fs = get_fs()
    with console.status(f"[cyan]Reading [bold]{path}[/bold]..."):
        try:
            with fs.open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            sys.exit(1)

    try:
        text = data.decode("utf-8")
        console.print(
            Panel(
                text[:4000],
                title=f"[bold]📄 {path}[/bold] ([dim]{format_size(len(data))}[/dim])",
                border_style="blue",
                expand=False,
            )
        )
        if len(data) > 4000:
            console.print(f"[dim]... truncated (showing first 4000 chars)[/dim]")
    except UnicodeDecodeError:
        console.print(
            Panel(
                f"[yellow]Binary content[/yellow] — use [bold]cc download[/bold] to save to disk.\n\nSize: [green]{format_size(len(data))}[/green]",
                title=f"[bold]📄 {path}[/bold]",
                border_style="yellow",
            )
        )


@cli.command()
@click.argument("path")
@click.argument("output", type=click.Path())
def download(path: str, output: str):
    """Download a file to disk."""
    fs = get_fs()
    out = Path(output)

    with console.status(f"[cyan]Downloading [bold]{path}[/bold]..."):
        try:
            with fs.open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            sys.exit(1)

    out.write_bytes(data)
    console.print(
        f"[bold green]✓ Downloaded[/bold green] [cyan]{format_size(len(data))}[/cyan] → [bold]{out}[/bold]"
    )


@cli.command()
@click.argument("path")
def info(path: str):
    """Show file metadata."""
    fs = get_fs()
    with console.status(f"[cyan]Getting info for [bold]{path}[/bold]..."):
        try:
            entry = fs.info(path)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}", soft_wrap=True)
            sys.exit(1)

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Field", style="bold cyan", width=14)
    table.add_column("Value", style="white")

    fields = [
        ("Path", entry.get("name", "")),
        ("Type", entry.get("type", "")),
        ("Size", format_size(entry.get("size", 0))),
        (
            "Modified",
            format_timestamp(entry.get("mtime")) if entry.get("mtime") else "—",
        ),
        ("URL", entry.get("url", "—")),
        ("Timestamp", entry.get("timestamp", "—")),
    ]

    for label, value in fields:
        if value and value != "—":
            table.add_row(label, str(value))

    console.print(Panel(table, title="[bold]📋 File Info[/bold]", border_style="blue"))


if __name__ == "__main__":
    cli()
