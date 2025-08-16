import os
import re
import yt_dlp
import asyncio
import requests
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
SESSION_ID = "70808632711%3AaVps8t4cBpXZlG%3A21%3AAYe2L2nE2r6Sjc3mcrKRebDdj_2uGSXRb2KQICTN3Q"   # Replace with your Instagram sessionid
COOKIES_FILE = "instagram_session.txt"

# Write minimal Netscape cookie file
COOKIES_TEXT = f"""# Netscape HTTP Cookie File
.instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t{SESSION_ID}
"""
with open(COOKIES_FILE, "w", encoding="utf-8") as f:
    f.write(COOKIES_TEXT.strip() + "\n")

# Regex for Instagram URLs
INSTAGRAM_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?instagram\.com\/(?:reel|p|tv)\/[A-Za-z0-9_\-]+)"
)

@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def instagram_downloader(c, m):
    match = INSTAGRAM_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "instagram_dl.%(ext)s"
    status = await m.reply_text("📥 Downloading Instagram content...")

    try:
        ydl_opts = {
            "outtmpl": temp_file,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": COOKIES_FILE,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.instagram.com/",
            },
            "format": "(bestvideo+bestaudio/best)[ext=mp4]",
            "merge_output_format": "mp4",
            "retries": 3,
            "ignoreerrors": False,
            "extractor_args": {
                "instagram": {"reels": True},
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("No downloadable content found")

            file_path = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4").lower()

        caption = f"📸 **Source:** [Instagram Post]({url})\n🤖 **Via:** @{c.me.username}"

        if ext in ["mp4", "webm", "mov"]:
            await m.reply_video(video=file_path, caption=caption)
        elif ext in ["jpg", "jpeg", "png", "webp"]:
            await m.reply_photo(photo=file_path, caption=caption)
        else:
            await m.reply_document(document=file_path, caption=caption)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"⚠️ Failed: {str(e)}")
    finally:
        for f in os.listdir():
            if f.startswith("instagram_dl."):
                try:
                    os.remove(f)
                except:
                    pass

# Metadata
__PLUGIN__ = "Instagram Downloader"
__HELP__ = """
📸 Download posts/reels/videos from Instagram:

• Send any Instagram post/reel/tv link
• Uses only `sessionid` for login
• Works with private posts (if your account has access)

⚠️ Both videos and images are supported.
"""
