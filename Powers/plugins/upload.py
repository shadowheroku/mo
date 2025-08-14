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

@Gojo.on_message(command(["catbox", "cb"]))
async def catbox_uploader(c: Gojo, m: Message):
    """Upload files to Catbox.moe"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload to Catbox!")

    msg = await m.reply_text("📥 Downloading your file...")
    
    try:
        # Download file
        file_path = await m.reply_to_message.download()
        file_size = os.path.getsize(file_path)

        # Check file size
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            return await msg.edit_text("🚫 File too large! Catbox max size is 200MB")

        # Upload to Catbox
        await msg.edit_text("🐱 Uploading to Catbox.moe...")
        
        with open(file_path, "rb") as f:
            files = {"fileToUpload": (os.path.basename(file_path), f)}
            response = requests.post(
                CATBOX_API,
                files=files,
                data={"reqtype": "fileupload"},
                timeout=TIMEOUT
            )

        # Clean up local file
        os.remove(file_path)

        if response.status_code != 200:
            return await msg.edit_text(f"❌ Upload failed (HTTP {response.status_code})")

        file_url = response.text.strip()
        if not file_url.startswith("http"):
            return await msg.edit_text("❌ Invalid response from Catbox")

        # Create share buttons
        share_url = f"https://t.me/share/url?url={quote(file_url)}"
        await msg.edit_text(
            f"✅ **Uploaded to Catbox!**\n\n"
            f"🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open Link", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)],
                [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{quote(file_url)}")]
            ])
        )

    except requests.exceptions.RequestException as e:
        await msg.edit_text(f"🌐 Network Error: {str(e)}")
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {str(e)}")
        if "file_path" in locals() and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "catbox_uploader"
__HELP__ = """
**🐱 Catbox.moe Uploader**
`/catbox` or `/cb` - Upload files to Catbox.moe

**Features:**
- Fast and reliable file hosting
- Supports files up to 200MB
- Direct download links
- Easy sharing options

**Note:** Works best for images, videos and small files.
Files are kept permanently unless they violate Catbox's terms.
"""
