import os
import mimetypes
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

UPLOAD_ENDPOINT = "https://upload.gofile.io/uploadfile"
CONTENT_ENDPOINT = "https://api.gofile.io/getContent"
TIMEOUT = 60
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB

@Gojo.on_message(command(["gofile", "gf"]))
async def gofile_uploader(c: Gojo, m: Message):
    """Upload any file to Gofile.io and fetch direct link."""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file…")
    file_path = None

    try:
        # Download the file
        file_path = await m.reply_to_message.download()
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({size//(1024*1024)} MB > 10 GB limit)")

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        # Upload to Gofile
        await msg.edit_text("☁️ Uploading to Gofile.io…")
        with open(file_path, "rb") as f:
            res = requests.post(
                UPLOAD_ENDPOINT,
                files={"file": (os.path.basename(file_path), f, mime_type)},
                timeout=TIMEOUT
            )

        if res.status_code != 200:
            raise ValueError(f"HTTP Error {res.status_code}: {res.text}")

        result = res.json()
        if result.get("status") != "ok":
            raise ValueError(f"Gofile API error: {result.get('status')}")

        download_page = result["data"]["downloadPage"]
        content_id = result["data"]["code"]

        # Fetch direct link from getContent API
        content_res = requests.get(
            f"{CONTENT_ENDPOINT}?contentId={content_id}&token=",
            timeout=TIMEOUT
        ).json()

        if content_res.get("status") != "ok":
            raise ValueError("Failed to retrieve direct link from Gofile.")

        files_info = content_res["data"]["contents"]
        first_file = next(iter(files_info.values()))
        direct_link = first_file.get("link")

        # Prepare Telegram buttons
        share_url = f"https://t.me/share/url?url={quote(download_page)}"
        buttons = [
            [InlineKeyboardButton("🌐 Open", url=download_page)],
            [InlineKeyboardButton("📥 Direct Download", url=direct_link)],
            [InlineKeyboardButton("📤 Share", url=share_url)],
        ]

        await msg.edit_text(
            f"✅ **Uploaded to Gofile.io!**\n\n"
            f"🔗 Download Page: `{download_page}`\n"
            f"📥 Direct Link: `{direct_link}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{e}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "gofile_uploader"
__HELP__ = """
**☁️ Gofile.io Uploader**
`/gofile` or `/gf` - Upload files to Gofile.io

✅ Any file type (≤10 GB)  
✅ Permanent storage  
✅ Direct download link support  
"""
