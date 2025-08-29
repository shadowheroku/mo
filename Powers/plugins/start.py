# Powers/plugins/start.py
from __future__ import annotations

import asyncio
from time import gmtime, strftime, time
from typing import List

from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus as CMS, ChatType
from pyrogram.errors import (
    MediaCaptionTooLong,
    MessageNotModified,
    QueryIdInvalid,
    RPCError,
    UserIsBlocked,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Project imports (expected to exist in your project)
from Powers import (
    HELP_COMMANDS,
    LOGGER,
    OWNER_ID,
    PYROGRAM_VERSION,
    PYTHON_VERSION,
    UPTIME,
    VERSION,
)
from Powers.bot_class import Gojo
from Powers.database.captcha_db import CAPTCHA_DATA
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import command
from Powers.utils.extras import StartPic
from Powers.utils.kbhelpers import ikb
from Powers.utils.start_utils import (
    gen_cmds_kb,
    gen_start_kb,
    get_help_msg,
    get_private_note,
    get_private_rules,
    get_divided_msg,
)
from Powers.utils.string import encode_decode

# Some helper imports that might be placed elsewhere in your project.
# If you moved mention_html/get_support_staff/OWNER_ID to another module,
# adjust the import above accordingly. The import above should work when
# your project layout is correct; otherwise adjust to your config.
try:
    # preferred helpers (if available)
    from Powers.utils.helpers import mention_html, get_support_staff as _gs, OWNER_ID as _OWN
    # if project has helpers, override references above
    get_support_staff = _gs  # type: ignore
    OWNER_ID = _OWN  # type: ignore
except Exception:
    # fallback mention generator (simple)
    async def mention_html(name: str, user_id: int) -> str:
        return f'<a href="tg://user?id={user_id}">{name}</a>'

# Replace with your working Catbox/hosted video url or file_id
CATBOX_VIDEO_URL = "https://files.catbox.moe/6qhbt4.MP4"


# -----------------------
# Pagination helper
# -----------------------
def paginate_buttons(buttons: List[InlineKeyboardButton], page: int = 1, per_page: int = 9) -> InlineKeyboardMarkup:
    """
    Paginate a flat list of InlineKeyboardButton into rows of 3 buttons,
    with navigation controls and a back-to-start button.
    """
    if per_page <= 0:
        per_page = 9

    total = len(buttons)
    total_pages = (total + per_page - 1) // per_page or 1
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_buttons = buttons[start:end]

    # chunk into rows of 3
    rows: List[List[InlineKeyboardButton]] = [page_buttons[i : i + 3] for i in range(0, len(page_buttons), 3)]

    # nav row
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀ ᴘʀᴇᴠ", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("ɴᴇxᴛ ▶", callback_data=f"help_page_{page+1}"))
    if nav:
        rows.append(nav)

    # Back to start always present
    rows.append([InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ sᴛᴀʀᴛ", callback_data="start_back")])

    return InlineKeyboardMarkup(rows)


# -----------------------
# Admin-only "close" callback
# -----------------------
@Gojo.on_callback_query(filters.regex("^close_admin$"))
async def close_admin_callback(_: Gojo, q: CallbackQuery):
    try:
        user_id = q.from_user.id
        # get member status in the chat where callback was triggered
        member = await q.message.chat.get_member(user_id)
        user_status = member.status
    except Exception as e:
        LOGGER.exception("Failed to fetch member status: %s", e)
        await q.answer("Unable to verify permissions.", show_alert=True)
        return

    # Only allow owner or chat owners/admins to close (owner stronger check)
    if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
        await q.answer("ʏᴏᴜ'ʀᴇ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ.", show_alert=True)
        return

    # If you want only chat owner (not admin) to perform final close:
    if user_status != CMS.OWNER:
        await q.answer("Only the chat owner can fully close this.", show_alert=True)
        return

    try:
        await q.message.edit_text("ᴄʟᴏsᴇᴅ!")
        await q.answer("Closed.", show_alert=True)
    except MessageNotModified:
        await q.answer("Already closed.", show_alert=False)
    except Exception as e:
        LOGGER.exception("Failed to close admin menu: %s", e)
        await q.answer("Failed to close.", show_alert=True)


# -----------------------
# Small loading animation helper
# -----------------------
async def send_loading_animation(m: Message):
    """
    Shows a tiny loading animation by editing a bot message.
    Keeps it minimal to avoid rate limits.
    """
    try:
        fire_msg = await m.reply_text("⚡", quote=True)
        await asyncio.sleep(1)
        await fire_msg.delete()
    except Exception:
        # ignore if we can't send/delete the emoji
        pass

    try:
        loading_msg = await m.reply_text("ʟᴏᴀᴅɪɴɢ", quote=True)
    except Exception:
        return

    try:
        # 3 cycles of dot animation
        for _ in range(3):
            for dots in range(1, 4):
                await loading_msg.edit_text(f"ʟᴏᴀᴅɪɴɢ{'.' * dots}")
                await asyncio.sleep(0.6)
        await loading_msg.edit_text(" ᴍᴏɴɪᴄ sᴛᴀʀᴛᴇᴅ !")
        await asyncio.sleep(0.7)
        await loading_msg.delete()
    except Exception:
        # editing might fail due to rate limits; ignore gracefully
        try:
            await loading_msg.delete()
        except Exception:
            pass


# -----------------------
# /start handler
# -----------------------
@Gojo.on_message(command("start") & (filters.group | filters.private))
async def start(c: Gojo, m: Message):
    """
    Start command handler:
     - In private: show animated "loading" then start content and support start parameters.
     - In group: replies with a small 'I'm alive' style message and a connect button.
    """
    # Ensure m.text is a string
    text = (m.text or "") .strip()

    # PRIVATE CHAT
    if m.chat.type == ChatType.PRIVATE:
        # show loading animation (non-blocking enough)
        await send_loading_animation(m)

        # parse start parameter (if present)
        if text and len(text.split()) > 1:
            # the arg is everything after '/start '
            arg = text.split(None, 1)[1].strip()
            help_option = arg.lower()

            # private note handling: start note<...>
            if help_option.startswith("note") and help_option not in ("note", "notes"):
                await get_private_note(c, m, help_option)
                return

            # private rules handling
            if help_option.startswith("rules"):
                await get_private_rules(c, m, help_option)
                return

            # /start help  -> paginated help menu
            if help_option == "help":
                modules = list(HELP_COMMANDS.keys())
                buttons = [
                    InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
                    for x in modules
                ]
                keyboard = paginate_buttons(buttons, page=1)
                msg = (
                    f"ʜᴇʏ {m.from_user.first_name or 'there'}! ɪ ᴀᴍ {c.me.first_name}✨.\n\n"
                    "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!\n\n"
                    "ᴄʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."
                )
                await m.reply_video(video=CATBOX_VIDEO_URL, caption=msg, reply_markup=keyboard, quote=True)
                return

            # /start qr_xxx  -> captcha unban flow
            if "_" in arg and arg.split("_", 1)[0] == "qr":
                try:
                    decoded = encode_decode(arg.split("_", 1)[1], "decode")
                except Exception:
                    await m.reply_text("Invalid QR token.")
                    return

                if ":" not in decoded:
                    await m.reply_text("Invalid QR token.")
                    return

                chat_str, user_str = decoded.split(":", 1)
                try:
                    chat_id = int(chat_str)
                    user_id = int(user_str)
                except ValueError:
                    await m.reply_text("Malformed QR information.")
                    return

                if m.from_user.id != user_id:
                    await m.reply_text("ɴᴏᴛ ғᴏʀ ʏᴏᴜ ʙᴀᴋᴀ")
                    return

                try:
                    await c.unban_chat_member(chat_id, user_id)
                except Exception:
                    await m.reply_text("Failed to unban. Try again later.")
                    return

                # delete stored captcha message id, and attempt to fetch invite link for keyboard
                msg_id = CAPTCHA_DATA().del_message_id(chat_id, user_id)
                kb = None
                try:
                    chat_obj = await c.get_chat(chat_id)
                    invite = getattr(chat_obj, "invite_link", None)
                    if invite:
                        kb = ikb([["ʟɪɴᴋ ᴛᴏ ᴄʜᴀᴛ", f"{invite}", "url"]])
                except Exception:
                    kb = None

                await m.reply_text("ʏᴏᴜ ᴄᴀɴ ɴᴏᴡ ᴛᴀʟᴋ ɪɴ ᴛʜᴇ ᴄʜᴀᴛ", reply_markup=kb)
                try:
                    if msg_id:
                        await c.delete_messages(chat_id, msg_id)
                except Exception:
                    pass
                return

        # default private start message (no args)
        try:
            cpt = (
                f"ʜᴇʏ {m.from_user.first_name or ''}! ɪ ᴀᴍ {c.me.first_name} ✨.\n\n"
                "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!\n"
                "ʜɪᴛ /help ᴛᴏ ғɪɴᴅ ᴏᴜᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ɪɴ ᴍʏ ғᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ!\n\n"
                "ᴊᴏɪɴ ᴍʏ ɴᴇᴡs ᴄʜᴀɴɴᴇʟ ᴛᴏ ɢᴇᴛ ʟᴀᴛᴇsᴛ ᴜᴘᴅᴀᴛᴇs."
            )
            await m.reply_video(video=CATBOX_VIDEO_URL, caption=cpt, reply_markup=(await gen_start_kb(m)), quote=True)
        except UserIsBlocked:
            LOGGER.warning("Bot blocked by user %s", m.from_user.id)
        except Exception as e:
            LOGGER.exception("Failed to send start private message: %s", e)

    # GROUP CHAT
    else:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("ᴄᴏɴɴᴇᴄᴛ ᴍᴇ ᴛᴏ ᴘᴍ", url=f"https://t.me/{c.me.username}?start=help")]]
        )
        try:
            await m.reply_video(video=CATBOX_VIDEO_URL, caption="ɪ'ᴍ ᴀʟɪᴠᴇ :3", reply_markup=kb, quote=True)
        except Exception as e:
            LOGGER.exception("Failed to reply in group start: %s", e)


# -----------------------
# start_back callback
# -----------------------
@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    try:
        cpt = (
            f"ʜᴇʏ {q.from_user.first_name or ''}! ɪ ᴀᴍ {c.me.first_name} ✨.\n\n"
            "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!\n\n"
            "ʜɪᴛ /help ᴛᴏ ғɪɴᴅ ᴏᴜᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ɪɴ ᴍʏ ғᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ!"
        )
        await q.edit_message_caption(caption=cpt, reply_markup=(await gen_start_kb(q.message)))
    except MessageNotModified:
        # nothing to do
        pass
    except Exception as e:
        LOGGER.exception("Failed in start_back: %s", e)
    await q.answer()


# -----------------------
# Commands (paginated) menu
# -----------------------
@Gojo.on_callback_query(filters.regex("^commands$"))
async def commands_menu(c: Gojo, q: CallbackQuery):
    modules = list(HELP_COMMANDS.keys())
    buttons = [
        InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
        for x in modules
    ]
    keyboard = paginate_buttons(buttons, page=1)

    msg = (
        f"ʜᴇʏ {q.from_user.first_name or ''}! ɪ ᴀᴍ {c.me.first_name}✨.\n\n"
        "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!\n\n"
        "ᴄʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."
    )

    try:
        await q.edit_message_caption(caption=msg, reply_markup=keyboard)
    except MessageNotModified:
        pass
    except QueryIdInvalid:
        # fallback: send as a new message
        try:
            await q.message.reply_video(video=CATBOX_VIDEO_URL, caption=msg, reply_markup=keyboard)
        except Exception as e:
            LOGGER.exception("Failed to fallback-send commands menu: %s", e)
    except Exception as e:
        LOGGER.exception("Failed to edit commands menu: %s", e)
    await q.answer()


# -----------------------
# /help handler
# -----------------------
@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    text = (m.text or "").strip()

    # user supplied an option: /help <module>
    if text and len(text.split()) >= 2:
        # reconstruct the option in a safe manner
        textt = text.replace(" ", "_", 1).replace("_", " ", 1)
        help_option = textt.split(None, 1)[1].lower()

        help_msg, help_kb = await get_help_msg(c, m, help_option)
        if not help_msg:
            LOGGER.error("No help_msg found for %s", help_option)
            return

        if m.chat.type == ChatType.PRIVATE:
            # If the caption is too long for video, send text first
            if len(help_msg) >= 1026:
                await m.reply_text(help_msg, parse_mode=enums.ParseMode.MARKDOWN, quote=True)
            await m.reply_video(
                video=CATBOX_VIDEO_URL,
                caption=help_msg,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=help_kb,
                quote=True,
            )
        else:
            # In groups provide button to open in PM
            await m.reply_video(
                video=CATBOX_VIDEO_URL,
                caption=f"ᴘʀᴇss ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ʜᴇʟᴘ ғᴏʀ <i>{help_option}</i>",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ʜᴇʟᴘ", url=f"https://t.me/{c.me.username}?start={help_option}")]]
                ),
            )
        return

    # no option -> show paginated module list
    if m.chat.type == ChatType.PRIVATE:
        modules = list(HELP_COMMANDS.keys())
        buttons = [
            InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
            for x in modules
        ]
        keyboard = paginate_buttons(buttons, page=1)
        msg = (
            f"ʜᴇʏ {m.from_user.first_name or ''}! ɪ ᴀᴍ {c.me.first_name}✨.\n\n"
            "ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!\n\n"
            "ᴄʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."
        )
        await m.reply_video(video=CATBOX_VIDEO_URL, caption=msg, reply_markup=keyboard)
    else:
        # group - ask user to open PM for help menu
        await m.reply_video(
            video=CATBOX_VIDEO_URL,
            caption="ɪ'ʟʟ sᴇɴᴅ ʏᴏᴜ ᴛʜᴇ ʜᴇʟᴘ ᴍᴇɴᴜ ɪɴ ᴘʀɪᴠᴀᴛᴇ!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("ᴏᴘᴇɴ ʜᴇʟᴘ ᴍᴇɴᴜ", url=f"https://t.me/{c.me.username}?start=help")]]
            ),
        )


# -----------------------
# pagination callback for help modules
# -----------------------
@Gojo.on_callback_query(filters.regex(r"^help_page_[0-9]+$"))
async def paginate_help(c: Gojo, q: CallbackQuery):
    try:
        page = int(q.data.split("_")[-1])
    except Exception:
        page = 1

    modules = list(HELP_COMMANDS.keys())
    buttons = [
        InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
        for x in modules
    ]
    keyboard = paginate_buttons(buttons, page=page)
    try:
        await q.edit_message_reply_markup(reply_markup=keyboard)
    except Exception as e:
        LOGGER.exception("Failed to paginate help: %s", e)
    await q.answer()


# -----------------------
# current info (ping, uptime, versions)
# -----------------------
@Gojo.on_callback_query(filters.regex("^bot_curr_info$"))
async def give_curr_info(c: Gojo, q: CallbackQuery):
    start_ts = time()
    up = strftime("%Hh %Mm %Ss", gmtime(time() - UPTIME))
    try:
        x = await c.send_message(q.message.chat.id, "ᴘɪɴɢɪɴɢ..")
        delta_ping = time() - start_ts
        await x.delete()
    except Exception:
        delta_ping = time() - start_ts

    txt = (
        f"🏓 ᴘɪɴɢ : {delta_ping * 1000:.3f} ms\n"
        f"📈 ᴜᴘᴛɪᴍᴇ : {up}\n"
        f"🤖 ʙᴏᴘ's ᴠᴇʀsɪᴏɴ: {VERSION}\n"
        f"🐍 ᴘʏᴛʜᴏɴ's ᴠᴇʀsɪᴏɴ: {PYTHON_VERSION}\n"
        f"🔥 ᴘʏʀᴏɢʀᴀᴍ's ᴠᴇʀsɪᴏɴ : {PYROGRAM_VERSION}"
    )
    await q.answer(txt, show_alert=True)


# -----------------------
# module info callback
# -----------------------
@Gojo.on_callback_query(filters.regex(r"^plugins\."))
async def get_module_info(c: Gojo, q: CallbackQuery):
    # data is like "plugins.ModuleName"
    try:
        module = q.data.split(".", 1)[1]
    except Exception:
        await q.answer("Invalid module.")
        return

    key = f"plugins.{module}"
    if key not in HELP_COMMANDS:
        await q.answer("Unknown module.")
        return

    help_msg = HELP_COMMANDS[key].get("help_msg", "")
    help_kb = HELP_COMMANDS[key].get("buttons", [])

    try:
        await q.edit_message_caption(caption=help_msg, parse_mode=enums.ParseMode.MARKDOWN, reply_markup=ikb(help_kb, True, todo="commands"))
    except MediaCaptionTooLong:
        caption, kb = await get_divided_msg(key, back_to_do="commands")
        try:
            await q.edit_message_caption(caption, enums.ParseMode.MARKDOWN, kb)
        except Exception as e:
            LOGGER.exception("Failed to edit message caption with divided msg: %s", e)
    except Exception as e:
        LOGGER.exception("Failed to show module info: %s", e)
    await q.answer()


# -----------------------
# botstaff command (owner/sudo-only - silently ignore others)
# -----------------------
from pyrogram.enums import ParseMode
# -----------------------
# botstaff command (owner/sudo-only - silently ignore others)
# -----------------------
def sudo_only(func):
    async def wrapper(c: Gojo, m: Message):
        try:
            uid = m.from_user.id
            # Import vars dynamically each time to get fresh data
            from Powers import vars as vars_module
            sudo_users = getattr(vars_module, "SUDO_USERS", []) or []
            if uid != OWNER_ID and uid not in sudo_users:
                return  # silently ignore
        except Exception:
            # if check fails, be conservative and ignore
            return
        return await func(c, m)
    return wrapper


@Gojo.on_message(command("botstaff") & (filters.group | filters.private))
@sudo_only
async def give_bot_staffs(c: Gojo, m: Message):
    # Import vars dynamically each time to get fresh data
    from Powers import vars as vars_module
    
    reply_lines: List[str] = []

    # Get fresh staff data from vars
    owner_id = getattr(vars_module, "OWNER_ID", OWNER_ID)
    dev_users = getattr(vars_module, "DEV_USERS", []) or []
    sudo_users = getattr(vars_module, "SUDO_USERS", []) or []
    whitelist_users = getattr(vars_module, "WHITELIST_USERS", []) or []

    # Owner
    try:
        owner = await c.get_users(owner_id)
        owner_name = owner.first_name or "ᴛʜᴇ ᴄʀᴇᴀᴛᴏʀ"
        reply_lines.append(
            f"<b>👑 sᴜᴘʀᴇᴍᴇ ᴄᴏᴍᴍᴀɴᴅᴇʀ:</b> "
            f"{(await mention_html(owner_name, owner_id))} (<code>{owner_id}</code>)"
        )
    except RPCError as e:
        LOGGER.error("Error getting owner info: %s", e)
        reply_lines.append(f"<b>👑 sᴜᴘʀᴇᴍᴇ ᴄᴏᴍᴍᴀɴᴅᴇʀ:</b> <code>{owner_id}</code>")

    # Developers
    reply_lines.append("\n<b>⚡️ ᴄᴏᴅᴇ ᴡɪᴢᴀʀᴅs:</b>")
    if not dev_users:
        reply_lines.append("No mystical coders found")
    else:
        dev_count = 0
        for user_id in dev_users:
            if user_id == owner_id:
                continue

            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "ᴀɴᴏɴʏᴍᴏᴜs ᴄᴏᴅᴇʀ"
                reply_lines.append(
                    f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)"
                )
            except RPCError:
                reply_lines.append(f"• <code>{user_id}</code>")
            dev_count += 1

        if dev_count == 0:
            reply_lines.append("No mystical coders found")

    # Sudo users
    reply_lines.append("\n<b>🐲 ᴅʀᴀɢᴏɴ ʀɪᴅᴇʀs:</b>")
    if not sudo_users:
        reply_lines.append("No dragon masters available")
    else:
        sudo_count = 0
        for user_id in sudo_users:
            if user_id == owner_id or user_id in dev_users:
                continue

            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "ᴍʏsᴛᴇʀɪᴏᴜs ʀɪᴅᴇʀ"
                reply_lines.append(
                    f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)"
                )
            except RPCError:
                reply_lines.append(f"• <code>{user_id}</code>")
            sudo_count += 1

        if sudo_count == 0:
            reply_lines.append("No dragon masters available")

    # Whitelisted users
    reply_lines.append("\n<b>🦊 sʜᴀᴅᴏᴡ ᴀɢᴇɴᴛs:</b>")
    if not whitelist_users:
        reply_lines.append("No covert operatives deployed")
    else:
        wl_count = 0
        for user_id in whitelist_users:
            if (
                user_id == owner_id
                or user_id in dev_users
                or user_id in sudo_users
            ):
                continue

            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "sᴇᴄʀᴇᴛ ᴀɢᴇɴᴛ"
                reply_lines.append(
                    f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)"
                )
            except RPCError:
                reply_lines.append(f"• <code>{user_id}</code>")
            wl_count += 1

        if wl_count == 0:
            reply_lines.append("No covert operatives deployed")

    # Flavor text
    reply_lines.append(
        "\n\n<i>These are whitelisted users — those chosen to wield the bot's power across the digital realm!</i> ✨"
    )

    reply = "\n".join(reply_lines)

    try:
        await m.reply_text(
            reply,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("« Back to Start", callback_data="start_back")]]
            ),
        )
    except Exception as e:
        LOGGER.exception("Failed to send botstaff reply: %s", e)

# -----------------------
# delete callback
# -----------------------
@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_: Gojo, q: CallbackQuery):
    try:
        await q.message.delete()
    except Exception:
        pass
    await q.answer()
