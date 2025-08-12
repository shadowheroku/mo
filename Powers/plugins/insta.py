import os
import re
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo

# Regex to match Instagram URLs (reels, posts, videos)
INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+)"
)

@Gojo.on_message(filters.regex(INSTAGRAM_REGEX) & filters.private)
async def insta_reel_downloader(c, m):
    url = INSTAGRAM_REGEX.search(m.text).group(1)
    temp_file = "insta_reel.mp4"

    try:
        await m.reply_text("📥 Downloading Instagram reel...")

        ydl_opts = {
            "outtmpl": temp_file,
            "format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        caption = (
            f"🎬 **Reel Title:** {info.get('title', 'Unknown')}\n"
            f"👤 **Uploader:** {info.get('uploader', 'Unknown')}\n"
            f"📅 **Upload Date:** {info.get('upload_date', 'Unknown')}\n"
            f"🔗 **Original Link:** {url}\n\n"
            f"🤖 **Downloaded by:** @{c.me.username}"
        )

        await m.reply_video(video=temp_file, caption=caption)

    except Exception as e:
        await m.reply_text(f"❌ Failed to download reel:\n`{e}`")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Plugin metadata
plugin_name = "Instagram Reel Downloader"
help = """
Send any Instagram reel/post link in chat, and I will download it and send it to you.

**Usage:**
Just paste an Instagram link, e.g.:
`https://www.instagram.com/reel/xyz/`
"""
