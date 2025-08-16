from asyncio import sleep
from html import escape
from os import remove, path
from tempfile import NamedTemporaryFile
from traceback import format_exc
from typing import Tuple

import re
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS, ChatType
from pyrogram.errors import (
    BotChannelsNa,
    ChatAdminInviteRequired,
    ChatAdminRequired,
    FloodWait,
    RightForbidden,
    RPCError,
    UserAdminInvalid,
)
from html import escape

def mention_html(name: str, user_id: int) -> str:
    """Return an HTML mention of a user."""
    name = escape(name)
    return f'<a href="tg://user?id={user_id}">{name}</a>'

from pyrogram.types import ChatPrivileges, Message

from Powers import LOGGER, OWNER_ID
from Powers.bot_class import Gojo
from Powers.database.approve_db import Approve
from Powers.database.reporting_db import Reporting
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload, TEMP_ADMIN_CACHE_BLOCK
from Powers.utils.custom_filters import admin_filter, command, promote_filter
from Powers.utils.extract_user import extract_user


# -----------------------------
# Admin list
# -----------------------------
@Gojo.on_message(command("adminlist"))
async def adminlist_show(c: Gojo, m: Message) -> None:
    """List all admins in the chat with proper formatting."""
    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        await m.reply_text("This command is made for groups only!")
        return

    try:
        # Try to get cached admin list first
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            note = "Note: These are cached values!"
        except KeyError:
            admin_list = await admin_cache_reload(m, "adminlist")
            note = "Note: These are up-to-date values!"

        # Prepare the admin list message
        admin_str = f"Admins in <b>{escape(m.chat.title)}</b>:\n\n"

        # Separate bots and human admins
        bot_admins = []
        user_admins = []
        
        for admin in admin_list:
            if isinstance(admin[1], str) and admin[1].lower().endswith("bot"):
                bot_admins.append(admin)
            else:
                user_admins.append(admin)

        # Format admin mentions - modified to not use await
        def format_admin(admin: Tuple[int, str, bool]) -> str:
            if admin[1].startswith("@"):
                return admin[1]
            return f"<a href='tg://user?id={admin[0]}'>{escape(admin[1])}</a>"

        # Format user admins (non-bots)
        mention_users = []
        for admin in user_admins:
            if not admin[2]:  # Skip anonymous admins
                mention_users.append(format_admin(admin))

        # Format bot admins
        mention_bots = []
        for admin in bot_admins:
            mention_bots.append(format_admin(admin))

        # Sort alphabetically (case-insensitive)
        mention_users.sort(key=lambda x: x.lower())
        mention_bots.sort(key=lambda x: x.lower())

        # Build the final message
        admin_str += "<b>User Admins:</b>\n" + "\n".join(f"• {user}" for user in mention_users)
        admin_str += "\n\n<b>Bots:</b>\n" + "\n".join(f"• {bot}" for bot in mention_bots)

        # Send the message with HTML parsing
        await m.reply_text(
            f"{admin_str}\n\n<i>{note}</i>",
            parse_mode="html",
            disable_web_page_preview=True
        )

    except Exception as ef:
        LOGGER.error(f"Error in adminlist: {ef}\n{format_exc()}")
        await m.reply_text(
            "An error occurred while fetching admin list.\n"
            f"Error: {escape(str(ef))}"
        )

# -----------------------------
# Tag admins
# -----------------------------
@Gojo.on_message(filters.regex(r"^(?i)@admin(s)?") & filters.group)
async def tag_admins(c: Gojo, m: Message) -> None:
    """Tag all admins in one mention when someone uses @admin."""
    db = Reporting(m.chat.id)
    if not db.get_settings():
        return

    try:
        admin_list = ADMIN_CACHE[m.chat.id]
    except KeyError:
        admin_list = await admin_cache_reload(m, "adminlist")

    # Filter out bots and get only user admins
    user_admins = [admin[0] for admin in admin_list if not admin[1].lower().endswith("bot")]
    
    if not user_admins:
        return await m.reply_text("No admins available to tag in this group!")

    try:
        # Create one big mention of all admins
        admin_mentions = []
        for user_id in user_admins:
            try:
                user = await c.get_users(user_id)
                admin_mentions.append(user.mention)
            except Exception:
                continue
        
        if not admin_mentions:
            return await m.reply_text("Couldn't fetch any admin information!")

        # Format the message with sender's name and all admin mentions
        message_text = (
            f"🚨 {m.from_user.mention} is calling for admins! 🚨\n\n"
            f"Admins: {' '.join(admin_mentions)}"
        )

        await m.reply_text(
            message_text,
            disable_web_page_preview=True,
            disable_notification=True  # To avoid spammy notifications
        )
        
    except Exception as e:
        LOGGER.error(f"Error in tag_admins: {e}\n{format_exc()}")
        await m.reply_text("Failed to tag admins. Please try again later.")
# -----------------------------
# Zombies (deleted accounts)
# -----------------------------
@Gojo.on_message(command("zombies") & admin_filter)
async def zombie_clean(c: Gojo, m: Message) -> None:
    """Clean deleted accounts from the group."""
    zombie_count = 0
    failed = 0
    wait_msg = await m.reply_text("Searching for deleted accounts...")

    async for member in c.get_chat_members(m.chat.id):
        if member.user.is_deleted:
            zombie_count += 1
            try:
                await c.ban_chat_member(m.chat.id, member.user.id)
            except UserAdminInvalid:
                failed += 1
            except FloodWait as e:
                await sleep(e.value)
                try:
                    await c.ban_chat_member(m.chat.id, member.user.id)
                except Exception:
                    failed += 1
            except Exception:
                failed += 1

    if zombie_count == 0:
        await wait_msg.edit_text("No deleted accounts found!")
        return

    await wait_msg.delete()
    result_text = (
        f"<b>{zombie_count}</b> deleted accounts found and "
        f"<b>{zombie_count - failed}</b> were banned!\n"
        f"<b>{failed}</b> accounts couldn't be banned."
    )

    await m.reply_animation(
        "https://graph.org/file/02a1dcf7788186ffb36cb.mp4",
        caption=result_text,
    )


# -----------------------------
# Admin cache reload
# -----------------------------
@Gojo.on_message(command("admincache"))
async def reload_admins(c: Gojo, m: Message) -> None:
    """Reload the admin cache."""
    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        await m.reply_text("This command is for groups only!")
        return

    SUPPORT_STAFF = get_support_staff()
    if (
        m.chat.id in TEMP_ADMIN_CACHE_BLOCK
        and m.from_user.id not in SUPPORT_STAFF
        and TEMP_ADMIN_CACHE_BLOCK[m.chat.id] == "manualblock"
    ):
        await m.reply_text("Can only reload admin cache once per 10 minutes!")
        return

    try:
        await admin_cache_reload(m, "admincache")
        TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "manualblock"
        await m.reply_text("Admin cache reloaded successfully!")
    except RPCError as ef:
        LOGGER.error(f"Error reloading admins: {ef}\n{format_exc()}")
        await m.reply_text(
            f"An error occurred. Report using `/bug`\n<b>Error:</b> <code>{escape(str(ef))}</code>"
        )


# -----------------------------
# Promote / Fullpromote / Demote
# -----------------------------
async def _promote_user(
    c: Gojo,
    m: Message,
    user_id: int,
    user_first_name: str,
    user_name: str,
    full_promote: bool = False,
) -> bool:
    """Helper function to promote users."""
    try:
        bot_member = await c.get_chat_member(m.chat.id, c.me.id)
        if not bot_member.privileges.can_promote_members:
            await m.reply_text("I don't have promote permissions!")
            return False

        try:
            admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
        except KeyError:
            admin_list = {i[0] for i in (await admin_cache_reload(m, "promote_cache_update"))}

        if user_id in admin_list:
            await m.reply_text("This user is already an admin!")
            return False

        if full_promote:
            privileges = bot_member.privileges
            default_title = "Gojo"
        else:
            privileges = ChatPrivileges(
                can_change_info=bot_member.privileges.can_change_info,
                can_invite_users=bot_member.privileges.can_invite_users,
                can_delete_messages=bot_member.privileges.can_delete_messages,
                can_restrict_members=bot_member.privileges.can_restrict_members,
                can_pin_messages=bot_member.privileges.can_pin_messages,
                can_manage_chat=bot_member.privileges.can_manage_chat,
                can_manage_video_chats=bot_member.privileges.can_manage_video_chats,
                can_post_messages=bot_member.privileges.can_post_messages,
                can_edit_messages=bot_member.privileges.can_edit_messages,
            )
            default_title = "Itadori"

        title = default_title
        if len(m.text.split()) >= (3 if not m.reply_to_message else 2):
            title = " ".join(m.text.split()[2:16]) if not m.reply_to_message else " ".join(m.text.split()[1:16])

        await m.chat.promote_member(user_id=user_id, privileges=privileges)

        if m.chat.type in (ChatType.SUPERGROUP, ChatType.GROUP):
            try:
                await c.set_administrator_title(m.chat.id, user_id, title)
            except Exception as e:
                LOGGER.error(f"Error setting title: {e}\n{format_exc()}")

        try:
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, user_name or user_first_name))
            ADMIN_CACHE[m.chat.id] = admins_group
        except KeyError:
            await admin_cache_reload(m, "promote_key_error")

        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        await m.reply_text(
            f"{mention_html(m.from_user.first_name, m.from_user.id)} "
            f"{'fully promoted' if full_promote else 'promoted'} "
            f"{mention_html(user_first_name, user_id)} in "
            f"<b>{escape(m.chat.title)}</b> with title: <code>{escape(title)}</code>"
        )
        return True

    except (ChatAdminRequired, RightForbidden):
        await m.reply_text("I don't have enough rights to promote this user.")
    except UserAdminInvalid:
        await m.reply_text("I can't act on this user (maybe I didn't promote them originally).")
    except RPCError as e:
        LOGGER.error(f"Promote error: {e}\n{format_exc()}")
        await m.reply_text(
            f"An error occurred. Report using `/bug`\n<b>Error:</b> <code>{escape(str(e))}</code>"
        )
    return False


@Gojo.on_message(command("fullpromote") & promote_filter)
async def fullpromote_usr(c: Gojo, m: Message) -> None:
    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text("Reply to a user or provide their username/ID!")
        return

    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return

    if user_id == c.me.id:
        await m.reply_text("I can't promote myself!")
        return

    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and user.status != CMS.OWNER:
        await m.reply_text("Only the chat owner can use this command!")
        return

    await _promote_user(c, m, user_id, user_first_name, user_name, full_promote=True)


@Gojo.on_message(command("promote") & promote_filter)
async def promote_usr(c: Gojo, m: Message) -> None:
    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text("Reply to a user or provide their username/ID!")
        return

    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return

    if user_id == c.me.id:
        await m.reply_text("I can't promote myself!")
        return

    await _promote_user(c, m, user_id, user_first_name, user_name)


@Gojo.on_message(command("demote") & promote_filter)
async def demote_usr(c: Gojo, m: Message) -> None:
    """Demote a user."""
    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text("Reply to a user or provide their username/ID!")
        return

    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return

    try:
        await c.promote_chat_member(
            m.chat.id,
            user_id,
            privileges=ChatPrivileges()
        )
        await m.reply_text(
            f"{mention_html(m.from_user.first_name, m.from_user.id)} demoted "
            f"{mention_html(user_first_name, user_id)} in <b>{escape(m.chat.title)}</b>"
        )

        try:
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group = [a for a in admins_group if a[0] != user_id]
            ADMIN_CACHE[m.chat.id] = admins_group
        except KeyError:
            await admin_cache_reload(m, "demote_cache_reload")

    except RPCError as e:
        await m.reply_text(f"Failed to demote: <code>{escape(str(e))}</code>")

# -----------------------------
# Set group photo
# -----------------------------
@Gojo.on_message(command("setgpic") & admin_filter)
async def set_group_photo(c: Gojo, m: Message):
    """Change group photo."""
    if m.reply_to_message and m.reply_to_message.photo:
        photo = m.reply_to_message.photo.file_id
    elif m.text and len(m.text.split()) > 1:
        photo = m.text.split(maxsplit=1)[1]
    else:
        await m.reply_text("Reply to a photo or provide a file ID!")
        return

    try:
        await c.set_chat_photo(m.chat.id, photo)
        await m.reply_text("✅ Group photo updated successfully!")
    except RPCError as e:
        await m.reply_text(f"Failed to set group photo: <code>{escape(str(e))}</code>")


# -----------------------------
# Set group title
# -----------------------------
@Gojo.on_message(command("setgtitle") & admin_filter)
async def set_group_title(c: Gojo, m: Message):
    """Change group title."""
    if len(m.text.split()) < 2:
        await m.reply_text("Provide the new group title!")
        return

    title = m.text.split(maxsplit=1)[1]
    try:
        await c.set_chat_title(m.chat.id, title)
        await m.reply_text(f"✅ Group title updated to <b>{escape(title)}</b>", parse_mode="html")
    except RPCError as e:
        await m.reply_text(f"Failed to set group title: <code>{escape(str(e))}</code>")


# -----------------------------
# Set group description
# -----------------------------
@Gojo.on_message(command("setgdes") & admin_filter)
async def set_group_description(c: Gojo, m: Message):
    """Change group description."""
    if len(m.text.split()) < 2:
        await m.reply_text("Provide the new group description!")
        return

    description = m.text.split(maxsplit=1)[1]
    try:
        await c.set_chat_description(m.chat.id, description)
        await m.reply_text("✅ Group description updated!")
    except RPCError as e:
        await m.reply_text(f"Failed to set group description: <code>{escape(str(e))}</code>")


# -----------------------------
# Change own admin title
# -----------------------------
@Gojo.on_message(command("title") & admin_filter)
async def change_admin_title(c: Gojo, m: Message):
    """Change the title of yourself or a promoted admin."""
    if len(m.text.split()) < 2:
        await m.reply_text("Provide a new admin title!")
        return

    title = m.text.split(maxsplit=1)[1]
    try:
        await c.set_administrator_title(m.chat.id, m.from_user.id, title)
        await m.reply_text(f"✅ Your admin title changed to <b>{escape(title)}</b>", parse_mode="html")
    except RPCError as e:
        await m.reply_text(f"Failed to change admin title: <code>{escape(str(e))}</code>")


# -----------------------------
# Get or create group invite link
# -----------------------------
@Gojo.on_message(command("invitelink") & admin_filter)
async def get_invite_link(c: Gojo, m: Message):
    """Fetch or create a group invite link."""
    try:
        chat = await c.get_chat(m.chat.id)
        if chat.invite_link:
            link = chat.invite_link
        else:
            link = await c.create_chat_invite_link(m.chat.id)
        await m.reply_text(f"🔗 Invite link: <code>{escape(link.invite_link)}</code>", parse_mode="html")
    except ChatAdminInviteRequired:
        await m.reply_text("I need 'Invite Users via Link' permission to create a link!")
    except RPCError as e:
        await m.reply_text(f"Failed to get/create invite link: <code>{escape(str(e))}</code>")



__PLUGIN__ = "admin"
__alt_name__ = [
    "admins",
    "promote",
    "demote",
    "adminlist",
    "setgpic",
    "title",
    "setgtitle",
    "fullpromote",
    "invitelink",
    "setgdes",
    "zombies",
]
__HELP__ = """
**Admin Tools**

**User Commands:**
• /adminlist - List all admins in the chat

**Admin Commands:**
• /invitelink - Get chat invite link
• /promote (<title>) - Promote a user (optional title)
• /fullpromote (<title>) - Fully promote a user with all permissions (owner only)
• /demote - Demote an admin
• /setgpic - Set group photo (reply to image)
• /admincache - Reload admin list
• /zombies - Ban deleted accounts (owner only)
• /title <title> - Set custom admin title for promoted users
• /setgtitle <title> - Set group title
• /setgdes <description> - Set group description

**Examples:**
`/promote @username` - Promote a user
`/promote @username Cool Admin` - Promote with custom title
`/title @username New Title` - Change admin's title
"""
