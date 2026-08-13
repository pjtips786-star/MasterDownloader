import os
import logging
from pyrogram import Client, filters
import yt_dlp

# Configure logging for tracking status and errors
logging.basicConfig(level=logging.INFO)

# Telegram Bot Credentials
API_ID = int(os.environ.get("API_ID", 1234567))  # Fallback ID if environment variable is missing
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
BOT_TOKEN = "8939157171:AAGXvgVFL1R7KmTwn9rTJ2tXy_jAjndKkDM"

# Initialize the Pyrogram Client
app = Client(
    "media_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    welcome_text = (
        "👋 **Welcome to the Media Downloader Bot!**\n\n"
        "Send me any social media video link (YouTube, Instagram, Facebook, etc.), "
        "and I will process and download the video for you."
    )
    await message.reply_text(welcome_text)

@app.on_message(filters.text & ~filters.command(["start"]))
async def download_media(client, message):
    url = message.text.strip()
    
    # Validate if the incoming text is a valid URL
    if not url.startswith("http"):
        await message.reply_text("❌ Please provide a valid HTTP or HTTPS link.")
        return

    status_message = await message.reply_text("⏳ Processing your link, please wait...")

    # Ensure the downloads directory exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    ydl_opts = {
        'format': 'best[filesize<50M]',  # Constrained to Telegram's standard bot upload limits
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
    }

    filename = None
    try:
        await status_message.edit_text("📥 Downloading media...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await status_message.edit_text("📤 Uploading to Telegram...")
        
        # Send the downloaded video file to the user
        await message.reply_video(
            video=filename,
            caption=f"✅ **Downloaded successfully via:** @{client.me.username}"
        )
        
        await status_message.delete()

    except Exception as error:
        logging.error(f"Download/Upload failure: {error}")
        await status_message.edit_text(f"❌ Failed to process the media.\n\n`{str(error)}`")

    finally:
        # Cleanup routine: Remove temporary local files to save storage
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception as cleanup_error:
                logging.error(f"File cleanup error: {cleanup_error}")

# Start the bot application
print("🤖 Bot is starting up...")
app.run()
