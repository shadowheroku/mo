import asyncio
from pyrogram.types import Message
from pyrogram.enums import ChatType, ChatMemberStatus
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Mention all members in batches of 5 with bullet points"""
    try:
        # Check if the command is used in a group
        if m.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await m.reply_text(f"❌ This command only works in groups! (Current type: {m.chat.type}")
        
        # Check if user is admin
        try:
            user = await m.chat.get_member(m.from_user.id)
            if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await m.reply_text("❌ You need to be an admin to use this command.")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check your permissions: {e}")
        
        # Check if message is a reply or has text
        if not m.reply_to_message and len(m.command) == 1:
            return await m.reply_text("𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗈𝗋 𝗉𝗋𝗈𝗏𝗂𝖽𝖾 𝗍𝖾𝗑𝗍 𝗍𝗈 𝗆𝖾𝗇𝗍𝗂𝗈𝗇 𝗈𝗍𝗁𝖾𝗋𝗌!")
        
        # Extract query if provided
        query = ""
        if len(m.command) > 1:
            query = " ".join(m.command[1:])
        elif m.reply_to_message:
            query = m.reply_to_message.text or m.reply_to_message.caption or ""
        
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
        
        # Delete the processing message first
        await processing_msg.delete()
        
        # Send first batch as a new message
        first_batch = member_batches[0]
        tag_text = f"**📢 Mentioning all members**\n\n"
        if query:
            tag_text += f"**Message:** {query}\n\n"
        
        for user in first_batch:
            tag_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
        
        # Send first batch as new message
        first_msg = await c.send_message(
            m.chat.id,
            tag_text,
            disable_web_page_preview=True,
            reply_to_message_id=m.reply_to_message.message_id if m.reply_to_message else m.id
        )
        
        # Send remaining batches as new messages with 1.5 second gap
        for batch in member_batches[1:]:
            batch_text = ""
            for user in batch:
                batch_text += f"• [{user.first_name}](tg://user?id={user.id})\n"
            
            await c.send_message(
                m.chat.id,
                batch_text,
                disable_web_page_preview=True
            )
            await asyncio.sleep(1.5)  # 1.5 second gap between batches
        
        # Send completion message
        await c.send_message(
            m.chat.id,
            "✅ All members tagged successfully!",
            reply_to_message_id=first_msg.id
        )
        
    except Exception as e:
        await m.reply_text(f"⚠️ An unexpected error occurred: {str(e)}")

__PLUGIN__ = "ᴛᴀɢᴀʟʟ"

__HELP__ = """
**👥 ᴀᴅᴠᴀɴᴄᴇᴅ ᴍᴇᴍʙ𝖾𝗋 𝗍𝖺𝗀𝗀𝖾𝗋**

`/tagall` - 𝗍𝖺𝗀𝗌 𝖺𝗅𝗅 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 𝗂𝗇 𝖻𝖺𝗍𝖼𝗁𝖾𝗌
• 5 𝗆𝖾𝗇𝗍𝗂𝗈𝗇𝗌 𝗉𝖾𝗋 𝗆𝖾𝗌𝗌𝖺𝗀𝖾
• 1.5 𝗌𝖾𝖼𝗈𝗇𝖽 𝖽𝖾𝗅𝖺𝗒 𝖻𝖾𝗍𝗐𝖾𝖾𝗇 𝖻𝖺𝗍𝖼𝗁𝖾𝗌
• 𝖻𝗎𝗅𝗅𝖾𝗍 𝗉𝗈𝗂𝗇𝗍 𝖿𝗈𝗋𝗆𝖺𝗍𝗍𝗂𝗇𝗀
• 𝗌𝗎𝗉𝗉𝗈𝗋𝗍𝗌 𝖺𝖽𝖽𝗂𝗇𝗀 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝖺𝖿𝗍𝖾𝗋 𝖼𝗈𝗆𝗆𝖺𝗇𝖽

**𝗋𝖾𝗊𝗎𝗂𝗋𝖾𝗆𝖾𝗇𝗍𝗌:**
- 𝗆𝗎𝗌𝗍 𝖻𝖾 𝗎𝗌𝖾𝖽 𝗂𝗇 𝗀𝗋𝗈𝗎𝗉𝗌/𝗌𝗎𝗉𝖾𝗋𝗀𝗋𝗈𝗎𝗉𝗌
- 𝗎𝗌𝖾𝗋 𝗆𝗎𝗌𝗍 𝖻𝖾 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇
- 𝗀𝗋𝗈𝗎𝗉 𝗆𝗎𝗌𝗍 𝗁𝖺𝗏𝖾 𝗆𝖾𝗆𝖻𝖾𝗋𝗌

**𝗎𝗌𝖺𝗀𝖾:**
`/tagall` - 𝗍𝖺𝗀 𝖺𝗅𝗅 𝗆𝖾𝗆𝖻𝖾𝗋𝗌 (𝗐𝗂𝗅𝗅 𝗌𝗁𝗈𝗐 𝗐𝖺𝗋𝗇𝗂𝗇𝗀)
`/tagall Hello everyone!` - 𝗍𝖺𝗀 𝖺𝗅𝗅 𝗐𝗂𝗍𝗁 𝗆𝖾𝗌𝗌𝖺𝗀𝖾
𝖱𝖾𝗉𝗅𝗒 𝗍𝗈 𝖺 𝗆𝖾𝗌𝗌𝖺𝗀𝖾 𝗐𝗂𝗍𝗁 `/tagall` - 𝗍𝖺𝗀 𝖺𝗅𝗅 𝗐𝗂𝗍𝗁 𝗋𝖾𝗉𝗅𝗂𝖾𝖽 𝗆𝖾𝗌𝗌𝖺𝗀𝖾
"""
