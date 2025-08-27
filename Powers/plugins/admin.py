from asyncio import sleep
from html import escape
from os import remove
from traceback import format_exc

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.enums import ChatType
from pyrogram.errors import (BotChannelsNa, ChatAdminInviteRequired,
                             ChatAdminRequired, FloodWait, RightForbidden,
                             RPCError, UserAdminInvalid)
from pyrogram.types import ChatPrivileges, Message

from Powers import LOGGER, OWNER_ID
from Powers.bot_class import Gojo
from Powers.database.approve_db import Approve
from Powers.database.reporting_db import Reporting
from Powers.supports import get_support_staff
from Powers.utils.caching import ADMIN_CACHE, admin_cache_reload
from Powers.utils.custom_filters import admin_filter, command, promote_filter
from Powers.utils.extract_user import extract_user
from Powers.utils.parser import mention_html

# A dictionary to keep track of cooldown per chat
TEMP_ADMIN_CACHE_BLOCK = {}


import traceback
import logging

LOGGER = logging.getLogger(__name__)

@Gojo.on_message(command("adminlist"))
async def adminlist_show(_, m: Message):
    global ADMIN_CACHE

    # ─── CHECK GROUP TYPE ───
    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return await m.reply_text(
            "⚠️ This command can only be used inside a <b>group chat</b>!",
        )

    try:
        # ─── LOAD ADMINS FROM CACHE ───
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            note = "⚡ <i>Showing cached results</i>"
        except KeyError:
            admin_list = await admin_cache_reload(m, "adminlist")
            note = "🔄 <i>Fetched fresh data</i>"

        if not admin_list:
            return await m.reply_text(
                "❌ Couldn’t fetch admin list. Try <code>/admincache</code> to reload."
            )

        # ─── SPLIT ADMINS ───
        bot_admins = [i for i in admin_list if i[1].lower().endswith("bot")]
        user_admins = [i for i in admin_list if not i[1].lower().endswith("bot")]

        # ─── FORMAT USER ADMINS ───
        mention_users = []
        for admin in user_admins:
            if not admin[2]:  # Non-anonymous admin
                if admin[1].startswith("@"):
                    mention_users.append(admin[1])
                else:
                    mention_users.append(await mention_html(admin[1], admin[0]))

        # ─── FORMAT BOT ADMINS ───
        mention_bots = []
        for admin in bot_admins:
            if admin[1].startswith("@"):
                mention_bots.append(admin[1])
            else:
                mention_bots.append(await mention_html(admin[1], admin[0]))

        # ─── SORT RESULTS ───
        mention_users.sort(key=lambda x: x.lower())
        mention_bots.sort(key=lambda x: x.lower())

        # ─── FINAL MESSAGE ───
        adminstr = f"👮‍♂️ <b>Admins in {m.chat.title}</b>\n\n"
        adminstr += "👤 <b>User Admins:</b>\n"
        adminstr += "\n".join(f"• {i}" for i in mention_users) if mention_users else "• None"
        adminstr += "\n\n🤖 <b>Bot Admins:</b>\n"
        adminstr += "\n".join(f"• {i}" for i in mention_bots) if mention_bots else "• None"
        adminstr += f"\n\n{note}"

        await m.reply_text(adminstr, disable_web_page_preview=True)

    # ─── ERROR HANDLING ───
    except PermissionError:
        await m.reply_text("🚫 I don’t have enough permissions to fetch admins.")
    except TimeoutError:
        await m.reply_text("⏳ Timed out while fetching admins. Please try again.")
    except Exception as ef:
        LOGGER.error(f"[AdminListError] {ef}\n{traceback.format_exc()}")
        await m.reply_text(
            "⚠️ An unexpected error occurred while fetching admins.\n"
            f"<b>Error:</b> <code>{ef}</code>\n"
            "👉 Try using <code>/admincache</code> to refresh."
        )



@Gojo.on_message(command("zombies") & admin_filter)
async def zombie_clean(c: Gojo, m: Message):
    status = await m.reply_text("🔍 Scanning for deleted accounts...")
    zombies, banned, failed = 0, 0, 0

    try:
        async for member in c.get_chat_members(m.chat.id):
            if member.user.is_deleted:
                zombies += 1
                try:
                    await c.ban_chat_member(m.chat.id, member.user.id)
                    banned += 1
                except UserAdminInvalid:
                    failed += 1
                except ChatAdminRequired:
                    failed += 1
                except FloodWait as e:
                    await sleep(e.value)
                    try:
                        await c.ban_chat_member(m.chat.id, member.user.id)
                        banned += 1
                    except Exception:
                        failed += 1
                except RPCError:
                    failed += 1

        if zombies == 0:
            return await status.edit_text("✅ Group is already clean! No deleted accounts found.")

        await status.delete()

        caption = (
            f"🧹 <b>Zombies Cleanup Complete</b>\n\n"
            f"👥 <b>Total Zombies Found:</b> <code>{zombies}</code>\n"
            f"✅ <b>Banned Successfully:</b> <code>{banned}</code>\n"
            f"⚠️ <b>Failed / Immune:</b> <code>{failed}</code>"
        )

        await m.reply_animation(
            "https://graph.org/file/02a1dcf7788186ffb36cb.mp4",
            caption=caption,
        )

    except ChatAdminRequired:
        await status.edit_text("🚫 I need <b>Ban Users</b> permission to clean zombies.")
    except Exception as e:
        await status.edit_text(
            f"⚠️ An unexpected error occurred:\n<code>{e}</code>"
        )


LOGGER = logging.getLogger(__name__)


@Gojo.on_message(command("admincache"))
async def reload_admins(_, m: Message):
    global TEMP_ADMIN_CACHE_BLOCK

    # ─── GROUP CHECK ───
    if m.chat.type not in [ChatType.SUPERGROUP, ChatType.GROUP]:
        return await m.reply_text("⚠️ This command can only be used inside <b>groups</b>.")

    SUPPORT_STAFF = get_support_staff()

    # ─── RATE LIMIT: ONCE IN 10 MIN ───
    if (
        (m.chat.id in set(TEMP_ADMIN_CACHE_BLOCK.keys()))
        and (m.from_user.id not in SUPPORT_STAFF)
        and TEMP_ADMIN_CACHE_BLOCK[m.chat.id] == "manualblock"
    ):
        return await m.reply_text(
            "⏳ <b>Cooldown active:</b> You can only reload admin cache once every <b>10 minutes</b>."
        )

    status = await m.reply_text("🔄 Reloading admin cache...")

    try:
        await admin_cache_reload(m, "admincache")
        TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "manualblock"

        await status.edit_text("✅ <b>Admin cache refreshed successfully!</b>\nNow using updated admin list.")

    except ChatAdminRequired:
        await status.edit_text("🚫 I need <b>admin privileges</b> to reload the admin cache.")
    except FloodWait as e:
        await status.edit_text(f"⏳ FloodWait triggered. Retrying in {e.value} seconds...")
        await sleep(e.value)
        try:
            await admin_cache_reload(m, "admincache")
            TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "manualblock"
            await status.edit_text("✅ <b>Admin cache refreshed after waiting!</b>")
        except Exception as ex:
            await status.edit_text(
                f"⚠️ Retried but failed:\n<code>{ex}</code>"
            )
            LOGGER.error(f"[AdminCache-FloodWait] {ex}\n{traceback.format_exc()}")
    except RPCError as ef:
        await status.edit_text(
            f"⚠️ <b>RPC Error:</b>\n<code>{ef}</code>\n👉 Report this via <code>/bug</code>."
        )
        LOGGER.error(f"[AdminCache-RPCError] {ef}\n{traceback.format_exc()}")
    except Exception as e:
        await status.edit_text(
            f"⚠️ <b>Unexpected Error:</b>\n<code>{e}</code>"
        )
        LOGGER.error(f"[AdminCache-UnknownError] {e}\n{traceback.format_exc()}")


@Gojo.on_message(filters.regex(r"^(?i)@admin(s)?") & filters.group)
async def tag_admins(_, m: Message):
    db = Reporting(m.chat.id)
    if not db.get_settings():
        return
    try:
        admin_list = ADMIN_CACHE[m.chat.id]
    except KeyError:
        admin_list = await admin_cache_reload(m, "adminlist")
    user_admins = [i for i in admin_list if not (i[1].lower()).endswith("bot")]
    mention_users = [(await mention_html("\u2063", admin[0])) for admin in user_admins]
    mention_users.sort(key=lambda x: x[1])
    mention_str = "".join(mention_users)
    await m.reply_text(
        (
            f"{(await mention_html(m.from_user.first_name, m.from_user.id))}"
            f" reported the message to admins!{mention_str}"
        ),
    )


@Gojo.on_message(command("fullpromote") & promote_filter)
async def fullpromote_usr(c: Gojo, m: Message):
    global ADMIN_CACHE

    # ─── Sanity check ───
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await m.reply_text(
            "⚠️ I can’t promote <b>nobody</b>! Provide a username, user ID, or reply to a user."
        )

    # ─── Extract user ───
    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return await m.reply_text("❌ Failed to extract user. Try again with a valid input.")

    # ─── Prevent bot self-promotion ───
    if user_id == c.me.id:
        return await m.reply_text("😅 I can’t promote myself!")

    # ─── Bot privilege check ───
    bot = await c.get_chat_member(m.chat.id, c.me.id)
    if not bot.privileges or not bot.privileges.can_promote_members:
        return await m.reply_text("🚫 I don’t have <b>promote rights</b> in this chat!")

    # ─── User privilege check ───
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and user.status != ChatMemberStatus.OWNER:
        return await m.reply_text("⚠️ Only the <b>chat owner</b> can use this command!")

    # ─── Already admin check ───
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {i[0] for i in await admin_cache_reload(m, "promote_cache_update")}

    if user_id in admin_list:
        return await m.reply_text("ℹ️ This user is already an admin here.")

    # ─── Promote process ───
    try:
        # Promote with bot’s full rights
        await m.chat.promote_member(user_id=user_id, privileges=bot.privileges)

        # ─── Handle custom title ───
        title = "Lᴜɪᴛᴇɴᴀɴᴛ"  # default title
        args = m.text.split()

        if len(args) > 1 and not m.reply_to_message:
            title = " ".join(args[1:17])  # cap at 16 words
        elif m.reply_to_message and len(args) > 1:
            title = " ".join(args[1:17])

        title = title[:16]  # force trim to 16 chars

        try:
            await c.set_administrator_title(m.chat.id, user_id, title)
        except Exception as e:
            LOGGER.warning(f"Could not set admin title: {e}")

        # ─── Success message ───
        await m.reply_text(
            (
                "{promoter} ➕ promoted {promoted} in <b>{chat_title}</b>\n"
                "💼 Title set to: <code>{title}</code>"
            ).format(
                promoter=await mention_html(m.from_user.first_name, m.from_user.id),
                promoted=await mention_html(user_first_name, user_id),
                chat_title=html.escape(m.chat.title),
                title=title,
            )
        )

        # ─── Auto disapprove if approved ───
        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        # ─── Update cache ───
        try:
            inp1 = user_name or user_first_name
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, inp1, False))  # False = not anonymous
            ADMIN_CACHE[m.chat.id] = admins_group
        except Exception as e:
            LOGGER.error(f"Cache update failed: {e}")
            await admin_cache_reload(m, "promote_key_error")

    # ─── Error handling ───
    except ChatAdminRequired:
        await m.reply_text("🚫 I’m not an admin or I lack rights to promote users.")
    except RightForbidden:
        await m.reply_text("⚠️ I don’t have enough rights to promote this user.")
    except UserAdminInvalid:
        await m.reply_text("❌ Cannot act on this user (maybe I wasn’t the one who set their permissions).")
    except FloodWait as e:
        await m.reply_text(f"⏳ FloodWait: sleeping for {e.value}s before retrying...")
        await sleep(e.value)
        try:
            await m.chat.promote_member(user_id=user_id, privileges=bot.privileges)
        except Exception as ex:
            await m.reply_text(f"❌ Retry failed: <code>{ex}</code>")
            LOGGER.error(traceback.format_exc())
    except RPCError as e:
        await m.reply_text(f"⚠️ RPC Error:\n<code>{e}</code>\nReport using /bug.")
        LOGGER.error(traceback.format_exc())
    except Exception as e:
        await m.reply_text(f"⚠️ Unexpected error:\n<code>{e}</code>")
        LOGGER.error(traceback.format_exc())

@Gojo.on_message(command("promote") & promote_filter)
async def promote_usr(c: Gojo, m: Message):
    global ADMIN_CACHE

    # ─── Check input ───
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await m.reply_text(
            "⚠️ Reply to a user or give username/ID to promote them!"
        )

    # ─── Extract user ───
    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return await m.reply_text("❌ Failed to extract user. Try again with valid input.")

    # ─── Prevent bot self-promotion ───
    if user_id == c.me.id:
        return await m.reply_text("😅 I can’t promote myself!")

    # ─── Bot privilege check ───
    bot = await c.get_chat_member(m.chat.id, c.me.id)
    if not bot.privileges or not bot.privileges.can_promote_members:
        return await m.reply_text("🚫 I don’t have <b>promote rights</b> in this chat!")

    # ─── Ensure promoter is admin ───
    promoter = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and promoter.status not in [
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ]:
        return await m.reply_text("⚠️ Only <b>admins</b> can promote others!")

    # ─── Already admin check ───
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {i[0] for i in await admin_cache_reload(m, "promote_cache_update")}

    if user_id in admin_list:
        return await m.reply_text("ℹ️ This user is already an admin here.")

    # ─── Promote process ───
    try:
        await m.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(
                can_change_info=bot.privileges.can_change_info,
                can_invite_users=bot.privileges.can_invite_users,
                can_delete_messages=bot.privileges.can_delete_messages,
                can_restrict_members=bot.privileges.can_restrict_members,
                can_pin_messages=bot.privileges.can_pin_messages,
                can_manage_chat=bot.privileges.can_manage_chat,
                can_manage_video_chats=bot.privileges.can_manage_video_chats,
                can_post_messages=bot.privileges.can_post_messages,
                can_edit_messages=bot.privileges.can_edit_messages,
            ),
        )

        # ─── Handle custom title ───
        title = "Oғғɪᴄᴇʀ"  # Default
        args = m.text.split()

        if not m.reply_to_message and len(args) > 1:
            title = " ".join(args[1:17])  # limit 16 words
        elif m.reply_to_message and len(args) > 1:
            title = " ".join(args[1:17])

        title = title[:16]  # hard trim to 16 chars

        try:
            await c.set_administrator_title(m.chat.id, user_id, title)
        except Exception as e:
            LOGGER.warning(f"Could not set admin title: {e}")

        # ─── Success message ───
        await m.reply_text(
            (
                "{promoter} ➕ promoted {promoted} in <b>{chat_title}</b>\n"
                "💼 Title set to: <code>{title}</code>"
            ).format(
                promoter=await mention_html(m.from_user.first_name, m.from_user.id),
                promoted=await mention_html(user_first_name, user_id),
                chat_title=html.escape(m.chat.title),
                title=title,
            )
        )

        # ─── Auto disapprove if approved ───
        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        # ─── Update admin cache ───
        try:
            inp1 = user_name or user_first_name
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, inp1, False))
            ADMIN_CACHE[m.chat.id] = admins_group
        except Exception as e:
            LOGGER.error(f"Cache update failed: {e}")
            await admin_cache_reload(m, "promote_key_error")

    # ─── Error handling ───
    except ChatAdminRequired:
        await m.reply_text("🚫 I’m not admin or I lack rights to promote users.")
    except RightForbidden:
        await m.reply_text("⚠️ I don’t have enough rights to promote this user.")
    except UserAdminInvalid:
        await m.reply_text("❌ Cannot act on this user. Maybe I wasn’t the one who set their permissions.")
    except FloodWait as e:
        await m.reply_text(f"⏳ FloodWait: retrying after {e.value}s...")
        await sleep(e.value)
        try:
            await m.chat.promote_member(user_id=user_id, privileges=bot.privileges)
        except Exception as ex:
            await m.reply_text(f"❌ Retry failed: <code>{ex}</code>")
            LOGGER.error(traceback.format_exc())
    except RPCError as e:
        await m.reply_text(f"⚠️ RPC Error:\n<code>{e}</code>\nReport with /bug")
        LOGGER.error(traceback.format_exc())
    except Exception as e:
        await m.reply_text(f"⚠️ Unexpected error:\n<code>{e}</code>")
        LOGGER.error(traceback.format_exc())



@Gojo.on_message(command("demote") & promote_filter)
async def demote_usr(c: Gojo, m: Message):
    global ADMIN_CACHE

    # ─── Check input ───
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await m.reply_text("⚠️ Reply to a user or give username/ID to demote them.")

    # ─── Extract user ───
    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return await m.reply_text("❌ Failed to extract user. Try again with valid input.")

    # ─── Prevent bot self-demotion ───
    if user_id == c.me.id:
        return await m.reply_text("😅 Get an admin to demote me, I won’t demote myself!")

    # ─── Bot privilege check ───
    bot = await c.get_chat_member(m.chat.id, c.me.id)
    if not bot.privileges or not bot.privileges.can_promote_members:
        return await m.reply_text("🚫 I don’t have <b>demote rights</b> in this chat!")

    # ─── Ensure demoter is admin ───
    demoter = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and demoter.status not in [
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ]:
        return await m.reply_text("⚠️ Only <b>admins</b> can demote others!")

    # ─── Already admin check ───
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {i[0] for i in await admin_cache_reload(m, "demote_cache_update")}

    if user_id not in admin_list:
        return await m.reply_text("ℹ️ This user is not an admin here.")

    # ─── Demote process ───
    try:
        await m.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(  # remove all admin rights
                can_manage_chat=False,
                can_delete_messages=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                can_manage_video_chats=False,
                can_post_messages=False,
                can_edit_messages=False,
            ),
        )

        # ─── Remove from admin cache ───
        try:
            admin_group = ADMIN_CACHE.get(m.chat.id, [])
            admin_group = [u for u in admin_group if u[0] != user_id]
            ADMIN_CACHE[m.chat.id] = admin_group
        except Exception as e:
            LOGGER.error(f"Cache update failed: {e}")
            await admin_cache_reload(m, "demote_key_error")

        # ─── Success message ───
        await m.reply_text(
            (
                "{demoter} ➖ demoted {demoted} in <b>{chat_title}</b>!"
            ).format(
                demoter=await mention_html(m.from_user.first_name, m.from_user.id),
                demoted=await mention_html(user_first_name, user_id),
                chat_title=html.escape(m.chat.title),
            )
        )

    # ─── Error handling ───
    except ChatAdminRequired:
        await m.reply_text("🚫 I’m not admin or I lack rights to demote users.")
    except RightForbidden:
        await m.reply_text("⚠️ I don’t have enough rights to demote this user.")
    except UserAdminInvalid:
        await m.reply_text("❌ Cannot act on this user. Maybe I wasn’t the one who set their permissions.")
    except FloodWait as e:
        await m.reply_text(f"⏳ FloodWait: retrying after {e.value}s...")
        await sleep(e.value)
        try:
            await m.chat.promote_member(
                user_id=user_id,
                privileges=ChatPrivileges(),  # reset privileges again after wait
            )
        except Exception as ex:
            await m.reply_text(f"❌ Retry failed: <code>{ex}</code>")
            LOGGER.error(traceback.format_exc())
    except RPCError as e:
        await m.reply_text(f"⚠️ RPC Error:\n<code>{e}</code>\nReport with /bug")
        LOGGER.error(traceback.format_exc())
    except Exception as e:
        await m.reply_text(f"⚠️ Unexpected error:\n<code>{e}</code>")
        LOGGER.error(traceback.format_exc())

@Gojo.on_message(command("invitelink"))
async def get_invitelink(c: Gojo, m: Message):
    DEV_LEVEL = get_support_staff("dev_level")

    # ─── Permission check ───
    if m.from_user.id not in DEV_LEVEL:
        user = await m.chat.get_member(m.from_user.id)
        if (
            not user.privileges
            or not user.privileges.can_invite_users
        ) and user.status != CMS.OWNER:
            return await m.reply_text("🚫 You don’t have <b>invite rights</b> here!")

    # ─── Generate invite link ───
    try:
        link = await c.export_chat_invite_link(m.chat.id)

        await m.reply_text(
            text=(
                "✨ <b>Invite Link Generated!</b> ✨\n\n"
                f"👥 <b>Chat:</b> {m.chat.title}\n"
                f"🆔 <b>Chat ID:</b> <code>{m.chat.id}</code>\n"
                f"🔗 <b>Invite Link:</b> <a href='{link}'>Click Here</a>"
            ),
            disable_web_page_preview=True,
        )

    # ─── Errors ───
    except ChatAdminRequired:
        await m.reply_text("⚠️ I need to be <b>admin</b> to create invite links.")
    except ChatAdminInviteRequired:
        await m.reply_text("🚫 I don’t have <b>invite link permission</b>.")
    except RightForbidden:
        await m.reply_text("❌ You are not allowed to generate invite links here.")
    except RPCError as e:
        await m.reply_text(
            f"⚠️ Unexpected error occurred!\n\n"
            f"📨 Report using <code>/bug</code>\n"
            f"<b>Error:</b> <code>{e}</code>"
        )
        LOGGER.error(e)
        LOGGER.error(format_exc())


@Gojo.on_message(command("setgtitle") & admin_filter)
async def setgtitle(_, m: Message):
    # Check permissions
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges or (not user.privileges.can_change_info and user.status != CMS.OWNER):
        return await m.reply_text("🚫 You don't have enough permission to change group info!")

    # Check if new title is provided
    if len(m.command) < 2:
        return await m.reply_text("⚠️ Usage: `/setgtitle New Group Title`", quote=True)

    new_title = m.text.split(None, 1)[1]

    old_title = m.chat.title
    try:
        await m.chat.set_title(new_title)
    except Exception as e:
        return await m.reply_text(f"❌ Error while changing title:\n`{e}`")

    return await m.reply_text(
        f"✅ Group title changed!\n\n**Old:** {old_title}\n**New:** {new_title}"
    )


from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command, admin_filter


@Gojo.on_message(command("setgdes") & admin_filter)
async def setgdes(_, m: Message):
    # Get sender privileges
    user = await m.chat.get_member(m.from_user.id)
    if not (
        (user.privileges and user.privileges.can_change_info)
        or user.status == CMS.OWNER
    ):
        return await m.reply_text("❌ You don't have permission to change group description!")

    # Check if new description is provided
    if len(m.command) < 2:
        return await m.reply_text("Usage: /setgdes <new description>")

    # Store old description first
    old_desc = m.chat.description or "No Description"
    new_desc = m.text.split(None, 1)[1]

    try:
        await m.chat.set_description(new_desc)
    except Exception as e:
        return await m.reply_text(f"⚠️ Error while setting description:\n`{e}`")

    return await m.reply_text(
        f"✅ Group description updated!\n\n**Old:** {old_desc}\n**New:** {new_desc}"
    )


@Gojo.on_message(command("title") & admin_filter)
async def set_user_title(c: Gojo, m: Message):
    # Permission check
    user = await m.chat.get_member(m.from_user.id)
    if not (
        (user.privileges and user.privileges.can_promote_members)
        or user.status == CMS.OWNER
    ):
        return await m.reply_text("❌ You don’t have permission to change admin titles!")

    # Get input
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await m.reply_text("⚠️ Usage: /title <reply to admin> <new title>")

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return await m.reply_text("❌ Couldn’t extract user.")

    if not user_id:
        return await m.reply_text("❌ Couldn’t find the user.")
    if user_id == c.me.id:
        return await m.reply_text("😂 I can’t change my own title!")

    # Check if new title is provided
    if m.reply_to_message and len(m.text.split()) >= 2:
        title = m.text.split(None, 1)[1]
    elif not m.reply_to_message and len(m.text.split()) >= 3:
        title = " ".join(m.text.split()[2:])
    else:
        return await m.reply_text("⚠️ Please provide a title.")

    # Validate title
    if len(title) > 16:
        return await m.reply_text("⚠️ Admin titles can’t be longer than **16 characters**!")

    # Ensure target is admin
    target = await m.chat.get_member(user_id)
    if target.status not in [CMS.ADMINISTRATOR, CMS.OWNER]:
        return await m.reply_text("❌ This user is not an admin!")

    try:
        await c.set_administrator_title(m.chat.id, user_id, title)
    except Exception as e:
        return await m.reply_text(f"⚠️ Error: `{e}`")

    return await m.reply_text(
        f"✅ Successfully changed {target.user.mention}’s admin title to **{title}**"
    )


@Gojo.on_message(command("setgpic") & filters.group)
async def setgpic(c: Gojo, m: Message):
    # check admin permission
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        return await m.reply_text("❌ You don't have permission to change group info.")

    # must reply to a photo/document
    if not m.reply_to_message:
        return await m.reply_text("Reply to a photo to set as group picture.")
    if not (m.reply_to_message.photo or m.reply_to_message.document):
        return await m.reply_text("Reply to a valid photo to set as group picture.")

    # download the file
    photo_path = await m.reply_to_message.download()
    try:
        await c.set_chat_photo(chat_id=m.chat.id, photo=photo_path)
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")
    else:
        await m.reply_text("✅ Successfully changed group photo!")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)

__PLUGIN__ = "ᴀᴅᴍɪɴ"
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
**ᴀᴅᴍɪɴ**

**ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs:**
• /adminlist: ʟɪsᴛ ᴀʟʟ ᴛʜᴇ ᴀᴅᴍɪɴs ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ.

**ᴀᴅᴍɪɴ ᴏɴʟʏ:**
• /invitelink: ɢᴇᴛs ᴄʜᴀᴛ ɪɴᴠɪᴛᴇʟɪɴᴋ.
• /promote: ᴘʀᴏᴍᴏᴛᴇs ᴛʜᴇ ᴜsᴇʀ ʀᴇᴘʟɪᴇᴅ ᴛᴏ ᴏʀ ᴛᴀɢɢᴇᴅ (sᴜᴘᴘᴏʀᴛs ᴡɪᴛʜ ᴛɪᴛʟᴇ).
• /fullpromote: ꜰᴜʟʟʏ ᴘʀᴏᴍᴏᴛᴇs ᴛʜᴇ ᴜsᴇʀ ʀᴇᴘʟɪᴇᴅ ᴛᴏ ᴏʀ ᴛᴀɢɢᴇᴅ (sᴜᴘᴘᴏʀᴛs ᴡɪᴛʜ ᴛɪᴛʟᴇ).
• /demote: ᴅᴇᴍᴏᴛᴇs ᴛʜᴇ ᴜsᴇʀ ʀᴇᴘʟɪᴇᴅ ᴛᴏ ᴏʀ ᴛᴀɢɢᴇᴅ.
• /setgpic: sᴇᴛ ɢʀᴏᴜᴘ ᴘɪᴄᴛᴜʀᴇ.
• /admincache: ʀᴇʟᴏᴀᴅs ᴛʜᴇ ʟɪsᴛ ᴏꜰ ᴀʟʟ ᴛʜᴇ ᴀᴅᴍɪɴs ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ.
• /zombies: ʙᴀɴs ᴀʟʟ ᴛʜᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs. (ᴏᴡɴᴇʀ ᴏɴʟʏ)
• /title: sᴇᴛs ᴀ ᴄᴜsᴛᴏᴍ ᴛɪᴛʟᴇ ꜰᴏʀ ᴀɴ ᴀᴅᴍɪɴ ᴛʜᴀᴛ ᴛʜᴇ ʙᴏᴛ ᴘʀᴏᴍᴏᴛᴇᴅ.
• /disable <commandname>: sᴛᴏᴘ ᴜsᴇʀs ꜰʀᴏᴍ ᴜsɪɴɢ "ᴄᴏᴍᴍᴀɴᴅɴᴀᴍᴇ" ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.
• /enable <item name>: ᴀʟʟᴏᴡ ᴜsᴇʀs ꜰʀᴏᴍ ᴜsɪɴɢ "ᴄᴏᴍᴍᴀɴᴅɴᴀᴍᴇ" ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.
• /disableable: ʟɪsᴛ ᴀʟʟ ᴅɪsᴀʙʟᴇᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs.
• /disabledel <yes/off>: ᴅᴇʟᴇᴛᴇ ᴅɪsᴀʙʟᴇᴅ ᴄᴏᴍᴍᴀɴᴅs ᴡʜᴇɴ ᴜsᴇᴅ ʙʏ ɴᴏɴ-ᴀᴅᴍɪɴs.
• /disabled: ʟɪsᴛ ᴛʜᴇ ᴅɪsᴀʙʟᴇᴅ ᴄᴏᴍᴍᴀɴᴅs ɪɴ ᴛʜɪs ᴄʜᴀᴛ.
• /enableall: ᴇɴᴀʙʟᴇ ᴀʟʟ ᴅɪsᴀʙʟᴇᴅ ᴄᴏᴍᴍᴀɴᴅs.

**ᴇxᴀᴍᴘʟᴇ:**
`/promote @username`: ᴛʜɪs ᴘʀᴏᴍᴏᴛᴇs ᴀ ᴜsᴇʀ ᴛᴏ ᴀᴅᴍɪɴ."""



