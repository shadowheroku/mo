import requests
import os
import mimetypes
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Catbox API Configuration
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

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
    """Upload media to Catbox"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a media file (photo/video/document)!")

    msg = await m.reply_text("⬇️ **Downloading file...**")

    try:
        # Download the media file
        media_path = await m.reply_to_message.download()
        file_size = os.path.getsize(media_path)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            os.remove(media_path)
            return await msg.edit_text(f"❌ File too large! Max size is {MAX_FILE_SIZE // (1024 * 1024)}MB.")

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
            os.remove(media_path)
            return await msg.edit_text("❌ Unsupported file type! Use: JPG, PNG, GIF, MP4, WEBM, MOV.")

        # Fix file extension
        correct_ext = SUPPORTED_MIME_TYPES[mime_type]
        if not media_path.lower().endswith(correct_ext):
            new_path = os.path.splitext(media_path)[0] + correct_ext
            os.rename(media_path, new_path)
            media_path = new_path

        # Upload to Catbox
        await msg.edit_text("⬆️ **Uploading to Catbox...**")
        with open(media_path, "rb") as file:
            response = requests.post(
                CATBOX_URL,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": file}
            )

        os.remove(media_path)  # Clean up temp file

        # Handle Catbox response
        if response.status_code == 200 and response.text.startswith("http"):
            await msg.edit_text(f"✅ **Uploaded!**\n🔗 [Catbox URL]({response.text})", disable_web_page_preview=True)
        elif response.status_code == 412:
            await msg.edit_text("❌ Catbox rejected the file.\nPossible reasons:\n- Corrupted file\n- Wrong format\n- Invalid extension")
        else:
            await msg.edit_text(f"❌ Upload failed. HTTP {response.status_code}\n{response.text}")

    except requests.RequestException as re:
        await msg.edit_text(f"⚠️ Network error while uploading: {str(re)}")
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {str(e)}")
        if "media_path" in locals() and os.path.exists(media_path):
            os.remove(media_path)

__PLUGIN__ = "catbox_upload"
__HELP__ = """
**📤 Catbox Uploader**
Reply to a media file and use `/tgm` to upload it.

✅ **Supported formats:** JPG, PNG, GIF, MP4, WEBM, MOV  
📦 **Max size:** 200MB
"""
