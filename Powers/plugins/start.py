from random import choice
from time import gmtime, strftime, time

from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import (
    MediaCaptionTooLong, MessageNotModified,
    QueryIdInvalid, RPCError, UserIsBlocked
)
from pyrogram.types import (
    CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, Message
)

from Powers import (
    HELP_COMMANDS, LOGGER, OWNER_ID, PREFIX_HANDLER,
    PYROGRAM_VERSION, PYTHON_VERSION, UPTIME, VERSION
)
from Powers.bot_class import Gojo
from Powers.database.captcha_db import CAPTCHA_DATA
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import command
from Powers.utils.extras import StartPic
from Powers.utils.kbhelpers import ikb
from Powers.utils.parser import mention_html
from Powers.utils.start_utils import (
    gen_cmds_kb, gen_start_kb, get_help_msg,
    get_private_note, get_private_rules
)
from Powers.utils.string import encode_decode


# ─── Pagination helper ───
def paginate_buttons(buttons: list, page: int = 1, per_page: int = 9):
    """
    Split buttons into pages of `per_page` (default 9) arranged in 3x3 grid.
    """
    total_pages = (len(buttons) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_buttons = buttons[start:end]

    # reshape into 3x3 grid
    rows = [page_buttons[i:i + 3] for i in range(0, len(page_buttons), 3)]

    # navigation row
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"help_page_{page+1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)


# ─── Admin Close ───
@Gojo.on_callback_query(filters.regex("^close_admin$"))
async def close_admin_callback(_, q: CallbackQuery):
    user_id = q.from_user.id
    user_status = (await q.message.chat.get_member(user_id)).status
    if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
        await q.answer("You're not even an admin, don't try this explosive shit!", show_alert=True)
        return
    if user_status != CMS.OWNER:
        await q.answer("You're just an admin, not owner\nStay in your limits!", show_alert=True)
        return
    await q.message.edit_text("Closed!")
    await q.answer("Closed menu!", show_alert=True)


# ─── Start ───
@Gojo.on_message(command("start") & (filters.group | filters.private))
async def start(c: Gojo, m: Message):
    if m.chat.type == ChatType.PRIVATE:
        if len(m.text.strip().split()) > 1:
            arg = m.text.split(None, 1)[1]
            help_option = arg.lower()

            if help_option.startswith("note") and (help_option not in ("note", "notes")):
                await get_private_note(c, m, help_option)
                return

            if help_option.startswith("rules"):
                await get_private_rules(c, m, help_option)
                return

            help_msg, help_kb = await get_help_msg(c, m, help_option)
            if help_msg:
                await m.reply_photo(
                    photo=str(choice(StartPic)),
                    caption=help_msg,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    reply_markup=help_kb,
                    quote=True,
                )
                return

            # captcha QR handling
            if len(arg.split("_", 1)) >= 2 and arg.split("_", 1)[0] == "qr":
                decoded = encode_decode(arg.split("_", 1)[1], "decode")
                chat, user = decoded.split(":")
                if m.from_user.id != int(user):
                    await m.reply_text("Not for you Baka")
                    return
                try:
                    await c.unban_chat_member(int(chat), int(user))
                    msg = CAPTCHA_DATA().del_message_id(chat, user)
                    try:
                        chat_ = await c.get_chat(chat)
                        kb = ikb([["Link to chat", f"{chat_.invite_link}", "url"]])
                    except Exception:
                        kb = None
                    await m.reply_text("You can now talk in the chat", reply_markup=kb)
                    try:
                        await c.delete_messages(chat, msg)
                    except Exception:
                        pass
                except Exception:
                    return

        try:
            cpt = f"""
Hey [{m.from_user.first_name}](http://t.me/{m.from_user.username})! I am {c.me.first_name} ✨.
I'm here to help you manage your group(s)!
Hit /help to find out more about how to use me in my full potential!

Join my [News Channel](https://t.me/ShadowBotsHQ) to get information on all the latest updates."""
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=(await gen_start_kb(m)),
                quote=True,
            )
        except UserIsBlocked:
            LOGGER.warning(f"Bot blocked by {m.from_user.id}")
    else:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Connect me to pm", url=f"https://{c.me.username}.t.me/")]]
        )
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="I'm alive :3",
            reply_markup=kb,
            quote=True,
        )


# ─── Start Back ───
@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    try:
        cpt = f"""
Hey [{q.from_user.first_name}](http://t.me/{q.from_user.username})! I am {c.me.first_name} ✨.
I'm here to help you manage your group(s)!
Hit /help to find out more about how to use me in my full potential!

Join my [News Channel](http://t.me/shadowbotshq) to get information on all the latest updates."""
        await q.edit_message_caption(caption=cpt, reply_markup=(await gen_start_kb(q.message)))
    except MessageNotModified:
        pass
    await q.answer()


# ─── Commands ───
@Gojo.on_callback_query(filters.regex("^commands$"))
async def commands_menu(c: Gojo, q: CallbackQuery):
    ou = await gen_cmds_kb(q.message)
    keyboard = ikb(ou, True)
    cpt = f"""
Hey **[{q.from_user.first_name}](http://t.me/{q.from_user.username})**! I am {c.me.first_name}✨.
I'm here to help you manage your group(s)!
Commands available:
× /start: Start the bot
× /help: Give's you this message.

You can use {", ".join(PREFIX_HANDLER)} as your prefix handler
"""
    try:
        await q.edit_message_caption(caption=cpt, reply_markup=keyboard)
    except MessageNotModified:
        pass
    except QueryIdInvalid:
        await q.message.reply_photo(photo=str(choice(StartPic)), caption=cpt, reply_markup=keyboard)
    await q.answer()


# ─── Help ───
@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    if len(m.text.split()) >= 2:
        textt = m.text.replace(" ", "_").replace("_", " ", 1)
        help_option = (textt.split(None)[1]).lower()
        help_msg, help_kb = await get_help_msg(c, m, help_option)

        if not help_msg:
            LOGGER.error(f"No help_msg found for help_option - {help_option}!!")
            return

        if m.chat.type == ChatType.PRIVATE:
            if len(help_msg) >= 1026:
                await m.reply_text(help_msg, parse_mode=enums.ParseMode.MARKDOWN, quote=True)
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=help_msg,
                parse_mode=enums.ParseMode.MARKDOWN,
                reply_markup=help_kb,
                quote=True,
            )
        else:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=f"Press the button below to get help for <i>{help_option}</i>",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Help", url=f"t.me/{c.me.username}?start={help_option}")]]
                ),
            )
    else:
        if m.chat.type == ChatType.PRIVATE:
            modules = sorted(list(HELP_COMMANDS.keys()))
            buttons = [
                InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
                for x in modules
            ]
            keyboard = paginate_buttons(buttons, page=1)
            msg = f"""
Hey **[{m.from_user.first_name}](http://t.me/{m.from_user.username})**! I am {c.me.first_name}✨.
I'm here to help you manage your group(s)!
Commands available:
× /start: Start the bot
× /help: Give's you this message."""
        else:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Help", url=f"t.me/{c.me.username}?start=start_help")]]
            )
            msg = "Contact me in PM to get the list of possible commands."

        await m.reply_photo(photo=str(choice(StartPic)), caption=msg, reply_markup=keyboard)


# ─── Pagination Handler ───
@Gojo.on_callback_query(filters.regex(r"^help_page_[0-9]+$"))
async def paginate_help(c: Gojo, q: CallbackQuery):
    page = int(q.data.split("_")[-1])
    modules = sorted(list(HELP_COMMANDS.keys()))
    buttons = [InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}") for x in modules]
    keyboard = paginate_buttons(buttons, page=page)
    await q.edit_message_reply_markup(reply_markup=keyboard)
    await q.answer()


# ─── Current Info ───
@Gojo.on_callback_query(filters.regex("^bot_curr_info$"))
async def give_curr_info(c: Gojo, q: CallbackQuery):
    start = time()
    up = strftime("%Hh %Mm %Ss", gmtime(time() - UPTIME))
    x = await c.send_message(q.message.chat.id, "Pinging..")
    delta_ping = time() - start
    await x.delete()
    txt = f"""
🏓 Ping : {delta_ping * 1000:.3f} ms
📈 Uptime : {up}
🤖 Bot's version: {VERSION}
🐍 Python's version: {PYTHON_VERSION}
🔥 Pyrogram's version : {PYROGRAM_VERSION}
    """
    await q.answer(txt, show_alert=True)


# ─── Module Info ───
@Gojo.on_callback_query(filters.regex("^plugins."))
async def get_module_info(c: Gojo, q: CallbackQuery):
    module = q.data.split(".", 1)[1]
    help_msg = HELP_COMMANDS[f"plugins.{module}"]["help_msg"]
    help_kb = HELP_COMMANDS[f"plugins.{module}"]["buttons"]

    try:
        await q.edit_message_caption(
            caption=help_msg,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=ikb(help_kb, True, todo="commands"),
        )
    except MediaCaptionTooLong:
        caption, kb = await get_divided_msg(f"plugins.{module}", back_to_do="commands")
        await q.edit_message_caption(caption, enums.ParseMode.MARKDOWN, kb)
    await q.answer()


# ─── Staffs ───
@Gojo.on_callback_query(filters.regex("^give_bot_staffs$"))
async def give_bot_staffs(c: Gojo, q: CallbackQuery):
    reply = ""
    try:
        owner = await c.get_users(OWNER_ID)
        reply = f"<b>🌟 Owner:</b> {(await mention_html(owner.first_name, OWNER_ID))} (<code>{OWNER_ID}</code>)\n"
    except RPCError:
        pass

    true_dev = get_support_staff("dev")
    reply += "\n<b>Developers ⚡️:</b>\n"
    if not true_dev:
        reply += "No Dev Users\n"
    else:
        for each_user in true_dev:
            try:
                user = await c.get_users(int(each_user))
                reply += f"• {(await mention_html(user.first_name, user.id))} (<code>{user.id}</code>)\n"
            except RPCError:
                pass

    true_sudo = get_support_staff("sudo")
    reply += "\n<b>Sudo Users 🐉:</b>\n"
    if not true_sudo:
        reply += "No Sudo Users\n"
    else:
        for each_user in true_sudo:
            try:
                user = await c.get_users(int(each_user))
                reply += f"• {(await mention_html(user.first_name, user.id))} (<code>{user.id}</code>)\n"
            except RPCError:
                pass

    reply += "\n<b>Whitelisted Users 🐺:</b>\n"
    wl = get_support_staff("whitelist")
    if not wl:
        reply += "No additional whitelisted users\n"
    else:
        for each_user in wl:
            try:
                user = await c.get_users(int(each_user))
                reply += f"• {(await mention_html(user.first_name, user.id))} (<code>{user.id}</code>)\n"
            except RPCError:
                pass

    await q.edit_message_caption(reply,
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", "start_back")]]))


# ─── Delete ───
@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
