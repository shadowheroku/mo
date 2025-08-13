import os
import re
import time
import asyncio
import wget
from urllib.parse import urlparse
from yt_dlp import YoutubeDL
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# YouTube link pattern
YT_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+"

@Gojo.on_message(filters.regex(YT_REGEX) )
async def yt_auto_download(c: Gojo, m: Message):
    url = re.search(YT_REGEX, m.text).group(0)
    user_mention = m.from_user.mention

    status = await m.reply_text("🔍 **Fetching YouTube video...**")

    try:
        # Fetch thumbnail first
        video_id = None
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        elif "youtube.com" in url and "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        thumb_path = None
        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            thumb_path = wget.download(thumb_url)

        # Download options
        opts = {
            "format": "best",
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            "outtmpl": "%(id)s.mp4",
            "quiet": True,
        }

        with YoutubeDL(opts) as ytdl:
            info = ytdl.extract_info(url, download=True)

        file_path = f"{info['id']}.mp4"
        caption = (
            f"🎬 **Title:** [{info['title']}]({url})\n"
            f"📺 **Channel:** {info.get('uploader', 'Unknown')}\n"
            f"🙋 **Requested by:** {user_mention}"
        )

        c_time = time.time()
        await c.send_video(
            m.chat.id,
            video=open(file_path, "rb"),
            duration=int(info["duration"]),
            file_name=str(info["title"]),
            thumb=thumb_path if thumb_path else None,
            caption=caption,
            supports_streaming=True
        )

    except Exception as e:
        await status.edit(f"❌ **Failed to download video:** `{e}`")
        return

    await status.delete()

    # Cleanup
    for file in [file_path, thumb_path]:
        if file and os.path.exists(file):
            os.remove(file)

__PLUGIN__ = "youtube"
__HELP__ = """
**🎥 Auto YouTube Video Downloader**
• Just send any YouTube link in chat — it will be downloaded and sent automatically.
"""
