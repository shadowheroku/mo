from html import escape as escape_html
import time

from pyrogram.enums import ChatMemberStatus as CMS, ChatMembersFilter
from pyrogram.errors import ChatAdminRequired, RightForbidden, RPCError
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import admin_filter, command
from Powers.utils.string import get_readable_time
from config import adminlist  # Assuming you have an adminlist dict like in ERISMUSIC

# cooldown tracker
_admin_reload_cooldown = {}


@Gojo.on_message(command(["reload", "admincache", "refresh"]) & admin_filter)
async def reload_admin_cache(c: Gojo, m: Message):
    try:
        now = time.time()
        chat_id = m.chat.id

        # cooldown check
        if chat_id in _admin_reload_cooldown and _admin_reload_cooldown[chat_id] > now:
            left = get_readable_time(int(_admin_reload_cooldown[chat_id] - now))
            return await m.reply_text(f"Please wait {left} before reloading again.")

        adminlist[chat_id] = []

        async for member in c.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if member.status in {CMS.ADMINISTRATOR, CMS.OWNER}:
                adminlist[chat_id].append(member.user.id)

        _admin_reload_cooldown[chat_id] = now + 180  # 3 minutes cooldown
        await m.reply_text("Admin cache updated successfully.")

    except ChatAdminRequired:
        await m.reply_text("I need to be an admin to reload the admin cache.")
    except RightForbidden:
        await m.reply_text("I don't have enough rights to fetch admin list.")
    except RPCError as ef:
        await m.reply_text(
            f"""Some error occurred while reloading admin cache.

<b>Error:</b> <code>{escape_html(str(ef))}</code>"""
        )
        LOGGER.error(ef)
