from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode as PM, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Different styles for tagall
TAGALL_STYLES = [
    "🔥 Attention everyone!\n\n{msg}\n\n{mentions}",
    "👋 Hey guys, gather up:\n\n{msg}\n\n{mentions}",
    "🚨 ALERT 🚨\n\n{msg}\n\n{mentions}",
    "✨ Summoning everyone ✨\n\n{msg}\n\n{mentions}",
    "📢 Important notice for:\n\n{msg}\n\n{mentions}",
    "🌀 Yo squad! Check in:\n\n{msg}\n\n{mentions}"
]

# Admin tag style
ADMIN_STYLE = "🛡 Calling all admins:\n\n{msg}\n\n{mentions}"


async def get_mentions(members):
    """Return a string of mentions from a list of ChatMember objects"""
    return " ".join(
        [member.user.mention for member in members if not member.user.is_bot]
    )


async def send_in_batches(c, chat_id, members, base_msg, style):
    """Send mentions in batches of 10 users per message"""
    batch = []
    for i, member in enumerate(members, start=1):
        if not member.user.is_bot:
            batch.append(member)
        if len(batch) == 10 or i == len(members):
            mentions = await get_mentions(batch)
            text = style.format(msg=base_msg, mentions=mentions)
            await c.send_message(chat_id, text, parse_mode=PM.MARKDOWN)
            batch.clear()


@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all(c: Gojo, m: Message):
    """Tags all members in the group with random style, supports text or reply."""
    chat = m.chat

    # Determine message content
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = " "

    members = []
    async for member in c.get_chat_members(chat.id):
        if not member.user.is_bot:
            members.append(member)

    if not members:
        return await m.reply_text("No members found to tag.")

    style = choice(TAGALL_STYLES)
    await send_in_batches(c, chat.id, members, base_msg, style)


@Gojo.on_message(command(["atag", "admincall"]) & filters.group)
async def tag_admins(c: Gojo, m: Message):
    """Tags only admins in batches."""
    chat = m.chat

    # Determine message content
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = " "

    admins = []
    async for member in c.get_chat_members(chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER] and not member.user.is_bot:
            admins.append(member)

    if not admins:
        return await m.reply_text("No admins found to tag.")

    await send_in_batches(c, chat.id, admins, base_msg, ADMIN_STYLE)


__PLUGIN__ = "tagall"

_DISABLE_CMDS_ = ["tagall", "all", "callall", "atag", "admincall"]

__alt_name__ = ["all", "callall", "admincall"]

__HELP__ = """
**Tagging Commands**
• /tagall [text] — Tag all members (batch of 10 per message)
• Reply to a message with /tagall — Tags all under that replied message
• /atag [text] — Tag only admins
• Reply to a message with /atag — Tags all admins under that replied message
"""
