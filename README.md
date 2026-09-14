# MasterDownloader

A universal media downloader built for Termux (Android). Paste any video link — YouTube, Instagram, Facebook, Twitter/X, and more — and download it in your preferred quality, right from the terminal, with a colorful live progress UI.

![Platform](https://img.shields.io/badge/platform-Termux-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Features

- 🔗 **Universal link support** — works with most platforms via `yt-dlp`
- 🎬 **Quality selection** — Best (auto), 720p, 480p, or Audio only (MP3)
- 📊 **Live progress bar** — real-time percentage, download speed, and ETA
- 🎨 **Colorful terminal UI** — ASCII art banner, styled menus, and panels (built with `rich`)
- 📜 **Session history** — see your last few downloads and their status at a glance
- 📂 **Auto-organized downloads** — saved directly to your phone's Downloads folder
- 🍪 **Cookie support** — optional `cookies.txt` for sites that require login
- ⚡ **One-word shortcut** — launch with a single alias instead of a full command

---

## Preview

```
 __  __           _            ____
|  \/  | __ _ ___| |_ ___ _ __ |  _ \  _____      ___ __
| |\/| |/ _` / __| __/ _ \ '__|| | | |/ _ \ \ /\ / / '_ \
| |  | | (_| \__ \ ||  __/ |   | |_| | (_) \ V  V /| | | |
|_|  |_|\__,_|___/\__\___|_|   |____/ \___/ \_/\_/ |_| |_|

Universal media downloader — Termux edition
────────────────────────────────────────────
📂 Save folder: ~/storage/downloads/MasterDownloader
```

---

## Installation

### 1. Update Termux packages
```bash
pkg update && pkg upgrade -y
```

### 2. Install required system tools
```bash
pkg install python ffmpeg git -y
```

### 3. Grant storage access (one-time)
```bash
termux-setup-storage
```
A permission popup will appear — tap **Allow**. This links `~/storage/downloads` to your phone's real Downloads folder.

### 4. Clone the repository
```bash
git clone https://github.com/pjtips786-star/MasterDownloader.git
cd MasterDownloader
```

### 5. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 6. Run the downloader
```bash
python downloader_ui.py
```

---

## Optional: One-word shortcut

Instead of typing the full command every time, create an alias:

```bash
echo "alias download='python ~/MasterDownloader/bot.py'" >> ~/.bashrc
source ~/.bashrc
```

From then on, just type:
```bash
download
```

---

## Usage

1. Run the script (`python downloader_ui.py` or `download`)
2. Paste any video link when prompted
3. Choose a quality:
   - `1` — Best (auto)
   - `2` — 720p
   - `3` — 480p
   - `4` — Audio only (MP3)
4. Watch the live progress bar as it downloads
5. Find your file in:
   ```
   ~/storage/downloads/MasterDownloader
   ```

---

## Optional: cookies for login-required content

Some platforms (e.g. private Instagram posts) require login to download. If needed, export your browser cookies to a `cookies.txt` file (Netscape format) and place it in the project folder — it will be picked up automatically.

---

## Requirements

- Termux (Android) or any Linux system with Python 3.10+
- FFmpeg (for audio extraction)
- Python packages: `yt-dlp`, `rich` (see `requirements.txt`)

---

## Disclaimer

This tool is intended for personal use only — downloading content you have the right to download (your own uploads, public domain media, or content where the platform/creator permits downloading). Respect the terms of service of the platform you're downloading from and applicable copyright law.

---

## License

MIT License — feel free to modify and use for personal projects.
