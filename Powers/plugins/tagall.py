import asyncio
from random import choice
from pyrogram import filters
from pyrogram.enums import ParseMode as PM, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Track ongoing tagging sessions
ACTIVE_TAGS = {}

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
        [member.user.mention for member in members if not member.user.is_bot and not member.user.is_deleted]
    )


async def send_in_batches(c, chat_id, members, base_msg, style):
    """Send mentions in batches of 5 users per message with delay"""
    batch = []
    for i, member in enumerate(members, start=1):
        if chat_id not in ACTIVE_TAGS or not ACTIVE_TAGS[chat_id]:
            # Tagging canceled
            break

        if not member.user.is_bot and not member.user.is_deleted:
            batch.append(member)

        if len(batch) == 5 or i == len(members):
            mentions = await get_mentions(batch)
            if mentions:  # send only if there are valid mentions
                text = style.format(msg=base_msg, mentions=mentions)
                await c.send_message(chat_id, text, parse_mode=PM.MARKDOWN)
                await asyncio.sleep(1.5)  # delay to avoid flood
            batch.clear()


@Gojo.on_message(command(["tagall", "all", "callall"]) & filters.group)
async def tag_all(c: Gojo, m: Message):
    """Tags all members in the group with random style, supports text or reply."""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True  # Mark tagging as active

    # Determine message content
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = " "

    members = []
    async for member in c.get_chat_members(chat.id):
        if not member.user.is_bot and not member.user.is_deleted:
            members.append(member)

    if not members:
        ACTIVE_TAGS.pop(chat.id, None)
        return await m.reply_text("No valid members found to tag.")

    style = choice(TAGALL_STYLES)
    await send_in_batches(c, chat.id, members, base_msg, style)

    ACTIVE_TAGS.pop(chat.id, None)  # Clear when done


@Gojo.on_message(command(["atag", "admincall"]) & filters.group)
async def tag_admins(c: Gojo, m: Message):
    """Tags only admins in batches."""
    chat = m.chat
    ACTIVE_TAGS[chat.id] = True  # Mark tagging as active

    # Determine message content
    if m.reply_to_message:
        base_msg = m.reply_to_message.text or ""
    elif len(m.command) > 1:
        base_msg = m.text.split(None, 1)[1]
    else:
        base_msg = " "

    admins = []
    async for member in c.get_chat_members(chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
        if (
            member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
            and not member.user.is_bot
            and not member.user.is_deleted
        ):
            admins.append(member)

    if not admins:
        ACTIVE_TAGS.pop(chat.id, None)
        return await m.reply_text("No valid admins found to tag.")

    await send_in_batches(c, chat.id, admins, base_msg, ADMIN_STYLE)

    ACTIVE_TAGS.pop(chat.id, None)  # Clear when done


@Gojo.on_message(command(["cancel"]) & filters.group)
async def cancel_tagging(c: Gojo, m: Message):
    """Cancels the current tagging process in the chat."""
    chat = m.chat
    if chat.id in ACTIVE_TAGS and ACTIVE_TAGS[chat.id]:
        ACTIVE_TAGS[chat.id] = False
        await m.reply_text("🚫 Tagging process has been cancelled.")
    else:
        await m.reply_text("No active tagging process to cancel.")


__PLUGIN__ = "tagall"

_DISABLE_CMDS_ = ["tagall", "all", "callall", "atag", "admincall", "cancel"]

__alt_name__ = ["all", "callall", "admincall", "cancel"]

__HELP__ = """
**Tagging Commands**
• /tagall [text] — Tag all members (batch of 5 per message, with delay)
• Reply to a message with /tagall — Tags all under that replied message
• /atag [text] — Tag only admins
• Reply to a message with /atag — Tags all admins under that replied message
• /cancel — Cancel the current tagging process
"""
