from html import escape as escape_html
import time
from typing import Dict, List

from pyrogram.enums import ChatMemberStatus as CMS, ChatMembersFilter
from pyrogram.errors import ChatAdminRequired, RightForbidden, RPCError
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import admin_filter, command

def get_readable_time(seconds: int) -> str:
    """Convert seconds to a human-readable time format (D days, HH:MM:SS)."""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")

    return " ".join(time_parts) if time_parts else "0s"

# Store chat admins with type hints
adminlist: Dict[int, List[int]] = {}

# cooldown tracker with type hints
_admin_reload_cooldown: Dict[int, float] = {}

@Gojo.on_message(command(["reload", "admincache", "refresh"]) & admin_filter)
async def reload_admin_cache(c: Gojo, m: Message):
    try:
        now = time.time()
        chat_id = m.chat.id

        # cooldown check
        if chat_id in _admin_reload_cooldown and _admin_reload_cooldown[chat_id] > now:
            left = get_readable_time(int(_admin_reload_cooldown[chat_id] - now))
            return await m.reply_text(f"Please wait {left} before reloading again.")

        # Clear existing admin list for this chat
        adminlist[chat_id] = []

        # Fetch new admin list
        async for member in c.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if member.status in {CMS.ADMINISTRATOR, CMS.OWNER}:
                adminlist[chat_id].append(member.user.id)

        # Set cooldown (3 minutes)
        _admin_reload_cooldown[chat_id] = now + 180  
        
        await m.reply_text("✅ Admin cache updated successfully!")

    except ChatAdminRequired:
        await m.reply_text("❌ I need to be an admin to reload the admin cache.")
    except RightForbidden:
        await m.reply_text("❌ I don't have enough rights to fetch admin list.")
    except RPCError as ef:
        error_msg = f"""Some error occurred while reloading admin cache.

<b>Error:</b> <code>{escape_html(str(ef))}</code>"""
        await m.reply_text(error_msg)
        LOGGER.error(f"Error in admincache reload: {ef}", exc_info=True)
