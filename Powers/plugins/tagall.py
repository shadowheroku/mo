import asyncio
from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message
from typing import List, Dict, Optional

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ================================================
#               CONSTANTS & CONFIG
# ================================================

# Track ongoing tagging sessions
ACTIVE_TAGS: Dict[int, bool] = {}

# Tagging styles with emojis and formatting
TAGALL_STYLES = [
    "📢 **Attention everyone!**\n\n{message}\n\n{mentions}",
    "👋 **Hey everyone!**\n\n{message}\n\n{mentions}",
    "🚨 **Important Notice**\n\n{message}\n\n{mentions}",
    "✨ **Summoning the squad!**\n\n{message}\n\n{mentions}",
    "🔔 **Tag Alert!**\n\n{message}\n\n{mentions}",
    "🌟 **Special Mention**\n\n{message}\n\n{mentions}"
]

ADMIN_STYLE = "🛡 **Admin Call**\n\n{message}\n\n{mentions}"

# Rate limiting configuration
TAG_BATCH_SIZE = 5  # Users per message
TAG_DELAY = 1.5     # Seconds between batches

# ================================================
#               HELPER FUNCTIONS
# ================================================

async def get_mentions(members: List) -> str:
    """Generate mentions string from member list, excluding bots/deleted accounts."""
    return " ".join(
        member.user.mention for member in members 
        if not member.user.is_bot 
        and not member.user.is_deleted
    )

async def send_tag_batches(
    client: Gojo,
    chat_id: int,
    members: List,
    message: str,
    style: str,
    is_admin_tag: bool = False
) -> None:
    """
    Send mentions in controlled batches with delays.
    
    Args:
        client: The Pyrogram client
        chat_id: Target chat ID
        members: List of members to tag
        message: The message to include
        style: Formatting style template
        is_admin_tag: Whether this is an admin-only tag
    """
    batch = []
    total_tagged = 0
    
    for i, member in enumerate(members, 1):
        if chat_id not in ACTIVE_TAGS or not ACTIVE_TAGS[chat_id]:
            break  # Tagging was cancelled

        if not member.user.is_bot and not member.user.is_deleted:
            batch.append(member)

        # Send batch when full or at end of list
        if len(batch) == TAG_BATCH_SIZE or i == len(members):
            if not batch:
                continue
                
            mentions = await get_mentions(batch)
            if mentions:
                tag_text = style.format(
                    message=message or ("📝 No message provided" if not is_admin_tag else "🛡 Admin attention needed"),
                    mentions=mentions
                )
                
                try:
                    await client.send_message(
                        chat_id,
                        tag_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    total_tagged += len(batch)
                    await asyncio.sleep(TAG_DELAY)  # Anti-flood delay
                except Exception as e:
                    LOGGER.error(f"Error sending tag batch: {e}")
                    
            batch.clear()
    
    return total_tagged

# ================================================
#               COMMAND HANDLERS
# ================================================

@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all_members(c: Gojo, m: Message):
    """
    Tag all group members with customizable message.
    Usage: /tagall [message] or reply to a message
    """
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True  # Mark session as active

    # Get message content from command or reply
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = "👋 Hello everyone!"

    try:
        # Collect all non-bot members
        members = [
            member async for member in c.get_chat_members(chat.id)
            if not member.user.is_bot 
            and not member.user.is_deleted
        ]

        if not members:
            await m.reply_text("❌ No active members found to tag.")
            return

        # Start tagging with random style
        style = choice(TAGALL_STYLES)
        total_tagged = await send_tag_batches(c, chat.id, members, base_msg, style)

        if total_tagged:
            await m.reply_text(f"✅ Successfully tagged {total_tagged} members!")
        else:
            await m.reply_text("⚠️ No valid members were tagged.")

    except Exception as e:
        await m.reply_text(f"❌ Error during tagging: {str(e)}")
        LOGGER.error(f"Tagall error: {e}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)  # Clean up session


@Gojo.on_message(command(["atag", "admincall"]) & filters.group)
async def tag_admins_only(c: Gojo, m: Message):
    """
    Tag only group admins.
    Usage: /atag [message] or reply to a message
    """
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True  # Mark session as active

    # Get message content
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = "🛡 Admin attention needed!"

    try:
        # Collect admins only
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
            await m.reply_text("❌ No active admins found to tag.")
            return

        total_tagged = await send_tag_batches(
            c, chat.id, admins, base_msg, ADMIN_STYLE, True
        )

        if total_tagged:
            await m.reply_text(f"✅ Successfully tagged {total_tagged} admins!")
        else:
            await m.reply_text("⚠️ No valid admins were tagged.")

    except Exception as e:
        await m.reply_text(f"❌ Error during admin tagging: {str(e)}")
        LOGGER.error(f"Admin tag error: {e}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)


@Gojo.on_message(command(["cancel"]) & filters.group)
async def cancel_tagging(c: Gojo, m: Message):
    """Cancel an ongoing tagging session in the chat."""
    chat = m.chat
    
    if chat.id in ACTIVE_TAGS and ACTIVE_TAGS[chat.id]:
        ACTIVE_TAGS[chat.id] = False
        await m.reply_text("⏹ Tagging process cancelled successfully.")
    else:
        await m.reply_text("ℹ️ No active tagging process to cancel.")


# ================================================
#               MODULE METADATA
# ================================================

__PLUGIN__ = "tagging"
__alt_name__ = ["tagall", "all", "callall", "atag", "admincall", "cancel"]

__HELP__ = """
**🔔 Tagging Commands**

• `/tagall` [message] - Tag all group members
• `/tagall` (reply) - Tag all with replied message
• `/atag` [message] - Tag only admins  
• `/atag` (reply) - Tag admins with replied message
• `/cancel` - Stop an ongoing tagging process

**Note:** Tags are sent in batches to avoid flooding.
"""
