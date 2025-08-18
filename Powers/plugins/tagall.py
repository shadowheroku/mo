import asyncio
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from pyrogram.errors import PeerIdInvalid, ChannelInvalid

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Tag all members in batches of 5 every 1.5 seconds"""
    try:
        # Debug chat type
        print(f"Debug - Chat Type: {getattr(m.chat, 'type', 'UNKNOWN')}")  # Debug line
        
        # Improved chat type checking
        chat_type = getattr(m.chat, 'type', '').lower()
        if chat_type not in ('group', 'supergroup'):
            return await m.reply_text(f"❌ This command only works in groups! (Current type: {chat_type})")

        # Check bot permissions
        try:
            me = await c.get_me()
            bot_member = await m.chat.get_member(me.id)
            if not getattr(bot_member, 'can_mention', True):
                return await m.reply_text("⚠️ I don't have mention permissions here!")
        except Exception as e:
            print(f"Permission check error: {e}")  # Debug line
            return await m.reply_text("⚠️ Failed to check my permissions!")

        processing_msg = await m.reply_text("🔄 Preparing to tag members...")
        
        members = []
        try:
            async for member in c.get_chat_members(m.chat.id):
                if not member.user.is_bot:
                    if member.user.username:
                        mention = f"@{member.user.username}"
                    else:
                        mention = f"[{member.user.first_name}](tg://user?id={member.user.id})"
                    members.append(mention)
        except Exception as e:
            print(f"Member fetch error: {e}")  # Debug line
            return await processing_msg.edit_text("⚠️ Failed to fetch members!")

        if not members:
            return await processing_msg.edit_text("❌ No members available to tag!")

        await processing_msg.edit_text(f"⏳ Tagging {len(members)} members...")

        # Tag in batches with delay
        for i in range(0, len(members), 5):
            batch = members[i:i+5]
            try:
                await c.send_message(
                    m.chat.id,
                    " ".join(batch),
                    reply_to_message_id=m.id
                )
                if i + 5 < len(members):
                    await asyncio.sleep(1.5)
            except Exception as e:
                print(f"Tagging error: {e}")  # Debug line
                await processing_msg.edit_text(f"⚠️ Tagging interrupted: {e}")
                return

        await processing_msg.edit_text("✅ All members tagged successfully!")

    except Exception as e:
        print(f"General error: {e}")  # Debug line
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

__PLUGIN__ = "member_tagger"
__HELP__ = """
**👥 Advanced Member Tagger**

`/tagall` - Tags all members in batches
• 5 mentions per message
• 1.5 second delay between batches
• Smart mention handling (username or ID)

**Requirements:**
- Must be used in groups/supergroups
- Bot needs mention permissions
- Group must have members
"""
