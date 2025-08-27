from traceback import format_exc

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.types import (
    Message,
    ChatJoinRequest,
    CallbackQuery,
    InlineKeyboardButton as ikb,
    InlineKeyboardMarkup as ikm,
)

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database.autojoin_db import AUTOJOIN
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import admin_filter, auto_join_filter, command


# ── Enable / Disable Auto Join ──
@Gojo.on_message(command(["joinreq"]) & admin_filter)
async def accept_join_requests(c: Gojo, m: Message):
    if m.chat.type == "private":
        await m.reply_text("⚠️ This command can only be used in groups.")
        return

    a_j = AUTOJOIN()

    try:
        status = (await m.chat.get_member(c.me.id)).status
        if status != CMS.ADMINISTRATOR:
            await m.reply_text("⚠️ I must be an <b>Admin</b> with rights to manage join requests.")
            return
    except Exception as ef:
        await m.reply_text(
            f"❌ Error while checking admin status.\nReport with `/bug`\n\n<b>Error:</b> <code>{ef}</code>"
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())
        return

    if len(m.command) == 1:
        txt = "**Usage:**\n`/joinreq [on | off]`"
    else:
        opt = m.command[1].lower()
        if opt == "on":
            already = a_j.load_autojoin(m.chat.id)
            if already:
                txt = (
                    "✅ Auto-join requests are now <b>enabled</b>.\n"
                    "I will approve all requests automatically.\n\n"
                    "💡 Use `/joinreqmode [manual | auto]` to switch modes."
                )
            else:
                txt = (
                    "⚠️ Auto-join was already enabled.\n\n"
                    "💡 Use `/joinreqmode [manual | auto]` to change mode."
                )
        elif opt == "off":
            a_j.remove_autojoin(m.chat.id)
            txt = "❌ Auto-join disabled.\nI will not approve or notify admins of join requests."
        else:
            txt = "**Usage:**\n`/joinreq [on | off]`"

    await m.reply_text(txt)


# ── Change Join Request Mode ──
@Gojo.on_message(command("joinreqmode") & admin_filter)
async def join_request_mode(c: Gojo, m: Message):
    if m.chat.type == "private":
        await m.reply_text("⚠️ This command can only be used in groups.")
        return

    usage = (
        "**Usage:**\n"
        "`/joinreqmode [auto | manual]`\n\n"
        "• <b>auto</b>: Requests will be approved automatically.\n"
        "• <b>manual</b>: Admins will be notified with Accept/Decline buttons."
    )

    a_j = AUTOJOIN()

    if len(m.command) == 1:
        await m.reply_text(usage)
        return

    opt = m.command[1].lower()
    if opt not in ["auto", "manual"]:
        await m.reply_text(usage)
        return

    a_j.update_join_type(m.chat.id, opt)
    await m.reply_text(f"✅ Join request mode set to <b>{opt.upper()}</b>.")


# ── Incoming Join Requests ──
@Gojo.on_chat_join_request(auto_join_filter)
async def join_request_handler(c: Gojo, j: ChatJoinRequest):
    user = j.from_user.id
    userr = j.from_user
    chat = j.chat.id
    aj = AUTOJOIN()
    join_type = aj.get_autojoin(chat)
    SUPPORT_STAFF = get_support_staff()

    if not join_type:
        return

    # Auto Approve
    if join_type == "auto" or user in SUPPORT_STAFF:
        try:
            await c.approve_chat_join_request(chat, user)
            await c.send_message(chat, f"✅ Approved join request of {userr.mention}")
            return
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error approving join request.\nReport with `/bug`\n\n<b>Error:</b> <code>{ef}</code>",
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())
            return

    # Manual Approval
    elif join_type == "manual":
        txt = (
            "📩 <b>New Join Request</b>\n\n"
            f"👤 <b>Name:</b> {userr.full_name}\n"
            f"🔗 <b>Mention:</b> {userr.mention}\n"
            f"🆔 <b>ID:</b> <code>{user}</code>\n"
            f"🚨 <b>Scam:</b> {'✅ Yes' if userr.is_scam else '❌ No'}\n"
        )
        if userr.username:
            txt += f"📛 <b>Username:</b> @{userr.username}\n"

        kb = [
            [
                ikb("✔️ Accept", f"accept_joinreq_{user}"),
                ikb("❌ Decline", f"decline_joinreq_{user}"),
            ]
        ]
        await c.send_message(chat, txt, reply_markup=ikm(kb))


# ── Accept / Decline ──
@Gojo.on_callback_query(filters.regex("^(accept_joinreq_|decline_joinreq_)"))
async def accept_decline_request(c: Gojo, q: CallbackQuery):
    admin_id = q.from_user.id
    chat = q.message.chat.id

    # Ensure only Admins can approve/decline
    try:
        status = (await q.message.chat.get_member(admin_id)).status
        if status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
            await q.answer("🚫 You’re not an admin here!", show_alert=True)
            return
    except Exception:
        await q.answer("⚠️ Could not verify admin status.")
        return

    split = q.data.split("_")
    action = split[0]  # "accept" or "decline"
    user = int(split[-1])

    try:
        userr = await c.get_users(user)
    except Exception:
        userr = None

    mention = userr.mention if userr else user

    if action == "accept":
        try:
            await c.approve_chat_join_request(chat, user)
            await q.answer(f"✅ Approved: {mention}", True)
            await q.edit_message_text(f"✅ <b>Approved join request of {mention}</b>")
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error approving join request.\nReport with `/bug`\n\n<b>Error:</b> <code>{ef}</code>",
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())

    elif action == "decline":
        try:
            await c.decline_chat_join_request(chat, user)
            await q.answer("❌ Declined", True)
            await q.edit_message_text(f"❌ <b>Declined join request of {mention}</b>")
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error declining join request.\nReport with `/bug`\n\n<b>Error:</b> <code>{ef}</code>",
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())


__PLUGIN__ = "ᴀᴜᴛᴏ ᴊᴏɪɴ"
__alt_name__ = ["join_request"]

__HELP__ = """
**ᴀᴜᴛᴏ ᴊᴏɪɴ ʀᴇǫᴜᴇsᴛs**

**ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:**
• `/joinreq [on | off]` → ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴀᴜᴛᴏ-ᴊᴏɪɴ.
• `/joinreqmode [auto | manual]`
   • `auto` → ᴀᴘᴘʀᴏᴠᴇs ᴀʟʟ ʀᴇǫᴜᴇsᴛs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ.
   • `manual` → ɴᴏᴛɪꜰɪᴇs ᴀᴅᴍɪɴs ᴡɪᴛʜ ᴀᴄᴄᴇᴘᴛ/ᴅᴇᴄʟɪɴᴇ ʙᴜᴛᴛᴏɴs.
"""

