from html import escape
from secrets import choice
from traceback import format_exc

from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from Powers import HELP_COMMANDS, LOGGER, OWNER_ID, SUPPORT_CHANNEL
from Powers.bot_class import Gojo
from Powers.database.chats_db import Chats
from Powers.database.notes_db import Notes
from Powers.database.rules_db import Rules
from Powers.utils.cmd_senders import send_cmd
from Powers.utils.kbhelpers import ikb
from Powers.utils.msg_types import Types
from Powers.utils.string import (build_keyboard,
                                 escape_mentions_using_curly_brackets,
                                 parse_button)
from Powers.vars import Config

# Initialize
notes_db = Notes()


async def gen_cmds_kb(m: Message or CallbackQuery):
    """Generate the keyboard"""
    if isinstance(m, CallbackQuery):
        m = m.message

    cmds = sorted(list(HELP_COMMANDS.keys()))
    kb = [cmd.lower() for cmd in cmds]

    return [kb[i: i + 3] for i in range(0, len(kb), 3)]


async def gen_start_kb(q: Message or CallbackQuery):
    """Generate keyboard with start menu options."""
    return ikb(
        [
            [
                ("📚 ᴄᴏᴍᴍᴀɴᴅs & ʜᴇʟᴘ", "commands"),
                ("sᴜᴘᴘᴏʀᴛ ⚡️", f"https://{SUPPORT_CHANNEL}.t.me", "url"),
            ],
            [
                ("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ᴀ ᴄʜᴀᴛ", f"https://t.me/{Config.BOT_USERNAME}?startgroup=new", "url"),
            ],
        ]
    )


async def get_private_note(c: Gojo, m: Message, help_option: str):
    """Get the note in pm of user, with parsing enabled."""
    help_lst = help_option.split("_")
    if len(help_lst) == 2:
        chat_id = int(help_lst[1])

        all_notes = notes_db.get_all_notes(chat_id)
        chat_title = Chats.get_chat_info(chat_id)["chat_name"]
        note_list = [
            f"- [{note[0]}](https://t.me/{c.me.username}?start=note_{chat_id}_{note[1]})"
            for note in all_notes
        ]
        rply = f"ᴀᴠᴀɪʟᴀʙʟᴇ ɴᴏᴛᴇs ɪɴ {chat_title}\n"
        rply += "\n".join(note_list)
        rply += "\n\nyᴏᴜ ᴄᴀɴ ʀᴇᴛʀɪᴇᴠᴇ ᴛʜᴇsᴇ ɴᴏᴛᴇs ʙʏ ᴛᴀᴘᴘɪɴɢ ᴏɴ ᴛʜᴇ ɴᴏᴛᴇɴᴀᴍᴇ."
        await m.reply_text(rply, disable_web_page_preview=True, quote=True)
        return

    if len(help_lst) != 3:
        return

    note_hash = help_option.split("_")[2]
    getnotes = notes_db.get_note_by_hash(note_hash)
    if not getnotes:
        await m.reply_text("ɴᴏᴛᴇ ᴅᴏᴇs ɴᴏᴛ ᴇxɪsᴛ", quote=True)
        return

    msgtype = getnotes["msgtype"]
    if not msgtype:
        await m.reply_text(
            "<b>ᴇʀʀᴏʀ:</b> ᴄᴀɴɴᴏᴛ ғɪɴᴅ ᴀ ᴛʏᴘᴇ ғᴏʀ ᴛʜɪs ɴᴏᴛᴇ!!",
            quote=True,
        )
        return

    try:
        # support for random notes texts
        splitter = "%%%"
        note_reply = getnotes["note_value"].split(splitter)
        note_reply = choice(note_reply)
    except KeyError:
        note_reply = ""

    parse_words = [
        "first",
        "last",
        "fullname",
        "username",
        "id",
        "chatname",
        "mention",
    ]
    text = await escape_mentions_using_curly_brackets(m, note_reply, parse_words)

    if msgtype == Types.TEXT:
        teks, button = await parse_button(text)
        button = await build_keyboard(button)
        button = ikb(button) if button else None
        if not teks:
            teks = "ʜᴇʀᴇ ɪs ʏᴏᴜʀ ɴᴏᴛᴇ"
        if button:
            try:
                await m.reply_text(
                    teks,
                    reply_markup=button,
                    disable_web_page_preview=True,
                    quote=True,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    "ᴀɴ ᴇʀʀᴏʀ ʜᴀs ᴏᴄᴄᴜʀᴇᴅ! ᴄᴀɴɴᴏᴛ ᴘᴀʀsᴇ ɴᴏᴛᴇ.",
                    quote=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await m.reply_text(teks, quote=True, disable_web_page_preview=True)
            return
    elif msgtype in (
            Types.STICKER,
            Types.VIDEO_NOTE,
            Types.CONTACT,
            Types.ANIMATED_STICKER,
    ):
        await (await send_cmd(c, msgtype))(m.chat.id, getnotes["fileid"])
    else:
        if getnotes["note_value"]:
            teks, button = await parse_button(getnotes["note_value"])
            button = await build_keyboard(button)
            button = ikb(button) if button else None
        else:
            teks = ""
            button = None
        if button:
            try:
                await (await send_cmd(c, msgtype))(
                    m.chat.id,
                    getnotes["fileid"],
                    caption=teks,
                    reply_markup=button,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    teks,
                    quote=True,
                    reply_markup=button,
                    disable_web_page_preview=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await (await send_cmd(c, msgtype))(
                m.chat.id,
                getnotes["fileid"],
                caption=teks,
            )
    return


async def get_private_rules(_, m: Message, help_option: str):
    chat_id = int(help_option.split("_")[1])
    rules = Rules(chat_id).get_rules()
    chat_title = Chats.get_chat_info(chat_id)["chat_name"]
    if not rules:
        await m.reply_text(
            "ᴛʜᴇ ᴀᴅᴍɪɴs ᴏғ ᴛʜᴀᴛ ɢʀᴏᴜᴘ ʜᴀᴠᴇ ɴᴏᴛ sᴇᴛᴜᴘ ᴀɴʏ ʀᴜʟᴇs, ᴛʜᴀᴛ ᴅᴏsᴇɴ'ᴛ ᴍᴇᴀɴ ʏᴏᴜ ʙʀᴇᴀᴋ ᴛʜᴇ ᴅᴇᴄᴏʀᴜᴍ ᴏғ ᴛʜᴇ ᴄʜᴀᴛ!",
            quote=True,
        )
        return ""
    teks, button = await parse_button(rules)
    button = await build_keyboard(button)
    button = ikb(button) if button else None
    textt = teks
    await m.reply_text(
        f"ᴛʜᴇ ʀᴜʟᴇs ғᴏʀ <b>{escape(chat_title)} ᴀʀᴇ</b>:\n\n{textt}",
        quote=True,
        disable_web_page_preview=True,
        reply_markup=button
    )
    return ""


async def get_help_msg(c: Gojo, m: Message or CallbackQuery, help_option: str):
    """Helper function for getting help_msg and it's keyboard."""
    help_msg = None
    help_kb = None
    help_cmd_keys = sorted(
        k
        for j in [HELP_COMMANDS[i]["alt_cmds"] for i in list(HELP_COMMANDS.keys())]
        for k in j
    )

    if help_option in help_cmd_keys:
        help_option_name = next(
            HELP_COMMANDS[i]
            for i in HELP_COMMANDS
            if help_option in HELP_COMMANDS[i]["alt_cmds"]
        )
        help_option_value = help_option_name["help_msg"]
        ou = next(
            HELP_COMMANDS[i]["buttons"]
            for i in HELP_COMMANDS
            if help_option in HELP_COMMANDS[i]["alt_cmds"]
        )
        help_kb = ikb(ou, True, "commands")
        help_msg = f"**{help_option_value}:**"

    else:
        mes = m.message if isinstance(m, CallbackQuery) else m
        help_msg = f"""
ʜᴇʏ **[{mes.from_user.first_name}](http://t.me/{mes.from_user.username})**! ɪ ᴀᴍ {c.me.first_name} ✨.
ɪ'ᴍ ʜᴇʀᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘs!

ᴄᴏᴍᴍᴀɴᴅs ᴀᴠᴀɪʟᴀʙʟᴇ:
× /start: sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
× /help: ɢɪᴠᴇ's ʏᴏᴜ ᴛʜɪs ᴍᴇssᴀɢᴇ."""
        ou = await gen_cmds_kb(m)
        help_kb = ikb(ou, True)

    return help_msg, help_kb


async def get_divided_msg(module: str, back_to_do: str = "start"):
    """
    Handle very long help messages that exceed Telegram's caption limit (1024 chars).
    Returns a shortened caption + a keyboard with a back button.
    """
    try:
        help_msg = HELP_COMMANDS[module]["help_msg"]
        help_kb = HELP_COMMANDS[module].get("buttons", [])
    except KeyError:
        return "ʜᴇʟᴘ ᴍᴇssᴀɢᴇ ɴᴏᴛ ғᴏᴜɴᴅ.", InlineKeyboardMarkup(
            [[InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=back_to_do)]]
        )

    # Telegram's max caption length is 1024 characters
    if len(help_msg) > 1024:
        caption = help_msg[:1000] + "...\n\n[ᴍᴇssᴀɢᴇ ᴛʀɪᴍᴍᴇᴅ]"
    else:
        caption = help_msg

    # Convert stored kb into InlineKeyboardMarkup
    if help_kb:
        keyboard = ikb(help_kb, True, todo="commands")
    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=back_to_do)]]
        )

    return caption, keyboard
