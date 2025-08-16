import os
import tempfile
import re
from pyrogram import filters
from Powers.bot_class import Gojo
import yt_dlp

# ========================
# INSTAGRAM REGEX
# ========================
INSTAGRAM_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?instagram\.com\/(?:reel|p|tv)\/[A-Za-z0-9_\-]+)"
)

# ========================
# BOT HANDLER
# ========================
@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def instagram_download(c, m):
    url_match = INSTAGRAM_REGEX.search(m.text or "")
    if not url_match:
        return

    url = url_match.group(1)
    status = await m.reply_text("📥 Downloading Instagram content...")

    try:
        # yt-dlp options
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",   # Best quality available
            "merge_output_format": "mp4",           # Merge into mp4
            "noplaylist": True,                     # Handle single post/reel
            "quiet": True,                          # Less logs
            "outtmpl": "%(title)s.%(ext)s",         # Filename
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        caption = f"📸 {info.get('title', 'Instagram Content')}\n🔗 [Post Link]({url})"
        ext = info.get("ext", "mp4").lower()

        if ext in ["mp4", "mov", "webm"]:
            await m.reply_video(video=file_path, caption=caption)
        elif ext in ["jpg", "jpeg", "png", "webp"]:
            await m.reply_photo(photo=file_path, caption=caption)
        else:
            await m.reply_document(document=file_path, caption=caption)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")

    finally:
        try:
            if "file_path" in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass


__PLUGIN__ = "Instagram Downloader"
__HELP__ = """
📸 **Instagram Downloader**

Send any Instagram `reel`, `post`, or `tv` link and I’ll fetch it.

⚡ Works without cookies or login!
"""
