import os
import re
import json
import yt_dlp
import asyncio
from instagrapi import Client
from pyrogram import filters
from Powers.bot_class import Gojo

# ========================
# CONFIG
# ========================
IG_USERNAME = os.getenv("IG_USERNAME", "nxtego")
IG_PASSWORD = os.getenv("IG_PASSWORD", "xd_ego")

SESSION_FILE = "insta_session.json"
COOKIES_FILE = "instagram_cookies.txt"

# Regex to match Instagram post/reel URLs
INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+(?:\?[^\s]*)?)"
)

# ========================
# LOGIN & COOKIE HANDLING
# ========================
def ensure_instagram_session():
    """Login or load session, then export cookies to yt-dlp format."""
    cl = Client()

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.login(IG_USERNAME, IG_PASSWORD)
        except Exception:
            # If session is broken, re-login fresh
            cl.login(IG_USERNAME, IG_PASSWORD)
            cl.dump_settings(SESSION_FILE)
    else:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(SESSION_FILE)

    # Export cookies for yt-dlp
    cookies = cl.get_cookie_dict()
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for name, value in cookies.items():
            f.write(f".instagram.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}\n")

    return COOKIES_FILE


# ========================
# BOT COMMAND
# ========================
@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def insta_downloader(c, m):
    match = INSTAGRAM_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "insta_reel.mp4"

    status = await m.reply_text("📥 Logging into Instagram & downloading...")

    try:
        cookie_path = ensure_instagram_session()

        ydl_opts = {
            "outtmpl": temp_file,
            "format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiefile": cookie_path,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        caption = (
            f"🎬 **Title:** {info.get('title', 'Unknown')}\n"
            f"👤 **Uploader:** {info.get('uploader', 'Unknown')}\n"
            f"📅 **Upload Date:** {info.get('upload_date', 'Unknown')}\n"
            f"🔗 **Original Link:** {url}\n\n"
            f"🤖 **Downloaded by:** @{c.me.username}"
        )

        sent_msg = await m.reply_video(video=temp_file, caption=caption)
        await status.delete()

        # Auto-delete after 30 sec
        await asyncio.sleep(30)
        await sent_msg.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# ========================
# PLUGIN INFO
# ========================
__PLUGIN__ = "Instagram Downloader (Auto-Login)"
__HELP__ = """
• Send an Instagram reel/post link — I’ll download it with auto-login cookies.
• You only need to set `IG_USERNAME` and `IG_PASSWORD` in your VPS env once.
• Cookies refresh automatically — no need to paste them manually.
"""
