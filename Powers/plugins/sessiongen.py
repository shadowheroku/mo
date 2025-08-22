import logging
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import PhoneCodeExpired, SessionPasswordNeeded
from telethon.sessions import StringSession
from telethon import TelegramClient
from telethon.errors import PhoneCodeExpiredError, SessionPasswordNeededError
from Powers.bot_class import Gojo

# ─── State storage ───
user_sessions = {}
logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSING, GET_API, GET_HASH,
    GET_PHONE, GET_CODE, GET_PASSWORD
) = range(6)


# ─── Start command ───
@Gojo.on_message(filters.command("gensession"))
async def gensession_cmd(c: Gojo, m: Message):
    """Start session generator wizard"""
    user_id = m.from_user.id
    user_sessions[user_id] = {"step": CHOOSING}

    text = (
        "⚡ <b>Session Generator</b>\n\n"
        "Choose the library you want a session for:"
    )
    buttons = [
        [InlineKeyboardButton("🐍 Pyrogram", callback_data="lib_pyrogram")],
        [InlineKeyboardButton("📡 Telethon", callback_data="lib_telethon")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    await m.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="html")


# ─── Callback handler for choices ───
@Gojo.on_callback_query(filters.regex("^lib_") | filters.regex("^cancel$"))
async def choose_lib(c: Gojo, q: CallbackQuery):
    user_id = q.from_user.id
    if user_id not in user_sessions:
        return await q.answer("❌ Session expired, use /gensession again.", show_alert=True)

    session = user_sessions[user_id]

    if q.data == "cancel":
        user_sessions.pop(user_id, None)
        return await q.message.edit("🚪 Cancelled session generation.")

    lib = "pyrogram" if q.data == "lib_pyrogram" else "telethon"
    session["library"] = lib
    session["step"] = GET_API

    await q.message.edit(
        f"✅ Using <b>{lib.capitalize()}</b>.\n\n📌 Now send me your <b>API ID</b>:",
        parse_mode="html"
    )


# ─── Main wizard steps ───
@Gojo.on_message(filters.text & ~filters.command(["cancel", "gensession"]))
async def session_wizard(c: Gojo, m: Message):
    user_id = m.from_user.id
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    step = session.get("step")

    # ─── API ID ───
    if step == GET_API:
        try:
            api_id = int(m.text.strip())
        except ValueError:
            return await m.reply_text("❌ API ID must be a number. Try again:")
        session["api_id"] = api_id
        session["step"] = GET_HASH
        return await m.reply_text("📌 Now send me your <b>API HASH</b>:", parse_mode="html")

    # ─── API HASH ───
    if step == GET_HASH:
        session["api_hash"] = m.text.strip()
        session["step"] = GET_PHONE
        return await m.reply_text("📌 Send me your <b>phone number</b> (with country code):", parse_mode="html")

    # ─── Phone ───
    if step == GET_PHONE:
        phone = m.text.strip()
        session["phone"] = phone
        lib = session["library"]

        try:
            if lib == "pyrogram":
                client = Client(
                    name=f"gen_{user_id}",
                    api_id=session["api_id"],
                    api_hash=session["api_hash"],
                    in_memory=True
                )
                await client.connect()
                sent = await client.send_code(phone)
                session.update(client=client, phone_code_hash=sent.phone_code_hash)
            else:
                client = TelegramClient(
                    StringSession(),
                    api_id=session["api_id"],
                    api_hash=session["api_hash"]
                )
                await client.connect()
                sent = await client.send_code_request(phone)
                session.update(client=client, phone_code_hash=sent.phone_code_hash)

            session["step"] = GET_CODE
            return await m.reply_text("📨 Code sent! Reply with it (example: <code>1 2 3 4 5</code>)", parse_mode="html")

        except Exception as e:
            logger.error(f"Error sending code: {e}")
            user_sessions.pop(user_id, None)
            return await m.reply_text(f"❌ Failed to send code: <code>{e}</code>", parse_mode="html")

    # ─── Verification code ───
    if step == GET_CODE:
        code = m.text.strip()
        lib = session["library"]
        client = session["client"]

        try:
            if lib == "pyrogram":
                try:
                    await client.sign_in(
                        phone_number=session["phone"],
                        phone_code_hash=session["phone_code_hash"],
                        phone_code=code
                    )
                except PhoneCodeExpired:
                    sent = await client.send_code(session["phone"])
                    session["phone_code_hash"] = sent.phone_code_hash
                    return await m.reply_text("⚠️ Code expired. Sent a new one, please reply again.", parse_mode="html")
                except SessionPasswordNeeded:
                    session["step"] = GET_PASSWORD
                    return await m.reply_text("🔒 Your account has 2FA. Send me your password:", parse_mode="html")

                string = await client.export_session_string()
                await client.disconnect()

            else:  # telethon
                try:
                    await client.sign_in(
                        phone=session["phone"],
                        code=code,
                        phone_code_hash=session["phone_code_hash"]
                    )
                except PhoneCodeExpiredError:
                    sent = await client.send_code_request(session["phone"])
                    session["phone_code_hash"] = sent.phone_code_hash
                    return await m.reply_text("⚠️ Code expired. Sent a new one, please reply again.", parse_mode="html")
                except SessionPasswordNeededError:
                    session["step"] = GET_PASSWORD
                    return await m.reply_text("🔒 Your account has 2FA. Send me your password:", parse_mode="html")

                string = client.session.save()
                await client.disconnect()

            user_sessions.pop(user_id, None)
            return await m.reply_text(
                f"✅ Here’s your <b>{lib.capitalize()}</b> session string:\n\n<code>{string}</code>\n\n⚠️ Keep it safe!",
                parse_mode="html"
            )

        except Exception as e:
            logger.error(f"Sign in error: {e}")
            user_sessions.pop(user_id, None)
            return await m.reply_text(f"❌ Error: <code>{e}</code>", parse_mode="html")

    # ─── Password ───
    if step == GET_PASSWORD:
        password = m.text.strip()
        lib = session["library"]
        client = session["client"]

        try:
            if lib == "pyrogram":
                await client.check_password(password=password)
                string = await client.export_session_string()
                await client.disconnect()
            else:
                await client.sign_in(password=password)
                string = client.session.save()
                await client.disconnect()

            user_sessions.pop(user_id, None)
            return await m.reply_text(
                f"✅ Here’s your <b>{lib.capitalize()}</b> session string:\n\n<code>{string}</code>\n\n⚠️ Keep it safe!",
                parse_mode="html"
            )
        except Exception as e:
            logger.error(f"2FA error: {e}")
            user_sessions.pop(user_id, None)
            return await m.reply_text(f"❌ Error: <code>{e}</code>", parse_mode="html")


__PLUGIN__ = "gensession"
__HELP__ = """
<b>⚡ Session Generator</b>
Command: <code>/gensession</code>

Step-by-step wizard to generate a session string.

Supports:
• Pyrogram
• Telethon

⚠️ Keep your session string private!
"""
