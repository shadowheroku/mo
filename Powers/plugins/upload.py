from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command(["upload", "tgm"]))
async def bot_api_upload(c: Gojo, m: Message):
    """Upload to Telegram's CDN and get a direct link"""
    if not m.reply_to_message or not m.reply_to_message.media:
        return await m.reply_text("❌ Please reply to a file or media")

    msg = await m.reply_text("📥 Processing your file...")

    try:
        # Send the replied media to bot's own saved messages
        sent = await m.reply_to_message.copy("me")

        # Get file info from Telegram
        file_info = await c.get_file(sent.document.file_id if sent.document else sent.photo.file_id)
        
        # Direct link from Telegram API
        bot_token = c.exported_token  # Some Pyrogram clients store it
        if not bot_token:
            bot_token = "<YOUR_BOT_TOKEN>"  # Put manually if needed

        direct_link = f"https://api.telegram.org/file/bot{bot_token}/{file_info.file_path}"

        await msg.edit_text(
            f"✅ **Uploaded to Telegram CDN**\n"
            f"🔗 Direct Link: `{direct_link}`\n\n"
            f"⚠️ Keep your bot token secret — this link contains it."
        )

    except Exception as e:
        await msg.edit_text(f"❌ Failed: {str(e)}")


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
