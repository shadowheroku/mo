import os
import mimetypes
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

GOFILE_API = "https://upload.gofile.io/uploadfile"
TIMEOUT = 60  # seconds
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB

@Gojo.on_message(command(["gofile", "gf"]))
async def gofile_uploader(c: Gojo, m: Message):
    """Upload any file to Gofile.io reliably."""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file…")
    file_path = None

    try:
        # Download the media
        file_path = await m.reply_to_message.download()
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({size//(1024*1024)} MB > 10 GB limit)")

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        await msg.edit_text("☁️ Uploading to Gofile.io…")
        with open(file_path, "rb") as f:
            response = requests.post(
                GOFILE_API,
                files={"file": (os.path.basename(file_path), f, mime_type)},
                timeout=TIMEOUT
            )

        if response.status_code != 200:
            raise ValueError(f"HTTP Error {response.status_code}: {response.text}")

        result = response.json()
        if result.get("status") != "ok":
            raise ValueError(f"Gofile API error: {result.get('status')}")

        download_page = result["data"]["downloadPage"]
        direct_link = result["data"]["directLink"]

        share_url = f"https://t.me/share/url?url={quote(download_page)}"
        await msg.edit_text(
            f"✅ **Uploaded to Gofile.io!**\n\n"
            f"• Download Page: `{download_page}`\n"
            f"• Direct Link: `{direct_link}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Open", url=download_page)],
                [InlineKeyboardButton("Direct Download", url=direct_link)],
                [InlineKeyboardButton("Share Link", url=share_url)],
            ])
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{e}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "gofile_uploader"
__HELP__ = """
**Gofile.io Uploader**
`/gofile` or `/gf` – Upload files (≤ 10 GB) to Gofile.io
• Returns both a public page link and a direct download link
"""
