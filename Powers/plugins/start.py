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
            "YOU'RE NOT AN ADMIN - STAY IN YOUR LANE!",
            show_alert=True,
        )
        return
    if user_status != CMS.OWNER:
        await q.answer(
            "ADMIN ONLY - OWNER PRIVILEGES REQUIRED!",
            show_alert=True,
        )
        return
    await q.message.edit_text("🛑 COMMAND TERMINATED!")
    await q.answer("MENU CLOSED!", show_alert=True)
    return

@Gojo.on_message(
    command("start") & (filters.group | filters.private),
)
async def start(c: Gojo, m: Message):
    # Send immediate sticker response
    try:
        await m.reply_sticker("CAACAgUAAxkBAAIBOWgAAWl0KxLk8vVXQv2vN8YyFvL2rAACrBQAAp7OCVfLJgUAAXh0AAJkNAQ")
    except:
        pass
    
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
                        await m.reply_text("🚫 ACCESS DENIED - NOT AUTHORIZED!")
                        return
                    try:
                        await c.unban_chat_member(int(chat), int(user))
                        msg = CAPTCHA_DATA().del_message_id(chat, user)
                        try:
                            chat_ = await c.get_chat(chat)
                            kb = ikb([[("🔗 JOIN CHAT", f"{chat_.invite_link}", "url")]])
                        except Exception:
                            kb = None
                        await m.reply_text("✅ ACCESS GRANTED - WELCOME TO THE CHAT!", reply_markup=kb)
                        try:
                            await c.delete_messages(chat, msg)
                        except Exception:
                            pass
                        return
                    except Exception:
                        return

        # Main start message - BOLD FORMATTING
        cpt = f"""**🔥 WELCOME {m.from_user.first_name.upper()}! 🔥**

**⚡ I AM {c.me.first_name.upper()} - ULTIMATE GROUP MANAGEMENT SYSTEM ⚡**

**🎯 CORE FEATURES:**
• **🚀 INSTANT MODERATION** - Real-time protection
• **🛡️ ADVANCED SECURITY** - Anti-spam, Anti-raid
• **📊 POWERFUL ANALYTICS** - Group insights & stats
• **⚙️ AUTOMATION TOOLS** - Smart management systems
• **🎮 ENTERTAINMENT** - Games & engagement features

**💡 QUICK START: ** `/help` **FOR FULL COMMAND LIST**

**📢 UPDATE CHANNEL: ** @ShadowBotsHQ

**🚀 ADD ME TO YOUR GROUP FOR MAXIMUM PROTECTION!**"""

        try:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=(await gen_start_kb(m)),
                quote=True,
            )
        except ButtonUserPrivacyRestricted:
            safe_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 COMMANDS", callback_data="commands"),
                 InlineKeyboardButton("🆘 SUPPORT", url="https://t.me/ShadowBotsHQ")],
                [InlineKeyboardButton("➕ ADD TO GROUP", url=f"https://t.me/{c.me.username}?startgroup=true")],
                [InlineKeyboardButton("📊 STATS", callback_data="bot_curr_info")]
            ])
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=cpt,
                reply_markup=safe_kb,
                quote=True,
            )
    else:
        # Group message - NO COMMANDS SHOWN
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 PRIVATE MESSAGE", url=f"https://{c.me.username}.t.me/")],
            [InlineKeyboardButton("➕ ADD TO GROUP", url=f"https://t.me/{c.me.username}?startgroup=true")]
        ])

        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="**🤖 BOT ACTIVE - READY FOR DEPLOYMENT!**\n\n**📩 PM ME FOR COMMANDS AND SETUP**",
            reply_markup=kb,
            quote=True,
        )
    return

@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    try:
        cpt = f"""**🔙 WELCOME BACK {q.from_user.first_name.upper()}!**

**⚡ I AM {c.me.first_name.upper()} - ULTIMATE GROUP MANAGEMENT SYSTEM**

**🎯 CORE FEATURES:**
• **🚀 INSTANT MODERATION** - Real-time protection
• **🛡️ ADVANCED SECURITY** - Anti-spam, Anti-raid
• **📊 POWERFUL ANALYTICS** - Group insights & stats

**💡 QUICK START: ** `/help` **FOR FULL COMMAND LIST**

**📢 UPDATE CHANNEL: ** @ShadowBotsHQ**"""

        try:
            await q.edit_message_caption(
                caption=cpt,
                reply_markup=(await gen_start_kb(q.message)),
            )
        except ButtonUserPrivacyRestricted:
            safe_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 COMMANDS", callback_data="commands"),
                 InlineKeyboardButton("🆘 SUPPORT", url="https://t.me/ShadowBotsHQ")],
                [InlineKeyboardButton("📊 STATS", callback_data="bot_curr_info")]
            ])
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
    # Only show commands in private chat
    if q.message.chat.type != ChatType.PRIVATE:
        await q.answer("🚫 COMMANDS ONLY AVAILABLE IN PRIVATE MESSAGES!", show_alert=True)
        return
        
    ou = await gen_cmds_kb(q.message)
    keyboard = ikb(ou, True)
    try:
        cpt = f"""**📖 COMMAND CENTRAL - {q.from_user.first_name.upper()}**

**🤖 BOT: ** {c.me.first_name}
**🎯 PURPOSE: ** ADVANCED GROUP MANAGEMENT
**⚡ PREFIXES: ** {", ".join(PREFIX_HANDLER)}

**🔧 CORE COMMANDS:**
• **/start** - ACTIVATE SYSTEM
• **/help** - DISPLAY THIS MENU
• **/settings** - CONFIGURE BOT OPTIONS

**🛡️ SECURITY COMMANDS AVAILABLE IN GROUPS**"""

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
        safe_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 BACK", callback_data="start_back")]
        ])
        await q.edit_message_caption(
            caption=cpt,
            reply_markup=safe_kb,
        )

    await q.answer()
    return

@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    # Only process help command in private chat
    if m.chat.type != ChatType.PRIVATE:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 PRIVATE MESSAGE", url=f"https://{c.me.username}.t.me/")],
            [InlineKeyboardButton("➕ ADD TO GROUP", url=f"https://t.me/{c.me.username}?startgroup=true")]
        ])
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="**🚫 COMMANDS ONLY AVAILABLE IN PRIVATE MESSAGES!**\n\n**📩 PM ME FOR FULL COMMAND LIST**",
            reply_markup=kb,
            quote=True,
        )
        return

    if len(m.text.split()) >= 2:
        textt = m.text.replace(" ", "_", ).replace("_", " ", 1)
        help_option = (textt.split(None)[1]).lower()
        help_msg, help_kb = await get_help_msg(c, m, help_option)

        if not help_msg:
            LOGGER.error(f"No help_msg found for help_option - {help_option}!!")
            return

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
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=help_msg,
                parse_mode=enums.ParseMode.MARKDOWN,
                quote=True,
            )
    else:
        ou = await gen_cmds_kb(m)
        keyboard = ikb(ou, True)
        msg = f"""**📖 COMMAND CENTRAL - {m.from_user.first_name.upper()}**

**🤖 BOT: ** {c.me.first_name}
**🎯 PURPOSE: ** ADVANCED GROUP MANAGEMENT
**⚡ PREFIXES: ** {", ".join(PREFIX_HANDLER)}

**🔧 CORE COMMANDS:**
• **/start** - ACTIVATE SYSTEM
• **/help** - DISPLAY THIS MENU
• **/settings** - CONFIGURE BOT OPTIONS

**🛡️ SECURITY COMMANDS AVAILABLE IN GROUPS**"""

        try:
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption=msg,
                reply_markup=keyboard,
            )
        except ButtonUserPrivacyRestricted:
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
                    "NEXT PAGE ▶️",
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
                        "◀️ PREVIOUS PAGE",
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
                        "◀️ PREVIOUS PAGE",
                        f"iter_page_{plugin_name}_{f'{back_to_do}_' if back_to_do else ''}{page - 1}",
                    ),
                    (
                        "NEXT PAGE ▶️",
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
**📊 SYSTEM STATUS:**
**🏓 PING:** {delta_ping * 1000:.3f} ms
**⏰ UPTIME:** {up}
**🤖 VERSION:** {VERSION}
**🐍 PYTHON:** {PYTHON_VERSION}
**🔥 PYROGRAM:** {PYROGRAM_VERSION}"""
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
        safe_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 BACK", callback_data="commands")]
        ])
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
        reply = f"**👑 OWNER:** {(await mention_html(owner.first_name, OWNER_ID))} (`{OWNER_ID}`)\n"
    except RPCError:
        reply = f"**👑 OWNER:** `{OWNER_ID}`\n"
    
    true_dev = get_support_staff("dev")
    reply += "\n**⚡ DEVELOPERS:**\n"
    if not true_dev:
        reply += "NO DEVELOPERS\n"
    else:
        for each_user in true_dev:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (`{user_id}`)\n"
            except RPCError:
                reply += f"• `{user_id}`\n"
    
    true_sudo = get_support_staff("sudo")
    reply += "\n**🐉 SUDO USERS:**\n"
    if not true_sudo:
        reply += "NO SUDO USERS\n"
    else:
        for each_user in true_sudo:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (`{user_id}`)\n"
            except RPCError:
                reply += f"• `{user_id}`\n"
    
    reply += "\n**🐺 WHITELISTED USERS:**\n"
    whitelist = get_support_staff("whitelist")
    if not whitelist:
        reply += "NO WHITELISTED USERS\n"
    else:
        for each_user in whitelist:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (`{user_id}`)\n"
            except RPCError:
                reply += f"• `{user_id}`\n"

    await q.edit_message_caption(
        reply,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", "start_back")]])
    )
    return

@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
    return
