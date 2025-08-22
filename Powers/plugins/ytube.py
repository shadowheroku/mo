import os
import wget
import asyncio
from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from youtubesearchpython import SearchVideos
from yt_dlp import YoutubeDL

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.cmd_senders import send_cmd
from Powers.utils.msg_types import Types


# Support button
SUPPORT_CHAT = "Shadowchathq"
BUTTON = [[InlineKeyboardButton("ꜱᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}")]]


def get_text(message: Message) -> str | None:
    """Extract text from a command message"""
    if not message.text:
        return None
    parts = message.text.split(None, 1)
    return parts[1] if len(parts) > 1 else None


@Gojo.on_message(command(["yt", "video"]))
async def yt_video_cmd(c: Gojo, m: Message):
    query = get_text(m)
    await m.delete()

    mention = f"[{m.from_user.first_name}](tg://user?id={m.from_user.id})"

    status = await c.send_message(m.chat.id, "🔍 Searching, please wait...")

    if not query:
        await status.edit("😴 No song found.\n\n» Maybe you typed it wrong?")
        return

    # 🔎 YouTube search
    search = SearchVideos(query, offset=1, mode="dict", max_results=1)
    result = search.result()
    if not result or "search_result" not in result or not result["search_result"]:
        await status.edit("❌ Couldn't find anything on YouTube.")
        return

    info = result["search_result"][0]
    video_url = info["link"]
    video_title = info["title"]
    video_id = info["id"]
    video_channel = info["channel"]
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    # Download thumbnail
    thumb_file = wget.download(thumbnail_url)

    # Create a temporary cookies file
    cookies_file = "temp_cookies.txt"
    cookies_content = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	FALSE	1790413715	HSID	ALZ5C0Px7v3KlQH8T
.youtube.com	TRUE	/	TRUE	1790413715	SSID	AMhSLS2ToFPTmfkF
"""
    with open(cookies_file, "w") as f:
        f.write(cookies_content)

    opts = {
        "format": "best",
        "addmetadata": True,
        "key": "FFmpegMetadata",
        "prefer_ffmpeg": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "cookiefile": cookies_file,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "outtmpl": "%(id)s.mp4",
        "quiet": True,
    }

    try:
        with YoutubeDL(opts) as ytdl:
            data = ytdl.extract_info(video_url, download=True)
    except Exception as e:
        await status.edit(f"**Failed to download.**\n\nError: `{str(e)}`")
        if os.path.exists(cookies_file):
            os.remove(cookies_file)
        return

    file_path = f"{data['id']}.mp4"
    caption = (
        f"❄ **Title:** [{video_title}]({video_url})\n"
        f"💫 **Channel:** {video_channel}\n"
        f"✨ **Searched:** `{query}`\n"
        f"🥀 **Requested by:** {mention}"
    )

    try:
        sent_msg = await (await send_cmd(c, Types.VIDEO))(
            m.chat.id,
            file_path,
            caption,
            parse_mode=PM.MARKDOWN,
            thumb=thumb_file,
            reply_markup=InlineKeyboardMarkup(BUTTON),
        )
        await asyncio.sleep(60)
        await sent_msg.delete()
    except Exception as e:
        await status.edit(f"⚠️ Failed to upload.\n\nError: `{str(e)}`")
        await asyncio.sleep(60)
        await status.delete()
        if os.path.exists(cookies_file):
            os.remove(cookies_file)
        return

    await status.delete()

    # Cleanup
    for f in (thumb_file, file_path, cookies_file):
        if f and os.path.exists(f):
            os.remove(f)


__PLUGIN__ = "yt_video"

_DISABLE_CMDS_ = ["yt", "video"]

__HELP__ = """
**YouTube Video Downloader** 🎥

• /yt <query>  
   Search & download a YouTube video  

• /video <query>  
   Same as `/yt`
"""
