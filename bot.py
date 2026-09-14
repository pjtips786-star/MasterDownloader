import os
import time
import yt_dlp
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn,
    DownloadColumn, TransferSpeedColumn, SpinnerColumn
)
from rich.prompt import Prompt
from rich.align import Align
from rich.rule import Rule
from rich import box
from rich.text import Text

console = Console()

DOWNLOAD_DIR = os.path.expanduser("~/storage/downloads/MasterDownloader")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

QUALITY_OPTIONS = {
    "1": ("🎬 Best (auto)", "bv*+ba/best", None, "bright_green"),
    "2": ("📺 720p", "bv*[height<=720]+ba/best[height<=720]", None, "bright_cyan"),
    "3": ("📱 480p", "bv*[height<=480]+ba/best[height<=480]", None, "bright_yellow"),
    "4": ("🎵 Audio only (MP3)", "ba/best", "mp3", "bright_magenta"),
}

BANNER = r"""
[bold bright_cyan] __  __           _            [/][bold bright_magenta]____                      [/]
[bold bright_cyan]|  \/  | __ _ ___| |_ ___ _ __ [/][bold bright_magenta]|  _ \  _____      ___ __  [/]
[bold bright_cyan]| |\/| |/ _` / __| __/ _ \ '__|[/][bold bright_magenta]| | | |/ _ \ \ /\ / / '_ \ [/]
[bold bright_cyan]| |  | | (_| \__ \ ||  __/ |   [/][bold bright_magenta]| |_| | (_) \ V  V /| | | |[/]
[bold bright_cyan]|_|  |_|\__,_|___/\__\___|_|   [/][bold bright_magenta]|____/ \___/ \_/\_/ |_| |_|[/]
"""

session_history = []


def show_banner():
    console.clear()
    console.print(Align.center(Text.from_markup(BANNER)))
    console.print(Align.center(
        "[dim italic]Universal media downloader — Termux edition[/dim italic]"
    ))
    console.print(Rule(style="bright_cyan"))
    console.print(f"[bold]📂 Save folder:[/bold] [green]{DOWNLOAD_DIR}[/green]")
    console.print()


def show_quality_menu():
    table = Table(box=box.HEAVY_HEAD, show_header=True, header_style="bold white on dark_magenta", expand=True)
    table.add_column("#", justify="center", width=3, style="bold white")
    table.add_column("Quality")
    for key, (label, _, _, color) in QUALITY_OPTIONS.items():
        table.add_row(key, f"[{color}]{label}[/{color}]")
    console.print(table)


def show_history():
    if not session_history:
        return
    table = Table(title="📜 Session History", box=box.SIMPLE, title_style="bold cyan")
    table.add_column("Status")
    table.add_column("Quality")
    table.add_column("Link", overflow="fold")
    for status, quality, link in session_history[-5:]:
        icon = "[green]✅[/green]" if status == "ok" else "[red]❌[/red]"
        table.add_row(icon, quality, link[:60])
    console.print(table)
    console.print()


def build_opts(choice: str, progress: Progress, task_id):
    label, fmt, audio_codec, _ = QUALITY_OPTIONS.get(choice, QUALITY_OPTIONS["1"])
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(title).80s.%(ext)s")

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                progress.update(task_id, total=total, completed=downloaded)
        elif d["status"] == "finished":
            t = progress.tasks[task_id].total or 100
            progress.update(task_id, completed=t)

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "format": fmt,
    }

    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"

    if audio_codec:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_codec,
            "preferredquality": "192",
        }]

    return opts


def fetch_title(url: str):
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", "Unknown title")
    except Exception:
        return None


def download_one(url: str, choice: str):
    label = QUALITY_OPTIONS.get(choice, QUALITY_OPTIONS["1"])[0]

    with console.status("[bold cyan]🔍 Fetching video info...[/bold cyan]", spinner="dots"):
        title = fetch_title(url)

    if title:
        console.print(Panel(f"[bold white]{title}[/bold white]", title="🎯 Target", border_style="bright_blue", box=box.ROUNDED))

    progress = Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="bright_green", finished_style="bright_green"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task(label, total=None)
        opts = build_opts(choice, progress, task_id)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            console.print(Panel(
                "[bold bright_green]✅ Download complete![/bold bright_green]",
                border_style="green", box=box.ROUNDED
            ))
            session_history.append(("ok", label, url))
        except Exception as e:
            console.print(Panel(
                f"[bold red]❌ Failed:[/bold red] {e}",
                border_style="red", box=box.ROUNDED
            ))
            session_history.append(("fail", label, url))
    console.print()


def main():
    show_banner()

    while True:
        show_history()
        url = Prompt.ask("[bold bright_white]🔗 Video link[/bold bright_white] [dim](ya 'exit')[/dim]").strip()
        if url.lower() in ("exit", "quit"):
            console.print(Align.center("[bold cyan]Bye! 👋[/bold cyan]"))
            break
        if not url.startswith("http"):
            console.print("[bold red]❌ Valid link nahi lag raha.[/bold red]\n")
            continue

        show_quality_menu()
        choice = Prompt.ask("[bold]Quality number[/bold]", choices=["1", "2", "3", "4"], default="1")

        download_one(url, choice)


if __name__ == "__main__":
    main()
