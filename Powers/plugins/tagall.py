from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode as PM, ChatMemberStatus
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Different styles for tagall
TAGALL_STYLES = [
    "🔥 Attention everyone!\n\n{mentions}",
    "👋 Hey guys, gather up:\n\n{mentions}",
    "🚨 ALERT 🚨\n\n{mentions}",
    "✨ Summoning everyone ✨\n\n{mentions}",
    "📢 Important notice for:\n\n{mentions}",
    "🌀 Yo squad! Check in:\n\n{mentions}"
]

# Admin tag style
ADMIN_STYLE = "🛡 Calling all admins:\n\n{mentions}"


async def get_mentions(members):
    """Return a string of mentions from a list of ChatMember objects"""
    return " ".join(
        [member.user.mention for member in members if not member.user.is_bot]
    )


@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all(c: Gojo, m: Message):
    """Tags all members in the group with random style."""
    chat = m.chat

    members = []
    async for member in c.get_chat_members(chat.id):
        if not member.user.is_bot:
            members.append(member)

    if not members:
        return await m.reply_text("No members found to tag.")

    mentions = await get_mentions(members)
    style = choice(TAGALL_STYLES).format(mentions=mentions)

    await m.reply_text(style, parse_mode=PM.MARKDOWN)


async for member in c.get_chat_members(chat.id, filter=ChatMembersFilter.ADMINISTRATORS):


__PLUGIN__ = "tagall"

_DISABLE_CMDS_ = ["tagall", "all", "callall", "atag", "admincall"]

__alt_name__ = ["all", "callall", "admincall"]

__HELP__ = """
**Tagging Commands**
• /tagall (/all, /callall) — Tag all members in the group (random style)
• /atag (/admincall) — Tag only admins
"""
