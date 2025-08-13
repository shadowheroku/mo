import os
import re
import time
import wget
from yt_dlp import YoutubeDL
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Path to your exported cookies file
COOKIES_FILE = "cookies.txt"  # Make sure this exists

# YouTube link pattern
YT_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+"

@Gojo.on_message(filters.regex(YT_REGEX))
async def yt_auto_download(c: Gojo, m: Message):
    url = re.search(YT_REGEX, m.text).group(0)
    user_mention = m.from_user.mention

    status = await m.reply_text("🔍 **Fetching the highest quality video (up to 4K)...**")

    try:
        # Get video ID for thumbnail
        video_id = None
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        elif "youtube.com" in url and "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        thumb_path = None
        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            thumb_path = wget.download(thumb_url)

        # Download options for best 4K
        opts = {
            "format": "bestvideo[ext=mp4][height<=4320]+bestaudio[ext=m4a]/best",
            "merge_output_format": "mp4",  # Force MP4 merge
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "cookiefile": COOKIES_FILE,  # Use saved cookies
            "outtmpl": "%(id)s.%(ext)s",
            "quiet": True,
        }

        with YoutubeDL(opts) as ytdl:
            info = ytdl.extract_info(url, download=True)

        file_path = f"{info['id']}.mp4"
        caption = (
            f"🎬 **Title:** [{info['title']}]({url})\n"
            f"📺 **Channel:** {info.get('uploader', 'Unknown')}\n"
            f"🎥 **Quality:** {info.get('height', 'Unknown')}p\n"
            f"🙋 **Requested by:** {user_mention}\n"
            f"📥 **Downloaded by:** {c.me.mention}"
        )

        await c.send_video(
            m.chat.id,
            video=open(file_path, "rb"),
            duration=int(info["duration"]),
            file_name=f"{info['title']}.mp4",
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
**🎥 Auto YouTube 4K Video Downloader**
• Sends the best possible quality (up to 4K or 8K).
• Just send any YouTube link.
• Requires `cookies.txt` in the bot folder for age-restricted/private videos.
"""
