from random import choice
from time import gmtime, strftime, time

from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import (
    ButtonUserPrivacyRestricted,
    MediaCaptionTooLong,
    MessageNotModified,
    QueryIdInvalid,
    RPCError,
)
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from Powers import (
    HELP_COMMANDS,
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
from Powers.utils.parser import mention_html
from Powers.utils.start_utils import gen_start_kb, get_help_msg, get_private_note, get_private_rules
from Powers.utils.string import encode_decode

# Store pagination state
help_pages = {}

# ---------------------- START ----------------------

@Gojo.on_message(command("start") & (filters.group | filters.private))
async def start(c: Gojo, m: Message):
    if m.chat.type == ChatType.PRIVATE:
        # Handle args like notes/rules/help
        if len(m.text.strip().split()) > 1:
            arg = m.text.split(None, 1)[1].lower()

            if arg.startswith("note") and arg not in ("note", "notes"):
                return await get_private_note(c, m, arg)

            if arg.startswith("rules"):
                return await get_private_rules(c, m, arg)

            help_msg, help_kb = await get_help_msg(c, m, arg)
            if help_msg:
                try:
                    return await m.reply_photo(
                        photo=str(choice(StartPic)),
                        caption=help_msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        reply_markup=help_kb,
                        quote=True,
                    )
                except ButtonUserPrivacyRestricted:
                    return await m.reply_photo(
                        photo=str(choice(StartPic)),
                        caption=help_msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        quote=True,
                    )

            if arg.startswith("qr_"):
                decoded = encode_decode(arg.split("_", 1)[1], "decode")
                chat, user = decoded.split(":")
                if m.from_user.id != int(user):
                    return await m.reply_text("Not authorized!")
                try:
                    await c.unban_chat_member(int(chat), int(user))
                    msg = CAPTCHA_DATA().del_message_id(chat, user)
                    try:
                        chat_ = await c.get_chat(chat)
                        kb = ikb([[ ("Join Chat", f"{chat_.invite_link}", "url") ]])
                    except Exception:
                        kb = None
                    await m.reply_text("Access granted!", reply_markup=kb)
                    try:
                        await c.delete_messages(chat, msg)
                    except Exception:
                        pass
                except Exception:
                    pass
                return

        # Default start message
        cpt = f"""Hey, {m.from_user.first_name} 💬

I am {c.me.first_name}, your versatile management bot, designed to help you manage your groups easily!

+ What I Can Do:
- Seamless management of your groups
- Powerful moderation tools
- Fun and engaging features

📌 Need Help?
Click the Help button below to view my modules and commands."""
        try:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=await gen_start_kb(m),
                quote=True,
            )
        except ButtonUserPrivacyRestricted:
            safe_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Help", callback_data="commands")],
                [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
                [InlineKeyboardButton("Support", url="https://t.me/ShadowBotsHQ")],
            ])
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=safe_kb,
                quote=True,
            )
    else:
        # Group message → redirect to PM
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Start in PM", url=f"https://t.me/{c.me.username}?start=start")],
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
        ])
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="Hello! Click below to explore my features in private chat.",
            reply_markup=kb,
            quote=True,
        )


# ---------------------- HELP ----------------------

@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    if m.chat.type != ChatType.PRIVATE:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open Help in PM", url=f"https://t.me/{c.me.username}?start=help")],
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
        ])
        return await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="Help is available in private only!",
            reply_markup=kb,
            quote=True,
        )

    # if /help module
    if len(m.text.split()) >= 2:
        help_option = m.text.split()[1].lower()
        help_msg, help_kb = await get_help_msg(c, m, help_option)
        if help_msg:
            try:
                return await m.reply_photo(
                    photo=str(choice(StartPic)),
                    caption=help_msg,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    reply_markup=help_kb,
                    quote=True,
                )
            except ButtonUserPrivacyRestricted:
                return await m.reply_photo(
                    photo=str(choice(StartPic)),
                    caption=help_msg,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    quote=True,
                )

    # Default → paginated menu
    all_commands = list(HELP_COMMANDS.keys())
    total_pages = (len(all_commands) + 8) // 9
    help_pages[m.from_user.id] = {"commands": all_commands, "page": 1, "total_pages": total_pages}
    await show_help_page(c, m.from_user.id, 1, m)


@Gojo.on_callback_query(filters.regex("^commands$"))
async def commands_menu(c: Gojo, q: CallbackQuery):
    if q.message.chat.type != ChatType.PRIVATE:
        return await q.answer("Open commands in PM!", show_alert=True)

    all_commands = list(HELP_COMMANDS.keys())
    total_pages = (len(all_commands) + 8) // 9
    help_pages[q.from_user.id] = {"commands": all_commands, "page": 1, "total_pages": total_pages}
    await show_help_page(c, q.from_user.id, 1, q)


async def show_help_page(c: Gojo, user_id: int, page: int, target):
    if user_id not in help_pages:
        return
    all_commands = help_pages[user_id]["commands"]
    total_pages = help_pages[user_id]["total_pages"]

    start, end = (page - 1) * 9, min((page - 1) * 9 + 9, len(all_commands))
    current_commands = all_commands[start:end]

    keyboard_buttons = [
        [InlineKeyboardButton(HELP_COMMANDS[cmd].get("name", cmd.replace("plugins.", "").title()), callback_data=f"help_{cmd}")]
        for cmd in current_commands
    ]

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"help_page_{page+1}"))
    if nav:
        keyboard_buttons.append(nav)

    keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="start_back")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    caption = f"**📖 Command Center - Page {page}/{total_pages}**\n\nSelect a module to view detailed commands:"
    help_pages[user_id]["page"] = page

    try:
        if isinstance(target, CallbackQuery):
            await target.edit_message_caption(caption=caption, reply_markup=keyboard)
            await target.answer()
        else:
            await target.reply_photo(photo=str(choice(StartPic)), caption=caption, reply_markup=keyboard)
    except MessageNotModified:
        pass


@Gojo.on_callback_query(filters.regex("^help_page_(\\d+)$"))
async def help_page_nav(c: Gojo, q: CallbackQuery):
    page = int(q.matches[0].group(1))
    await show_help_page(c, q.from_user.id, page, q)


@Gojo.on_callback_query(filters.regex("^help_(.*)"))
async def help_command_detail(c: Gojo, q: CallbackQuery):
    module = q.data.split("help_")[1]
    if module not in HELP_COMMANDS:
        return await q.answer("Unknown module!", show_alert=True)

    help_msg = HELP_COMMANDS[module].get("help_msg", "No description available.")
    help_buttons = list(HELP_COMMANDS[module].get("buttons", []))

    if q.from_user.id in help_pages:
        page = help_pages[q.from_user.id]["page"]
        help_buttons.append(("🔙 Back", f"help_page_{page}"))

    try:
        await q.edit_message_caption(
            caption=help_msg,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=ikb(help_buttons) if help_buttons else None,
        )
    except MediaCaptionTooLong:
        parts = [help_msg[i:i+4000] for i in range(0, len(help_msg), 4000)]
        for part in parts[:-1]:
            await q.message.reply_text(part, parse_mode=enums.ParseMode.MARKDOWN)
        await q.edit_message_caption(
            caption=parts[-1],
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=ikb(help_buttons) if help_buttons else None,
        )


# ---------------------- EXTRA CALLBACKS ----------------------

@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    cpt = f"""Hey, {q.from_user.first_name} 💬

I am {c.me.first_name}, your versatile management bot, designed to help you manage your groups easily!"""
    try:
        await q.edit_message_caption(caption=cpt, reply_markup=await gen_start_kb(q.message))
    except ButtonUserPrivacyRestricted:
        safe_kb = InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="commands")]])
        await q.edit_message_caption(caption=cpt, reply_markup=safe_kb)
    await q.answer()


@Gojo.on_callback_query(filters.regex("^bot_curr_info$"))
async def give_curr_info(c: Gojo, q: CallbackQuery):
    start = time()
    up = strftime("%Hh %Mm %Ss", gmtime(time() - UPTIME))
    x = await c.send_message(q.message.chat.id, "Pinging..")
    delta = time() - start
    await x.delete()
    txt = f"""
**📊 System Status:**
**🏓 Ping:** {delta*1000:.3f} ms
**⏰ Uptime:** {up}
**🤖 Version:** {VERSION}
**🐍 Python:** {PYTHON_VERSION}
**🔥 Pyrogram:** {PYROGRAM_VERSION}"""
    await q.answer(txt, show_alert=True)


@Gojo.on_callback_query(filters.regex("^give_bot_staffs$"))
async def give_bot_staffs(c: Gojo, q: CallbackQuery):
    reply = ""
    try:
        owner = await c.get_users(OWNER_ID)
        reply += f"**👑 Owner:** {(await mention_html(owner.first_name, OWNER_ID))} (`{OWNER_ID}`)\n"
    except RPCError:
        reply += f"**👑 Owner:** `{OWNER_ID}`\n"

    reply += "\n**⚡ Developers:**\n"
    for uid in get_support_staff("dev") or []:
        try:
            u = await c.get_users(int(uid))
            reply += f"• {(await mention_html(u.first_name, int(uid)))} (`{uid}`)\n"
        except RPCError:
            reply += f"• `{uid}`\n"

    reply += "\n**🐉 Sudo Users:**\n"
    for uid in get_support_staff("sudo") or []:
        try:
            u = await c.get_users(int(uid))
            reply += f"• {(await mention_html(u.first_name, int(uid)))} (`{uid}`)\n"
        except RPCError:
            reply += f"• `{uid}`\n"

    reply += "\n**🐺 Whitelisted Users:**\n"
    for uid in get_support_staff("whitelist") or []:
        try:
            u = await c.get_users(int(uid))
            reply += f"• {(await mention_html(u.first_name, int(uid)))} (`{uid}`)\n"
        except RPCError:
            reply += f"• `{uid}`\n"

    await q.edit_message_caption(reply, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "start_back")]]))


@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
