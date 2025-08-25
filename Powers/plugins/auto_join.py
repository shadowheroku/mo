from traceback import format_exc

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS
from pyrogram.types import CallbackQuery, ChatJoinRequest
from pyrogram.types import InlineKeyboardButton as ikb
from pyrogram.types import InlineKeyboardMarkup as ikm
from pyrogram.types import Message

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.database.autojoin_db import AUTOJOIN
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import admin_filter, auto_join_filter, command


@Gojo.on_message(command(["joinreq"]) & admin_filter)
async def accept_join_requests(c: Gojo, m: Message):
    if m.chat.id == m.from_user.id:
        await m.reply_text("Use it in groups")
        return

    split = m.command
    a_j = AUTOJOIN()

    try:
        status = (await m.chat.get_member(c.me.id)).status
        if status != CMS.ADMINISTRATOR:
            await m.reply_text("I should be admin to accept and reject join requests")
            return
    except Exception as ef:
        await m.reply_text(f"Some error occured, report it using `/bug`\n<b>Error:</b> <code>{ef}</code>")
        LOGGER.error(ef)
        LOGGER.error(format_exc())
        return
    if len(split) == 1:
        txt = "**USAGE**\n/joinreq [on | off]"
    else:
        yes_no = split[1].lower()
        if yes_no == "on":
            is_al = a_j.load_autojoin(m.chat.id)

            txt = (
                "Now I will approve all the join request of the chat\nIf you want that I will just notify admins about the join request use command\n/joinreqmode [manual | auto]"
                if is_al
                else "Auto approve join request is already on for this chat\nIf you want that I will just notify admins about the join request use command\n/joinreqmode [manual | auto]"
            )
        elif yes_no == "off":
            a_j.remove_autojoin(m.chat.id)
            txt = "Now I will neither auto approve join request nor notify any admins about it"
        else:
            txt = "**USAGE**\n/joinreq [on | off]"

    await m.reply_text(txt)
    return


@Gojo.on_message(command("joinreqmode") & admin_filter)
async def join_request_mode(c: Gojo, m: Message):
    if m.chat.id == m.from_user.id:
        await m.reply_text("Use it in groups")
        return
    u_text = "**USAGE**\n/joinreqmode [auto | manual]\nauto: auto approve joins\nmanual: will notify admin about the join request"

    split = m.command
    a_j = AUTOJOIN()

    if len(split) == 1:
        await m.reply_text(u_text)
    else:
        auto_manual = split[1]
        if auto_manual not in ["auto", "manual"]:
            await m.reply_text(u_text)
        else:
            a_j.update_join_type(m.chat.id, auto_manual)
            txt = "Changed join request type"
            await m.reply_text(txt)

    return


from pyrogram.types import ChatJoinRequest, CallbackQuery
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus as CMS

# ── Join Request Handler ──
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

    # ── Auto Accept ──
    if join_type == "auto" or user in SUPPORT_STAFF:
        try:
            await c.approve_chat_join_request(chat, user)
            await c.send_message(
                chat,
                f"✅ Approved join request of {userr.mention}"
            )
            return
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error approving join request.\nReport with `/bug`.\n\n<b>Error:</b> <code>{ef}</code>"
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())
            return

    # ── Manual Approval ──
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
                ikb("❌ Decline", f"decline_joinreq_{user}")
            ]
        ]
        await c.send_message(chat, txt, reply_markup=ikm(kb))
        return


# ── Accept / Decline Buttons ──
@Gojo.on_callback_query(filters.regex("^(accept_joinreq_|decline_joinreq_)"))
async def accept_decline_request(c: Gojo, q: CallbackQuery):
    user_id = q.from_user.id
    chat = q.message.chat.id

    # Only Admins can use buttons
    try:
        user_status = (await q.message.chat.get_member(user_id)).status
        if user_status not in {CMS.OWNER, CMS.ADMINISTRATOR}:
            await q.answer(
                "🚫 You’re not an admin here!",
                show_alert=True,
            )
            return
    except Exception:
        await q.answer("⚠️ Unknown error. Maybe you’re not admin/owner.")
        return

    # Extract callback data
    split = q.data.split("_")
    action = split[0]     # "accept" or "decline"
    user = int(split[-1])

    try:
        userr = await c.get_users(user)
    except Exception:
        userr = None

    # ── Accept ──
    if action == "accept":
        try:
            await c.approve_chat_join_request(chat, user)
            mention = userr.mention if userr else user
            await q.answer(f"✅ Approved: {mention}", True)
            await q.edit_message_text(f"✅ <b>Approved join request of {mention}</b>")
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error approving join request.\nReport with `/bug`.\n\n<b>Error:</b> <code>{ef}</code>"
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())

    # ── Decline ──
    elif action == "decline":
        try:
            await c.decline_chat_join_request(chat, user)
            await q.answer("❌ Declined")
            await q.edit_message_text(f"❌ <b>Declined join request of {userr.mention if userr else user}</b>")
        except Exception as ef:
            await c.send_message(
                chat,
                f"⚠️ Error declining join request.\nReport with `/bug`.\n\n<b>Error:</b> <code>{ef}</code>"
            )
            LOGGER.error(ef)
            LOGGER.error(format_exc())


__PLUGIN__ = "auto join"

__alt_name__ = ["join_request"]

__HELP__ = """
**Auto join request**

**Admin commands:**
• /joinreq [on | off]: To switch on auto accept join request 
• /joinreqmode [auto | manual]: `auto` to accept join request automatically and `manual` to get notified when new join request is available
"""
