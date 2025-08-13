import random
from typing import Optional, List
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Emoji collections for different effects
WAIFU_EMOJIS = ["🌸", "💘", "💝", "💖", "💗", "💓", "💞", "💕", "💟", "❣️", "💔", "❤️", "🧡", "💛", "💚", "💙", "💜"]
COUPLE_EMOJIS = ["💑", "👩‍❤️‍👨", "👩‍❤️‍👩", "👨‍❤️‍👨", "💏", "👫", "👬", "👭"]
ROMANTIC_ADJECTIVES = [
    "adorable", "amazing", "angelic", "beautiful", "charming", 
    "cute", "darling", "delightful", "elegant", "enchanting",
    "exquisite", "fabulous", "gorgeous", "lovely", "magnificent",
    "marvelous", "radiant", "stunning", "wonderful"
]

def command(commands: str or list, prefixes: str or list = "/", case_sensitive: bool = False):
    """Command decorator (same as before)"""
    if isinstance(commands, str):
        commands = [commands]
    if isinstance(prefixes, str):
        prefixes = [prefixes]

    async def func(flt, _, message):
        text = message.text or message.caption or ""
        if not text:
            return False

        text = text.split()
        if not text:
            return False

        command_parts = text[0].lower() if not flt.case_sensitive else text[0]
        command_parts = command_parts.lstrip(flt.prefixes[0])

        for command in flt.commands:
            cmd = command.lower() if not flt.case_sensitive else command
            if command_parts == cmd:
                return True

        return False

    return filters.create(
        func,
        "CustomCommandFilter",
        commands=commands,
        prefixes=prefixes,
        case_sensitive=case_sensitive
    )

async def generate_waifu_message(user_mention: str, waifu_mention: str) -> str:
    """Generate attractive waifu announcement"""
    emoji = random.choice(WAIFU_EMOJIS)
    adjective = random.choice(ROMANTIC_ADJECTIVES)
    templates = [
        f"{emoji} **{user_mention}**, fate has chosen your {adjective} waifu: {waifu_mention} {emoji}",
        f"{emoji}✨ {user_mention}'s {adjective} soulmate is... {waifu_mention}! ✨{emoji}",
        f"🌟 {user_mention} × {waifu_mention} 🌟\nA match made in heaven! {emoji}",
        f"💫 {waifu_mention} has been chosen as {user_mention}'s {adjective} partner! 💫",
        f"🔥 {user_mention} + {waifu_mention} = OTP! 🔥\nShip it! {emoji}"
    ]
    return random.choice(templates)

async def generate_couple_message(user1_mention: str, user2_mention: str) -> str:
    """Generate attractive couple announcement"""
    emoji = random.choice(COUPLE_EMOJIS)
    templates = [
        f"✨ **Today's Power Couple** ✨\n{user1_mention} {emoji} {user2_mention}",
        f"🌟 **Match of the Day** 🌟\n{user1_mention} × {user2_mention} {emoji}",
        f"💞 {user1_mention} + {user2_mention} = True Love! 💞",
        f"🔥 **Dynamic Duo Alert** 🔥\n{user1_mention} & {user2_mention} {emoji}",
        f"💑 {user1_mention} and {user2_mention} sitting in a tree... K-I-S-S-I-N-G! 💏"
    ]
    return random.choice(templates) 

@Gojo.on_message(command("waifu"))
async def waifu_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        await m.reply_text("This command only works in groups!")
        return
    
    # Get random member (excluding bots and self)
    members = [
        member.user 
        async for member in chat.get_members() 
        if not member.user.is_bot and member.user.id != m.from_user.id
    ]
    
    if not members:
        await m.reply_text("Couldn't find anyone worthy to be your waifu 😢")
        return
    
    waifu = random.choice(members)
    message = await generate_waifu_message(m.from_user.mention, waifu.mention)
    await m.reply_text(message, disable_web_page_preview=True)

@Gojo.on_message(command(["couple", "pair", "ship"]))
async def couple_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        await m.reply_text("This command only works in groups!")
        return
    
    # Get random members (excluding bots)
    members = [
        member.user 
        async for member in chat.get_members() 
        if not member.user.is_bot
    ]
    
    if len(members) < 2:
        await m.reply_text("Need at least 2 members to form a couple!")
        return
    
    # Get two distinct random members
    user1, user2 = random.sample(members, 2)
    while user1.id == user2.id and len(members) > 1:
        user2 = random.choice(members)
    
    message = await generate_couple_message(user1.mention, user2.mention)
    await m.reply_text(message, disable_web_page_preview=True)

__PLUGIN__ = "waifu_couple"
__HELP__ = """
**💖 Waifu & Couple Commands 💖**

• `/waifu` - Choose a random member as your waifu/husbando
• `/couple` or `/pair` - Choose two random members as today's couple

✨ *No images needed - pure romantic magic!* ✨
"""
