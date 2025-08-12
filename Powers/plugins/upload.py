import requests
import os
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Catbox API URL
CATBOX_URL = "https://catbox.moe/user/api.php"

@Gojo.on_message(command("tgm"))
async def upload_media_to_catbox(c: Gojo, m: Message):
    """Upload media files to Catbox"""
    if not m.reply_to_message or not m.reply_to_message.media:
        await m.reply_text("Please reply to a media file to upload!")
        return

    try:
        # Download the media file
        media_path = await m.reply_to_message.download()
        
        # Upload to Catbox
        files = {'fileToUpload': open(media_path, 'rb')}
        response = requests.post(CATBOX_URL, files=files)
        
        # Clean up downloaded file
        os.remove(media_path)
        
        if response.status_code == 200:
            await m.reply_text(f"Media uploaded to Catbox!\nURL: {response.text}")
        else:
            await m.reply_text(f"Failed to upload media. Status code: {response.status_code}")
            
    except Exception as e:
        await m.reply_text(f"An error occurred: {str(e)}")
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
        
        # Upload to Catbox
        data = {
            'reqtype': 'paste',
            'userhash': '',
            'paste': text_content
        }
        response = requests.post(CATBOX_URL, data=data)
        
        if response.status_code == 200:
            await m.reply_text(f"Text uploaded to Catbox!\nURL: {response.text}")
        else:
            await m.reply_text(f"Failed to upload text. Status code: {response.status_code}")
            
    except Exception as e:
        await m.reply_text(f"An error occurred: {str(e)}")

__PLUGIN__ = "catbox_upload"
__HELP__ = """
**Catbox Upload Commands**

• `/tgm` - Upload replied media file to Catbox
• `/tgt` - Upload replied text to Catbox

Reply to a media file or text message with these commands to upload them to Catbox.
"""
