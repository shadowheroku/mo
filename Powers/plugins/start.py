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
    get_private_note, get_private_rules, get_divided_msg
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
        nav.append(InlineKeyboardButton("◀ Pʀᴇᴠ", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Nᴇxᴛ ▶", callback_data=f"help_page_{page+1}"))
    if nav:
        rows.append(nav)
    
    # Add back button
    rows.append([InlineKeyboardButton("« Bᴀᴄᴋ ᴛᴏ Sᴛᴀʀᴛ", callback_data="start_back")])

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

            # Handle help pagination in private chat
            if help_option == "help":
                modules = sorted(list(HELP_COMMANDS.keys()))
                buttons = [
                    InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
                    for x in modules
                ]
                keyboard = paginate_buttons(buttons, page=1)
                msg = f"""
Hᴇʏ **[{m.from_user.first_name}](http://t.me/{m.from_user.username})**! I ᴀᴍ {c.me.first_name}✨.
I'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!

Aᴠᴀɪʟᴀʙʟᴇ Mᴏᴅᴜʟᴇs:
Cʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."""
                await m.reply_photo(photo=str(choice(StartPic)), caption=msg, reply_markup=keyboard)
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
Hᴇʏ [{m.from_user.first_name}](http://t.me/{m.from_user.username})! I ᴀᴍ {c.me.first_name} ✨.
I'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!
Hɪᴛ /help ᴛᴏ ғɪɴᴅ ᴏᴜᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ɪɴ ᴍʏ ғᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ!

Jᴏɪɴ ᴍʏ [Nᴇᴡs Cʜᴀɴɴᴇʟ](http://t.me/shadowbotshq) ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴏɴ ᴀʟʟ ᴛʜᴇ ʟᴀᴛᴇsᴛ ᴜᴘᴅᴀᴛᴇs."""
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
            [[InlineKeyboardButton("Cᴏɴɴᴇᴄᴛ ᴍᴇ ᴛᴏ ᴘᴍ", url=f"https://{c.me.username}.t.me/")]]
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
Hᴇʏ [{q.from_user.first_name}](http://t.me/{q.from_user.username})! I ᴀᴍ {c.me.first_name} ✨.
I'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!
Hɪᴛ /help ᴛᴏ ғɪɴᴅ ᴏᴜᴛ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ɪɴ ᴍʏ ғᴜʟʟ ᴘᴏᴛᴇɴᴛɪᴀʟ!

Jᴏɪɴ ᴍʏ [Nᴇᴡs Cʜᴀɴɴᴇʟ](http://t.me/shadowbotshq) ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴏɴ ᴀʟʟ ᴛʜᴇ ʟᴀᴛᴇsᴛ ᴜᴘᴅᴀᴛᴇs."""
        await q.edit_message_caption(caption=cpt, reply_markup=(await gen_start_kb(q.message)))
    except MessageNotModified:
        pass
    await q.answer()


# ─── Commands ───
@Gojo.on_callback_query(filters.regex("^commands$"))
async def commands_menu(c: Gojo, q: CallbackQuery):
    modules = sorted(list(HELP_COMMANDS.keys()))
    buttons = [
        InlineKeyboardButton(x.split(".")[-1].title(), callback_data=f"plugins.{x.split('.')[-1]}")
        for x in modules
    ]
    keyboard = paginate_buttons(buttons, page=1)
    
    msg = f"""
Hᴇʏ **[{q.from_user.first_name}](http://t.me/{m.from_user.username})**! I ᴀᴍ {c.me.first_name}✨.
I'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!

Aᴠᴀɪʟᴀʙʟᴇ Mᴏᴅᴜʟᴇs:
Cʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."""

    try:
        await q.edit_message_caption(caption=msg, reply_markup=keyboard)
    except MessageNotModified:
        pass
    except QueryIdInvalid:
        await q.message.reply_photo(photo=str(choice(StartPic)), caption=msg, reply_markup=keyboard)
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
                    [[InlineKeyboardButton("Hᴇʟᴘ", url=f"t.me/{c.me.username}?start={help_option}")]]
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
Hᴇʏ **[{m.from_user.first_name}](http://t.me/{m.from_user.username})**! I ᴀᴍ {c.me.first_name}✨.
I'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ(s)!

Aᴠᴀɪʟᴀʙʟᴇ Mᴏᴅᴜʟᴇs:
Cʜᴏᴏsᴇ ᴀ ᴍᴏᴅᴜʟᴇ ғʀᴏᴍ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ᴅᴇᴛᴀɪʟᴇᴅ ʜᴇʟᴘ."""
            await m.reply_photo(photo=str(choice(StartPic)), caption=msg, reply_markup=keyboard)
        else:
            # In groups, redirect to the paginated help menu
            await m.reply_photo(
                photo=str(choice(StartPic)),
                caption="I'll send you the help menu in private!",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Oᴘᴇɴ Hᴇʟᴘ Mᴇɴᴜ", url=f"https://t.me/{c.me.username}?start=help")]]
                )
            )


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
🏓 Pɪɴɢ : {delta_ping * 1000:.3f} ms
📈 Uᴘᴛɪᴍᴇ : {up}
🤖 Bᴏᴛ's ᴠᴇʀsɪᴏɴ: {VERSION}
🐍 Pʏᴛʜᴏɴ's ᴠᴇʀsɪᴏɴ: {PYTHON_VERSION}
🔥 Pʏʀᴏɢʀᴀᴍ's ᴠᴇʀsɪᴏɴ : {PYROGRAM_VERSION}
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
    
    # Owner information
    try:
        owner = await c.get_users(OWNER_ID)
        owner_name = owner.first_name or "The Creator"
        reply = f"<b>👑 Sᴜᴘʀᴇᴍᴇ Cᴏᴍᴍᴀɴᴅᴇʀ:</b> {(await mention_html(owner_name, OWNER_ID))} (<code>{OWNER_ID}</code>)\n"
    except RPCError as e:
        LOGGER.error(f"Error getting owner info: {e}")
        reply = f"<b>👑 Sᴜᴘʀᴇᴍᴇ Cᴏᴍᴍᴀɴᴅᴇʀ:</b> <code>{OWNER_ID}</code>\n"
    
    # Developers information (excluding owner)
    true_dev = get_support_staff("dev")
    reply += "\n<b>⚡️ Cᴏᴅᴇ Wɪᴢᴀʀᴅs:</b>\n"
    if not true_dev:
        reply += "No mystical coders found\n"
    else:
        dev_count = 0
        for each_user in true_dev:
            user_id = int(each_user)
            # Skip if this is the owner
            if user_id == OWNER_ID:
                continue
                
            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "Anonymous Coder"
                reply += f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)\n"
                dev_count += 1
            except RPCError as e:
                LOGGER.error(f"Error getting dev user {each_user}: {e}")
                reply += f"• <code>{each_user}</code>\n"
                dev_count += 1
        
        if dev_count == 0:
            reply += "No mystical coders found\n"
    
    # Sudo users information (excluding owner and developers)
    true_sudo = get_support_staff("sudo")
    reply += "\n<b>🐲 Dʀᴀɢᴏɴ Rɪᴅᴇʀs:</b>\n"
    if not true_sudo:
        reply += "Nᴏ ᴅʀᴀɢᴏɴ ᴍᴀsᴛᴇʀs ᴀᴠᴀɪʟᴀʙʟᴇ\n"
    else:
        sudo_count = 0
        for each_user in true_sudo:
            user_id = int(each_user)
            # Skip if this is the owner or a developer
            if user_id == OWNER_ID or (true_dev and str(user_id) in true_dev):
                continue
                
            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "Mysterious Rider"
                reply += f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)\n"
                sudo_count += 1
            except RPCError as e:
                LOGGER.error(f"Error getting sudo user {each_user}: {e}")
                reply += f"• <code>{each_user}</code>\n"
                sudo_count += 1
        
        if sudo_count == 0:
            reply += "Nᴏ ᴅʀᴀɢᴏɴ ᴍᴀsᴛᴇʀs ᴀᴠᴀɪʟᴀʙʟᴇ\n"
    
    # Whitelisted users information (excluding owner, developers, and sudo users)
    wl = get_support_staff("whitelist")
    reply += "\n<b>🦊 Sʜᴀᴅᴏᴡ Aɢᴇɴᴛs:</b>\n"
    if not wl:
        reply += "No covert operatives deployed\n"
    else:
        wl_count = 0
        for each_user in wl:
            user_id = int(each_user)
            # Skip if this user is in higher privilege groups
            if (user_id == OWNER_ID or 
                (true_dev and str(user_id) in true_dev) or 
                (true_sudo and str(user_id) in true_sudo)):
                continue
                
            try:
                user = await c.get_users(user_id)
                user_name = user.first_name or "Secret Agent"
                reply += f"• {(await mention_html(user_name, user_id))} (<code>{user_id}</code>)\n"
                wl_count += 1
            except RPCError as e:
                LOGGER.error(f"Error getting whitelisted user {each_user}: {e}")
                reply += f"• <code>{each_user}</code>\n"
                wl_count += 1
        
        if wl_count == 0:
            reply += "No covert operatives deployed\n"

    # Add some flavor text
    reply += "\n\n<i>Tʜᴇsᴇ ᴀʀᴇ ᴛʜᴇ ᴄʜᴏsᴇɴ ᴏɴᴇs ᴡʜᴏ ᴡɪᴇʟᴅ ᴛʜᴇ ʙᴏᴛ's ᴘᴏᴡᴇʀ ᴀᴄʀᴏss ᴛʜᴇ ᴅɪɢɪᴛᴀʟ ʀᴇᴀʟᴍ!</i> ✨"

    await q.edit_message_caption(
        caption=reply,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Bᴀᴄᴋ ᴛᴏ Sᴛᴀʀᴛ", "start_back")]])
    )
    await q.answer()


# ─── Delete ───
@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
