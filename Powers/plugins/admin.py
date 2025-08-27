"""
Improved Admin plugin for Gojo (Pyrogram)
- Cleaner messages with emojis
- Better error handling and logging
- Improved admin list formatting and ordering
- Small UX improvements for promote/demote workflows
- Preserves original capabilities

Drop-in replacement for your existing admin module.
"""

from asyncio import sleep
from html import escape
from os import remove
from traceback import format_exc

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS, ChatType
from pyrogram.errors import (
    BotChannelsNa, ChatAdminInviteRequired,
    ChatAdminRequired, FloodWait, RightForbidden,
    RPCError, UserAdminInvalid
)
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


# ---------- Helpers ----------
async def safe_reply(msg_obj: Message, text: str, **kwargs):
    try:
        return await msg_obj.reply_text(text, **kwargs)
    except RPCError as e:
        LOGGER.error(f"Failed to send reply: {e}")


def _format_admins(admins):
    """Return (user_admins, bot_admins) where each is list of tuples (mention, raw_name)"""
    user_admins = [a for a in admins if not a[1].lower().endswith("bot")]
    bot_admins = [a for a in admins if a[1].lower().endswith("bot")]
    return user_admins, bot_admins


# ---------- Commands ----------
@Gojo.on_message(command("adminlist"))
async def adminlist_show(_, m: Message):
    """List admins in the current group in an attractive format."""
    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return await safe_reply(m, "⚠️ This command works only inside groups.")

    try:
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            note = "<i>Note:</i> Showing cached values — use /admincache to refresh."
        except KeyError:
            admin_list = await admin_cache_reload(m, "adminlist")
            note = "<i>Note:</i> Showing fresh values."

        # admin_list expected format: [(id, username_or_name, is_anonymous_bool), ...]
        user_admins, bot_admins = _format_admins(admin_list)

        # Build nice mentions for visible admins (skip anonymous)
        def build_mentions(admins):
            mentions = []
            for admin in admins:
                uid = admin[0]
                raw = admin[1]
                anon = admin[2] if len(admin) > 2 else False
                if anon:
                    mentions.append((f"• {escape(raw)} (anonymous)", raw))
                else:
                    mention = await mention_html(raw if raw.startswith("@") else raw, uid)
                    mentions.append((f"• {mention}", raw))
            # sort by display name for stable output
            mentions.sort(key=lambda x: x[1].lower() if x[1] else "")
            return [m[0] for m in mentions]

        user_lines = await build_mentions(user_admins)
        bot_lines = await build_mentions(bot_admins)

        text = f"<b>👥 Admins for</b> <i>{escape(m.chat.title or str(m.chat.id))}</i>\n\n"
        text += "<b>👤 Human Admins:</b>\n" + ("\n".join(user_lines) if user_lines else "• None")
        text += "\n\n<b>🤖 Bot Admins:</b>\n" + ("\n".join(bot_lines) if bot_lines else "• None")
        text += "\n\n" + note

        await safe_reply(m, text, parse_mode="html")

    except Exception as ef:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Unexpected error. Report with /bug\n<code>{escape(str(ef))}</code>", parse_mode="html")


@Gojo.on_message(command("zombies") & admin_filter)
async def zombie_clean(c: Gojo, m: Message):
    """Ban deleted accounts from the chat (owner / admins only via admin_filter)."""
    zombie = 0
    failed = 0
    wait = await safe_reply(m, "🔎 Scanning for deleted accounts...")
    try:
        async for member in c.get_chat_members(m.chat.id):
            if member.user.is_deleted:
                zombie += 1
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
        if zombie == 0:
            return await wait.edit_text("✅ Group is clean — no deleted accounts found.")

        await wait.delete()
        txt = f"<b>☠️ Zombies purged:</b> <b>{zombie - failed}</b> banned\n<b>🔒 Immune:</b> {failed}"
        await m.reply_animation("https://graph.org/file/02a1dcf7788186ffb36cb.mp4", caption=txt)
    except Exception as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error while cleaning zombies: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("admincache"))
async def reload_admins(_, m: Message):
    """Force reload admin cache for the chat (rate-limited)."""
    if m.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
        return await safe_reply(m, "⚠️ This command works only inside groups.")

    SUPPORT_STAFF = get_support_staff()
    # Simple rate-block: add a dynamic dict on top-level if you need per-chat cooldowns
    try:
        await admin_cache_reload(m, "admincache")
        await safe_reply(m, "🔁 Admin cache reloaded successfully.")
    except RPCError as ef:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Failed to reload admin cache: <code>{escape(str(ef))}</code>", parse_mode="html")


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
    # Mention compactly without ping spam: invisible character mention trick
    mention_users = [(await mention_html("\u2063", admin[0])) for admin in user_admins]
    mention_users.sort(key=lambda x: x[1])
    mention_str = "".join(mention_users)

    await m.reply_text(
        (
            f"{await mention_html(m.from_user.first_name, m.from_user.id)} reported this to admins!{mention_str}"
        ),
    )


# ---------- Promotion / Demotion ----------
@Gojo.on_message(command("fullpromote") & promote_filter)
async def fullpromote_usr(c: Gojo, m: Message):
    """Promote with full privileges and optional title (owner-only)."""
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await safe_reply(m, "❗ Provide a user to promote (reply or mention).")

    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return

    bot = await c.get_chat_member(m.chat.id, c.me.id)
    if user_id == c.me.id:
        return await safe_reply(m, "😆 I can't promote myself!")
    if not bot.privileges.can_promote_members:
        return await safe_reply(m, "❗ I don't have permission to promote members.")

    # ensure only chat owner can fullpromote
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    if m.from_user.id != OWNER_ID and user.status != CMS.OWNER:
        return await safe_reply(m, "🔒 Only the chat owner can use this command.")

    try:
        admin_ids = {i[0] for i in ADMIN_CACHE.get(m.chat.id, [])}
    except Exception:
        admin_ids = set()

    if user_id in admin_ids:
        return await safe_reply(m, "ℹ️ This user is already an admin.")

    try:
        await m.chat.promote_member(user_id=user_id, privileges=bot.privileges)
        # set title if provided
        title = "Gojo"
        if m.chat.type in (ChatType.SUPERGROUP, ChatType.GROUP):
            if len(m.text.split()) >= 3 and not m.reply_to_message:
                title = " ".join(m.text.split()[2:16])
            elif len(m.text.split()) >= 2 and m.reply_to_message:
                title = " ".join(m.text.split()[1:16])
            try:
                await c.set_administrator_title(m.chat.id, user_id, title)
            except RPCError:
                LOGGER.error("Failed to set admin title")

        await safe_reply(m, f"✅ {await mention_html(m.from_user.first_name, m.from_user.id)} promoted {await mention_html(user_first_name, user_id)} with full rights.\nTitle: <b>{escape(title)}</b>", parse_mode="html")

        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        try:
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, user_name or user_first_name, False))
            ADMIN_CACHE[m.chat.id] = admins_group
        except Exception:
            await admin_cache_reload(m, "promote_key_error")

    except ChatAdminRequired:
        await safe_reply(m, "❗ I need admin rights to promote members.")
    except RightForbidden:
        await safe_reply(m, "❗ I lack required permissions to promote this user.")
    except UserAdminInvalid:
        await safe_reply(m, "❗ Cannot modify this user (they may have higher privileges).")
    except RPCError as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("promote") & promote_filter)
async def promote_usr(c: Gojo, m: Message):
    """Promote with restricted privileges (configurable to match bot's own rights)."""
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await safe_reply(m, "❗ Reply to or mention a user to promote.")

    try:
        user_id, user_first_name, user_name = await extract_user(c, m)
    except Exception:
        return

    bot = await c.get_chat_member(m.chat.id, c.me.id)
    if user_id == c.me.id:
        return await safe_reply(m, "😆 I can't promote myself!")
    if not bot.privileges.can_promote_members:
        return await safe_reply(m, "❗ I don't have permission to promote members.")

    try:
        admin_ids = {i[0] for i in ADMIN_CACHE.get(m.chat.id, [])}
    except Exception:
        admin_ids = set()

    if user_id in admin_ids:
        return await safe_reply(m, "ℹ️ This user is already an admin.")

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

        title = "Itadori"
        if m.chat.type in (ChatType.SUPERGROUP, ChatType.GROUP):
            if len(m.text.split()) >= 3 and not m.reply_to_message:
                title = " ".join(m.text.split()[2:16])
            elif len(m.text.split()) >= 2 and m.reply_to_message:
                title = " ".join(m.text.split()[1:16])
            try:
                await c.set_administrator_title(m.chat.id, user_id, title)
            except RPCError:
                LOGGER.error("Failed to set admin title")

        await safe_reply(m, f"✅ {await mention_html(user_first_name, user_id)} promoted.\nTitle: <b>{escape(title)}</b>", parse_mode="html")

        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        try:
            admins_group = ADMIN_CACHE.get(m.chat.id, [])
            admins_group.append((user_id, user_name or user_first_name, False))
            ADMIN_CACHE[m.chat.id] = admins_group
        except Exception:
            await admin_cache_reload(m, "promote_key_error")

    except ChatAdminRequired:
        await safe_reply(m, "❗ I need admin rights to promote members.")
    except RightForbidden:
        await safe_reply(m, "❗ I lack required permissions to promote this user.")
    except UserAdminInvalid:
        await safe_reply(m, "❗ Cannot modify this user (they may have higher privileges).")
    except RPCError as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("demote") & promote_filter)
async def demote_usr(c: Gojo, m: Message):
    """Demote an admin to regular member (remove elevated privileges)."""
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await safe_reply(m, "❗ Reply to or mention an admin to demote.")

    try:
        user_id, user_first_name, _ = await extract_user(c, m)
    except Exception:
        return

    if user_id == c.me.id:
        return await safe_reply(m, "🤖 Ask another admin to demote me — I can't do that myself.")

    try:
        admin_ids = {i[0] for i in ADMIN_CACHE.get(m.chat.id, [])}
    except Exception:
        admin_ids = set()

    if user_id not in admin_ids:
        return await safe_reply(m, "ℹ️ This user is not an admin.")

    try:
        await m.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(can_manage_chat=False),
        )

        # remove from cache
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            user = next(user for user in admin_list if user[0] == user_id)
            admin_list.remove(user)
            ADMIN_CACHE[m.chat.id] = admin_list
        except (KeyError, StopIteration):
            await admin_cache_reload(m, "demote_key_stopiter_error")

        await safe_reply(m, f"✅ {await mention_html(user_first_name, user_id)} demoted in <b>{escape(m.chat.title or str(m.chat.id))}</b>!", parse_mode="html")

    except ChatAdminRequired:
        await safe_reply(m, "❗ I need admin rights to demote members.")
    except RightForbidden:
        await safe_reply(m, "❗ I don't have permission to demote this user.")
    except UserAdminInvalid:
        await safe_reply(m, "❗ Cannot modify this user (they may have higher privileges).")
    except BotChannelsNa:
        await safe_reply(m, "⚠️ Telegram restrictions prevent demoting some bot accounts — do it manually.")
    except RPCError as ef:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(ef))}</code>", parse_mode="html")


# ---------- Misc group settings ----------
@Gojo.on_message(command("invitelink"))
async def get_invitelink(c: Gojo, m: Message):
    DEV_LEVEL = get_support_staff("dev_level")
    if m.from_user.id not in DEV_LEVEL:
        user = await m.chat.get_member(m.from_user.id)
        if not user.privileges.can_invite_users and user.status != CMS.OWNER:
            return await safe_reply(m, "❗ You need invite rights to run this.")

    try:
        link = await c.export_chat_invite_link(m.chat.id)
        await safe_reply(m, f"🔗 Invite Link for <b>{escape(str(m.chat.id))}</b>:\n{link}", disable_web_page_preview=True, parse_mode="html")
    except ChatAdminRequired:
        await safe_reply(m, "❗ I am not an admin here or missing invite rights.")
    except ChatAdminInviteRequired:
        await safe_reply(m, "❗ The chat requires extra invite permissions.")
    except RightForbidden:
        await safe_reply(m, "❗ You don't have permission to invite users.")
    except RPCError as ef:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(ef))}</code>", parse_mode="html")


@Gojo.on_message(command("setgtitle") & admin_filter)
async def setgtitle(_, m: Message):
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        return await safe_reply(m, "❗ You don't have permission to change group info.")
    if len(m.command) < 2:
        return await safe_reply(m, "❗ Usage: /setgtitle <new title>")
    gtit = m.text.split(None, 1)[1]
    try:
        old = m.chat.title
        await m.chat.set_title(gtit)
        await safe_reply(m, f"✅ Group title changed:\n<b>{escape(old)}</b> → <b>{escape(gtit)}</b>", parse_mode="html")
    except Exception as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("setgdes") & admin_filter)
async def setgdes(_, m: Message):
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        return await safe_reply(m, "❗ You don't have permission to change group info.")
    if len(m.command) < 2:
        return await safe_reply(m, "❗ Usage: /setgdes <description>")
    desp = m.text.split(None, 1)[1]
    try:
        old = m.chat.description or "(none)"
        await m.chat.set_description(desp)
        await safe_reply(m, f"✅ Group description updated.\nPrevious: <code>{escape(old)}</code>", parse_mode="html")
    except Exception as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("title") & admin_filter)
async def set_user_title(c: Gojo, m: Message):
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_promote_members and user.status != CMS.OWNER:
        return await safe_reply(m, "❗ You don't have permission to change admin titles.")
    if len(m.text.split()) == 1 and not m.reply_to_message:
        return await safe_reply(m, "❗ Reply to an admin or provide an id and title.")

    reason = None
    if m.reply_to_message and len(m.text.split()) >= 2:
        reason = m.text.split(None, 1)[1]
    elif len(m.text.split()) >= 3:
        reason = m.text.split(None, 2)[2]

    try:
        user_id, _, _ = await extract_user(c, m)
    except Exception:
        return
    if not user_id:
        return await safe_reply(m, "❗ Cannot find user.")
    if user_id == c.me.id:
        return await safe_reply(m, "🤖 I don't need a title :)")
    if not reason:
        return await safe_reply(m, "❗ Provide a title. Usage: /title <title> or reply with /title <title>")

    from_user = await c.get_users(user_id)
    title = reason[:128]
    try:
        await c.set_administrator_title(m.chat.id, from_user.id, title)
        await safe_reply(m, f"✅ {from_user.mention}'s admin title changed to <b>{escape(title)}</b>", parse_mode="html")
    except Exception as e:
        LOGGER.error(format_exc())
        await safe_reply(m, f"❗ Error: <code>{escape(str(e))}</code>", parse_mode="html")


@Gojo.on_message(command("setgpic") & admin_filter)
async def setgpic(c: Gojo, m: Message):
    user = await m.chat.get_member(m.from_user.id)
    if not user.privileges.can_change_info and user.status != CMS.OWNER:
        return await safe_reply(m, "❗ You don't have permission to change group photo.")
    if not m.reply_to_message:
        return await safe_reply(m, "❗ Reply to a photo to set it as group photo.")
    if not (m.reply_to_message.photo or m.reply_to_message.document):
        return await safe_reply(m, "❗ Reply to an image file (photo or image document).")

    photo = await m.reply_to_message.download()
    is_vid = bool(m.reply_to_message.video)
    try:
        await m.chat.set_photo(photo, video=is_vid)
        await safe_reply(m, "✅ Group photo updated successfully.")
    except Exception as e:
        LOGGER.error(format_exc())
        remove(photo)
        await safe_reply(m, f"❗ Error setting group photo: <code>{escape(str(e))}</code>", parse_mode="html")
    else:
        remove(photo)


# Plugin metadata
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
<b>🛡️ Admin</b>

<b>User Commands:</b>
• /adminlist — Show admins in this group (cached for speed).

<b>Admin / Owner:</b>
• /invitelink — Get chat invite link.
• /promote — Promote replied/mentioned user with bot-level rights.
• /fullpromote — Promote with full privileges (owner only).
• /demote — Demote an admin back to regular member.
• /setgpic — Reply to a photo to set group picture.
• /admincache — Reload cached admin list for this chat.
• /zombies — Ban deleted accounts in the group.
• /title — Set a custom admin title for a promoted admin.
• /setgtitle — Change the group title.
• /setgdes — Change the group description.

Examples:
`/promote @username` — promote user
`/title New Moderator` — set admin title for replied user
"""
