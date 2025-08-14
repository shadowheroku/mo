import os
import mimetypes
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

# Gofile.io configuration
GOFILE_API = "https://api.gofile.io/uploadFile"
TIMEOUT = 60  # seconds
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

@Gojo.on_message(command(["gofile", "gf"]))
async def gofile_uploader(c: Gojo, m: Message):
    """Upload files to Gofile.io with proper error handling"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    file_path = None
    
    try:
        # Download file
        file_path = await m.reply_to_message.download()
        file_size = os.path.getsize(file_path)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({file_size//(1024*1024)}MB > 10GB limit)")

        # Check MIME type
        mime_type = get_mime_type(file_path)

        # Upload to Gofile.io
        await msg.edit_text("☁️ Uploading to Gofile.io...")
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
            raise ValueError(f"Gofile API Error: {result.get('status')}")

        file_link = result["data"]["downloadPage"]
        direct_link = result["data"]["directLink"]

        # Success - send result
        share_url = f"https://t.me/share/url?url={quote(file_link)}"
        await msg.edit_text(
            f"✅ **Uploaded to Gofile.io!**\n\n"
            f"🔗 Download Page: `{file_link}`\n"
            f"📥 Direct Link: `{direct_link}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open", url=file_link)],
                [InlineKeyboardButton("📥 Direct Download", url=direct_link)],
                [InlineKeyboardButton("📤 Share", url=share_url)],
                [InlineKeyboardButton("📋 Copy", callback_data=f"copy_{quote(file_link)}")]
            ])
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{str(e)}")
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def get_mime_type(file_path: str) -> str:
    """Get MIME type with proper fallback"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

__PLUGIN__ = "gofile_uploader"
__HELP__ = """
**☁️ Gofile.io Uploader**
`/gofile` or `/gf` - Upload files to Gofile.io

✅ **Supported Files:**
- Any type (≤10GB)
- Permanent storage
- Direct download links

❌ **Common Issues:**
- Files >10GB will be rejected
- Some countries may block Gofile.io
"""
