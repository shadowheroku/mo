import os
import logging
import requests
import mimetypes
from typing import Tuple, Optional
from urllib.parse import quote
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Upload services configuration (updated with more reliable options)
UPLOAD_SERVICES = {
    "gofile": {
        "url": "https://{server}.gofile.io/uploadFile",
        "server_url": "https://api.gofile.io/getServer",
        "max_size": 2 * 1024 * 1024 * 1024,  # 2GB
        "display_name": "GoFile.io",
        "method": "post"
    },
    "filebin": {
        "url": "https://filebin.net",
        "max_size": 100 * 1024 * 1024,  # 100MB
        "display_name": "FileBin.net",
        "method": "post"
    },
    "anonfiles": {
        "url": "https://api.anonfiles.com/upload",
        "max_size": 20 * 1024 * 1024 * 1024,  # 20GB
        "display_name": "AnonFiles",
        "method": "post"
    }
}

TIMEOUT = 45  # Increased timeout
MAX_RETRIES = 2

async def download_telegram_file(c: Gojo, msg: Message) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Download Telegram file with error handling"""
    try:
        media_path = await msg.download()
        if not media_path or not os.path.exists(media_path):
            return None, None, None
            
        file_size = os.path.getsize(media_path)
        mime_type, _ = mimetypes.guess_type(media_path)
        return media_path, file_size, mime_type
        
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return None, None, None

async def upload_to_gofile(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Special handler for GoFile with server selection"""
    try:
        # Get best server
        server_resp = requests.get(
            UPLOAD_SERVICES["gofile"]["server_url"],
            timeout=TIMEOUT
        )
        if server_resp.status_code != 200:
            return None, "Failed to get server"
            
        server_data = server_resp.json()
        if not server_data.get("status") == "ok":
            return None, server_data.get("message", "Server selection failed")
            
        server = server_data["data"]["server"]
        upload_url = UPLOAD_SERVICES["gofile"]["url"].format(server=server)
        
        # Upload file
        with open(file_path, "rb") as f:
            response = requests.post(
                upload_url,
                files={"file": f},
                timeout=TIMEOUT
            )
            
        data = response.json()
        if data.get("status") == "ok":
            return data["data"]["downloadPage"], None
        return None, data.get("message", "Upload failed")
        
    except Exception as e:
        return None, str(e)

async def upload_to_service(service: str, file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Handle file upload with retries"""
    config = UPLOAD_SERVICES.get(service)
    if not config:
        return None, "Invalid service"
        
    for attempt in range(MAX_RETRIES):
        try:
            if service == "gofile":
                return await upload_to_gofile(file_path)
                
            with open(file_path, "rb") as f:
                if config["method"] == "post":
                    response = requests.post(
                        config["url"],
                        files={"file": f},
                        timeout=TIMEOUT
                    )
                else:
                    response = requests.put(
                        config["url"],
                        data=f,
                        timeout=TIMEOUT
                    )
                    
                if response.status_code == 200:
                    if service == "anonfiles":
                        data = response.json()
                        if data.get("status"):
                            return data["data"]["file"]["url"]["full"], None
                    elif service == "filebin":
                        return response.url, None
                    else:
                        return response.text.strip(), None
                        
                return None, f"HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                return None, f"Network error: {str(e)}"
            continue
            
    return None, "Upload failed after retries"

@Gojo.on_message(command(["upload", "up"]))
async def handle_upload_command(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    
    # Download file
    file_path, file_size, mime_type = await download_telegram_file(c, m.reply_to_message)
    if not file_path:
        return await msg.edit_text("❌ Failed to download file")
        
    try:
        # Try services in order of reliability
        services_to_try = ["gofile", "anonfiles", "filebin"]
        file_url = None
        last_error = None
        
        for service in services_to_try:
            if file_size > UPLOAD_SERVICES[service]["max_size"]:
                continue
                
            await msg.edit_text(f"☁️ Uploading to {UPLOAD_SERVICES[service]['display_name']}...")
            file_url, error = await upload_to_service(service, file_path)
            
            if file_url:
                break
            last_error = error
            logger.warning(f"Upload to {service} failed: {error}")

        if not file_url:
            return await msg.edit_text(f"❌ All upload attempts failed. Last error: {last_error}")
            
        # Create share buttons
        share_url = f"https://t.me/share/url?url={quote(file_url)}"
        buttons = [
            [InlineKeyboardButton("🌐 Open Link", url=file_url)],
            [InlineKeyboardButton("📤 Share", url=share_url)]
        ]
        
        await msg.edit_text(
            f"✅ **Upload Successful!**\n\n"
            f"🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        await msg.edit_text(f"⚠️ An error occurred: {str(e)}")
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "file_uploader"
__HELP__ = """
**📤 Reliable File Uploader**
`/upload` or `/up` - Upload files to various hosting services

**Features:**
- Multiple reliable hosting options
- Automatic retry on failure
- Supports files up to 20GB
- Clean sharing interface

**Supported Services:**
- GoFile.io (2GB, permanent)
- AnonFiles (20GB, permanent)
- FileBin.net (100MB, temporary)

**Note:** The bot will automatically select the best service for your file.
"""
