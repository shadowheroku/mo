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
MAX_MESSAGE_LENGTH = 4096  # Telegram's maximum message length
MENTIONS_PER_MESSAGE = 50  # Max mentions per message to avoid hitting length limit

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

async def format_mentions(members: List) -> List[str]:
    """Format mentions into chunks that won't exceed message limits"""
    mentions_chunks = []
    current_chunk = []
    
    for member in members:
        if not member.user.is_bot:  # Skip bots
            mention = await clean_mention(member)
            current_chunk.append(f"• {mention}")
            
            # Start new chunk when reaching limit
            if len(current_chunk) >= MENTIONS_PER_MESSAGE:
                mentions_chunks.append("\n".join(current_chunk))
                current_chunk = []
    
    # Add any remaining mentions
    if current_chunk:
        mentions_chunks.append("\n".join(current_chunk))
    
    return mentions_chunks

async def safe_send_message(client, chat_id, text):
    """Send message with length checking"""
    if len(text) > MAX_MESSAGE_LENGTH:
        # Split message if too long
        parts = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        for part in parts:
            await client.send_message(chat_id, part, parse_mode=ParseMode.MARKDOWN)
            await asyncio.sleep(1)  # Anti-flood delay
    else:
        await client.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)

# ================================================
#               TAG COMMANDS
# ================================================

@Gojo.on_message(command(["tagall", "all"]) & filters.group)
async def tag_all_members(c: Gojo, m: Message):
    """Tag all group members with clean formatting and length checks"""
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

        # Format mentions into manageable chunks
        mentions_chunks = await format_mentions(members)
        if not mentions_chunks:
            return await m.reply_text("No valid members to tag!")

        # Send initial message
        style = choice(TAG_STYLES)
        header = style.split("{mentions}")[0].format(message=base_msg)
        await m.reply_text(header, parse_mode=ParseMode.MARKDOWN)

        # Send mentions in chunks
        for chunk in mentions_chunks:
            if not ACTIVE_TAGS.get(chat.id, False):
                break  # Stop if tagging was cancelled
            
            await safe_send_message(c, chat.id, chunk)
            await asyncio.sleep(1)  # Anti-flood delay

    except Exception as e:
        await m.reply_text(f"Error: {str(e)}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

@Gojo.on_message(command(["admintag", "atag"]) & filters.group)
async def tag_admins(c: Gojo, m: Message):
    """Tag only admins with clean formatting and length checks"""
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

        # Format mentions into manageable chunks
        mentions_chunks = await format_mentions(admins)
        
        # Send initial message
        header = ADMIN_STYLE.split("{mentions}")[0].format(message=base_msg)
        await m.reply_text(header, parse_mode=ParseMode.MARKDOWN)

        # Send mentions in chunks
        for chunk in mentions_chunks:
            if not ACTIVE_TAGS.get(chat.id, False):
                break  # Stop if tagging was cancelled
            
            await safe_send_message(c, chat.id, chunk)
            await asyncio.sleep(1)  # Anti-flood delay

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
**Improved Tagging Commands**

• /tagall [message] - Tag all members (with smart message splitting)
• /tagall (reply) - Tag all with replied message
• /atag [message] - Tag only admins  
• /atag (reply) - Tag admins with replied message

**Features:**
- Automatic handling of large groups
- Clean, readable mentions
- Message length protection
- Rate limiting to prevent flooding
"""
