import asyncio
from pyrogram.types import Message
from pyrogram.enums import ChatType
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Mention all members in batches of 5 every 1.5 seconds"""
    try:
        # Check if the command is used in a group
        if m.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await m.reply_text(f"❌ This command only works in groups! (Current type: {m.chat.type})")
        
        # Check if the bot has permission to mention users
        try:
            bot_member = await m.chat.get_member((await c.get_me()).id)
            if not getattr(bot_member, 'can_mention_all', False):
                return await m.reply_text("⚠️ I don't have permission to mention all users!")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check my permissions: {e}")
        
        # Send initial processing message
        processing_msg = await m.reply_text("🔄 Preparing to mention members...")
        
        # Fetch all members
        members = []
        try:
            async for member in c.get_chat_members(m.chat.id):
                if not member.user.is_bot and not member.user.is_deleted:
                    # Format as proper mention
                    if member.user.username:
                        mention = f"@{member.user.username}"
                    else:
                        mention = f"[{member.user.first_name}](tg://user?id={member.user.id})"
                    members.append(mention)
        except Exception as e:
            return await processing_msg.edit_text(f"⚠️ Failed to fetch members: {e}")
        
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
                    disable_web_page_preview=True
                )
                if i + 5 < len(members):  # Only sleep if there are more batches
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
