import random
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

def command(commands, prefixes="/", case_sensitive=False):
    if isinstance(commands, str):
        commands = [commands]
    if isinstance(prefixes, str):
        prefixes = [prefixes]

    async def func(flt, _, message):
        text = message.text or message.caption or ""
        if not text:
            return False
        parts = text.split()
        if not parts:
            return False
        cmd = parts[0].lstrip("".join(flt.prefixes))
        if not flt.case_sensitive:
            cmd = cmd.lower()
        return cmd in ([c.lower() for c in flt.commands] if not flt.case_sensitive else flt.commands)

    return filters.create(func, "CustomCommandFilter", commands=commands, prefixes=prefixes, case_sensitive=case_sensitive)

@Gojo.on_message(command("waifu"))
async def waifu_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        return await m.reply_text("This command only works in groups!")

    members = [
        member.user
        async for member in chat.get_members()
        if not member.user.is_bot and member.user.id != m.from_user.id
    ]
    if not members:
        return await m.reply_text("Couldn't find anyone to be your waifu 😢")

    waifu = random.choice(members)
    bond_percentage = random.randint(10, 100)

    message = (
        f"✨ {m.from_user.mention}'s Today's Waifu ✨\n"
        f"╭──────────────\n"
        f"┊•➢ {waifu.mention}\n"
        f"┊•➢ Bond Percentage: {bond_percentage}%\n"
        f"╰───•➢♡"
    )
    await m.reply_text(message)

@Gojo.on_message(command(["couple", "pair", "ship"]))
async def couple_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        return await m.reply_text("This command only works in groups!")

    members = [
        member.user
        async for member in chat.get_members()
        if not member.user.is_bot
    ]
    if len(members) < 2:
        return await m.reply_text("Need at least 2 members to form a couple!")

    user1, user2 = random.sample(members, 2)

    message = (
        f"🎀  𝒞❁𝓊𝓅𝓁𝑒 ❀𝒻 𝒯𝒽𝑒 𝒟𝒶𝓎  🎀\n"
        f"╭──────────────\n"
        f"┊•➢ {user1.mention} <3 + {user2.mention} = 💞\n"
        f"╰───•➢♡"
    )
    await m.reply_text(message)

__PLUGIN__ = "waifu_couple"
__HELP__ = """
**💖 Waifu & Couple Commands 💖**
• `/waifu` - See today's waifu
• `/couple` or `/pair` - See today's couple
"""
