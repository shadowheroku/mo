from random import choice
from time import gmtime, strftime, time

from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import (ButtonUserPrivacyRestricted, MediaCaptionTooLong, 
                             MessageNotModified, QueryIdInvalid, RPCError, UserIsBlocked)
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup, Message)

from Powers import (HELP_COMMANDS, LOGGER, OWNER_ID, PREFIX_HANDLER,
                    PYROGRAM_VERSION, PYTHON_VERSION, UPTIME, VERSION)
from Powers.bot_class import Gojo
from Powers.database.captcha_db import CAPTCHA_DATA
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import command
from Powers.utils.extras import StartPic
from Powers.utils.kbhelpers import ikb
from Powers.utils.parser import mention_html
from Powers.utils.start_utils import (gen_cmds_kb, gen_start_kb, get_help_msg,
                                      get_private_note, get_private_rules)
from Powers.utils.string import encode_decode

@Gojo.on_callback_query(filters.regex("^close_admin$"))
async def close_admin_callback(_, q: CallbackQuery):
    user_id = q.from_user.id
    user_status = (await q.message.chat.get_member(user_id)).status
    if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
        await q.answer(
            "You're not even an admin, don't try this explosive shit!",
            show_alert=True,
        )
        return
    if user_status != CMS.OWNER:
        await q.answer(
            "You're just an admin, not owner\nStay in your limits!",
            show_alert=True,
        )
        return
    await q.message.edit_text("Closed!")
    await q.answer("Closed menu!", show_alert=True)
    return

@Gojo.on_message(
    command("start") & (filters.group | filters.private),
)
async def start(c: Gojo, m: Message):
    # Send immediate response first
    try:
        await m.reply_sticker("CAACAgUAAxkBAAIBOWgAAWl0KxLk8vVXQv2vN8YyFvL2rAACrBQAAp7OCVfLJgUAAXh0AAJkNAQ")  # Heart/love sticker
    except:
        pass  # Continue even if sticker fails
    
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
                try:
                    await m.reply_photo(
                        photo=str(choice(StartPic)),
                        caption=help_msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        reply_markup=help_kb,
                        quote=True,
                    )
                except ButtonUserPrivacyRestricted:
                    await m.reply_photo(
                        photo=str(choice(StartPic)),
                        caption=help_msg,
                        parse_mode=enums.ParseMode.MARKDOWN,
                        quote=True,
                    )
                return
            
            if len(arg.split("_", 1)) >= 2:
                if arg.split("_")[1] == "help":
                    try:
                        await m.reply_photo(
                            photo=str(choice(StartPic)),
                            caption=help_msg,
                            parse_mode=enums.ParseMode.MARKDOWN,
                            reply_markup=help_kb,
                            quote=True,
                        )
                    except ButtonUserPrivacyRestricted:
                        await m.reply_photo(
                            photo=str(choice(StartPic)),
                            caption=help_msg,
                            parse_mode=enums.ParseMode.MARKDOWN,
                            quote=True,
                        )
                    return
                elif arg.split("_", 1)[0] == "qr":
                    decoded = encode_decode(arg.split("_", 1)[1], "decode")
                    decode = decoded.split(":")
                    chat = decode[0]
                    user = decode[1]
                    if m.from_user.id != int(user):
                        await m.reply_text("❌ Not for you!")
                        return
                    try:
                        await c.unban_chat_member(int(chat), int(user))
                        msg = CAPTCHA_DATA().del_message_id(chat, user)
                        try:
                            chat_ = await c.get_chat(chat)
                            kb = ikb([[("🚀 Join Chat", f"{chat_.invite_link}", "url")]])
                        except Exception:
                            kb = None
                        await m.reply_text("🎉 Access granted! You can chat now!", reply_markup=kb)
                        try:
                            await c.delete_messages(chat, msg)
                        except Exception:
                            pass
                        return
                    except Exception:
                        return

        # Main start message
        cpt = f"""💖 **Hey {m.from_user.first_name}!** 💖

⚡ **I'm {c.me.first_name} - Blazing Fast Group Manager!** ⚡

✨ **Features:**
• 🚀 Instant moderation
• 🛡️ Advanced protection
• 🎮 Fun activities
• 📊 Smart analytics
• 💫 Auto services

💡 **Quick start:** `/help` for commands!

📢 **Updates:** @ShadowBotsHQ

🔥 **Add me now and experience lightning-fast management!**"""

        try:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=(await gen_start_kb(m)),
                quote=True,
            )
        except ButtonUserPrivacyRestricted:
            safe_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Commands", callback_data="commands"),
                 InlineKeyboardButton("🌟 Support", url="https://t.me/ShadowBotsHQ")],
                [InlineKeyboardButton("🚀 Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
                [InlineKeyboardButton("⚡ Stats", callback_data="bot_curr_info"),
                 InlineKeyboardButton("💫 Community", url="https://t.me/ShadowBotsHQ")]
            ])
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=safe_kb,
                quote=True,
            )
    else:
        # Group message
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💖 PM Me", url=f"https://{c.me.username}.t.me/")],
            [InlineKeyboardButton("⚡ Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
            [InlineKeyboardButton("✨ Features", callback_data="commands")]
        ])

        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="💖 **I'm here!** ⚡\n\nNeed lightning-fast group management? Add me for instant moderation!",
            reply_markup=kb,
            quote=True,
        )
    return


@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    try:
        cpt = f"""
Hey [{q.from_user.first_name}](http://t.me/{q.from_user.username})! I am {c.me.first_name} ✨.
I'm here to help you manage your group(s)!
Hit /help to find out more about how to use me in my full potential!

Join my [News Channel](http://t.me/shadowbotshq) to get information on all the latest updates."""

        try:
            await q.edit_message_caption(
                caption=cpt,
                reply_markup=(await gen_start_kb(q.message)),
            )
        except ButtonUserPrivacyRestricted:
            LOGGER.warning(f"User privacy restricted for button creation in start_back")
            # Create a safe keyboard without user profile buttons
            safe_kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Help", 
                            callback_data="commands"
                        ),
                        InlineKeyboardButton(
                            "Support", 
                            url="https://t.me/ShadowBotsHQ"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "Bot Info", 
                            callback_data="bot_curr_info"
                        ),
                    ],
                ]
            )
            await q.edit_message_caption(
                caption=cpt,
                reply_markup=safe_kb,
            )
    except MessageNotModified:
        pass
    await q.answer()
    return

@Gojo.on_callback_query(filters.regex("^commands$"))
async def commands_menu(c: Gojo, q: CallbackQuery):
    ou = await gen_cmds_kb(q.message)
    keyboard = ikb(ou, True)
    try:
        cpt = f"""
Hey **[{q.from_user.first_name}](http://t.me/{q.from_user.username})**! I am {c.me.first_name}✨.
I'm here to help you manage your group(s)!
Commands available:
× /start: Start the bot
× /help: Give's you this message.

You can use {", ".join(PREFIX_HANDLER)} as your prefix handler
"""

        await q.edit_message_caption(
            caption=cpt,
            reply_markup=keyboard,
        )
    except MessageNotModified:
        pass
    except QueryIdInvalid:
        await q.message.reply_photo(
            photo=str(choice(StartPic)), caption=cpt, reply_markup=keyboard
        )
    except ButtonUserPrivacyRestricted:
        LOGGER.warning(f"User privacy restricted for button creation in commands menu")
        # Create a simplified keyboard without problematic buttons
        safe_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "« Back", 
                        callback_data="start_back"
                    ),
                ],
            ]
        )
        await q.edit_message_caption(
            caption=cpt,
            reply_markup=safe_kb,
        )

    await q.answer()
    return

@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    if len(m.text.split()) >= 2:
        textt = m.text.replace(" ", "_", ).replace("_", " ", 1)
        help_option = (textt.split(None)[1]).lower()
        help_msg, help_kb = await get_help_msg(c, m, help_option)

        if not help_msg:
            LOGGER.error(
                f"No help_msg found for help_option - {help_option}!!")
            return

        if m.chat.type == ChatType.PRIVATE:
            if len(help_msg) >= 1026:
                await m.reply_text(
                    help_msg, parse_mode=enums.ParseMode.MARKDOWN, quote=True
                )
            try:
                await m.reply_photo(
                    photo=str(choice(StartPic)),
                    caption=help_msg,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    reply_markup=help_kb,
                    quote=True,
                )
            except ButtonUserPrivacyRestricted:
                LOGGER.warning(f"User privacy restricted for button creation in help menu")
                await m.reply_photo(
                    photo=str(choice(StartPic)),
                    caption=help_msg,
                    parse_mode=enums.ParseMode.MARKDOWN,
                    quote=True,
                )
        else:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=f"Press the button below to get help for <i>{help_option}</i>",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Help",
                                url=f"t.me/{c.me.username}?start={help_option}",
                            ),
                        ],
                    ],
                ),
            )
    else:
        if m.chat.type == ChatType.PRIVATE:
            ou = await gen_cmds_kb(m)
            keyboard = ikb(ou, True)
            msg = f"""
Hey **[{m.from_user.first_name}](http://t.me/{m.from_user.username})**!I am {c.me.first_name}✨.
I'm here to help you manage your group(s)!
Commands available:
× /start: Start the bot
× /help: Give's you this message."""
        else:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Help",
                            url=f"t.me/{c.me.username}?start=start_help",
                        ),
                    ],
                ],
            )
            msg = "Contact me in PM to get the list of possible commands."

        try:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=msg,
                reply_markup=keyboard,
            )
        except ButtonUserPrivacyRestricted:
            LOGGER.warning(f"User privacy restricted for button creation in help command")
            # Send without keyboard if there are privacy issues
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=msg,
            )

    return

async def get_divided_msg(plugin_name: str, page: int = 1, back_to_do=None):
    msg = HELP_COMMANDS[plugin_name]["help_msg"]
    msg = msg.split("\n")
    l = len(msg)
    new_msg = ""
    total = l // 10
    first = 10 * (page - 1)
    last = 10 * page

    if not first:
        for i in msg[first:last]:
            new_msg += f"{i}\n"
        kb = [
            [
                (
                    "Next page ▶️",
                    f"iter_page_{plugin_name}_{f'{back_to_do}_' if back_to_do else ''}{page + 1}",
                )
            ]
        ]
    else:
        first += 1
        if page == total:
            for i in msg[first:]:
                new_msg += f"{i}\n"
            kb = [
                [
                    (
                        "◀️ Previous page",
                        f"iter_page_{plugin_name}_{f'{back_to_do}_' if back_to_do else ''}{page - 1}",
                    )
                ]
            ]
        else:
            for i in msg[first:last]:
                new_msg += f"{i}\n"
            kb = [
                [
                    (
                        "◀️ Previous page",
                        f"iter_page_{plugin_name}_{f'{back_to_do}_' if back_to_do else ''}{page - 1}",
                    ),
                    (
                        "Next page ▶️",
                        f"iter_page_{plugin_name}_{f'{back_to_do}_' if back_to_do else ''}{page + 1}",
                    ),
                ]
            ]
    kb = ikb(kb, True, back_to_do) if back_to_do else ikb(kb)
    return new_msg, kb

@Gojo.on_callback_query(filters.regex(r"^iter_page_.*[0-9]$"))
async def helppp_page_iter(c: Gojo, q: CallbackQuery):
    data = q.data.split("_")
    plugin_ = data[2]
    try:
        back_to = data[-2]
    except Exception:
        back_to = None
    curr_page = int(data[-1])
    msg, kb = await get_divided_msg(plugin_, curr_page, back_to_do=back_to)

    await q.edit_message_caption(msg, reply_markup=kb)
    return

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
    return

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
        await q.edit_message_caption(
            caption,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except ButtonUserPrivacyRestricted:
        LOGGER.warning(f"User privacy restricted for button creation in plugin info")
        # Create a simplified keyboard
        safe_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "« Back", 
                        callback_data="commands"
                    ),
                ],
            ]
        )
        await q.edit_message_caption(
            caption=help_msg,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=safe_kb,
        )
    await q.answer()
    return

@Gojo.on_callback_query(filters.regex("^give_bot_staffs$"))
async def give_bot_staffs(c: Gojo, q: CallbackQuery):
    try:
        owner = await c.get_users(OWNER_ID)
        reply = f"<b>🌟 Owner:</b> {(await mention_html(owner.first_name, OWNER_ID))} (<code>{OWNER_ID}</code>)\n"
    except RPCError:
        reply = f"<b>🌟 Owner:</b> <code>{OWNER_ID}</code>\n"
    
    true_dev = get_support_staff("dev")
    reply += "\n<b>Developers ⚡️:</b>\n"
    if not true_dev:
        reply += "No Dev Users\n"
    else:
        for each_user in true_dev:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (<code>{user_id}</code>)\n"
            except RPCError:
                reply += f"• <code>{user_id}</code>\n"
    
    true_sudo = get_support_staff("sudo")
    reply += "\n<b>Sudo Users 🐉:</b>\n"
    if not true_sudo:
        reply += "No Sudo Users\n"
    else:
        for each_user in true_sudo:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (<code>{user_id}</code>)\n"
            except RPCError:
                reply += f"• <code>{user_id}</code>\n"
    
    reply += "\n<b>Whitelisted Users 🐺:</b>\n"
    whitelist = get_support_staff("whitelist")
    if not whitelist:
        reply += "No additional whitelisted users\n"
    else:
        for each_user in whitelist:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (<code>{user_id}</code>)\n"
            except RPCError:
                reply += f"• <code>{user_id}</code>\n"

    await q.edit_message_caption(
        reply,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Back", "start_back")]])
    )
    return

@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
    return
