import requests, os, mimetypes
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# File.io settings
FILEIO_URL = "https://file.io"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
SUPPORTED_MIME_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"
}

@Gojo.on_message(command("tgm"))
async def upload_media_to_fileio(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ **Reply to a photo/video/document to upload!**")

    msg = await m.reply_text("📥 **Step 1:** Downloading...")
    try:
        # Download
        media_path = await m.reply_to_message.download()
        if os.path.getsize(media_path) > MAX_FILE_SIZE:
            os.remove(media_path)
            return await msg.edit_text(f"🚫 **File too large!** Max {MAX_FILE_SIZE//(1024*1024)}MB")

        # Validate type
        mime_type, _ = mimetypes.guess_type(media_path)
        if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
            os.remove(media_path)
            return await msg.edit_text("⚠️ **Unsupported format!** JPG, PNG, GIF, MP4, WEBM, MOV")

        # Correct extension
        ext = SUPPORTED_MIME_TYPES[mime_type]
        if not media_path.lower().endswith(ext):
            new_path = os.path.splitext(media_path)[0] + ext
            os.rename(media_path, new_path)
            media_path = new_path

        # Upload
        await msg.edit_text("☁️ **Step 2:** Uploading to File.io...")
        with open(media_path, "rb") as f:
            r = requests.post(FILEIO_URL, files={"file": f})
        os.remove(media_path)

        if r.status_code == 200:
            data = r.json()
            if data.get("success") and "link" in data:
                fileio_url = data["link"]
                await msg.edit_text(
                    f"✅ **Upload Successful!**\n📎 Link: `{fileio_url}`",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Open Link", url=fileio_url)],
                        [InlineKeyboardButton("🔄 Share Link", url=f"https://t.me/share/url?url={fileio_url}")]
                    ])
                )
            else:
                await msg.edit_text(f"❌ **Upload failed!**\nResponse: {data}")
        else:
            await msg.edit_text(f"❌ **Upload failed!**\nHTTP {r.status_code}\n{r.text}")

    except requests.RequestException as re:
        await msg.edit_text(f"🌐 **Network Error:** `{re}`")
    except Exception as e:
        await msg.edit_text(f"⚠️ **Error:** `{e}`")
        if "media_path" in locals() and os.path.exists(media_path):
            os.remove(media_path)

__PLUGIN__ = "Upload"
__HELP__ = """
**📤 File.io Uploader**
`/tgm` — Reply to a media file to upload to File.io.

**✅ Supported formats:** JPG, PNG, GIF, MP4, WEBM, MOV  
📦 **Max size:** 200MB  
🔄 **Includes share button for easy link sharing!**
"""
