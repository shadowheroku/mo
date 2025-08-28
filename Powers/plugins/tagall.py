import asyncio
from pyrogram.types import Message
from pyrogram.enums import ChatType
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Mention all members in batches of 5 with bullet points"""
    try:
        # Check if the command is used in a group
        if m.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await m.reply_text(f"❌ This command only works in groups! (Current type: {m.chat.type})")
        
        # Check if user is admin
        try:
            user = await m.chat.get_member(m.from_user.id)
            if user.status not in ["administrator", "creator"]:
                return await m.reply_text("❌ You need to be an admin to use this command.")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check your permissions: {e}")
        
        # Extract query if provided
        query = ""
        if len(m.command) > 1:
            query = " ".join(m.command[1:])
        
        # Send initial processing message
        processing_msg = await m.reply_text("🔄 Tagging all members...")
        
        # Fetch all members
        members = []
        try:
            async for member in c.get_chat_members(m.chat.id):
                if not member.user.is_bot and not member.user.is_deleted:
                    members.append(member.user)
        except Exception as e:
            return await processing_msg.edit_text(f"⚠️ Failed to fetch members: {e}")
        
        if not members:
            return await processing_msg.edit_text("❌ No members available to tag!")
        
        # Create batches of 5 members
        batch_size = 5
        member_batches = [members[i:i + batch_size] for i in range(0, len(members), batch_size)]
        
        # Send initial message with first batch
        first_batch = member_batches[0]
        tag_text = f"**📢 Mentioning all members**\n\n"
        if query:
            tag_text += f"**Message:** {query}\n\n"
        
        for user in first_batch:
            tag_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
        
        # Edit the processing message with the first batch
        await processing_msg.edit_text(tag_text, disable_web_page_preview=True)
        
        # Send remaining batches as new messages
        for batch in member_batches[1:]:
            batch_text = ""
            for user in batch:
                batch_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            
            await c.send_message(
                m.chat.id,
                batch_text,
                disable_web_page_preview=True,
                reply_to_message_id=m.id
            )
            await asyncio.sleep(1.5)  # Avoid rate limits
        
        await processing_msg.edit_text("✅ All members tagged successfully!")
        
    except Exception as e:
        await m.reply_text(f"⚠️ An unexpected error occurred: {str(e)}")

__PLUGIN__ = "ᴛᴀɢᴀʟʟ"

__HELP__ = """
**👥 ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴇᴍʙᴇʀ ᴛᴀɢɢᴇʀ**

`/tagall` - ᴛᴀɢs ᴀʟʟ ᴍᴇᴍʙᴇʀs ɪɴ ʙᴀᴛᴄʜᴇs
• 5 ᴍᴇɴᴛɪᴏɴs ᴘᴇʀ ᴍᴇssᴀɢᴇ
• 1.5 sᴇᴄᴏɴᴅ ᴅᴇʟᴀʏ ʙᴇᴛᴡᴇᴇɴ ʙᴀᴛᴄʜᴇs
• ʙᴜʟʟᴇᴛ ᴘᴏɪɴᴛ ғᴏʀᴍᴀᴛᴛɪɴɢ
• sᴜᴘᴘᴏʀᴛs ᴀᴅᴅɪɴɢ ᴀ ᴍᴇssᴀɢᴇ ᴀғᴛᴇʀ ᴄᴏᴍᴍᴀɴᴅ

**ʀᴇǫᴜɪʀᴇᴍᴇɴᴛs:**
- ᴍᴜsᴛ ʙᴇ ᴜsᴇᴅ ɪɴ ɢʀᴏᴜᴘs/sᴜᴘᴇʀɢʀᴏᴜᴘs
- ᴜsᴇʀ ᴍᴜsᴛ ʙᴇ ᴀɴ ᴀᴅᴍɪɴ
- ɢʀᴏᴜᴘ ᴍᴜsᴛ ʜᴀᴠᴇ ᴍᴇᴍʙᴇʀs

**ᴜsᴀɢᴇ:**
`/tagall` - ᴛᴀɢ ᴀʟʟ ᴍᴇᴍʙᴇʀs
`/tagall Hello everyone!` - ᴛᴀɢ ᴀʟʟ ᴡɪᴛʜ ᴍᴇssᴀɢᴇ
"""
