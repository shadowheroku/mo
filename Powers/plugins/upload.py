import os
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from urllib.parse import quote

@Gojo.on_message(command(["tgm"]))
async def tgm_uploader(c: Gojo, m: Message):
    """Upload a file to Telegram and get direct/public links."""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file to upload!")

    msg = await m.reply_text("📥 Downloading your file…")
    file_path = None

    try:
        # Download file locally
        file_path = await m.reply_to_message.download()

        await msg.edit_text("☁️ Uploading to Telegram…")
        # Send to Telegram (your own uploads channel or saved messages)
        up_msg = await c.send_document(
            "me",  # change to your uploads channel ID if needed
            document=file_path,
            caption=f"Uploaded from {m.from_user.mention}"
        )

        # Direct CDN link
        direct_link = await c.get_file_url(up_msg.document.file_id)

        # Public Telegram view link (share link)
        share_url = f"https://t.me/share/url?url={quote(direct_link)}"

        buttons = [
            [InlineKeyboardButton("📥 Direct Download", url=direct_link)],
            [InlineKeyboardButton("📤 Share", url=share_url)]
        ]

        await msg.edit_text(
            f"✅ **Uploaded to Telegram!**\n\n"
            f"📥 Direct Link: `{direct_link}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await msg.edit_text(f"❌ Upload failed:\n{e}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

__PLUGIN__ = "tgm_uploader"
__HELP__ = """
**📤 Telegram Uploader**
`/tgm` — Upload a file to Telegram and get a direct CDN link.

✅ Fast, no size limits (up to Telegram’s 2 GB/4 GB limit)
✅ Works from any network/IP
✅ Direct file link + share button
"""
