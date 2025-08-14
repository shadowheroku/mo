import os
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

# Catbox.moe configuration
CATBOX_API = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
TIMEOUT = 45  # seconds
SUPPORTED_MIME_TYPES = [
    "image/jpeg", "image/png", "image/gif", 
    "video/mp4", "video/webm", "video/quicktime",
    "application/octet-stream"  # For generic files
]

@Gojo.on_message(command(["upload", "tgm"]))
async def catbox_uploader(c: Gojo, m: Message):
    """Upload files to Catbox.moe with proper error handling"""
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
            raise ValueError(f"File too large ({file_size//(1024*1024)}MB > 200MB limit)")

        # Check MIME type
        mime_type = get_mime_type(file_path)
        if mime_type not in SUPPORTED_MIME_TYPES:
            raise ValueError(f"Unsupported file type: {mime_type}")

        # Prepare upload
        await msg.edit_text("🐱 Uploading to Catbox.moe...")
        file_name = os.path.basename(file_path)
        
        # Catbox requires specific formatting
        with open(file_path, "rb") as f:
            files = {
                "fileToUpload": (file_name, f),
                "reqtype": (None, "fileupload"),
                "userhash": (None, "")  # Needed to avoid 412 error
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.post(
                CATBOX_API,
                files=files,
                headers=headers,
                timeout=TIMEOUT
            )

        # Handle response
        if response.status_code == 412:
            raise ValueError("Catbox rejected the file (possibly invalid format)")
        elif response.status_code != 200:
            raise ValueError(f"HTTP Error {response.status_code}: {response.text}")

        file_url = response.text.strip()
        if not file_url.startswith(("http://", "https://")):
            raise ValueError("Invalid response from Catbox")

        # Success - send result
        share_url = f"https://t.me/share/url?url={quote(file_url)}"
        await msg.edit_text(
            f"✅ **Uploaded to Catbox!**\n\n"
            f"🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)],
                [InlineKeyboardButton("📋 Copy", callback_data=f"copy_{quote(file_url)}")]
            ])
        )

    except Exception as e:
        error_msg = f"❌ Failed to upload:\n{str(e)}"
        if "412" in str(e):
            error_msg += "\n\nℹ️ Tip: Catbox may not support this file type"
        await msg.edit_text(error_msg)
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def get_mime_type(file_path: str) -> str:
    """Get MIME type with proper fallback"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

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
