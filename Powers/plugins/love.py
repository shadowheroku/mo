import random
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode as PM

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command


@Gojo.on_message(command("love") & filters.group)
async def love_calc(c: Gojo, m: Message):
    if len(m.command) < 3:
        return await m.reply_text("❌ Usage: `/love name1 name2`", parse_mode=PM.MARKDOWN)

    name1, name2 = m.command[1], m.command[2]

    processing = await m.reply_text(
        f"Calculating love between **{name1}** and **{name2}**...",
        parse_mode=PM.MARKDOWN,
    )

    # ─── Simple processing animation ───
    stages = [
        "Analyzing compatibility...",
        "Measuring connection..."
    ]

    for stage in stages:
        await asyncio.sleep(1.2)
        await processing.edit(stage)

    await asyncio.sleep(1.2)

    love_percent = random.randint(0, 100)

    # Progress bar (clean style)
    filled = int(love_percent / 10)
    empty = 10 - filled
    progress = "█" * filled + "░" * empty

    # Responses
    if love_percent < 30:
        status = "Not much spark between them."
    elif love_percent < 60:
        status = "A decent bond with room to grow."
    elif love_percent < 90:
        status = "A strong and promising connection."
    else:
        status = "A perfect match!"

    result_text = (
        f"**Love Compatibility Result**\n"
        f"👤 {name1} + {name2}\n"
        f"❤️ Score: **{love_percent}%**\n"
        f"`{progress}`\n"
        f"{status}"
    )

    await processing.edit(result_text)


__PLUGIN__ = "ʟᴏᴠᴇ"

_DISABLE_CMDS_ = ["love"]

__alt_name__ = []

__HELP__ = """
**ʟᴏᴠᴇ ᴄᴀʟᴄᴜʟᴀᴛᴏʀ**
• /love <name1> <name2>
ᴄᴀʟᴄᴜʟᴀᴛᴇs ʟᴏᴠᴇ ᴄᴏᴍᴘᴀᴛɪʙɪʟɪᴛʏ ʙᴇᴛᴡᴇᴇɴ ᴛᴡᴏ ɴᴀᴍᴇs.

ᴇxᴀᴍᴘʟᴇ:
`/love Naruto Hinata`
"""

