import asyncio
from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message
from typing import List, Dict

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ================================================
#               CONSTANTS
# ================================================

ACTIVE_TAGS: Dict[int, bool] = {}  # Track active tagging sessions

TAG_STYLES = [
    "📢 **Attention everyone!**\n\n{message}\n\n{mentions}",
    "👋 **Hello everyone!**\n\n{message}\n\n{mentions}",
    "🌟 **Special mention!**\n\n{message}\n\n{mentions}",
    "🔔 **Tag alert!**\n\n{message}\n\n{mentions}"
]

ADMIN_STYLE = "🛡 **Admin notice!**\n\n{message}\n\n{mentions}"

# ================================================
#               HELPER FUNCTIONS
# ================================================

async def clean_mention(member) -> str:
    """Generate clean mention without extra spaces"""
    user = member.user
    if user.is_deleted:
        return f"@{user.id}"  # Fallback for deleted accounts
    return user.mention

async def format_mentions(members: List) -> str:
    """Format mentions with proper spacing and line breaks"""
    mentions = []
    for member in members:
        if not member.user.is_bot:  # Skip bots
            mention = await clean_mention(member)
            mentions.append(mention)
    
    # Organize mentions with line breaks for readability
    return "\n".join([f"• {m}" for m in mentions]) if mentions else ""

# ================================================
#               TAG COMMANDS
# ================================================

@Gojo.on_message(command(["tagall", "all"]) & filters.group)
async def tag_all_members(c: Gojo, m: Message):
    """Tag all group members with clean formatting"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True
    
    # Get message content
    base_msg = (
        m.reply_to_message.text if m.reply_to_message
        else m.text.split(None, 1)[1] if len(m.command) > 1
        else "Hello everyone! 👋"
    )

    try:
        # Get all non-bot members
        members = [
            member async for member in c.get_chat_members(chat.id)
            if not member.user.is_bot
        ]

        if not members:
            return await m.reply_text("No active members to tag!")

        # Format mentions cleanly
        mentions = await format_mentions(members)
        if not mentions:
            return await m.reply_text("No valid members to tag!")

        # Send with random style
        style = choice(TAG_STYLES)
        await m.reply_text(
            style.format(message=base_msg, mentions=mentions),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await m.reply_text(f"Error: {str(e)}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

@Gojo.on_message(command(["admintag", "atag"]) & filters.group)
async def tag_admins(c: Gojo, m: Message):
    """Tag only admins with clean formatting"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True
    
    base_msg = (
        m.reply_to_message.text if m.reply_to_message
        else m.text.split(None, 1)[1] if len(m.command) > 1
        else "Admin attention needed!"
    )

    try:
        admins = [
            member async for member in c.get_chat_members(
                chat.id,
                filter=ChatMembersFilter.ADMINISTRATORS
            )
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            and not member.user.is_bot
        ]

        if not admins:
            return await m.reply_text("No active admins to tag!")

        mentions = await format_mentions(admins)
        await m.reply_text(
            ADMIN_STYLE.format(message=base_msg, mentions=mentions),
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        await m.reply_text(f"Error: {str(e)}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

# ================================================
#               MODULE INFO
# ================================================

__PLUGIN__ = "tagging"
__alt_name__ = ["tagall", "all", "admintag", "atag"]

__HELP__ = """
**Clean Tagging Commands**

• /tagall [message] - Tag all members (formatted neatly)
• /tagall (reply) - Tag all with replied message
• /atag [message] - Tag only admins  
• /atag (reply) - Tag admins with replied message

**Features:**
- Clean, readable mentions
- Skips bots automatically
- Proper message formatting
- Fallback for deleted accounts
"""
