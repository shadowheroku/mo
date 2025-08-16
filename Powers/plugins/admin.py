from asyncio import sleep
from html import escape
from os import remove
from traceback import format_exc
from typing import Dict, List, Set, Tuple, Union

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import (
    BotChannelsNa,
    ChatAdminInviteRequired,
    ChatAdminRequired,
    FloodWait,
    RightForbidden,
    RPCError,
    UserAdminInvalid,
)
from pyrogram.types import ChatPrivileges, Message

from Powers import LOGGER, OWNER_ID
from Powers.bot_class import Gojo
from Powers.database.approve_db import Approve
from Powers.database.reporting_db import Reporting
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload, TEMP_ADMIN_CACHE_BLOCK
from Powers.utils.custom_filters import admin_filter, command, promote_filter
from Powers.utils.extract_user import extract_user
from Powers.utils.parser import mention_html


@Gojo.on_message(command("adminlist"))
async def adminlist_show(c: Gojo, m: Message) -> None:
    """List all admins in the chat."""
    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        await m.reply_text("This command is made for groups only!")
        return

    try:
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            note = "<i>Note:</i> These are cached values!"
        except KeyError:
            admin_list = await admin_cache_reload(m, "adminlist")
            note = "<i>Note:</i> These are up-to-date values!"

        admin_str = f"Admins in <b>{escape(m.chat.title)}</b>:\n\n"
        
        # Separate bots and human admins
        bot_admins = [i for i in admin_list if i[1].lower().endswith("bot")]
        user_admins = [i for i in admin_list if not i[1].lower().endswith("bot")]
        
        # Format mentions
        def format_admin(admin: Tuple[int, str, bool]) -> str:
            return (
                admin[1] if admin[1].startswith("@") 
                else mention_html(admin[1], admin[0])
            )

        mention_users = [format_admin(admin) for admin in user_admins if not admin[2]]
        mention_bots = [format_admin(admin) for admin in bot_admins]
        
        # Sort alphabetically
        mention_users.sort(key=lambda x: x[1].lower())
        mention_bots.sort(key=lambda x: x[1].lower())
        
        admin_str += "<b>User Admins:</b>\n" + "\n".join(f"- {i}" for i in mention_users)
        admin_str += "\n\n<b>Bots:</b>\n" + "\n".join(f"- {i}" for i in mention_bots)
        
        await m.reply_text(f"{admin_str}\n\n{note}")

    except Exception as ef:
        if str(ef) == str(m.chat.id):
            await m.reply_text("Use /admincache to reload admins!")
        else:
            LOGGER.error(f"Error in adminlist: {ef}\n{format_exc()}")
            await m.reply_text(
                f"An error occurred. Report using `/bug`\n<b>Error:</b> <code>{escape(str(ef))}</code>"
            )


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


@Gojo.on_message(filters.regex(r"^(?i)@admin(s)?") & filters.group)
async def tag_admins(c: Gojo, m: Message) -> None:
    """Tag admins in the group."""
    db = Reporting(m.chat.id)
    if not db.get_settings():
        return

    try:
        admin_list = ADMIN_CACHE[m.chat.id]
    except KeyError:
        admin_list = await admin_cache_reload(m, "adminlist")

    user_admins = [i for i in admin_list if not i[1].lower().endswith("bot")]
    mention_users = [mention_html("\u2063", admin[0]) for admin in user_admins]
    mention_str = "".join(mention_users)
    
    await m.reply_text(
        f"{mention_html(m.from_user.first_name, m.from_user.id)} "
        f"reported the message to admins!{mention_str}"
    )


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

        # Check if user is already admin
        try:
            admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
        except KeyError:
            admin_list = {i[0] for i in (await admin_cache_reload(m, "promote_cache_update"))}

        if user_id in admin_list:
            await m.reply_text("This user is already an admin!")
            return False

        # Set privileges based on promotion type
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

        # Get custom title if provided
        title = default_title
        if len(m.text.split()) >= (3 if not m.reply_to_message else 2):
            title = " ".join(m.text.split()[2:16]) if not m.reply_to_message else " ".join(m.text.split()[1:16])

        # Perform promotion
        await m.chat.promote_member(user_id=user_id, privileges=privileges)
        
        # Set admin title
        if m.chat.type in (ChatType.SUPERGROUP, ChatType.GROUP):
            try:
                await c.set_administrator_title(m.chat.id, user_id, title)
            except Exception as e:
                LOGGER.error(f"Error setting title: {e}\n{format_exc()}")

        # Update admin cache
        try:
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, user_name or user_first_name))
            ADMIN_CACHE[m.chat.id] = admins_group
        except KeyError:
            await admin_cache_reload(m, "promote_key_error")

        # Remove from approved users if they were approved
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
    """Fully promote a user with all bot's privileges."""
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

    # Only chat owner can use fullpromote
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and user.status != CMS.OWNER:
        await m.reply_text("Only the chat owner can use this command!")
        return

    await _promote_user(c, m, user_id, user_first_name, user_name, full_promote=True)


@Gojo.on_message(command("promote") & promote_filter)
async def promote_usr(c: Gojo, m: Message) -> None:
    """Promote a user with basic admin privileges."""
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

    await _promote_user(c, m, user_id, user_first_name, user_name, full_promote=False)


@Gojo.on_message(command("demote") & promote_filter)
async def demote_usr(c: Gojo, m: Message) -> None:
    """Demote an admin."""
    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text("Reply to a user or provide their username/ID!")
        return

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return

    if user_id == c.me.id:
        await m.reply_text("Get an admin to demote me!")
        return

    # Check if user is actually an admin
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {i[0] for i in (await admin_cache_reload(m, "demote_cache_update"))}

    if user_id not in admin_list:
        await m.reply_text("This user isn't an admin!")
        return

    try:
        await m.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(can_manage_chat=False),
        )

        # Update admin cache
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            admin_list = [admin for admin in admin_list if admin[0] != user_id]
            ADMIN_CACHE[m.chat.id] = admin_list
        except (KeyError, StopIteration):
            await admin_cache_reload(m, "demote_key_stopiter_error")

        await m.reply_text(
            f"{mention_html(m.from_user.first_name, m.from_user.id)} "
            f"demoted {mention_html(user_first_name, user_id)} in "
            f"<b>{escape(m.chat.title)}</b>!"
        )

    except (ChatAdminRequired, RightForbidden):
        await m.reply_text("I don't have permission to demote users!")
    except UserAdminInvalid:
        await m.reply_text("I can't act on this user (maybe I didn't promote them originally).")
    except BotChannelsNa:
        await m.reply_text("Cannot demote bots due to Telegram restrictions. Please demote manually.")
    except RPCError as ef:
        LOGGER.error(f"Demote error: {ef}\n{format_exc()}")
        await m.reply_text(
            f"An error occurred. Report using `/bug`\n<b>Error:</b> <code>{escape(str(ef))}</code>"
        )


@Gojo.on_message(command("invitelink"))
async def get_invitelink(c: Gojo, m: Message) -> None:
    """Get the chat invite link."""
    # Bypass the bot devs, sudos and owner
    DEV_LEVEL = get_support_staff("dev_level")
    
    if m.from_user.id not in DEV_LEVEL:
        user = await m.chat.get_member(m.from_user.id)
        if not user.privileges.can_invite_users and user.status != CMS.OWNER:
            await m.reply_text("You don't have invite permissions!")
            return

    try:
        link = await c.export_chat_invite_link(m.chat.id)
        await m.reply_text(
            f"Invite link for <b>{escape(m.chat.title)}</b>:\n<code>{link}</code>",
            disable_web_page_preview=True,
        )
    except (ChatAdminRequired, ChatAdminInviteRequired, RightForbidden):
        await m.reply_text("I don't have permission to get invite links!")
    except RPCError as ef:
        LOGGER.error(f"Invitelink error: {ef}\n{format_exc()}")
        await m.reply_text(
            f"An error occurred. Report using `/bug`\n<b>Error:</b> <code>{escape(str(ef))}</code>"
        )


@Gojo.on_message(command("setgtitle") & admin_filter)
async def setgtitle(c: Gojo, m: Message) -> None:
    """Set group title."""
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        await m.reply_text("You don't have permission to change group info!")
        return

    if len(m.text.split()) < 2:
        await m.reply_text("Please provide a new title!")
        return

    new_title = m.text.split(None, 1)[1]
    try:
        old_title = m.chat.title
        await m.chat.set_title(new_title)
        await m.reply_text(
            f"Successfully changed group title from <b>{escape(old_title)}</b> "
            f"to <b>{escape(new_title)}</b>"
        )
    except Exception as e:
        LOGGER.error(f"Setgtitle error: {e}\n{format_exc()}")
        await m.reply_text(f"Failed to change title: {e}")


@Gojo.on_message(command("setgdes") & admin_filter)
async def setgdes(c: Gojo, m: Message) -> None:
    """Set group description."""
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        await m.reply_text("You don't have permission to change group info!")
        return

    if len(m.text.split()) < 2:
        await m.reply_text("Please provide a new description!")
        return

    new_des = m.text.split(None, 1)[1]
    try:
        old_des = m.chat.description or "None"
        await m.chat.set_description(new_des)
        await m.reply_text(
            f"Successfully changed group description from <b>{escape(old_des)}</b> "
            f"to <b>{escape(new_des)}</b>"
        )
    except Exception as e:
        LOGGER.error(f"Setgdes error: {e}\n{format_exc()}")
        await m.reply_text(f"Failed to change description: {e}")


@Gojo.on_message(command("title") & admin_filter)
async def set_user_title(c: Gojo, m: Message) -> None:
    """Set custom admin title."""
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_promote_members and user.status != CMS.OWNER:
        await m.reply_text("You don't have permission to set admin titles!")
        return

    if len(m.text.split()) < 2 and not m.reply_to_message:
        await m.reply_text("Please specify a user and title!")
        return

    try:
        user_id, _, _ = await extract_user(c, m)
        if not user_id:
            return await m.reply_text("Can't find that user!")
            
        if user_id == c.me.id:
            return await m.reply_text("Nice try, but no.")

        # Get title from message
        if m.reply_to_message:
            if len(m.text.split()) >= 2:
                title = m.text.split(None, 1)[1]
            else:
                return await m.reply_text("Please provide a title!")
        else:
            if len(m.text.split()) >= 3:
                title = m.text.split(None, 2)[2]
            else:
                return await m.reply_text("Please provide a title!")

        from_user = await c.get_users(user_id)
        await c.set_administrator_title(m.chat.id, from_user.id, title)
        await m.reply_text(
            f"Successfully set {mention_html(from_user.first_name, from_user.id)}'s "
            f"admin title to <code>{escape(title)}</code>"
        )
    except Exception as e:
        LOGGER.error(f"Title error: {e}\n{format_exc()}")
        await m.reply_text(f"Failed to set title: {e}")


@Gojo.on_message(command("setgpic") & admin_filter)
async def setgpic(c: Gojo, m: Message) -> None:
    """Set group photo (images only)."""
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        await m.reply_text("❌ You don't have permission to change group info!")
        return

    if not m.reply_to_message:
        await m.reply_text("ℹ️ Reply to a photo to set as group photo!")
        return

    if m.reply_to_message.photo:
        file_id = m.reply_to_message.photo.file_id
    elif m.reply_to_message.document and (m.reply_to_message.document.mime_type or "").startswith("image/"):
        file_id = m.reply_to_message.document.file_id
    else:
        await m.reply_text("❌ Only photos can be set as group photo!")
        return

    try:
        msg = await m.reply_text("⬇️ Downloading media...")
        media_bytes = await c.download_media(file_id, in_memory=True)
        
        if not media_bytes:
            await msg.edit_text("❌ Failed to download media!")
            return

        await msg.edit_text("🖼️ Setting group photo...")

        from io import BytesIO
        bio = BytesIO(media_bytes)
        bio.name = "group_photo.jpg"  # Pyrogram requires a filename attribute
        bio.seek(0)

        await m.chat.set_photo(photo=bio)
        await msg.edit_text("✅ Group photo updated successfully!")

    except RPCError as e:
        await msg.edit_text(f"❌ Telegram error: {e}")
        LOGGER.error(f"Setgpic RPCError: {e}\n{format_exc()}")
    except Exception as e:
        await msg.edit_text(f"❌ Failed to set group photo: {e}")
        LOGGER.error(f"Setgpic error: {e}\n{format_exc()}")


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
