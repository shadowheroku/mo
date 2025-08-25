from datetime import datetime
from random import choice

from pyrogram import filters, ContinuePropagation
from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.database.afk_db import AFK
from Powers.plugins import till_date
from Powers.utils.cmd_senders import send_cmd
from Powers.utils.custom_filters import command
from Powers.utils.msg_types import Types, get_afk_type


# ─── AFK RESPONSES ───
res = [
    "{first} is resting for a while...",
    "{first} living his real life, go and live yours.",
    "{first} is quite busy now-a-days.",
    "I am looking for {first} too...tell me if you see him/her around",
    "{first} ran away from the chat...",
    "{first} is busy in his/her work ||simping||",
    "{first} is busy saving the world",
    "{first} is now tired fighting all the curses"
]

back = [
    "{first} is finally back to life",
    "{first} welcome back",
    "{first} the spy is back watch what you talk about",
    "{first} is now finally back from the dead"
]


# ─── SET AFK ───
@Gojo.on_message(command(["afk", "brb"]) & ~filters.private)
async def going_afk(c: Gojo, m: Message):
    user = m.from_user.id
    chat = m.chat.id
    afk = AFK()
    text, data_type, content = await get_afk_type(m)

    time = str(datetime.now()).rsplit(".", 1)[0]

    if len(m.command) == 1:
        text = choice(res)
    elif len(m.command) > 1:
        text = m.text.split(None, 1)[1]

    if not data_type:
        data_type = Types.TEXT

    afk.insert_afk(chat, user, str(time), text, data_type, content)
    await m.reply_text(f"{m.from_user.mention} is now AFK")

    raise ContinuePropagation


# ─── FORMAT HOURS ───
async def get_hours(hour: str):
    tim = hour.strip().split(":")
    txt = ""
    if int(tim[0]):
        txt += f"{tim[0]} hours "
    if int(tim[1]):
        txt += f"{tim[1]} minutes "
    if int(round(float(tim[2]))):
        txt += f"{str(round(float(tim[2])))} seconds"
    return txt


# ─── AFK RETURN ───
@Gojo.on_message(filters.group & ~filters.bot & ~filters.via_bot)
async def afk_return(c: Gojo, m: Message):
    if not m.from_user:  # ignore channel posts etc
        raise ContinuePropagation

    afk = AFK()
    user = m.from_user.id
    chat = m.chat.id

    # don’t trigger return if user is setting AFK again
    if m.text and m.text.split()[0].lower() in ["/afk", "/brb"]:
        raise ContinuePropagation

    # if user was AFK → remove
    if afk.check_afk(chat, user):
        con = afk.get_afk(chat, user)
        time = till_date(con["time"])
        tim_ = datetime.now() - time
        tim_ = str(tim_).split(",")
        tim = await get_hours(tim_[-1])
        tims = tim if len(tim_) == 1 else f"{tim_[0]} {tim}"

        txt = f"{choice(back).format(first=m.from_user.mention)}\n\nAfk for: {tims}"
        await m.reply_text(txt)
        afk.delete_afk(chat, user)

    raise ContinuePropagation


# ─── AFK NOTIFIER ───
@Gojo.on_message(filters.group & filters.reply)
async def afk_notifier(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.from_user:
        raise ContinuePropagation

    afk = AFK()
    rep_user = m.reply_to_message.from_user.id
    chat = m.chat.id

    if afk.check_afk(chat, rep_user):
        con = afk.get_afk(chat, rep_user)
        time = till_date(con["time"])
        media = con["media"]
        media_type = con["media_type"]

        tim_ = datetime.now() - time
        tim_ = str(tim_).split(",")
        tim = await get_hours(tim_[-1])
        tims = tim if len(tim_) == 1 else f"{tim_[0]} {tim}"

        reason = f"{m.reply_to_message.from_user.first_name} is afk since {tims}\n"
        if con['reason'] not in res:
            reason += f"\nDue to: {con['reason'].format(first=m.reply_to_message.from_user.first_name)}"
        else:
            reason += f"\n{con['reason'].format(first=m.reply_to_message.from_user.first_name)}"

        txt = reason

        if media_type == Types.TEXT:
            await (await send_cmd(c, media_type))(
                chat,
                txt,
                parse_mode=PM.MARKDOWN,
                reply_to_message_id=m.id,
            )
        else:
            await (await send_cmd(c, media_type))(
                chat,
                media,
                txt,
                parse_mode=PM.MARKDOWN,
                reply_to_message_id=m.id,
            )

    raise ContinuePropagation


# ─── PLUGIN INFO ───
__PLUGIN__ = "afk"
_DISABLE_CMDS_ = ["afk", "brb"]
__alt_name__ = ["brb"]

__HELP__ = """
**AFK**
• /afk (/brb) [reason | reply to a message]

`reply to a message` can be any media or text
"""
