import asyncio
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from pyrogram.errors import PeerIdInvalid, ChannelInvalid

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Tag all members in batches of 5 every 1.5 seconds"""
    try:
        # Check if in group/supergroup
        if not m.chat or m.chat.type not in (Chat.Type.GROUP, Chat.Type.SUPERGROUP):
            return await m.reply_text("❌ This command only works in groups/supergroups!")

        # Check if bot has permissions
        try:
            bot_member = await m.chat.get_member("me")
            if not getattr(bot_member, "privileges", None) or not bot_member.privileges.can_mention:
                return await m.reply_text("⚠️ I don't have permission to mention members here!")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check permissions: {e}")

        msg = await m.reply_text("🔍 Fetching members...")
        
        members = []
        async for member in c.get_chat_members(m.chat.id):
            if not member.user.is_bot and (member.user.username or member.user.id):
                mention = f"@{member.user.username}" if member.user.username else f"[{member.user.first_name}](tg://user?id={member.user.id})"
                members.append(mention)

        if not members:
            return await msg.edit_text("❌ No taggable members found in this group!")

        await msg.edit_text(f"⏳ Tagging {len(members)} members...")

        # Tag in batches of 5 with 1.5 second delay
        for i in range(0, len(members), 5):
            batch = members[i:i+5]
            try:
                await m.reply_text(" ".join(batch))
            except Exception as e:
                await msg.edit_text(f"⚠️ Error sending mentions: {e}")
                return
            
            if i + 5 < len(members):  # Don't wait after last batch
                await asyncio.sleep(1.5)

    except (PeerIdInvalid, ChannelInvalid):
        await m.reply_text("❌ Invalid chat or I'm not a member!")
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

@Gojo.on_message(command("atag"))
async def tag_admins(c: Gojo, m: Message):
    """Tag all admins in batches of 5 every 1.5 seconds"""
    try:
        # Check if in group/supergroup
        if not m.chat or m.chat.type not in ("group", "supergroup"):
            return await m.reply_text("❌ This command only works in groups/supergroups!")

        # Check if bot has permissions
        try:
            bot_member = await m.chat.get_member("me")
            if not getattr(bot_member, "privileges", None) or not bot_member.privileges.can_mention:
                return await m.reply_text("⚠️ I don't have permission to mention members here!")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check permissions: {e}")

        msg = await m.reply_text("🔍 Fetching admins...")
        
        admins = []
        async for member in c.get_chat_members(m.chat.id, filter="administrators"):
            if not member.user.is_bot and (member.user.username or member.user.id):
                mention = f"@{member.user.username}" if member.user.username else f"[{member.user.first_name}](tg://user?id={member.user.id})"
                admins.append(mention)

        if not admins:
            return await msg.edit_text("❌ No taggable admins found in this group!")

        await msg.edit_text(f"⏳ Tagging {len(admins)} admins...")

        # Tag in batches of 5 with 1.5 second delay
        for i in range(0, len(admins), 5):
            batch = admins[i:i+5]
            try:
                await m.reply_text(" ".join(batch))
            except Exception as e:
                await msg.edit_text(f"⚠️ Error sending mentions: {e}")
                return
            
            if i + 5 < len(admins):  # Don't wait after last batch
                await asyncio.sleep(1.5)

    except (PeerIdInvalid, ChannelInvalid):
        await m.reply_text("❌ Invalid chat or I'm not a member!")
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

__PLUGIN__ = "member_tagger"
__HELP__ = """
**👥 Member Tagger Plugin**

`/tagall` - Tags all group members (5 at a time with 1.5s delay)  
`/atag` - Tags all group admins (5 at a time with 1.5s delay)

**Features:**
- Mentions users by username if available, otherwise by ID
- Checks bot permissions before tagging
- Handles large groups efficiently
- Works in both groups and supergroups

**Requirements:**
- Bot must have mention permissions
- Group must have at least one taggable member/admin
"""
