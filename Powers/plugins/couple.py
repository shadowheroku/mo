import random
from typing import Union, List
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# -------------------- Constants -------------------- #
WAIFU_EMOJIS: List[str] = [
    "🌸", "💘", "💝", "💖", "💗", "💓", "💞", "💕", "💟",
    "❣️", "💔", "❤️", "🧡", "💛", "💚", "💙", "💜"
]

COUPLE_EMOJIS: List[str] = [
    "💑", "👩‍❤️‍👨", "👩‍❤️‍👩", "👨‍❤️‍👨", "💏", "👫", "👬", "👭"
]

ROMANTIC_ADJECTIVES: List[str] = [
    "adorable", "amazing", "angelic", "beautiful", "charming",
    "cute", "darling", "delightful", "elegant", "enchanting",
    "exquisite", "fabulous", "gorgeous", "lovely", "magnificent",
    "marvelous", "radiant", "stunning", "wonderful"
]

# -------------------- Custom Command Filter -------------------- #
def command(commands: Union[str, List[str]], prefixes: Union[str, List[str]] = "/", case_sensitive: bool = False):
    """Creates a custom command filter similar to Pyrogram's built-in filters.command."""
    commands = [commands] if isinstance(commands, str) else commands
    prefixes = [prefixes] if isinstance(prefixes, str) else prefixes

    async def func(flt, _, message: Message) -> bool:
        text = message.text or message.caption or ""
        if not text:
            return False

        parts = text.split()
        if not parts:
            return False

        cmd_text = parts[0]
        if not flt.case_sensitive:
            cmd_text = cmd_text.lower()

        for prefix in flt.prefixes:
            if cmd_text.startswith(prefix):
                cmd_body = cmd_text[len(prefix):]
                for cmd in flt.commands:
                    if (cmd_body.lower() if not flt.case_sensitive else cmd_body) == (cmd.lower() if not flt.case_sensitive else cmd):
                        return True
        return False

    return filters.create(
        func,
        "CustomCommandFilter",
        commands=commands,
        prefixes=prefixes,
        case_sensitive=case_sensitive
    )

# -------------------- Message Generators -------------------- #
async def generate_waifu_message(user_mention: str, waifu_mention: str) -> str:
    emoji = random.choice(WAIFU_EMOJIS)
    adjective = random.choice(ROMANTIC_ADJECTIVES)
    ship_name = f"{user_mention[:3]}{waifu_mention[:3]}".replace("[", "").replace("]", "")

    templates = [
        f"🎉✨ **EPIC WAIFU REVEAL** ✨🎉\n\n"
        f"{emoji} {user_mention}'s {random.choice(['destiny', 'fate', 'dream'])} has arrived!\n"
        f"Please welcome their {adjective} {random.choice(['waifu', 'soulmate', 'anime partner'])}:\n"
        f"╰☆╮ {waifu_mention} ╰☆╮\n\n"
        f"#ShipName: {ship_name.upper()} {emoji}",

        f"💖🌸⚡ **WAIFU MATCHMAKING** ⚡🌸💖\n\n"
        f"After {random.choice(['centuries', '84 years', 'an intense season'])} of searching...\n"
        f"{user_mention} has found their {adjective} {random.choice(['match', 'perfect pair'])}!\n\n"
        f"┏━━━━━━━━━━━━┓\n"
        f"┃  💌  {waifu_mention}  💌  ┃\n"
        f"┗━━━━━━━━━━━━┛\n\n"
        f"Will you accept this {random.choice(['rose', 'chocolate', 'love letter'])}? {emoji}",

        f"🌠 *~Cosmic Waifu Connection~* 🌠\n\n"
        f"The stars have aligned for {user_mention}!\n"
        f"Your {adjective} {random.choice(['anime partner', 'manga lover', 'k-drama co-star'])} is:\n\n"
        f"▂▂ξ▂▂\n"
        f"✧ {waifu_mention} ✧\n"
        f"▂▂ξ▂▂\n\n"
        f"Compatibility: {random.randint(85, 110)}% {emoji}",

        f"🎎 **Waifu/Husbando Ceremony** 🎎\n\n"
        f"By the power of {random.choice(['romance', 'anime gods', 'shoujo manga'])},\n"
        f"I now pronounce {user_mention} and {waifu_mention} as:\n\n"
        f"╔═══════════╗\n"
        f"   {adjective.upper()} PARTNERS\n"
        f"╚═══════════╝\n\n"
        f"You may now {random.choice(['headpat', 'hug', 'share umbrella'])}! {emoji}",

        f"💥 **BEST WAIFU ALERT** 💥\n\n"
        f"After {random.choice(['rigorous testing', 'careful consideration', 'a tournament arc'])},\n"
        f"{user_mention} has earned the {adjective} {random.choice(['companion', 'partner', 'waifu'])}:\n\n"
        f"✧･ﾟ: *✧･ﾟ:* {waifu_mention} *:･ﾟ✧*:･ﾟ✧\n\n"
        f"Relationship Status: {random.choice([\"It's complicated\", 'More than friends', 'Tsundere'])} {emoji}"
    ]
    return random.choice(templates)


async def generate_couple_message(user1_mention: str, user2_mention: str) -> str:
    emoji = random.choice(COUPLE_EMOJIS)
    ship_name = f"{user1_mention[:2]}{user2_mention[:2]}".replace("[", "").replace("]", "")
    love_percent = random.randint(75, 100)

    templates = [
        f"💘✨ **OFFICIAL COUPLE ANNOUNCEMENT** ✨💘\n\n"
        f"After {random.choice(['secret meetings', 'years of pining', 'a dramatic confession'])},\n"
        f"we proudly present today's {random.choice(['power couple', 'OTP', 'soulmates'])}:\n\n"
        f"┌───────────────┐\n"
        f"  {user1_mention} × {user2_mention}\n"
        f"└───────────────┘\n\n"
        f"Ship Name: {ship_name.upper()}\n"
        f"Approval Rating: {love_percent}% {emoji}",

        f"🌸⚡💑 **LOVE CONNECTION** 💑⚡🌸\n\n"
        f"The universe has spoken!\n"
        f"Today's {random.choice(['perfect match', 'destined pair', 'dynamic duo'])} is:\n\n"
        f"✧˖° {user1_mention} + {user2_mention} = FOREVER °˖✧\n\n"
        f"Compatibility Factors:\n"
        f"• {random.choice(['Shared love of anime', 'Complementary personalities', 'Mutual blushing'])}\n"
        f"• {random.choice(['Adorable awkwardness', 'Protective instincts', 'Secret handshakes'])}\n\n"
        f"{emoji} Congratulations! {emoji}",

        f"💞🌠 **COSMIC LOVE ALERT** 🌠💞\n\n"
        f"Attention everyone!\n"
        f"The stars have blessed us with a new couple:\n\n"
        f"╔♡══════════════♡╗\n"
        f"   {user1_mention} ♡ {user2_mention}\n"
        f"╚♡══════════════♡╝\n\n"
        f"Love Compatibility: {love_percent}%\n"
        f"Recommended Date: {random.choice(['Anime marathon', 'Sunset picnic', 'Arcade battle'])} {emoji}",

        f"🎎 **TRADITIONAL COUPLE BLESSING** 🎎\n\n"
        f"By the power of {random.choice(['anime romance', 'shoujo tropes', 'k-drama fate'])},\n"
        f"we unite {user1_mention} and {user2_mention} in {random.choice(['virtual', 'wholesome', 'dramatic'])} love!\n\n"
        f"✿.｡.:* ☆:**:. {emoji} .:**:.☆*.:｡.✿\n\n"
        f"May your {random.choice(['ship', 'relationship', 'love story'])} be filled with:\n"
        f"• {random.choice(['Blushing confessions', 'Accidental hand touches', 'Dramatic rain scenes'])}\n"
        f"• {random.choice(['Shared boba teas', 'Protective moments', 'Tsundere denial'])}",

        f"🔥💥 **HOT NEW COUPLE ALERT** 💥🔥\n\n"
        f"BREAKING NEWS: Romance blooms in the chat!\n"
        f"Today's {random.choice(['hottest', 'cutest', 'most unexpected'])} couple is:\n\n"
        f"▄︻デ══━ {user1_mention} ♡ {user2_mention} ══━︻▄\n\n"
        f"Relationship Status: {random.choice(['Official', \"It's complicated\", 'Secret dating'])}\n"
        f"Fan Rating: {love_percent}/100 {emoji}\n\n"
        f"#Ship{ship_name.upper()}"
    ]
    return random.choice(templates)

# -------------------- Command Handlers -------------------- #
@Gojo.on_message(command("waifu"))
async def waifu_cmd(c: Gojo, m: Message):
    if m.chat.type == "private":
        return await m.reply_text("This command only works in groups!")

    members = [
        member.user
        async for member in m.chat.get_members()
        if not member.user.is_bot and member.user.id != m.from_user.id
    ]
    if not members:
        return await m.reply_text("Couldn't find anyone worthy to be your waifu 😢")

    waifu = random.choice(members)
    message = await generate_waifu_message(m.from_user.mention, waifu.mention)
    await m.reply_text(message, disable_web_page_preview=True)


@Gojo.on_message(command(["couple", "pair", "ship"]))
async def couple_cmd(c: Gojo, m: Message):
    if m.chat.type == "private":
        return await m.reply_text("This command only works in groups!")

    members = [
        member.user
        async for member in m.chat.get_members()
        if not member.user.is_bot
    ]
    if len(members) < 2:
        return await m.reply_text("Need at least 2 members to form a couple!")

    user1, user2 = random.sample(members, 2)
    message = await generate_couple_message(user1.mention, user2.mention)
    await m.reply_text(message, disable_web_page_preview=True)

# -------------------- Help -------------------- #
__PLUGIN__ = "waifu_couple"
__HELP__ = """
**💖 Waifu & Couple Commands 💖**

• `/waifu` - Choose a random member as your waifu/husbando.
• `/couple` or `/pair` - Choose two random members as today's couple.

✨ *No images needed — pure romantic magic!* ✨
"""
