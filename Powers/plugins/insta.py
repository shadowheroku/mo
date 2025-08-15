import os
import re
import requests
from pyrogram import filters
from Powers.bot_class import Gojo

# ========================
# CONFIG
# ========================
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "db695f9a31msh317d0f72b049ab7p1c6935jsn65e8560b2087")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com")

# Regex to match Instagram post/reel URLs
INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+(?:\?[^\s]*)?)"
)


# ========================
# API REQUEST
# ========================
def get_instagram_download(url: str):
    endpoint = f"https://{RAPIDAPI_HOST}/hls"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {"url": url}
    r = requests.get(endpoint, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


# ========================
# BOT COMMAND
# ========================
@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def insta_downloader(c, m):
    match = INSTAGRAM_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    status = await m.reply_text("📥 Fetching Instagram video...")

    try:
        data = get_instagram_download(url)

        # API should return a direct video URL under a known key (check docs)
        video_url = data.get("url") or data.get("video") or None
        if not video_url:
            raise ValueError("No video URL found in API response.")

        caption = (
            f"🎬 **Instagram Download**\n"
            f"🔗 **Original:** {url}\n"
            f"🤖 **Downloaded by:** @{c.me.username}"
        )

        await m.reply_video(video=video_url, caption=caption)
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")


# ========================
# PLUGIN INFO
# ========================
__PLUGIN__ = "Instagram Downloader (RapidAPI)"
__HELP__ = """
• Send an Instagram reel/post link — I’ll download it using RapidAPI (no login needed).
• Set `RAPIDAPI_KEY` and `RAPIDAPI_HOST` in your VPS environment.
"""
