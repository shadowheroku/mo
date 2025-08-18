import asyncio
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Tag all members in batches of 5 every 1.5 seconds"""
    if not m.chat.type in ["group", "supergroup"]:
        await m.reply_text("This command only works in groups/supergroups!")
        return

    members = []
    async for member in c.get_chat_members(m.chat.id):
        if not member.user.is_bot and member.user.username:
            members.append(f"@{member.user.username}")

    if not members:
        await m.reply_text("No members to tag in this group!")
        return

    msg = await m.reply_text(f"Tagging all {len(members)} members...")

    # Tag in batches of 5 with 1.5 second delay
    for i in range(0, len(members), 5):
        batch = members[i:i+5]
        mention_text = " ".join(batch)
        await msg.reply_text(mention_text)
        
        if i + 5 < len(members):  # Don't wait after last batch
            await asyncio.sleep(1.5)

@Gojo.on_message(command("atag"))
async def tag_admins(c: Gojo, m: Message):
    """Tag all admins in batches of 5 every 1.5 seconds"""
    if not m.chat.type in ["group", "supergroup"]:
        await m.reply_text("This command only works in groups/supergroups!")
        return

    admins = []
    async for member in c.get_chat_members(m.chat.id, filter="administrators"):
        if not member.user.is_bot and member.user.username:
            admins.append(f"@{member.user.username}")

    if not admins:
        await m.reply_text("No admins to tag in this group!")
        return

    msg = await m.reply_text(f"Tagging {len(admins)} admins...")

    # Tag in batches of 5 with 1.5 second delay
    for i in range(0, len(admins), 5):
        batch = admins[i:i+5]
        mention_text = " ".join(batch)
        await msg.reply_text(mention_text)
        
        if i + 5 < len(admins):  # Don't wait after last batch
            await asyncio.sleep(1.5)

__PLUGIN__ = "member_tagger"
__HELP__ = """
**👥 Member Tagger Plugin**

`/tagall` - Tags all group members (5 at a time with 1.5s delay)  
`/atag` - Tags all group admins (5 at a time with 1.5s delay)

**Note:**  
- Works only in groups/supergroups  
- Skips bot accounts automatically  
- Uses username mentions (@username)
"""
