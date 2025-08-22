import random
import requests

from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.cmd_senders import send_cmd
from Powers.utils.msg_types import Types

SUPPORT_CHAT = "l_ABOUT_PRINCE_l"

# Buttons and static data
BUTTON = [[InlineKeyboardButton("ꜱᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}")]]
CUTIE = "https://64.media.tumblr.com/d701f53eb5681e87a957a547980371d2/tumblr_nbjmdrQyje1qa94xto1_500.gif"


@Gojo.on_message(command("wish"))
async def wish_cmd(c: Gojo, m: Message):
    if len(m.command) < 2:
        await m.reply_text("ᴀᴅᴅ ᴡɪꜱʜ ʙᴀʙʏ🥀!")
        return

    try:
        api = requests.get("https://nekos.best/api/v2/happy").json()
        url = api["results"][0]["url"]
    except Exception:
        url = CUTIE  # fallback gif

    text = m.text.split(None, 1)[1]
    wish_count = random.randint(1, 100)

    wish = (
        f"✨ ʜᴇʏ {m.from_user.mention}!\n\n"
        f"✨ ʏᴏᴜʀ ᴡɪꜱʜ: {text}\n"
        f"✨ ᴘᴏꜱꜱɪʙʟᴇ ᴛᴏ: {wish_count}%"
    )

    await (await send_cmd(c, Types.ANIMATION))(
        m.chat.id,
        url,
        wish,
        parse_mode=PM.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(BUTTON),
        reply_to_message_id=m.id,
    )


@Gojo.on_message(command("cute"))
async def cute_cmd(c: Gojo, m: Message):
    if not m.reply_to_message:
        user_id = m.from_user.id
        user_name = m.from_user.first_name
    else:
        user_id = m.reply_to_message.from_user.id
        user_name = m.reply_to_message.from_user.first_name

    mention = f"[{user_name}](tg://user?id={str(user_id)})"
    cuteness = random.randint(1, 100)
    CUTE = f"🍑 {mention} {cuteness}% ᴄᴜᴛᴇ ʙᴀʙʏ🥀"

    await (await send_cmd(c, Types.DOCUMENT))(
        m.chat.id,
        CUTIE,
        CUTE,
        parse_mode=PM.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(BUTTON),
        reply_to_message_id=m.reply_to_message.id if m.reply_to_message else None,
    )


__PLUGIN__ = "fun_wish"

_DISABLE_CMDS_ = ["wish", "cute"]

__HELP__ = """
**Wish & Cute**

• /wish <your wish>
   Check how possible your wish is ✨
   Example: `/wish I want a new iPhone`

• /cute (or reply to a user)
   Check how much cute you or your friend is 🍑
"""
