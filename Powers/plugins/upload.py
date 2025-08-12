import requests
import os
from pathlib import Path
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Catbox API Configuration
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB (Catbox limit)

@Gojo.on_message(command("tgm"))
async def upload_media_to_catbox(c: Gojo, m: Message):
    """Upload media files to Catbox"""
    if not m.reply_to_message or not m.reply_to_message.media:
        await m.reply_text("Please reply to a media file to upload!")
        return

    try:
        # Download the media file with progress
        msg = await m.reply_text("Downloading media...")
        media_path = await m.reply_to_message.download()
        file_size = os.path.getsize(media_path)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            await msg.edit_text(f"File too large! Max size: {MAX_FILE_SIZE//(1024*1024)}MB")
            os.remove(media_path)
            return
            
        # Validate file extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mov']
        if Path(media_path).suffix.lower() not in valid_extensions:
            await msg.edit_text("Unsupported file type! Supported: JPG, PNG, GIF, MP4, WEBM, MOV")
            os.remove(media_path)
            return

        # Upload to Catbox
        await msg.edit_text("Uploading to Catbox...")
        files = {'fileToUpload': open(media_path, 'rb')}
        response = requests.post(CATBOX_URL, files=files)
        
        # Clean up
        os.remove(media_path)
        
        if response.status_code == 200 and response.text.startswith("http"):
            await msg.edit_text(f"✅ Upload successful!\n🔗 URL: {response.text}")
        else:
            error_msg = f"Failed to upload (Status {response.status_code})"
            if "412" in str(response.status_code):
                error_msg += "\nCatbox rejected the file (possibly invalid format)"
            await msg.edit_text(error_msg)
            
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {str(e)}")
        if 'media_path' in locals() and os.path.exists(media_path):
            os.remove(media_path)

@Gojo.on_message(command("tgt"))
async def upload_text_to_catbox(c: Gojo, m: Message):
    """Upload text to Catbox"""
    if not m.reply_to_message or not m.reply_to_message.text:
        await m.reply_text("Please reply to a text message to upload!")
        return

    try:
        text_content = m.reply_to_message.text
        
        # Check text length
        if len(text_content) > 50000:
            await m.reply_text("Text too long! Max 50,000 characters")
            return

        msg = await m.reply_text("Uploading text to Catbox...")
        
        # Upload to Catbox
        data = {
            'reqtype': 'paste',
            'userhash': '',
            'paste': text_content
        }
        response = requests.post(CATBOX_URL, data=data)
        
        if response.status_code == 200 and response.text.startswith("http"):
            await msg.edit_text(f"✅ Text uploaded!\n🔗 URL: {response.text}")
        else:
            await msg.edit_text(f"Failed to upload text (Status {response.status_code})")
            
    except Exception as e:
        await m.reply_text(f"Error: {str(e)}")

__PLUGIN__ = "catbox_upload"
__HELP__ = """
**📤 Catbox Uploader**

`/tgm` - Upload media to Catbox (reply to any media)
Supported formats: JPG, PNG, GIF, MP4, WEBM, MOV
Max size: 200MB

`/tgt` - Upload text to Catbox (reply to any text)
Max length: 50,000 characters

The bot will reply with the Catbox URL after upload.
"""
