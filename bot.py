import os
import re
import json
import time
import subprocess
import urllib.request
import urllib.parse
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

# ---------------- OPTIONS ----------------
VIDEO_QUALITY_OPTIONS = {
    "1": ("🎬 Best (auto)", "bv*+ba/best", None, "bright_green"),
    "2": ("📺 720p", "bv*[height<=720]+ba/best[height<=720]", None, "bright_cyan"),
    "3": ("📱 480p", "bv*[height<=480]+ba/best[height<=480]", None, "bright_yellow"),
    "4": ("🎵 Audio only (MP3)", "ba/best", "mp3", "bright_magenta"),
}

PHOTO_QUALITY_OPTIONS = {
    "1": ("🖼️ Original / Best", "best", None, "bright_green"),
    "2": ("📷 Compressed / smaller", "compressed", None, "bright_cyan"),
}

AUDIO_QUALITY_OPTIONS = {
    "1": ("🎵 Best Audio (MP3)", "ba/best", "mp3", "bright_magenta"),
    "2": ("🎵 Audio (M4A)", "ba/best", "m4a", "bright_cyan"),
}

BANNER = r"""
[bold bright_cyan] __  __           _            [/][bold bright_magenta]____                      [/]
[bold bright_cyan]|  \/  | __ _ ___| |_ ___ _ __ [/][bold bright_magenta]|  _ \  _____      ___ __  [/]
[bold bright_cyan]| |\/| |/ _` / __| __/ _ \ '__|[/][bold bright_magenta]| | | |/ _ \ \ /\ / / '_ \ [/]
[bold bright_cyan]| |  | | (_| \__ \ ||  __/ |   [/][bold bright_magenta]| |_| | (_) \ V  V /| | | |[/]
[bold bright_cyan]|_|  |_|\__,_|___/\__\___|_|   [/][bold bright_magenta]|____/ \___/ \_/\_/ |_| |_|[/]
"""

session_history = []
UA = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"


def show_banner():
    console.clear()
    console.print(Align.center(Text.from_markup(BANNER)))
    console.print(Align.center("[dim italic]Universal media downloader — Termux edition[/dim italic]"))
    console.print(Rule(style="bright_cyan"))
    console.print(f"[bold]📂 Save folder:[/bold] [green]{DOWNLOAD_DIR}[/green]\n")


def show_quality_menu(options, title="🎚️ Select Quality"):
    table = Table(title=title, box=box.HEAVY_HEAD, show_header=True,
                  header_style="bold white on dark_magenta", expand=True,
                  title_style="bold cyan")
    table.add_column("#", justify="center", width=3, style="bold white")
    table.add_column("Option")
    for key, (label, _, _, color) in options.items():
        table.add_row(key, f"[{color}]{label}[/{color}]")
    console.print(table)


def show_history():
    if not session_history:
        return
    table = Table(title="📜 Session History", box=box.SIMPLE, title_style="bold cyan")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Quality")
    table.add_column("Link", overflow="fold")
    for status, mtype, quality, link in session_history[-5:]:
        icon = "[green]✅[/green]" if status == "ok" else "[red]❌[/red]"
        table.add_row(icon, mtype, quality, link[:50])
    console.print(table)
    console.print()


# ============================================================
# INSTAGRAM HELPERS
# ============================================================
def is_instagram(url: str) -> bool:
    return "instagram.com" in url


def extract_shortcode(url: str) -> str | None:
    m = re.search(r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def http_get(url: str, extra_headers: dict | None = None) -> str:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    if extra_headers:
        for k, v in extra_headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="ignore")


def instagram_oembed(shortcode: str) -> dict | None:
    """Instagram oEmbed — public posts ke liye kaam karta hai."""
    try:
        api = f"https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/p/{shortcode}/"
        data = http_get(api)
        return json.loads(data)
    except Exception:
        return None


def instagram_html_scrape(url: str) -> dict | None:
    """
    Instagram HTML page se meta tags aur JSON nikalta hai.
    Image URL, caption, aur carousel detect kar sakta hai.
    """
    try:
        html = http_get(url)
    except Exception:
        return None

    info = {"images": [], "title": None, "is_carousel": False}

    # Meta og:image (single image / first image of carousel)
    og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if og_img:
        info["images"].append(og_img.group(1).replace("&amp;", "&"))

    # og:title
    og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    if og_title:
        info["title"] = og_title.group(1)

    # Try to extract full image list from embedded JSON
    # Instagram embeds data in <script type="application/json"> or in window._sharedData
    json_matches = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        html, re.DOTALL
    )
    for jm in json_matches:
        try:
            jdata = json.loads(jm)
            if isinstance(jdata, dict):
                imgs = jdata.get("image")
                if imgs:
                    if isinstance(imgs, str):
                        info["images"].append(imgs)
                    elif isinstance(imgs, list):
                        info["images"].extend(imgs)
        except Exception:
            pass

    # Carousel detection: og:image count + sidecar hint
    if 'edge_sidecar_to_children' in html or 'carousel_media' in html:
        info["is_carousel"] = True

    # Try to dig edge_sidecar_to_children for all images
    sidecar = re.search(
        r'"edge_sidecar_to_children":\{"edges":\[(.*?)\]\}', html, re.DOTALL
    )
    if sidecar:
        try:
            # Try to find all display_url in the sidecar block
            block = sidecar.group(1)
            urls = re.findall(r'"display_url":"([^"]+)"', block)
            if urls:
                # dedupe
                seen = set()
                clean = []
                for u in urls:
                    u2 = u.encode().decode("unicode_escape")
                    if u2 not in seen:
                        seen.add(u2)
                        clean.append(u2)
                info["images"] = clean
                info["is_carousel"] = len(clean) > 1
        except Exception:
            pass

    # Deduplicate
    seen = set()
    unique = []
    for u in info["images"]:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    info["images"] = unique

    return info if info["images"] else None


def instagram_gallery_dl(url: str) -> bool:
    """Fallback: gallery-dl se download (agar installed hai)."""
    try:
        result = subprocess.run(
            ["gallery-dl", "-d", DOWNLOAD_DIR, url],
            capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def download_image(img_url: str, filename: str) -> bool:
    """Direct image download with proper headers."""
    try:
        req = urllib.request.Request(img_url)
        req.add_header("User-Agent", UA)
        req.add_header("Referer", "https://www.instagram.com/")
        with urllib.request.urlopen(req, timeout=30) as r, open(filename, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        console.print(f"[red]Image download fail: {e}[/red]")
        return False


# ============================================================
# MEDIA DETECTION
# ============================================================
def detect_media_info(url: str):
    """Detect media type. Instagram ke liye special handling."""
    # -------- Instagram special path --------
    if is_instagram(url):
        shortcode = extract_shortcode(url)
        if not shortcode:
            return {"type": "unknown", "error": "Instagram shortcode nahi mila", "raw": None}

        # 1) Try yt-dlp (works for reels/videos)
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info:
                formats = info.get("formats") or []
                has_video = any(f.get("vcodec") and f.get("vcodec") != "none" for f in formats)
                has_audio = any(f.get("acodec") and f.get("acodec") != "none" for f in formats)
                if has_video and has_audio:
                    return {
                        "type": "video",
                        "title": info.get("title", "Instagram video"),
                        "uploader": info.get("uploader", ""),
                        "duration": info.get("duration"),
                        "has_video": True, "has_audio": True,
                        "ext": info.get("ext", "mp4"),
                        "raw": info,
                    }
        except Exception:
            pass  # video nahi hai → image path try karo

        # 2) Try HTML scrape for images
        scraped = instagram_html_scrape(url)
        if scraped and scraped["images"]:
            return {
                "type": "photo",
                "title": scraped.get("title") or f"Instagram post {shortcode}",
                "uploader": "",
                "images": scraped["images"],
                "is_carousel": scraped.get("is_carousel", False),
                "raw": scraped,
            }

        # 3) Try oEmbed
        oembed = instagram_oembed(shortcode)
        if oembed and oembed.get("thumbnail_url"):
            return {
                "type": "photo",
                "title": oembed.get("title") or f"Instagram post {shortcode}",
                "uploader": oembed.get("author_name", ""),
                "images": [oembed["thumbnail_url"]],
                "is_carousel": False,
                "raw": oembed,
            }

        return {
            "type": "unknown",
            "error": "Instagram post ka koi media nahi mila (login/cookies zaroori ho sakta hai)",
            "raw": None,
        }

    # -------- Non-Instagram (yt-dlp generic) --------
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": False}
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"type": "unknown", "error": str(e), "raw": None}

    if info is None:
        return {"type": "unknown", "error": "No info returned", "raw": None}

    if info.get("_type") == "playlist" or info.get("entries"):
        entries = info.get("entries") or []
        return {
            "type": "playlist",
            "title": info.get("title", "Unknown playlist"),
            "uploader": info.get("uploader", ""),
            "entries": len(entries),
            "raw": info,
        }

    formats = info.get("formats") or []
    has_video = any(f.get("vcodec") and f.get("vcodec") != "none" for f in formats)
    has_audio = any(f.get("acodec") and f.get("acodec") != "none" for f in formats)
    ext = (info.get("ext") or "").lower()
    vcodec = info.get("vcodec") or "none"
    acodec = info.get("acodec") or "none"

    is_image_ext = ext in ("jpg", "jpeg", "png", "webp", "heic", "gif")
    if is_image_ext or (vcodec == "none" and acodec == "none"):
        mtype = "photo"
    elif has_video and has_audio:
        mtype = "video"
    elif has_video and not has_audio:
        mtype = "video"
    elif has_audio and not has_video:
        mtype = "audio"
    else:
        mtype = "unknown"

    return {
        "type": mtype,
        "title": info.get("title", "Unknown title"),
        "uploader": info.get("uploader", ""),
        "duration": info.get("duration"),
        "entries": 1,
        "ext": ext,
        "formats_count": len(formats),
        "has_video": has_video,
        "has_audio": has_audio,
        "raw": info,
    }


def format_duration(seconds):
    if not seconds:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


def show_detection_panel(info: dict):
    mtype = info.get("type", "unknown")
    type_badge = {
        "video": "[bold green]🎬 VIDEO[/bold green]",
        "photo": "[bold yellow]🖼️ PHOTO / IMAGE[/bold yellow]",
        "audio": "[bold magenta]🎵 AUDIO[/bold magenta]",
        "playlist": "[bold cyan]📚 PLAYLIST[/bold cyan]",
        "unknown": "[bold red]❓ UNKNOWN[/bold red]",
    }.get(mtype, "[bold red]❓ UNKNOWN[/bold red]")

    lines = [f"[bold white]Title:[/bold white] {info.get('title', 'Unknown')}"]
    if info.get("uploader"):
        lines.append(f"[bold white]Uploader:[/bold white] {info['uploader']}")
    lines.append(f"[bold white]Detected type:[/bold white] {type_badge}")

    if mtype == "video":
        lines.append(f"[bold white]Duration:[/bold white] {format_duration(info.get('duration'))}")
    elif mtype == "playlist":
        lines.append(f"[bold white]Entries:[/bold white] {info.get('entries')}")
    elif mtype == "photo":
        imgs = info.get("images") or []
        lines.append(f"[bold white]Images:[/bold white] {len(imgs)}")
        if info.get("is_carousel"):
            lines.append("[bold yellow]📚 Carousel post (multi-image)[/bold yellow]")

    console.print(Panel("\n".join(lines), title="🔎 Media Detection",
                        border_style="bright_blue", box=box.ROUNDED))


# ============================================================
# DOWNLOAD
# ============================================================
def build_opts(choice: str, options_map: dict, progress: Progress, task_id):
    label, fmt, audio_codec, _ = options_map.get(choice, list(options_map.values())[0])
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


def download_ytdlp(url: str, choice: str, options_map: dict, media_type: str):
    label = options_map.get(choice, list(options_map.values())[0])[0]
    progress = Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="bright_green", finished_style="bright_green"),
        DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
        console=console,
    )
    with progress:
        task_id = progress.add_task(label, total=None)
        opts = build_opts(choice, options_map, progress, task_id)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            console.print(Panel("[bold bright_green]✅ Download complete![/bold bright_green]",
                                border_style="green", box=box.ROUNDED))
            session_history.append(("ok", media_type, label, url))
            return True
        except Exception as e:
            console.print(Panel(f"[bold red]❌ Failed:[/bold red] {e}",
                                border_style="red", box=box.ROUNDED))
            session_history.append(("fail", media_type, label, url))
            return False


def download_instagram_photos(info: dict, url: str, choice: str):
    """Instagram images ko manually download karta hai."""
    images = info.get("images") or []
    title = re.sub(r"[^\w\s\-]", "", info.get("title", "instagram_post"))[:60].strip() or "instagram_post"

    if not images:
        console.print("[red]❌ Koi image URL nahi mila.[/red]")
        session_history.append(("fail", "photo", "image", url))
        return

    # gallery-dl fallback (agar available hai) → best for carousel
    if info.get("is_carousel") and len(images) > 1:
        console.print("[cyan]📚 Carousel detected — gallery-dl try kar raha hoon...[/cyan]")
        if instagram_gallery_dl(url):
            console.print(Panel("[bold bright_green]✅ Carousel downloaded via gallery-dl![/bold bright_green]",
                                border_style="green", box=box.ROUNDED))
            session_history.append(("ok", "photo", f"carousel ({len(images)})", url))
            return

    console.print(f"[cyan]⬇️  {len(images)} image(s) download kar raha hoon...[/cyan]")
    success = 0
    for i, img_url in enumerate(images, 1):
        # Determine extension
        path = urllib.parse.urlparse(img_url).path
        ext = os.path.splitext(path)[1] or ".jpg"
        if len(images) > 1:
            filename = os.path.join(DOWNLOAD_DIR, f"{title}_{i}{ext}")
        else:
            filename = os.path.join(DOWNLOAD_DIR, f"{title}{ext}")

        with console.status(f"[cyan]Image {i}/{len(images)}...[/cyan]"):
            if download_image(img_url, filename):
                success += 1
                console.print(f"  [green]✅[/green] {os.path.basename(filename)}")
            else:
                console.print(f"  [red]❌[/red] Failed: {img_url[:60]}...")

    if success:
        console.print(Panel(f"[bold bright_green]✅ {success}/{len(images)} image(s) downloaded![/bold bright_green]",
                            border_style="green", box=box.ROUNDED))
        session_history.append(("ok", "photo", f"{success}/{len(images)} imgs", url))
    else:
        console.print(Panel("[bold red]❌ Koi image download nahi hui.[/bold red]",
                            border_style="red", box=box.ROUNDED))
        session_history.append(("fail", "photo", "0 imgs", url))
    console.print()


# ============================================================
# MAIN
# ============================================================
def main():
    show_banner()

    while True:
        show_history()
        url = Prompt.ask("[bold bright_white]🔗 Video/Photo link[/bold bright_white] [dim](ya 'exit')[/dim]").strip()

        if url.lower() in ("exit", "quit"):
            console.print(Align.center("[bold cyan]Bye! 👋[/bold cyan]"))
            break

        if not url.startswith("http"):
            console.print("[bold red]❌ Valid link nahi lag raha.[/bold red]\n")
            continue

        with console.status("[bold cyan]🔍 Detecting media type...[/bold cyan]", spinner="dots"):
            info = detect_media_info(url)

        if info["type"] == "unknown":
            console.print(Panel(
                f"[bold red]❌ Media detect nahi ho paya.[/bold red]\n[dim]{info.get('error', '')}[/dim]",
                border_style="red", box=box.ROUNDED))
            session_history.append(("fail", "unknown", "—", url))
            console.print()
            continue

        show_detection_panel(info)
        mtype = info["type"]

        if mtype == "video":
            show_quality_menu(VIDEO_QUALITY_OPTIONS, title="🎚️ Video Quality Options")
            choice = Prompt.ask("[bold]Quality number[/bold]",
                                choices=list(VIDEO_QUALITY_OPTIONS.keys()), default="1")
            download_ytdlp(url, choice, VIDEO_QUALITY_OPTIONS, "video")

        elif mtype == "photo":
            if is_instagram(url):
                show_quality_menu(PHOTO_QUALITY_OPTIONS, title="🖼️ Instagram Image Options")
                choice = Prompt.ask("[bold]Option number[/bold]",
                                    choices=list(PHOTO_QUALITY_OPTIONS.keys()), default="1")
                download_instagram_photos(info, url, choice)
            else:
                show_quality_menu(PHOTO_QUALITY_OPTIONS, title="🖼️ Image Options")
                choice = Prompt.ask("[bold]Option number[/bold]",
                                    choices=list(PHOTO_QUALITY_OPTIONS.keys()), default="1")
                download_ytdlp(url, choice, PHOTO_QUALITY_OPTIONS, "photo")

        elif mtype == "audio":
            show_quality_menu(AUDIO_QUALITY_OPTIONS, title="🎵 Audio Options")
            choice = Prompt.ask("[bold]Option number[/bold]",
                                choices=list(AUDIO_QUALITY_OPTIONS.keys()), default="1")
            download_ytdlp(url, choice, AUDIO_QUALITY_OPTIONS, "audio")

        elif mtype == "playlist":
            console.print(f"[bold cyan]📚 Playlist detected ({info.get('entries')} entries).[/bold cyan]\n")
            show_quality_menu(VIDEO_QUALITY_OPTIONS, title="🎚️ Playlist Item Quality")
            choice = Prompt.ask("[bold]Quality number[/bold]",
                                choices=list(VIDEO_QUALITY_OPTIONS.keys()), default="1")
            download_ytdlp(url, choice, VIDEO_QUALITY_OPTIONS, "playlist")


if __name__ == "__main__":
    main()
