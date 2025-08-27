import asyncio
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Mention all members in batches of 5 every 1.5 seconds"""
    try:
        chat_type = getattr(m.chat, 'type', '').lower()
        if chat_type not in ('group', 'supergroup'):
            return await m.reply_text(f"❌ This command only works in groups! (Current type: {chat_type})")

        # Check bot mention permissions
        try:
            me = await c.get_me()
            bot_member = await m.chat.get_member(me.id)
            if not getattr(bot_member, 'can_mention', True):
                return await m.reply_text("⚠️ I don't have permission to mention users here!")
        except Exception:
            return await m.reply_text("⚠️ Failed to check my permissions!")

        processing_msg = await m.reply_text("🔄 Preparing to mention members...")

        # Fetch all members
        members = []
        try:
            async for member in c.get_chat_members(m.chat.id):
                if not member.user.is_bot:
                    # Format as proper mention
                    mention = f"[{member.user.first_name}](tg://user?id={member.user.id})"
                    members.append(mention)
        except Exception:
            return await processing_msg.edit_text("⚠️ Failed to fetch members!")

        if not members:
            return await processing_msg.edit_text("❌ No members available to mention!")

        await processing_msg.edit_text(f"⏳ Mentioning {len(members)} members in batches of 5...")

        # Send in batches of 5 with 1.5s delay
        for i in range(0, len(members), 5):
            batch = members[i:i+5]
            try:
                await c.send_message(
                    chat_id=m.chat.id,
                    text=" ".join(batch),
                    reply_to_message_id=m.id,
                    parse_mode="markdown",
                    disable_web_page_preview=True
                )
                if i + 5 < len(members):
                    await asyncio.sleep(1.5)
            except Exception as e:
                await processing_msg.edit_text(f"⚠️ Error while mentioning: {e}")
                return

        await processing_msg.edit_text("✅ All members mentioned successfully!")

    except Exception as e:
        await m.reply_text(f"⚠️ An unexpected error occurred: {str(e)}")

__PLUGIN__ = "ᴛᴀɢᴀʟʟ"

__HELP__ = """
**👥 ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴇᴍʙᴇʀ ᴛᴀɢɢᴇʀ**

`/tagall` - ᴛᴀɢs ᴀʟʟ ᴍᴇᴍʙᴇʀs ɪɴ ʙᴀᴛᴄʜᴇs
• 5 ᴍᴇɴᴛɪᴏɴs ᴘᴇʀ ᴍᴇssᴀɢᴇ
• 1.5 sᴇᴄᴏɴᴅ ᴅᴇʟᴀʏ ʙᴇᴛᴡᴇᴇɴ ʙᴀᴛᴄʜᴇs
• sᴍᴀʀᴛ ᴍᴇɴᴛɪᴏɴ ʜᴀɴᴅʟɪɴɢ (ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɪᴅ)

**ʀᴇǫᴜɪʀᴇᴍᴇɴᴛs:**
- ᴍᴜsᴛ ʙᴇ ᴜsᴇᴅ ɪɴ ɢʀᴏᴜᴘs/sᴜᴘᴇʀɢʀᴏᴜᴘs
- ʙᴏᴛ ɴᴇᴇᴅs ᴍᴇɴᴛɪᴏɴ ᴘᴇʀᴍɪssɪᴏɴs
- ɢʀᴏᴜᴘ ᴍᴜsᴛ ʜᴀᴠᴇ ᴍᴇᴍʙᴇʀs
"""

