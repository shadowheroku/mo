import asyncio
from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ================================================
#               CONSTANTS
# ================================================

ACTIVE_TAGS: Dict[int, bool] = {}
MAX_MENTIONS_PER_MESSAGE = 5  # Reduced from 50 to prevent flooding
TAG_DELAY = 2.0  # Increased delay between messages

TAGALL_STYLES = [
    "📢 **Attention everyone!**\n\n{message}\n\n{mentions}",
    "👋 **Hey everyone!**\n\n{message}\n\n{mentions}",
    "🚨 **Important Notice**\n\n{message}\n\n{mentions}",
    "✨ **Summoning the group** ✨\n\n{message}\n\n{mentions}",
    "🔔 **Tag Alert**\n\n{message}\n\n{mentions}"
]

ADMIN_STYLE = "🛡 **Admin Notification**\n\n{message}\n\n{mentions}"

# ================================================
#               HELPER FUNCTIONS
# ================================================

async def format_user_mention(member) -> str:
    """Format user mention with their first name"""
    user = member.user
    if user.is_deleted:
        return f"🗑 Deleted Account ({user.id})"
    
    first_name = user.first_name or ""
    last_name = f" {user.last_name}" if user.last_name else ""
    username = f" (@{user.username})" if user.username else ""
    
    return f"👤 {first_name}{last_name}{username}"

async def send_mentions_batch(
    client: Gojo,
    chat_id: int,
    mentions: List[str],
    base_msg: str,
    style: str,
    is_admin: bool = False
) -> bool:
    """Send a batch of mentions with proper formatting"""
    mentions_text = "\n".join([f"• {m}" for m in mentions])
    full_text = style.format(
        message=base_msg or ("📝 Notification" if not is_admin else "🛡 Admin Attention Needed"),
        mentions=mentions_text
    )
    
    try:
        await client.send_message(
            chat_id,
            full_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Go Back", callback_data="tagall_back")
            ]]) if len(mentions) > 5 else None
        )
        return True
    except Exception as e:
        LOGGER.error(f"Error sending tag batch: {e}")
        return False

# ================================================
#               TAG COMMANDS
# ================================================

@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all_members(c: Gojo, m: Message):
    """Enhanced tagall command with better formatting"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True
    
    # Get message content
    base_msg = (
        m.reply_to_message.text if m.reply_to_message
        else m.text.split(None, 1)[1] if len(m.command) > 1
        else "📢 Group Notification"
    )

    try:
        # Get members with progress indicator
        progress_msg = await m.reply_text("🔄 Collecting members...")
        members = [
            member async for member in c.get_chat_members(chat.id)
            if not member.user.is_bot
        ]

        if not members:
            await progress_msg.edit_text("❌ No active members found!")
            return

        await progress_msg.edit_text(f"✅ Found {len(members)} members. Starting tags...")
        
        # Prepare mentions in batches
        mentions_batch = []
        style = choice(TAGALL_STYLES)
        
        for i, member in enumerate(members, 1):
            if not ACTIVE_TAGS.get(chat.id, False):
                break  # Cancellation check
            
            mention = await format_user_mention(member)
            mentions_batch.append(mention)
            
            # Send batch when full or at end
            if len(mentions_batch) >= MAX_MENTIONS_PER_MESSAGE or i == len(members):
                if mentions_batch:
                    success = await send_mentions_batch(c, chat.id, mentions_batch, base_msg, style)
                    if not success:
                        await m.reply_text("⚠️ Failed to send some tags. Trying again...")
                        await asyncio.sleep(TAG_DELAY * 2)  # Longer delay on failure
                        await send_mentions_batch(c, chat.id, mentions_batch, base_msg, style)
                    
                    mentions_batch = []
                    await asyncio.sleep(TAG_DELAY)

        await progress_msg.edit_text(f"✅ Tagging completed! {len(members)} members notified.")

    except Exception as e:
        await m.reply_text(f"❌ Error: {str(e)}")
        LOGGER.error(f"Tagall error: {e}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

@Gojo.on_message(command(["admintag", "atag"]))
async def tag_admins(c: Gojo, m: Message):
    """Enhanced admin tag with better formatting"""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True
    
    base_msg = (
        m.reply_to_message.text if m.reply_to_message
        else m.text.split(None, 1)[1] if len(m.command) > 1
        else "🛡 Admin Attention Needed"
    )

    try:
        progress_msg = await m.reply_text("🔄 Collecting admins...")
        admins = [
            member async for member in c.get_chat_members(
                chat.id,
                filter=ChatMembersFilter.ADMINISTRATORS
            )
            if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            and not member.user.is_bot
        ]

        if not admins:
            await progress_msg.edit_text("❌ No active admins found!")
            return

        await progress_msg.edit_text(f"✅ Found {len(admins)} admins. Starting tags...")
        
        # Admin mentions are sent all together (usually fewer)
        admin_mentions = [await format_user_mention(admin) for admin in admins]
        await send_mentions_batch(c, chat.id, admin_mentions, base_msg, ADMIN_STYLE, True)
        
        await progress_msg.edit_text(f"✅ Admin tagging completed! {len(admins)} admins notified.")

    except Exception as e:
        await m.reply_text(f"❌ Error: {str(e)}")
        LOGGER.error(f"Admintag error: {e}")
    finally:
        ACTIVE_TAGS.pop(chat.id, None)

# ================================================
#               OTHER COMMANDS
# ================================================

@Gojo.on_message(command(["canceltag", "cancel"]))
async def cancel_tagging(c: Gojo, m: Message):
    """Enhanced cancellation with confirmation"""
    chat = m.chat
    
    if chat.id in ACTIVE_TAGS and ACTIVE_TAGS[chat.id]:
        ACTIVE_TAGS[chat.id] = False
        await m.reply_text(
            "⏹ Tagging process cancelled!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Restart", callback_data="tagall_restart")
            ]])
        )
    else:
        await m.reply_text("ℹ️ No active tagging process to cancel.")

# ================================================
#               MODULE METADATA
# ================================================

__PLUGIN__ = "advanced_tagging"
__alt_name__ = ["tagall", "all", "admintag", "atag", "canceltag"]

__HELP__ = """
**🌟 Advanced Tagging System**

• /tagall [message] - Mention all members with names
• /tagall (reply) - Tag all with replied message
• /atag [message] - Mention only admins with names  
• /atag (reply) - Tag admins with replied message
• /canceltag - Stop ongoing tagging process

**Features:**
- Shows user's full name and username
- Properly formatted mentions
- Progress indicators
- Anti-flood protection
- Smart batch processing
"""
