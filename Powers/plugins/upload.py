import os
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

# Your private channel ID (make bot admin there)
UPLOAD_CHANNEL = -1002800777153  # replace with your channel ID

@Gojo.on_message(command(["upload", "ul"]))
async def tg_channel_upload(c: Gojo, m: Message):
    """Upload files to a private Telegram channel and return a link"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file...")
    file_path = None

    try:
        # Download
        file_path = await m.reply_to_message.download()

        await msg.edit_text("☁️ Uploading to Telegram channel...")
        sent = await c.send_document(
            chat_id=UPLOAD_CHANNEL,
            document=file_path,
            caption=f"Uploaded by {m.from_user.mention}"
        )

        # Telegram public link format
        # For private channel: https://t.me/c/<channel_id_without_-100>/<message_id>
        channel_id_str = str(UPLOAD_CHANNEL).replace("-100", "")
        file_url = f"https://t.me/c/{channel_id_str}/{sent.id}"
        share_url = f"https://t.me/share/url?url={quote(file_url)}"

        await msg.edit_text(
            f"✅ **Uploaded!**\n\n🔗 URL: `{file_url}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Open", url=file_url)],
                [InlineKeyboardButton("📤 Share", url=share_url)]
            ])
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed to upload:\n{str(e)}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)



__PLUGIN__ = "catbox_uploader"
__HELP__ = """
**🐱 Catbox.moe Uploader**
`/upload` or `/tgm` - Upload files to Catbox.moe

✅ **Supported Files:**
- Images (JPEG, PNG, GIF)
- Videos (MP4, WebM, MOV)
- Other files (≤200MB)

❌ **Common Issues:**
- Files >200MB will be rejected
- Some file types may cause HTTP 412 errors
- Server-side issues may temporarily prevent uploads
"""
