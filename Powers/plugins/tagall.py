import asyncio
from random import choice
from typing import List, Optional

from pyrogram import filters
from pyrogram.enums import ParseMode as PM, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message, ChatMember

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Track ongoing tagging sessions
ACTIVE_TAGS = {}

# Tagging styles with more variety
TAGALL_STYLES = [
    "🔥 Attention everyone!\n\n{msg}\n\n{mentions}",
    "👋 Hey everyone! Check this out:\n\n{msg}\n\n{mentions}",
    "🚨 IMPORTANT NOTICE 🚨\n\n{msg}\n\n{mentions}",
    "✨ Summoning all members ✨\n\n{msg}\n\n{mentions}",
    "📢 Announcement for everyone:\n\n{msg}\n\n{mentions}",
    "🌟 Special mention for:\n\n{msg}\n\n{mentions}",
    "📣 Group notification:\n\n{msg}\n\n{mentions}",
    "👀 Heads up everyone!\n\n{msg}\n\n{mentions}",
    "💬 Group message:\n\n{msg}\n\n{mentions}",
    "🎉 Let's all see this!\n\n{msg}\n\n{mentions}"
]

ADMIN_STYLES = [
    "🛡 Admin attention needed:\n\n{msg}\n\n{mentions}",
    "🔐 Admin notification:\n\n{msg}\n\n{mentions}",
    "⚙️ Admin team assemble:\n\n{msg}\n\n{mentions}",
    "👨‍💻 Calling all admins:\n\n{msg}\n\n{mentions}",
    "🛠 Admin assistance required:\n\n{msg}\n\n{mentions}"
]

class TaggingSession:
    """Class to manage tagging sessions with more control"""
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.is_active = True
        self.last_batch_sent = 0
        
    def cancel(self):
        """Cancel the tagging session"""
        self.is_active = False
        
    def should_continue(self) -> bool:
        """Check if tagging should continue"""
        return self.is_active

async def get_mentions(members: List[ChatMember]) -> str:
    """Generate mentions string from chat members"""
    return " ".join(
        member.user.mention for member in members 
        if not member.user.is_bot 
        and not member.user.is_deleted
    )

async def send_tag_batch(
    client: Gojo,
    chat_id: int,
    members: List[ChatMember],
    base_msg: str,
    style: str,
    batch_size: int = 5,
    delay: float = 1.5
) -> None:
    """
    Send mentions in batches with delay
    Args:
        batch_size: Number of users per batch
        delay: Seconds to wait between batches
    """
    for i in range(0, len(members), batch_size):
        batch = members[i:i + batch_size]
        
        # Check if tagging was cancelled
        if chat_id not in ACTIVE_TAGS or not ACTIVE_TAGS[chat_id].should_continue():
            break
            
        mentions = await get_mentions(batch)
        if not mentions:
            continue
            
        text = style.format(msg=base_msg, mentions=mentions)
        await client.send_message(
            chat_id,
            text,
            parse_mode=PM.MARKDOWN,
            disable_web_page_preview=True
        )
        await asyncio.sleep(delay)

async def get_message_content(m: Message) -> str:
    """Extract message content from command or reply"""
    if m.reply_to_message:
        return m.reply_to_message.text or m.reply_to_message.caption or ""
    return m.text.split(None, 1)[1] if len(m.command) > 1 else ""

@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all_members(c: Gojo, m: Message):
    """Tag all members in the group with stylish message"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = TaggingSession(chat.id)
    
    try:
        base_msg = await get_message_content(m)
        members = [
            member async for member in c.get_chat_members(chat.id)
            if not member.user.is_bot
            and not member.user.is_deleted
        ]
        
        if not members:
            return await m.reply_text("No valid members found to tag.")
            
        style = choice(TAGALL_STYLES)
        await m.reply_text(f"🚀 Starting to tag {len(members)} members...")
        await send_tag_batch(c, chat.id, members, base_msg, style)
        
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {str(e)}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

@Gojo.on_message(command(["atag", "admincall", "admins"]) & filters.group)
async def tag_admins_only(c: Gojo, m: Message):
    """Tag only admins in the group"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = TaggingSession(chat.id)
    
    try:
        base_msg = await get_message_content(m)
        admins = [
            member async for member in c.get_chat_members(
                chat.id,
                filter=ChatMembersFilter.ADMINISTRATORS
            )
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            and not member.user.is_bot
            and not member.user.is_deleted
        ]
        
        if not admins:
            return await m.reply_text("No active admins found to tag.")
            
        style = choice(ADMIN_STYLES)
        await m.reply_text(f"🛡 Starting to tag {len(admins)} admins...")
        await send_tag_batch(c, chat.id, admins, base_msg, style)
        
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {str(e)}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

@Gojo.on_message(command(["ctag", "canceltag", "stop"]) & filters.group)
async def cancel_tagging_process(c: Gojo, m: Message):
    """Cancel ongoing tagging process"""
    chat = m.chat
    if chat.id in ACTIVE_TAGS:
        ACTIVE_TAGS[chat.id].cancel()
        await m.reply_text("⏹ Tagging process cancelled successfully.")
    else:
        await m.reply_text("❌ No active tagging process to cancel.")

__PLUGIN__ = "tagging_tools"
__HELP__ = """
✪ **Tagging Tools** ✪

• `/tagall` [text] - Tag all members (reply to a message to use its content)
• `/atag` [text] - Tag only admins
• `/ctag` - Cancel ongoing tagging process

⚙️ **Features:**
- Mentions in batches to avoid flooding
- Stylish notification templates
- Safe mentions (skips bots/deleted accounts)
- Cancellable operations
"""

__alt_name__ = [
    "tagall", 
    "all", 
    "callall", 
    "atag", 
    "admincall", 
    "admins",
    "ctag",
    "canceltag",
    "stop"
]

_DISABLE_CMDS_ = __alt_name__
