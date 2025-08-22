import asyncio
import logging
from pyrogram import filters, Client
from pyrogram.types import Message
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


@Gojo.on_message(filters.command("gensession"))
async def gensession_cmd(c: Gojo, m: Message):
    """Start session generator wizard"""
    user_id = m.from_user.id
    user_sessions[user_id] = {"step": CHOOSING}

    text = (
        "⚡ **Session Generator**\n\n"
        "Choose the library you want a session for:\n"
        "• `pyrogram`\n• `telethon`\n\n"
        "_Reply with one of the above._"
    )
    await m.reply_text(text)


@Gojo.on_message(filters.text & ~filters.command(["cancel", "gensession"]))
async def session_wizard(c: Gojo, m: Message):
    user_id = m.from_user.id
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    step = session.get("step")

    # ─── Choose library ───
    if step == CHOOSING:
        lib = m.text.lower().strip()
        if lib not in ["pyrogram", "telethon"]:
            return await m.reply_text("❌ Please reply with `pyrogram` or `telethon`.")
        session["library"] = lib
        session["step"] = GET_API
        return await m.reply_text("📌 Send me your **API ID**:")

    # ─── API ID ───
    if step == GET_API:
        try:
            api_id = int(m.text.strip())
        except ValueError:
            return await m.reply_text("❌ API ID must be a number. Try again:")
        session["api_id"] = api_id
        session["step"] = GET_HASH
        return await m.reply_text("📌 Now send me your **API HASH**:")

    # ─── API HASH ───
    if step == GET_HASH:
        session["api_hash"] = m.text.strip()
        session["step"] = GET_PHONE
        return await m.reply_text("📌 Send me your **phone number** (with country code):")

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
            return await m.reply_text("📨 Code sent! Reply with it in this format: `1 2 3 4 5`")

        except Exception as e:
            logger.error(f"Error sending code: {e}")
            del user_sessions[user_id]
            return await m.reply_text(f"❌ Failed to send code: `{e}`")

    # ─── Verification code ───
    if step == GET_CODE:
        code = m.text.strip()  # keep spaces as user types them
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
                    return await m.reply_text("⚠️ Code expired. Sent a new one, please reply again.")
                except SessionPasswordNeeded:
                    session["step"] = GET_PASSWORD
                    return await m.reply_text("🔒 Your account has 2FA. Send me your password:")

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
                    return await m.reply_text("⚠️ Code expired. Sent a new one, please reply again.")
                except SessionPasswordNeededError:
                    session["step"] = GET_PASSWORD
                    return await m.reply_text("🔒 Your account has 2FA. Send me your password:")

                string = client.session.save()
                await client.disconnect()

            del user_sessions[user_id]
            return await m.reply_text(
                f"✅ Here’s your **{lib.capitalize()}** session string:\n\n`{string}`\n\n⚠️ Keep it safe!",
                parse_mode="markdown"
            )

        except Exception as e:
            logger.error(f"Sign in error: {e}")
            del user_sessions[user_id]
            return await m.reply_text(f"❌ Error: `{e}`")

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

            del user_sessions[user_id]
            return await m.reply_text(
                f"✅ Here’s your **{lib.capitalize()}** session string:\n\n`{string}`\n\n⚠️ Keep it safe!",
                parse_mode="markdown"
            )
        except Exception as e:
            logger.error(f"2FA error: {e}")
            del user_sessions[user_id]
            return await m.reply_text(f"❌ Error: `{e}`")


__PLUGIN__ = "gensession"
__HELP__ = """
**⚡ Session Generator**
Command: `/gensession`

Step-by-step wizard to generate a session string.

Supports:
• Pyrogram
• Telethon

⚠️ Keep your session string private!
"""
