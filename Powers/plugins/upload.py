import requests
import os
import mimetypes
from pathlib import Path
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Catbox API Configuration
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB (Catbox limit)

# Supported MIME types (Catbox accepts these)
SUPPORTED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

@Gojo.on_message(command("tgm"))
async def upload_media_to_catbox(c: Gojo, m: Message):
    """Upload media files to Catbox with proper validation"""
    if not m.reply_to_message or not m.reply_to_message.media:
        await m.reply_text("❌ Please reply to a media file (photo/video/document)!")
        return

    try:
        # Download the media file
        msg = await m.reply_text("⬇️ Downloading file...")
        media_path = await m.reply_to_message.download()
        file_size = os.path.getsize(media_path)
        
        # --- FILE VALIDATION CHECKS ---
        # 1. Check file size
        if file_size > MAX_FILE_SIZE:
            await msg.edit_text(f"❌ File too large! (Max {MAX_FILE_SIZE//(1024*1024)}MB)")
            os.remove(media_path)
            return
            
        # 2. Check MIME type (real file type, not just extension)
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
            await msg.edit_text("❌ Unsupported file type! Use: JPG, PNG, GIF, MP4, WEBM, MOV")
            os.remove(media_path)
            return

        # 3. Ensure correct file extension (Catbox is strict about this)
        correct_ext = SUPPORTED_MIME_TYPES[mime_type]
        if not media_path.lower().endswith(correct_ext):
            new_path = f"{os.path.splitext(media_path)[0]}{correct_ext}"
            os.rename(media_path, new_path)
            media_path = new_path

        # --- UPLOAD TO CATBOX ---
        await msg.edit_text("⬆️ Uploading to Catbox...")
        with open(media_path, "rb") as file:
            files = {"fileToUpload": file}
            response = requests.post(CATBOX_URL, files=files)
        
        # --- RESPONSE HANDLING ---
        os.remove(media_path)  # Cleanup
        
        if response.status_code == 200 and response.text.startswith("http"):
            await msg.edit_text(f"✅ **Uploaded!**\n🔗 [Catbox URL]({response.text})", parse_mode="Markdown")
        elif response.status_code == 412:
            await msg.edit_text("❌ Catbox rejected the file.\n⚠️ Possible reasons:\n- Corrupted file\n- Wrong format\n- Invalid extension")
        else:
            await msg.edit_text(f"❌ Upload failed (HTTP {response.status_code})")

    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {str(e)}")
        if "media_path" in locals() and os.path.exists(media_path):
            os.remove(media_path)

__PLUGIN__ = "catbox_upload"
__HELP__ = """
**📤 Catbox Uploader**

`/tgm` - Upload media to Catbox (reply to a file)
✅ **Supported formats:**  
- Images: `JPG, PNG, GIF`  
- Videos: `MP4, WEBM, MOV`  
📦 **Max size:** 200MB

The bot will reply with the Catbox URL after upload.
"""
