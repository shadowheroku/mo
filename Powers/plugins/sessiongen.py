# Powers/plugins/sessiongen.py

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional

from pyrogram import filters, enums
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
)
from pyrogram.errors import (
    FloodWait, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded, BadRequest
)
from pyrogram.enums import ParseMode as PM

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError
from telethon.sessions import StringSession as TLStringSession

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ------------- CONFIG -------------

WIZARD_TIMEOUT = 10 * 60  # seconds of inactivity before auto-cancel
MASK = "•"  # use to mask api_hash echo

# ------------- STATE -------------

@dataclass
class WizardState:
    user_id: int
    framework: Optional[str] = None  # "pyrogram" | "telethon"
    step: str = "start"
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None  # for Pyrogram flow
    started_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def expired(self) -> bool:
        return (asyncio.get_event_loop().time() - self.started_at) > WIZARD_TIMEOUT

# In-memory wizard store
WIZARDS: Dict[int, WizardState] = {}


# ------------- HELPERS -------------

def _reset(user_id: int) -> None:
    if user_id in WIZARDS:
        del WIZARDS[user_id]

def _mk_kb_framework():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🐍 Pyrogram", callback_data="sess_fw_pyrogram"),
            InlineKeyboardButton("⚡ Telethon", callback_data="sess_fw_telethon"),
        ],
         [
            InlineKeyboardButton("❌ Cancel", callback_data="sess_cancel")
         ]]
    )

def _mk_kb_resend_cancel():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔁 Resend Code", callback_data="sess_resend")],
         [InlineKeyboardButton("❌ Cancel", callback_data="sess_cancel")]]
    )

def _mk_kb_cancel():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="sess_cancel")]])


async def _ensure_dm(m: Message) -> bool:
    if not m.chat or m.chat.type != enums.ChatType.PRIVATE:
        await m.reply_text("This command works **only in DM**. Please DM the bot.", parse_mode=PM.MARKDOWN)
        return False
    return True


# ------------- ENTRY -------------

@Gojo.on_message(command(["session", "gensession", "string"]) & filters.private)
async def session_entry(c: Gojo, m: Message):
    if not await _ensure_dm(m):
        return

    uid = m.from_user.id
    _reset(uid)
    WIZARDS[uid] = WizardState(user_id=uid)
    await m.reply_text(
        "Let’s generate a **Session String**.\n\n"
        "Choose your framework:",
        reply_markup=_mk_kb_framework(),
        parse_mode=PM.MARKDOWN
    )


# ------------- CALLBACKS -------------

@Gojo.on_callback_query(filters.regex(r"^sess_fw_(pyrogram|telethon)$"))
async def choose_framework(c: Gojo, q: CallbackQuery):
    if q.message.chat.type != enums.ChatType.PRIVATE:
        await q.answer("Use in DM only.", show_alert=True)
        return
    uid = q.from_user.id
    st = WIZARDS.get(uid)
    if not st or st.expired():
        _reset(uid)
        await q.message.reply_text("Session wizard expired. Start again with /session.")
        return

    st.framework = "pyrogram" if q.data.endswith("pyrogram") else "telethon"
    st.step = "need_api_id"
    st.started_at = asyncio.get_event_loop().time()

    await q.message.edit_text(
        f"**Framework:** `{st.framework}`\n\n"
        "Send your **API ID** (numeric).",
        parse_mode=PM.MARKDOWN,
        reply_markup=_mk_kb_cancel()
    )
    await q.answer()


@Gojo.on_callback_query(filters.regex(r"^sess_cancel$"))
async def cancel_wizard(c: Gojo, q: CallbackQuery):
    uid = q.from_user.id
    _reset(uid)
    await q.message.edit_text("Wizard **cancelled**. No data stored. ✅", parse_mode=PM.MARKDOWN)
    await q.answer("Cancelled.")


@Gojo.on_callback_query(filters.regex(r"^sess_resend$"))
async def resend_code(c: Gojo, q: CallbackQuery):
    uid = q.from_user.id
    st = WIZARDS.get(uid)
    if not st or st.expired():
        _reset(uid)
        await q.message.edit_text("Session wizard expired. Start again with /session.")
        await q.answer()
        return

    if not st.api_id or not st.api_hash or not st.phone:
        await q.answer("Missing details to resend. Start over.", show_alert=True)
        return

    if st.framework == "pyrogram":
        # Re-send code using Pyrogram
        try:
            tmp = ClientTempPyro(api_id=st.api_id, api_hash=st.api_hash)
            phone_code_hash = await tmp.send_code(st.phone)
            st.phone_code_hash = phone_code_hash
            await q.message.reply_text("Code **resent**. Please send the **OTP** you received.",
                                       parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_cancel())
        except Exception as e:
            await q.message.reply_text(f"Failed to resend code: `{e}`\nTry again or /session to restart.",
                                       parse_mode=PM.MARKDOWN)
        finally:
            await asyncio.sleep(0.05)
    else:
        # Telethon re-send
        try:
            async with TelegramClient(TLStringSession(), st.api_id, st.api_hash) as tcli:
                await tcli.send_code_request(st.phone)
            await q.message.reply_text("Code **resent**. Please send the **OTP** you received.",
                                       parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_cancel())
        except Exception as e:
            await q.message.reply_text(f"Failed to resend code: `{e}`\nTry again or /session to restart.",
                                       parse_mode=PM.MARKDOWN)
    await q.answer("Code resent.")


# ------------- TEXT FLOW -------------

# ------------------- TEXT FLOW -------------------

@Gojo.on_message(filters.private & ~filters.service)
async def session_wizard_flow(c: Gojo, m: Message):
    uid = m.from_user.id
    st = WIZARDS.get(uid)
    if not st:
        return  # ignore other DMs

    if st.expired():
        _reset(uid)
        await m.reply_text("Wizard timed out. Start again with /session.")
        return

    # STEP: API ID
    if st.step == "need_api_id":
        try:
            st.api_id = int(m.text.strip())
        except Exception:
            await m.reply_text("API ID must be a number.\nSend again:", reply_markup=_mk_kb_cancel())
            return
        st.step = "need_api_hash"
        await m.reply_text("Great. Now send your **API HASH**:",
                           parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_cancel())
        return

    # STEP: API HASH
    if st.step == "need_api_hash":
        st.api_hash = m.text.strip()
        masked = MASK * max(6, min(len(st.api_hash), 32))
        st.step = "need_phone"
        await m.reply_text(
            f"API ID: `{st.api_id}`\nAPI HASH: `{masked}`\n\n"
            "Now send your **phone number** in international format (e.g., +9198xxxxxxx).",
            parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_cancel()
        )
        return

    # STEP: PHONE
    if st.step == "need_phone":
        st.phone = m.text.strip().replace(" ", "")
        st.step = "need_code"
        # Trigger sending code
        try:
            if st.framework == "pyrogram":
                tmp = ClientTempPyro(api_id=st.api_id, api_hash=st.api_hash)
                st.phone_code_hash = await tmp.send_code(st.phone)
            else:
                async with TelegramClient(TLStringSession(), st.api_id, st.api_hash) as tcli:
                    await tcli.send_code_request(st.phone)
            await m.reply_text(
                "Sent a login code to your Telegram.\n"
                "👉 Please send the **OTP code** (you can copy-paste it with spaces, e.g. `1 2 3 4 5`).",
                reply_markup=_mk_kb_resend_cancel(), parse_mode=PM.MARKDOWN
            )
        except FloodWait as fw:
            await m.reply_text(f"Flood wait: **{fw.value}s**. Try again later with /session.", parse_mode=PM.MARKDOWN)
            _reset(uid)
        except Exception as e:
            await m.reply_text(f"Error sending code: `{e}`\nRestart with /session.", parse_mode=PM.MARKDOWN)
            _reset(uid)
        return

    # STEP: CODE
    if st.step == "need_code":
        code = m.text.strip()  # ✅ keep spaces in OTP
        if not code:
            await m.reply_text("Please send the OTP code you received (digits, spaces allowed).",
                               parse_mode=PM.MARKDOWN)
            return

        if st.framework == "pyrogram":
            try:
                sess = await make_pyrogram_string(
                    st.api_id, st.api_hash, st.phone, code, st.phone_code_hash
                )
                await _deliver_session(m, sess, framework="Pyrogram")
                _reset(uid)
            except PhoneCodeExpired:
                # 🔁 auto-resend a new code
                tmp = ClientTempPyro(api_id=st.api_id, api_hash=st.api_hash)
                st.phone_code_hash = await tmp.send_code(st.phone)
                await m.reply_text("⌛ Code expired. A new code has been sent — please enter the latest OTP.",
                                   reply_markup=_mk_kb_resend_cancel(), parse_mode=PM.MARKDOWN)
            except PhoneCodeInvalid:
                await m.reply_text("❌ Invalid code. Try again or tap **Resend Code**.",
                                   parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_resend_cancel())
            except SessionPasswordNeeded:
                st.step = "need_2fa"
                await m.reply_text("2FA is enabled. Send your **password**.", parse_mode=PM.MARKDOWN,
                                   reply_markup=_mk_kb_cancel())
            except Exception as e:
                await m.reply_text(f"Login failed: `{e}`\nRestart with /session.", parse_mode=PM.MARKDOWN)
                _reset(uid)
            return

        else:
            # Telethon
            try:
                sess = await make_telethon_string(st.api_id, st.api_hash, st.phone, code)
                await _deliver_session(m, sess, framework="Telethon")
                _reset(uid)
            except PhoneCodeExpiredError:
                async with TelegramClient(TLStringSession(), st.api_id, st.api_hash) as tcli:
                    await tcli.send_code_request(st.phone)
                await m.reply_text("⌛ Code expired. A new code has been sent — please enter the latest OTP.",
                                   reply_markup=_mk_kb_resend_cancel(), parse_mode=PM.MARKDOWN)
            except PhoneCodeInvalidError:
                await m.reply_text("❌ Invalid code. Try again or tap **Resend Code**.",
                                   parse_mode=PM.MARKDOWN, reply_markup=_mk_kb_resend_cancel())
            except SessionPasswordNeededError:
                st.step = "need_2fa"
                await m.reply_text("2FA is enabled. Send your **password**.", parse_mode=PM.MARKDOWN,
                                   reply_markup=_mk_kb_cancel())
            except Exception as e:
                await m.reply_text(f"Login failed: `{e}`\nRestart with /session.", parse_mode=PM.MARKDOWN)
                _reset(uid)
            return



# ------------- CORE LOGIN BUILDERS -------------

class ClientTempPyro:
    """
    Minimal helper to send code via Pyrogram without persisting a file session.
    """
    def __init__(self, api_id: int, api_hash: str):
        from pyrogram import Client
        # Use in_memory session so nothing is written to disk
        self.client = Client(name=":memory:", api_id=api_id, api_hash=api_hash, in_memory=True)

    async def send_code(self, phone: str) -> str:
        await self.client.connect()
        sent = await self.client.send_code(phone)
        # sent contains .phone_code_hash in Pyrogram v2+
        phone_code_hash = getattr(sent, "phone_code_hash", None)
        await self.client.disconnect()
        if not phone_code_hash:
            raise RuntimeError("Could not retrieve phone_code_hash.")
        return phone_code_hash


async def make_pyrogram_string(
    api_id: int,
    api_hash: str,
    phone: str,
    code: Optional[str],
    phone_code_hash: Optional[str],
    password: Optional[str] = None
) -> str:
    from pyrogram import Client
    app = Client(name=":memory:", api_id=api_id, api_hash=api_hash, in_memory=True)

    await app.connect()
    try:
        if password:
            # 2FA path: sign-in with password
            await app.check_password(password)
        else:
            if not (code and phone_code_hash):
                raise RuntimeError("Missing code/hash for sign-in.")
            await app.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
        session_string = await app.export_session_string()
        return session_string
    finally:
        await app.disconnect()


async def make_telethon_string(
    api_id: int,
    api_hash: str,
    phone: str,
    code: Optional[str],
    password: Optional[str] = None
) -> str:
    # Start with an empty in-memory session
    sess = TLStringSession()
    client = TelegramClient(sess, api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            if password:
                # When SessionPasswordNeededError was already raised, we arrive here with password available
                await client.sign_in(password=password)
            else:
                if not code:
                    # send_code_request already done earlier in the flow
                    raise RuntimeError("Missing OTP code.")
                await client.sign_in(phone=phone, code=code)
        # Export the string
        s = client.session.save()
        return s
    finally:
        await client.disconnect()


# ------------- DELIVERY & CLEANUP -------------

async def _deliver_session(m: Message, sess: str, framework: str):
    try:
        await m.reply_text(
            f"**{framework} Session String** (keep it secret):\n\n"
            f"`{sess}`\n\n"
            "Tip: You can revoke sessions from **Telegram > Settings > Privacy & Security > Active Sessions**.\n"
            "For safety, delete this chat after saving.",
            parse_mode=PM.MARKDOWN, disable_web_page_preview=True
        )
    except Exception:
        # Fallback: split if too long (very rare)
        chunks = [sess[i:i+4000] for i in range(0, len(sess), 4000)]
        await m.reply_text(f"**{framework} Session (part 1/{len(chunks)})**:\n`{chunks[0]}`", parse_mode=PM.MARKDOWN)
        for i, ch in enumerate(chunks[1:], start=2):
            await m.reply_text(f"**Part {i}/{len(chunks)}**:\n`{ch}`", parse_mode=PM.MARKDOWN)


# ------------- CANCEL COMMAND -------------

@Gojo.on_message(command(["cancel", "stop"]) & filters.private)
async def cancel_cmd(c: Gojo, m: Message):
    uid = m.from_user.id
    if uid in WIZARDS:
        _reset(uid)
        await m.reply_text("Wizard **cancelled**. No data stored. ✅", parse_mode=PM.MARKDOWN)
    else:
        await m.reply_text("Nothing to cancel.", parse_mode=PM.MARKDOWN)


# ------------- PLUGIN META -------------

__PLUGIN__ = "sessiongen"

_DISABLE_CMDS_ = ["session", "gensession", "string", "cancel", "stop"]

__HELP__ = """
**Session String Generator (DM only)**
Start the wizard:
• /session — generate a Pyrogram or Telethon session string

Controls:
• Inline buttons to choose framework, resend OTP, or cancel
• /cancel — aborts the wizard anytime

Notes:
• Works only in **private chat** for security
• Supports 2FA accounts
• No files are written; sessions are generated **in-memory**
"""
