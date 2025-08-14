
import requests
import os
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo  # Gojo client

API_URL = "https://file.io"

@Gojo.on_message(filters.command(["upload", "ul"]))
async def upload_file(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply_text("⚠️ Reply to a file to upload.")

    file_path = await message.reply_to_message.download()
    await message.reply_text("⏳ Uploading file to File.io...")

    try:
        with open(file_path, "rb") as f:
            response = requests.post(API_URL, files={"file": f})
        os.remove(file_path)

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                await message.reply_text(f"✅ Uploaded successfully!\n🔗 {data['link']}")
            else:
                await message.reply_text(f"❌ Upload failed: {data.get('error', 'Unknown error')}")
        else:
            await message.reply_text(f"❌ HTTP Error {response.status_code}")

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "tgm_uploader"
__HELP__ = """
**📤 Telegram Uploader**
`/tgm` — Upload a file to Telegram and get a direct CDN link.

✅ Fast, no size limits (up to Telegram’s 2 GB/4 GB limit)
✅ Works from any network/IP
✅ Direct file link + share button
"""
