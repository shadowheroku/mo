import requests
import os
import mimetypes
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

# Updated AnonFiles settings
ANONFILES_UPLOAD_URL = "https://api.anonfiles.com/upload"
ANONFILES_STATUS_URL = "https://api.anonfiles.com/v2/file/{}/info"
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
TIMEOUT = 30  # seconds

@Gojo.on_message(command("tgm"))
async def upload_media_to_anonfiles(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a media file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    
    try:
        # Download file
        media_path = await m.reply_to_message.download()
        file_size = os.path.getsize(media_path)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            os.remove(media_path)
            return await msg.edit_text(f"🚫 File too large! Max size is {MAX_FILE_SIZE//(1024*1024)}MB")

        # Upload to AnonFiles
        await msg.edit_text("☁️ Uploading to AnonFiles...")
        
        try:
            with open(media_path, "rb") as f:
                response = requests.post(
                    ANONFILES_UPLOAD_URL,
                    files={"file": f},
                    timeout=TIMEOUT
                )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            os.remove(media_path)
            return await msg.edit_text(f"❌ Upload failed: {str(e)}")

        # Check response
        if not data.get("status"):
            error = data.get("error", {}).get("message", "Unknown error")
            os.remove(media_path)
            return await msg.edit_text(f"❌ AnonFiles error: {error}")

        # Get file URL
        file_url = data["data"]["file"]["url"]["full"]
        short_url = data["data"]["file"]["url"]["short"]
        
        # Create share button
        share_url = f"https://t.me/share/url?url={quote(file_url)}&text=Check%20this%20file%20I%20uploaded!"
        
        await msg.edit_text(
            f"✅ **Upload Successful!**\n\n"
            f"🔗 Full URL: `{file_url}`\n"
            f"🪶 Short URL: `{short_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open Link", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)]
            ])
        )
        
        os.remove(media_path)

    except Exception as e:
        await msg.edit_text(f"⚠️ An error occurred: {str(e)}")
        if "media_path" in locals() and os.path.exists(media_path):
            os.remove(media_path)

__PLUGIN__ = "anonfiles_upload"
__HELP__ = """
**📤 AnonFiles Uploader**
`/tgm` - Upload media files to AnonFiles

**Features:**
- Supports most file types
- Max size: 2GB
- Direct download links
- Easy sharing options
"""
