import os
import re
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo

# ========================
# CONFIG
# ========================
SESSIONID = os.getenv("IG_SESSIONID", "70808632711%3AJycNCkj1wzuDLO%3A29%3AAYf96VLRjfMtGMxkNhQcuXis8j_vXPDZl0mccRC5xg")  # put your sessionid here or set env var
COOKIE_FILE = "ig_session.txt"

# Create minimal cookie file if it doesn't exist
if not os.path.exists(COOKIE_FILE):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write(f".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\t{SESSIONID}\n")

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
            "cookiefile": COOKIE_FILE,
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
__PLUGIN__ = "Instagram Downloader (SessionID)"
__HELP__ = """
• Send an Instagram reel/post link — I’ll download it using your `sessionid` (no login needed).
• Set `IG_SESSIONID` in your VPS environment.
• Session lasts until Instagram expires it (~1 month or more).
"""
