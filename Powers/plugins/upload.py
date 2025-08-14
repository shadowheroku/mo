import os
import mimetypes
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

TIMEOUT = 60
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB

# ===================== transfer.sh =====================
@Gojo.on_message(command(["transfer", "ts"]))
async def transfer_uploader(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file…")
    file_path = None
    try:
        file_path = await m.reply_to_message.download()
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({size//(1024*1024)} MB > 10 GB limit)")

        filename = os.path.basename(file_path)
        await msg.edit_text("☁️ Uploading to transfer.sh…")
        with open(file_path, "rb") as f:
            res = requests.put(f"https://transfer.sh/{filename}", data=f, timeout=TIMEOUT)

        if res.status_code != 200:
            raise ValueError(f"HTTP Error {res.status_code}: {res.text}")

        link = res.text.strip()
        share_url = f"https://t.me/share/url?url={quote(link)}"
        buttons = [
            [InlineKeyboardButton("🌐 Open", url=link)],
            [InlineKeyboardButton("📤 Share", url=share_url)]
        ]
        await msg.edit_text(
            f"✅ **Uploaded to transfer.sh!**\n\n🔗 `{link}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ===================== 0x0.st =====================
@Gojo.on_message(command(["0x0", "0x0st"]))
async def oxo_uploader(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file…")
    file_path = None
    try:
        file_path = await m.reply_to_message.download()
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({size//(1024*1024)} MB > 10 GB limit)")

        await msg.edit_text("☁️ Uploading to 0x0.st…")
        with open(file_path, "rb") as f:
            res = requests.post("https://0x0.st", files={"file": f}, timeout=TIMEOUT)

        if res.status_code != 200:
            raise ValueError(f"HTTP Error {res.status_code}: {res.text}")

        link = res.text.strip()
        share_url = f"https://t.me/share/url?url={quote(link)}"
        buttons = [
            [InlineKeyboardButton("🌐 Open", url=link)],
            [InlineKeyboardButton("📤 Share", url=share_url)]
        ]
        await msg.edit_text(
            f"✅ **Uploaded to 0x0.st!**\n\n🔗 `{link}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "file_uploaders"
__HELP__ = """
**📤 File Uploaders**
`/transfer` or `/ts` - Upload file to transfer.sh (14 days retention)  
`/0x0` or `/0x0st` - Upload file to 0x0.st (short permanent link)  

✅ Any file type (≤10 GB)  
✅ Direct links  
"""
