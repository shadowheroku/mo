import os
import re
import requests
import asyncio
from pyrogram import filters
from Powers.bot_class import Gojo

# ========================
# CONFIG
# ========================
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "db695f9a31msh317d0f72b049ab7p1c6935jsn65e8560b2087")
RAPIDAPI_HOST = "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"  # Example, replace with your API host from RapidAPI

INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+(?:\?[^\s]*)?)"
)

# ========================
# API FUNCTION
# ========================
def get_instagram_download(url: str):
    """Fetch download link from RapidAPI Instagram downloader."""
    endpoint = f"https://{RAPIDAPI_HOST}/get"  # Adjust path based on your API docs
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
    status = await m.reply_text("📥 Fetching download link from API...")

    try:
        data = get_instagram_download(url)

        # Depending on API, adjust JSON parsing here
        video_url = data.get("media", [])[0].get("url") if "media" in data else data.get("url")

        if not video_url:
            await status.edit_text("❌ Could not find a downloadable video.")
            return

        sent_msg = await m.reply_video(video_url, caption=f"🔗 [Original Post]({url})", quote=True)
        await status.delete()

        # Auto-delete after 30 seconds
        await asyncio.sleep(30)
        await sent_msg.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")

# ========================
# PLUGIN INFO
# ========================
__PLUGIN__ = "Instagram Downloader (RapidAPI)"
__HELP__ = """
• Send an Instagram reel/post link — I’ll download it via RapidAPI (no login needed).
• Set `RAPIDAPI_KEY` and `RAPIDAPI_HOST` in your VPS environment.
• No cookies, no session expiry.
"""
