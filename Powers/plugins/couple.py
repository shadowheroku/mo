import random
import datetime
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Store results so they don't change until the next day
waifu_data = {}
couple_data = {}

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
        return await m.reply_text("🌸 This command only works in groups!")

    today = datetime.date.today()
    key = (chat.id, m.from_user.id)  # Each user gets their own waifu

    if key in waifu_data and waifu_data[key]["date"] == today:
        waifu = waifu_data[key]["waifu"]
        bond_percentage = waifu_data[key]["bond"]
    else:
        members = [
            member.user
            async for member in chat.get_members()
            if not member.user.is_bot and member.user.id != m.from_user.id
        ]
        if not members:
            return await m.reply_text("💔 Couldn't find anyone to be your waifu 😢")

        waifu = random.choice(members)
        bond_percentage = random.randint(10, 100)

        waifu_data[key] = {
            "date": today,
            "waifu": waifu,
            "bond": bond_percentage
        }

    message = (
        f"💫✨ 𝒯𝑜𝒹𝒶𝓎'𝓈 𝒲𝒶𝒾𝒻𝓊 ✨💫\n"
        f"╭───────────────╮\n"
        f"🌸 ᴹᵃˢᵗᵉʳ ➢ {m.from_user.mention}\n"
        f"💖 ᵂᵃᶦᶠᵘ ➢ {waifu.mention}\n"
        f"💞 ᴮᵒⁿᵈ ➢ {bond_percentage}%\n"
        f"╰───────────────╯\n"
        f"✨ Cherish your waifu for today! ✨"
    )
    await m.reply_text(message)

@Gojo.on_message(command(["couple", "pair", "ship"]))
async def couple_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        return await m.reply_text("🌸 This command only works in groups!")

    today = datetime.date.today()
    key = chat.id  # One couple per group per day

    if key in couple_data and couple_data[key]["date"] == today:
        user1 = couple_data[key]["u1"]
        user2 = couple_data[key]["u2"]
    else:
        members = [
            member.user
            async for member in chat.get_members()
            if not member.user.is_bot
        ]
        if len(members) < 2:
            return await m.reply_text("💔 Need at least 2 members to form a couple!")

        user1, user2 = random.sample(members, 2)

        couple_data[key] = {
            "date": today,
            "u1": user1,
            "u2": user2
        }

    message = (
        f"🎀💞 𝒞❁𝓊𝓅𝓁𝑒 𝑜𝒻 𝓉𝒽𝑒 𝒟𝒶𝓎 💞🎀\n"
        f"╭───────────────╮\n"
        f"💌 {user1.mention} 💘 {user2.mention}\n"
        f"💍 Matched by fate ✨\n"
        f"╰───────────────╯\n"
        f"💖 Spread the love, everyone!"
    )
    await m.reply_text(message)

__PLUGIN__ = "waifu_couple"
__HELP__ = """
**💖 Waifu & Couple Commands 💖**
• `/waifu` - Get today's waifu (fixed for the day)
• `/couple` or `/pair` - Get today's couple (fixed for the day)
"""
