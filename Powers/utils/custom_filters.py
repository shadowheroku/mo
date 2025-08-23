# custom_filters.py (Pyrogram v2 compatible)

from __future__ import annotations

from re import compile as compile_re
from re import escape as re_escape
from shlex import split
from typing import List, Union, Optional

from pyrogram.enums import ChatMemberStatus as CMS, ChatType
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.filters import create
from pyrogram.types import CallbackQuery, ChatJoinRequest, Message

from Powers import OWNER_ID, PREFIX_HANDLER
from Powers.bot_class import Gojo
from Powers.database.afk_db import AFK
from Powers.database.approve_db import Approve
from Powers.database.autojoin_db import AUTOJOIN
from Powers.database.captcha_db import CAPTCHA
from Powers.database.disable_db import Disabling
from Powers.database.flood_db import Floods
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload


# ---------- Helpers ----------

def _compile_cmd_regex(prefixes: List[str], bot_username: str) -> object:
    # ^([!/.])(cmd)(@bot)?(?:\s|$)(.*)
    return compile_re(
        r"^[{prefix}](\w+)(?:@{bot})?(?:\s|$)(.*)".format(
            prefix="|".join(re_escape(p) for p in prefixes),
            bot=re_escape(bot_username or "")
        ),
        flags=0
    )


async def _get_user_status(m: Message) -> Optional[CMS]:
    """
    Returns the user's ChatMemberStatus in the chat, or:
    - CMS.ADMINISTRATOR for anonymous admins
    - CMS.OWNER for private chats
    - None on RPC error
    """
    # Anonymous admin messages come via sender_chat == chat.id
    if m.sender_chat and m.sender_chat.id == m.chat.id:
        return CMS.ADMINISTRATOR

    if m.chat.type == ChatType.PRIVATE:
        return CMS.OWNER

    if not m.from_user:
        return None

    try:
        member = await m.chat.get_member(m.from_user.id)
        return member.status
    except UserNotParticipant:
        # Not a participant; treat as non-admin
        return None
    except RPCError:
        return None


async def _ensure_admin_cache(m: Message):
    """Warm/refresh the admin cache if missing."""
    try:
        return {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        return {i[0] for i in await admin_cache_reload(m, "custom_filter_update")}


# ---------- Command filter ----------

def command(
    commands: Union[str, List[str]],
    case_sensitive: bool = False,
    owner_cmd: bool = False,
    dev_cmd: bool = False,
    sudo_cmd: bool = False,
):
    """
    Matches messages that start with PREFIX_HANDLER + command.
    - Supports @BotUsername suffix.
    - Enforces owner/dev/sudo levels when requested.
    - Deletes messages for disabled commands if action == "del" and user is not admin/owner.
    """

    async def func(flt, c: Gojo, m: Message):
        if not m:
            return False

        # ignore edits/reactions
        if m.edit_date:
            return False

        # ignore channels
        if m.chat and m.chat.type == ChatType.CHANNEL:
            return False

        # no author (service/anon-but-not-channel); let anon admin pass via sender_chat logic later
        if not m.from_user and not (m.sender_chat and m.sender_chat.id == (m.chat.id if m.chat else 0)):
            return False

        # ignore forwarded
        if getattr(m, "forward_from_chat", None) or getattr(m, "forward_from", None):
            return False

        # ignore bots
        if m.from_user and m.from_user.is_bot:
            return False

        # role gates
        if m.from_user:
            if owner_cmd and (m.from_user.id != OWNER_ID):
                return False

            DEV_LEVEL = get_support_staff("dev_level")
            if dev_cmd and (m.from_user.id not in DEV_LEVEL):
                return False

            SUDO_LEVEL = get_support_staff("sudo_level")
            if sudo_cmd and (m.from_user.id not in SUDO_LEVEL):
                return False

        text: str = m.text or m.caption or ""
        if not text:
            return False

        # parse command
        regex = _compile_cmd_regex(PREFIX_HANDLER, c.me.username)
        match = regex.search(text)
        if not match:
            return False

        cmd_name = match.group(1)
        args_str = match.group(2) or ""

        # normalize case
        key = cmd_name if case_sensitive else cmd_name.lower()
        if key not in flt.commands:
            return False

        # disable checks in groups
        if m.chat and m.chat.type in {ChatType.SUPERGROUP, ChatType.GROUP}:
            user_status = await _get_user_status(m)
            ddb = Disabling(m.chat.id)
            if str(key) in ddb.get_disabled():
                if (user_status not in (CMS.OWNER, CMS.ADMINISTRATOR)) and ddb.get_action() == "del":
                    try:
                        await m.delete()
                    except RPCError:
                        pass
                    return False

        # build m.command similar to Pyrogram's behavior
        m.command = [cmd_name]
        try:
            if args_str:
                for arg in split(args_str):
                    m.command.append(arg)
        except ValueError:
            # malformed quotes; ignore args
            pass

        return True

    commands_list = commands if isinstance(commands, list) else [commands]
    commands_set = {c if case_sensitive else c.lower() for c in commands_list}

    return create(
        func,
        "NormalCommandFilter",
        commands=commands_set,
        case_sensitive=case_sensitive,
    )


# ---------- Role/permission filters ----------

async def bot_admin_check_func(_, c: Gojo, m: Message | CallbackQuery):
    """True if bot is admin in the group."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return False

    # sender_chat updates (Telegram service) -> allow
    if m.sender_chat:
        return True

    admin_group = await _ensure_admin_cache(m)
    if c.me.id in admin_group:
        return True

    await m.reply_text("I need to be an admin to work properly here. Please promote me.")
    return False


async def admin_check_func(_, __, m: Message | CallbackQuery):
    """True if user is admin or anonymous admin."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return False

    # anonymous admin
    if m.sender_chat and m.sender_chat.id == m.chat.id:
        return True

    if not m.from_user:
        return False

    admin_group = await _ensure_admin_cache(m)
    if m.from_user.id in admin_group:
        return True

    await m.reply_text("You cannot use an admin command!")
    return False


async def owner_check_func(_, __, m: Message | CallbackQuery):
    """True if user is group owner."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return False

    if not m.from_user:
        return False

    member = await m.chat.get_member(m.from_user.id)
    if member.status == CMS.OWNER:
        return True

    await m.reply_text("Owner-only command.")
    return False


async def restrict_check_func(_, __, m: Message | CallbackQuery):
    """True if user can restrict members."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return False

    if not m.from_user:
        return False

    member = await m.chat.get_member(m.from_user.id)
    if member and member.status in (CMS.ADMINISTRATOR, CMS.OWNER) and getattr(member.privileges, "can_restrict_members", False):
        return True

    await m.reply_text("You don't have permission to restrict members!")
    return False


async def promote_check_func(_, __, m: Message | CallbackQuery):
    """True if user can promote members."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat or m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return False

    if not m.from_user:
        return False

    member = await m.chat.get_member(m.from_user.id)
    if member and member.status in (CMS.ADMINISTRATOR, CMS.OWNER) and getattr(member.privileges, "can_promote_members", False):
        return True

    await m.reply_text("You don't have permission to promote members!")
    return False


async def changeinfo_check_func(_, __, m: Message | CallbackQuery):
    """True if user can change chat info."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        await m.reply_text("This command is meant for groups, not PM.")
        return False

    # anonymous admin
    if m.sender_chat and m.sender_chat.id == m.chat.id:
        return True

    if not m.from_user:
        return False

    member = await m.chat.get_member(m.from_user.id)
    if member and member.status in (CMS.ADMINISTRATOR, CMS.OWNER) and getattr(member.privileges, "can_change_info", False):
        return True

    await m.reply_text("You don't have: can_change_info permission!")
    return False


async def can_pin_message_func(_, __, m: Message | CallbackQuery):
    """True if user can pin messages. Sudo-level bypass allowed."""
    if isinstance(m, CallbackQuery):
        m = m.message

    if not m or not m.chat:
        return False

    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        await m.reply_text("This command is meant for groups, not PM.")
        return False

    # anonymous admin
    if m.sender_chat and m.sender_chat.id == m.chat.id:
        return True

    if not m.from_user:
        return False

    SUDO_LEVEL = get_support_staff("sudo_level")
    if m.from_user.id in SUDO_LEVEL:
        return True

    member = await m.chat.get_member(m.from_user.id)
    if member and member.status in (CMS.ADMINISTRATOR, CMS.OWNER) and getattr(member.privileges, "can_pin_messages", False):
        return True

    await m.reply_text("You don't have: can_pin_messages permission!")
    return False


# ---------- Feature filters ----------

async def auto_join_check_filter(_, __, j: ChatJoinRequest):
    aj = AUTOJOIN()
    join_type = aj.get_autojoin(j.chat.id)
    return bool(join_type)


async def afk_check_filter(_, __, m: Message):
    if not m.from_user or m.from_user.is_bot:
        return False
    if m.chat.type == ChatType.PRIVATE:
        return False

    afk = AFK()
    chat = m.chat.id

    if m.reply_to_message and m.reply_to_message.from_user:
        repl_user_id = m.reply_to_message.from_user.id
        return bool(afk.check_afk(chat, repl_user_id))

    return bool(afk.check_afk(chat, m.from_user.id))


async def flood_check_filter(_, __, m: Message):
    if not m.chat or not m.from_user or m.chat.type == ChatType.PRIVATE:
        return False

    Flood = Floods()
    if not Flood.is_chat(m.chat.id):
        return False

    try:
        admin_group = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_group = {i[0] for i in await admin_cache_reload(m, "custom_filter_update")}

    app_users = Approve(m.chat.id).list_approved()
    approved_ids = {i[0] for i in app_users}
    SUDO_LEVEL = get_support_staff("sudo_level")

    uid = m.from_user.id
    if uid in SUDO_LEVEL or uid in admin_group or uid in approved_ids:
        return False

    return True


async def captcha_filt(_, __, m: Message):
    try:
        return CAPTCHA().is_captcha(m.chat.id)
    except Exception:
        return False


# ---------- Exported filters ----------

captcha_filter = create(captcha_filt)
flood_filter = create(flood_check_filter)
afk_filter = create(afk_check_filter)
auto_join_filter = create(auto_join_check_filter)
admin_filter = create(admin_check_func)
owner_filter = create(owner_check_func)
restrict_filter = create(restrict_check_func)
promote_filter = create(promote_check_func)
bot_admin_filter = create(bot_admin_check_func)
can_change_filter = create(changeinfo_check_func)
can_pin_filter = create(can_pin_message_func)
