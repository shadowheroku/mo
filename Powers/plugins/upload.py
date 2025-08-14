import requests
import os
import mimetypes
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote
from typing import Tuple, Optional

# Upload services configuration
UPLOAD_SERVICES = {
    "gofile": {
        "url": ""https://api.gofile.io/uploadFile"",
        "max_size": 2 * 1024 * 1024 * 1024,  # 2GB
        "expires": "permanent",
        "requires_api_key": False
    },
    "fileio": {
        "url": "https://file.io",
        "max_size": 100 * 1024 * 1024,  # 100MB
        "expires": "14d",
        "requires_api_key": False
    },
    "transfersh": {
        "url": "https://transfer.sh",
        "max_size": 10 * 1024 * 1024 * 1024,  # 10GB
        "expires": "14d",
        "requires_api_key": False
    },
    "0x0st": {
        "url": "https://0x0.st",
        "max_size": 512 * 1024 * 1024,  # 512MB
        "expires": "30d",
        "requires_api_key": False
    }
}

# Global settings
TIMEOUT = 30  # seconds
DEFAULT_SERVICE = "gofile"  # Most reliable default

async def download_telegram_file(c: Gojo, msg: Message) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Download Telegram file and return (path, size, mime_type)"""
    try:
        media_path = await msg.download()
        file_size = os.path.getsize(media_path)
        mime_type, _ = mimetypes.guess_type(media_path)
        return media_path, file_size, mime_type
    except Exception as e:
        return None, None, None

async def upload_to_service(service: str, file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload file to specified service and return (url, error)"""
    config = UPLOAD_SERVICES.get(service)
    if not config:
        return None, "Invalid service"

    try:
        with open(file_path, "rb") as f:
            if service == "gofile":
                response = requests.post(
                    config["url"],
                    files={"file": f},
                    timeout=TIMEOUT
                )
                data = response.json()
                if data["status"] == "ok":
                    return data["data"]["downloadPage"], None
                return None, data.get("message", "Upload failed")

            elif service == "fileio":
                response = requests.post(
                    config["url"],
                    files={"file": f},
                    params={"expires": config["expires"]},
                    timeout=TIMEOUT
                )
                data = response.json()
                if data["success"]:
                    return data["link"], None
                return None, data.get("message", "Upload failed")

            elif service == "transfersh":
                filename = os.path.basename(file_path)
                response = requests.put(
                    f"{config['url']}/{filename}",
                    data=f,
                    timeout=TIMEOUT
                )
                if response.status_code == 200:
                    return response.text.strip(), None
                return None, f"HTTP {response.status_code}"

            elif service == "0x0st":
                response = requests.post(
                    config["url"],
                    files={"file": f},
                    timeout=TIMEOUT
                )
                if response.status_code == 200:
                    return response.text.strip(), None
                return None, f"HTTP {response.status_code}"

    except requests.RequestException as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

@Gojo.on_message(command(["upload", "tgm"]))
async def handle_file_upload(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    
    # Download the file
    file_path, file_size, mime_type = await download_telegram_file(c, m.reply_to_message)
    if not file_path:
        return await msg.edit_text("❌ Failed to download file")

    # Check if file is too large for all services
    max_allowed = max(s["max_size"] for s in UPLOAD_SERVICES.values())
    if file_size > max_allowed:
        os.remove(file_path)
        return await msg.edit_text(f"🚫 File too large! Max supported size is {max_allowed//(1024*1024)}MB")

    # Try uploading to default service first
    await msg.edit_text(f"☁️ Uploading to {DEFAULT_SERVICE}...")
    file_url, error = await upload_to_service(DEFAULT_SERVICE, file_path)
    
    # If default fails, try other services
    if not file_url:
        for service in [s for s in UPLOAD_SERVICES if s != DEFAULT_SERVICE]:
            await msg.edit_text(f"⚠️ Retrying with {service}...")
            file_url, error = await upload_to_service(service, file_path)
            if file_url:
                break

    # Clean up local file
    if os.path.exists(file_path):
        os.remove(file_path)

    # Handle result
    if file_url:
        share_url = f"https://t.me/share/url?url={quote(file_url)}&text=Check%20this%20file!"
        await msg.edit_text(
            f"✅ **Upload Successful!**\n\n"
            f"🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open Link", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)],
                [InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{quote(file_url)}")]
            ])
        )
    else:
        await msg.edit_text(f"❌ All upload attempts failed. Last error: {error}")

__PLUGIN__ = "file_uploader"
__HELP__ = """
**📤 Multi-File Uploader**
`/upload` - Upload files to various hosting services

**Features:**
- Automatic service fallback if one fails
- Supports files up to 10GB (depending on service)
- Multiple hosting options
- Easy sharing interface

**Supported Services:**
- GoFile.io (2GB, permanent)
- File.io (100MB, 14 days)
- transfer.sh (10GB, 14 days)
- 0x0.st (512MB, 30 days)
"""
