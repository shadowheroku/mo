import os
import re
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
# No cookies required for public videos
YOUTUBE_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?youtube\.com\/watch\?v=[\w\-]+|https?:\/\/youtu\.be\/[\w\-]+)"
)

@Gojo.on_message(filters.regex(YOUTUBE_REGEX))
async def youtube_downloader(c, m):
    match = YOUTUBE_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "youtube_dl.%(ext)s"
    status = await m.reply_text("📥 Downloading YouTube video...")

    try:
        ydl_opts = {
            "outtmpl": temp_file,
            "quiet": True,
            "no_warnings": True,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "retries": 3,
            "ignoreerrors": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.youtube.com/",
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("No downloadable content found")

            file_path = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4").lower()

        caption = f"▶️ **Source:** [YouTube]({url})\n🤖 **Via:** @{c.me.username}"

        if ext in ["mp4", "webm", "mov"]:
            await m.reply_video(video=file_path, caption=caption)
        else:
            await m.reply_document(document=file_path, caption=caption)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"⚠️ Failed: {str(e)}")
    finally:
        for f in os.listdir():
            if f.startswith("youtube_dl."):
                try:
                    os.remove(f)
                except:
                    pass

# Metadata
__PLUGIN__ = "YouTube Downloader (Cookies-less)"
__HELP__ = """
▶️ Download YouTube videos without cookies:

• Send any YouTube link
• Downloads in best video+audio quality
• Works for public videos
"""
