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
        f"💘 Calculating love between **{name1}** ❤️ **{name2}**...",
        parse_mode=PM.MARKDOWN,
    )

    # ─── Fun processing animation ───
    stages = [
        "🔍 Analyzing feelings...",
        "💭 Reading hidden emotions...",
        "💓 Checking heartbeats...",
        "💞 Matching vibes...",
        "💘 Almost done..."
    ]

    for stage in stages:
        await asyncio.sleep(1.2)
        await processing.edit(stage)

    await asyncio.sleep(1.5)

    love_percent = random.randint(0, 100)

    # Progress bar using hearts
    filled = int(love_percent / 10)
    empty = 10 - filled
    progress = "❤️" * filled + "🤍" * empty

    # Define attractive responses
    if love_percent < 30:
        status = "💔 Not a match made in heaven..."
    elif love_percent < 60:
        status = "💞 There’s something special here!"
    elif love_percent < 90:
        status = "💖 A strong bond full of sparks!"
    else:
        status = "💘 Twin flames destined forever!"

    result_text = (
        f"✨ **Love Calculator** ✨\n\n"
        f"🥰 **{name1}** + **{name2}** = ❤️ `{love_percent}%`\n\n"
        f"{progress}\n\n"
        f"{status}"
    )

    await processing.edit(result_text)


__PLUGIN__ = "love"

_DISABLE_CMDS_ = ["love"]

__alt_name__ = []

__HELP__ = """
**Love Calculator**
• /love <name1> <name2>
Calculates love compatibility between two names 💘

Example:
`/love Naruto Hinata`
"""
