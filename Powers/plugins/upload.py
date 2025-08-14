import os
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

TRANSFER_API = "https://transfer.sh"
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
TIMEOUT = 60  # seconds

@Gojo.on_message(command(["upload", "ul"]))
async def transfer_upload(c: Gojo, m: Message):
    """Upload files to transfer.sh"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    file_path = None

    try:
        file_path = await m.reply_to_message.download()
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({file_size//(1024*1024)}MB > 1024MB limit)")

        await msg.edit_text("☁️ Uploading to Transfer.sh...")
        file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            response = requests.put(
                f"{TRANSFER_API}/{file_name}",
                data=f,
                timeout=TIMEOUT
            )

        if response.status_code != 200:
            raise ValueError(f"HTTP Error {response.status_code}: {response.text}")

        file_url = response.text.strip()
        share_url = f"https://t.me/share/url?url={quote(file_url)}"

        await msg.edit_text(
            f"✅ **Uploaded!**\n\n🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)]
            ])
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{str(e)}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


__PLUGIN__ = "catbox_uploader"
__HELP__ = """
**🐱 Catbox.moe Uploader**
`/upload` or `/tgm` - Upload files to Catbox.moe

✅ **Supported Files:**
- Images (JPEG, PNG, GIF)
- Videos (MP4, WebM, MOV)
- Other files (≤200MB)

❌ **Common Issues:**
- Files >200MB will be rejected
- Some file types may cause HTTP 412 errors
- Server-side issues may temporarily prevent uploads
"""
