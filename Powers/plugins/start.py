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

# Store pagination data temporarily
help_pages = {}

@Gojo.on_callback_query(filters.regex("^close_admin$"))
async def close_admin_callback(_, q: CallbackQuery):
    user_id = q.from_user.id
    user_status = (await q.message.chat.get_member(user_id)).status
    if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
        await q.answer(
            "You're not an admin!",
            show_alert=True,
        )
        return
    if user_status != CMS.OWNER:
        await q.answer(
            "Admin only!",
            show_alert=True,
        )
        return
    await q.message.delete()
    await q.answer("Closed!", show_alert=True)
    return

@Gojo.on_message(
    command("start") & (filters.group | filters.private),
)
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
                        await m.reply_text("Not authorized!")
                        return
                    try:
                        await c.unban_chat_member(int(chat), int(user))
                        msg = CAPTCHA_DATA().del_message_id(chat, user)
                        try:
                            chat_ = await c.get_chat(chat)
                            kb = ikb([[("Join Chat", f"{chat_.invite_link}", "url")]])
                        except Exception:
                            kb = None
                        await m.reply_text("Access granted!", reply_markup=kb)
                        try:
                            await c.delete_messages(chat, msg)
                        except Exception:
                            pass
                        return
                    except Exception:
                        return

        # New start message design
        cpt = f"""Hey, {m.from_user.first_name} 💬

I am {c.me.first_name}, your versatile management bot, designed to help you take control of your groups with ease using my powerful modules and commands!

+ What I Can Do:
- Seamless management of your groups
- Powerful moderation tools
- Fun and engaging features

📌 Need Help?
Click the Help button below to get all the details about my modules and commands."""

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
                [InlineKeyboardButton("Support", url="https://t.me/ShadowBotsHQ")]
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
            [InlineKeyboardButton("Start in PM", url=f"https://t.me/{c.me.username}?start=start")],
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")]
        ])

        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="Hello! Click the button below to explore my features and commands!",
            reply_markup=kb,
            quote=True,
        )
    return

@Gojo.on_callback_query(filters.regex("^start_back$"))
async def start_back(c: Gojo, q: CallbackQuery):
    try:
        cpt = f"""Hey, {q.from_user.first_name} 💬

I am {c.me.first_name}, your versatile management bot, designed to help you take control of your groups with ease using my powerful modules and commands!

+ What I Can Do:
- Seamless management of your groups
- Powerful moderation tools
- Fun and engaging features

📌 Need Help?
Click the Help button below to get all the details about my modules and commands."""

        try:
            await q.edit_message_caption(
                caption=cpt,
                reply_markup=await gen_start_kb(q.message),
            )
        except ButtonUserPrivacyRestricted:
            safe_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Help", callback_data="commands")],
                [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
                [InlineKeyboardButton("Support", url="https://t.me/ShadowBotsHQ")]
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
    if q.message.chat.type != ChatType.PRIVATE:
        await q.answer("Commands available in PM only!", show_alert=True)
        return
        
    # Generate paginated help with 9 buttons per page
    all_commands = list(HELP_COMMANDS.keys())
    total_pages = (len(all_commands) + 8) // 9  # Calculate total pages (9 items per page)
    
    # Store the commands list for this user
    help_pages[q.from_user.id] = {
        "commands": all_commands,
        "page": 1,
        "total_pages": total_pages
    }
    
    # Show first page
    await show_help_page(c, q, 1)
    return

async def show_help_page(c: Gojo, q: CallbackQuery, page: int):
    user_id = q.from_user.id
    if user_id not in help_pages:
        await q.answer("Session expired. Please try again.", show_alert=True)
        return
        
    all_commands = help_pages[user_id]["commands"]
    total_pages = help_pages[user_id]["total_pages"]
    
    # Calculate start and end indices
    start_idx = (page - 1) * 9
    end_idx = min(start_idx + 9, len(all_commands))
    
    # Create buttons for current page
    keyboard_buttons = []
    current_commands = all_commands[start_idx:end_idx]
    
    for cmd in current_commands:
        # Extract display name from command info or use the key
        display_name = HELP_COMMANDS[cmd].get("name", cmd.replace("plugins.", "").title())
        keyboard_buttons.append([InlineKeyboardButton(display_name, callback_data=f"help_{cmd}")])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"help_page_{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    # Always add back button
    keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="start_back")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    # Update the page in storage
    help_pages[user_id]["page"] = page
    
    try:
        caption = f"**📖 Command Center - Page {page}/{total_pages}**\n\nSelect a module to view detailed commands:"
        await q.edit_message_caption(
            caption=caption,
            reply_markup=keyboard,
        )
    except MessageNotModified:
        pass
    except QueryIdInvalid:
        await q.message.reply_photo(
            photo=str(choice(StartPic)), 
            caption=caption, 
            reply_markup=keyboard
        )
    except ButtonUserPrivacyRestricted:
        safe_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
        ])
        await q.edit_message_caption(
            caption=caption,
            reply_markup=safe_kb,
        )

    await q.answer()
    return

@Gojo.on_callback_query(filters.regex("^help_page_(.*)"))
async def help_page_nav(c: Gojo, q: CallbackQuery):
    page = int(q.matches[0].group(1))
    await show_help_page(c, q, page)
    return

@Gojo.on_callback_query(filters.regex("^help_plugins.(.*)"))
async def help_command_detail(c: Gojo, q: CallbackQuery):
    module = q.data.split("help_")[1]
    
    if module not in HELP_COMMANDS:
        await q.answer("Command not found!", show_alert=True)
        return
        
    help_msg = HELP_COMMANDS[module].get("help_msg", "No description available.")
    help_buttons = HELP_COMMANDS[module].get("buttons", [])
    
    # Add back button to return to help menu
    user_id = q.from_user.id
    if user_id in help_pages:
        current_page = help_pages[user_id]["page"]
        help_buttons.append([("🔙 Back", f"help_page_{current_page}")])
    
    try:
        await q.edit_message_caption(
            caption=help_msg,
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=ikb(help_buttons) if help_buttons else None,
        )
    except MediaCaptionTooLong:
        # Handle cases where the help message is too long
        parts = [help_msg[i:i+4000] for i in range(0, len(help_msg), 4000)]
        for part in parts[:-1]:
            await q.message.reply_text(part, parse_mode=enums.ParseMode.MARKDOWN)
        await q.edit_message_caption(
            caption=parts[-1],
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=ikb(help_buttons) if help_buttons else None,
        )
    except ButtonUserPrivacyRestricted:
        await q.edit_message_caption(
            caption=help_msg,
            parse_mode=enums.ParseMode.MARKDOWN,
        )
    
    await q.answer()
    return

@Gojo.on_message(command("help"))
async def help_menu(c: Gojo, m: Message):
    if m.chat.type != ChatType.PRIVATE:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Start in PM", url=f"https://t.me/{c.me.username}?start=help")],
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{c.me.username}?startgroup=true")]
        ])
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption="Help is available in private messages only!",
            reply_markup=kb,
            quote=True,
        )
        return

    if len(m.text.split()) >= 2:
        help_option = m.text.split()[1].lower()
        help_msg, help_kb = await get_help_msg(c, m, help_option)

        if not help_msg:
            return

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
        # Show the first page of help
        all_commands = list(HELP_COMMANDS.keys())
        total_pages = (len(all_commands) + 8) // 9
        
        # Store the commands list for this user
        help_pages[m.from_user.id] = {
            "commands": all_commands,
            "page": 1,
            "total_pages": total_pages
        }
        
        # Show first page
        await show_help_message(c, m, 1)
    return

async def show_help_message(c: Gojo, m: Message, page: int):
    user_id = m.from_user.id
    if user_id not in help_pages:
        return
        
    all_commands = help_pages[user_id]["commands"]
    total_pages = help_pages[user_id]["total_pages"]
    
    # Calculate start and end indices
    start_idx = (page - 1) * 9
    end_idx = min(start_idx + 9, len(all_commands))
    
    # Create buttons for current page
    keyboard_buttons = []
    current_commands = all_commands[start_idx:end_idx]
    
    for cmd in current_commands:
        display_name = HELP_COMMANDS[cmd].get("name", cmd.replace("plugins.", "").title())
        keyboard_buttons.append([InlineKeyboardButton(display_name, callback_data=f"help_{cmd}")])
    
    # Add navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"help_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"help_page_{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    keyboard_buttons.append([InlineKeyboardButton("🔙 Back", callback_data="start_back")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    # Update the page in storage
    help_pages[user_id]["page"] = page
    
    caption = f"**📖 Command Center - Page {page}/{total_pages}**\n\nSelect a module to view detailed commands:"
    
    try:
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption=caption,
            reply_markup=keyboard,
        )
    except ButtonUserPrivacyRestricted:
        await m.reply_photo(
            photo=str(choice(StartPic)),
            caption=caption,
        )
    return

# Other handlers remain the same as in the original code
# (bot_curr_info, plugins, give_bot_staffs, DELETEEEE, etc.)

@Gojo.on_callback_query(filters.regex("^bot_curr_info$"))
async def give_curr_info(c: Gojo, q: CallbackQuery):
    start = time()
    up = strftime("%Hh %Mm %Ss", gmtime(time() - UPTIME))
    x = await c.send_message(q.message.chat.id, "Pinging..")
    delta_ping = time() - start
    await x.delete()
    txt = f"""
**📊 System Status:**
**🏓 Ping:** {delta_ping * 1000:.3f} ms
**⏰ Uptime:** {up}
**🤖 Version:** {VERSION}
**🐍 Python:** {PYTHON_VERSION}
**🔥 Pyrogram:** {PYROGRAM_VERSION}"""
    await q.answer(txt, show_alert=True)
    return

@Gojo.on_callback_query(filters.regex("^give_bot_staffs$"))
async def give_bot_staffs(c: Gojo, q: CallbackQuery):
    try:
        owner = await c.get_users(OWNER_ID)
        reply = f"**👑 Owner:** {(await mention_html(owner.first_name, OWNER_ID))} (`{OWNER_ID}`)\n"
    except RPCError:
        reply = f"**👑 Owner:** `{OWNER_ID}`\n"
    
    true_dev = get_support_staff("dev")
    reply += "\n**⚡ Developers:**\n"
    if not true_dev:
        reply += "No developers\n"
    else:
        for each_user in true_dev:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (`{user_id}`)\n"
            except RPCError:
                reply += f"• `{user_id}`\n"
    
    true_sudo = get_support_staff("sudo")
    reply += "\n**🐉 Sudo Users:**\n"
    if not true_sudo:
        reply += "No sudo users\n"
    else:
        for each_user in true_sudo:
            user_id = int(each_user)
            try:
                user = await c.get_users(user_id)
                reply += f"• {(await mention_html(user.first_name, user_id))} (`{user_id}`)\n"
            except RPCError:
                reply += f"• `{user_id}`\n"
    
    reply += "\n**🐺 Whitelisted Users:**\n"
    whitelist = get_support_staff("whitelist")
    if not whitelist:
        reply += "No whitelisted users\n"
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", "start_back")]])
    )
    return

@Gojo.on_callback_query(filters.regex("^DELETEEEE$"))
async def delete_back(_, q: CallbackQuery):
    await q.message.delete()
    return
