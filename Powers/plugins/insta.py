import os
import re
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo

# ========================
# CONFIG
# ========================
# Change this to your browser name: chrome, brave, edge, firefox, chromium
BROWSER_NAME = os.getenv("BROWSER_NAME", "chrome")  

# Regex to match Instagram post/reel URLs
INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+(?:\?[^\s]*)?)"
)

# ========================
# BOT COMMAND
# ========================
@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def insta_downloader(c, m):
    match = INSTAGRAM_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "insta_video.mp4"
    status = await m.reply_text("📥 Downloading from Instagram...")

    try:
        ydl_opts = {
            "cookiesfrombrowser": (BROWSER_NAME,),  # grabs cookies from your local browser
            "outtmpl": temp_file,
            "format": "mp4",
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        caption = (
            f"🎬 **Title:** {info.get('title', 'Unknown')}\n"
            f"👤 **Uploader:** {info.get('uploader', 'Unknown')}\n"
            f"🔗 **Original Link:** {url}\n"
            f"🤖 **Downloaded by:** @{c.me.username}"
        )

        await m.reply_video(video=temp_file, caption=caption)
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# ========================
# PLUGIN INFO
# ========================
__PLUGIN__ = "Instagram Downloader (Browser Cookies)"
__HELP__ = """
• Send an Instagram reel/post link — I’ll download it using your **browser cookies** (no manual sessionid needed).
• Set `BROWSER_NAME` env var to your browser (chrome, brave, edge, firefox, chromium).
• Must run the bot on the same machine where you are logged into Instagram in that browser.
"""
