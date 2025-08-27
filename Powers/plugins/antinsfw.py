import os
import json
import asyncio
import tempfile
import traceback

from pyrogram import filters, ContinuePropagation
from pyrogram.enums import ParseMode as PM, ChatMemberStatus
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── CONFIG ───
HF_API_URL = os.getenv(
    "HF_API_URL",
    "https://api-inference.huggingface.co/models/erfanzar/NSFW-Detection"
)
HF_API_KEY = os.getenv("HF_API_KEY", "")  # optional, free Hugging Face token

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

DATA_FILE = os.path.join(os.getcwd(), "antinsfw.json")  # file persists settings


# ─── UTIL: load/save JSON ───
def _normalize_loaded(d):
    ant = {}
    free = {}
    for k, v in (d.get("antinsfw") or {}).items():
        ant[str(k)] = bool(v)
    for k, v in (d.get("free_users") or {}).items():
        free[str(k)] = [str(uid) for uid in (v or [])]
    return {"antinsfw": ant, "free_users": free}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"antinsfw": {}, "free_users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_loaded(data)
    except Exception:
        return {"antinsfw": {}, "free_users": {}}


def save_data():
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(DATA_FILE) or ".")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmpf:
            json.dump({"antinsfw": ANTINSFW, "free_users": FREE_USERS}, tmpf, indent=2, ensure_ascii=False)
        os.replace(tmp_path, DATA_FILE)
    except Exception:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


_data = load_data()
ANTINSFW = _data.get("antinsfw", {})     # {chat_id_str: True/False}
FREE_USERS = _data.get("free_users", {}) # {chat_id_str: [user_id_str,...]}


# ─── HELPERS ───
async def is_chat_admin(c: Gojo, chat_id: int, user_id: int) -> bool:
    """Check if user is owner or admin with 'can_promote_members' rights."""
    try:
        member = await c.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member.privileges, "can_promote_members", False):
            return True
        return False
    except Exception:
        return False


async def scan_nsfw(file_path: str):
    """
    Scan file using Hugging Face NSFW model.
    Returns (is_nsfw: bool, raw_response: dict or None).
    """
    import httpx, requests

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        if "httpx" in globals():
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(HF_API_URL, headers=HEADERS, data=data)
                result = resp.json()
        else:
            loop = asyncio.get_event_loop()
            def _sync_post():
                return requests.post(HF_API_URL, headers=HEADERS, data=open(file_path, "rb"))
            resp = await loop.run_in_executor(None, _sync_post)
            result = resp.json()

        # Expecting something like: [{'label': 'NSFW', 'score': 0.98}, {'label': 'SFW', 'score': 0.02}]
        if isinstance(result, list):
            nsfw_score = max([x["score"] for x in result if "nsfw" in x["label"].lower()])
            return nsfw_score >= 0.6, result
        return False, result
    except Exception as e:
        print("Anti-NSFW scan error:", e)
        traceback.print_exc()
        return False, None


def _content_type_label(m: Message) -> str:
    if m.photo: return "📸 Photo"
    if m.video: return "🎥 Video"
    if m.animation: return "🎞️ GIF"
    if m.document: return "📂 Document"
    if m.sticker: return "🖼️ Sticker"
    return "📦 Media"


def _user_markdown_link(user) -> str:
    name = user.first_name or "User"
    if getattr(user, "last_name", None):
        name = f"{name} {user.last_name}"
    return f"[{name}](tg://user?id={user.id})"


# ─── COMMANDS ───
@Gojo.on_message(command(["antinsfw"]) & filters.group)
async def toggle_antinsfw(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    if len(m.command) == 1:
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw:on:{chat_id_str}"),
                    InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw:off:{chat_id_str}")
                ],
                [InlineKeyboardButton("⚙️ View Settings", callback_data=f"antinsfw:status:{chat_id_str}")]
            ]
        )
        return await m.reply_text(
            f"🚨 **Anti-NSFW System** 🚨\n\nCurrent status: **{status}**",
            reply_markup=kb,
            parse_mode=PM.MARKDOWN
        )
    await m.reply_text("ℹ️ Use `/antinsfw` without args and press the buttons.")


@Gojo.on_callback_query(filters.regex(r"^antinsfw:(on|off|status):(-?\d+)$"))
async def antinsfw_callback(c: Gojo, q: CallbackQuery):
    action, chat_id_str = q.data.split(":", 2)[1:]
    chat_id = int(chat_id_str)
    user_id = q.from_user.id

    if action != "status" and not await is_chat_admin(c, chat_id, user_id):
        return await q.answer("Admins with 'add admin' rights only.", show_alert=True)

    if action == "on":
        ANTINSFW[chat_id_str] = True
        save_data()
        await q.message.edit_text("🚨 Anti-NSFW is now **ENABLED ✅**", parse_mode=PM.MARKDOWN)
        await q.answer("Enabled.")
    elif action == "off":
        ANTINSFW[chat_id_str] = False
        save_data()
        await q.message.edit_text("⚠️ Anti-NSFW is now **DISABLED ❌**", parse_mode=PM.MARKDOWN)
        await q.answer("Disabled.")
    else:
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        await q.answer(f"Anti-NSFW: {status}", show_alert=True)


# ─── FREE USERS ───
@Gojo.on_message(command(["free"]) & filters.group)
async def free_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /free them.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Admins only.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)
    FREE_USERS.setdefault(chat_id_str, [])

    if target_id_str not in FREE_USERS[chat_id_str]:
        FREE_USERS[chat_id_str].append(target_id_str)
        save_data()
        await m.reply_text(
            f"✅ {_user_markdown_link(target)} has been *freed* from Anti-NSFW scans.",
            parse_mode=PM.MARKDOWN
        )
    else:
        await m.reply_text(f"⚡ {_user_markdown_link(target)} is already free.", parse_mode=PM.MARKDOWN)


@Gojo.on_message(command(["unfree"]) & filters.group)
async def unfree_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /unfree them.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("🚫 Admins only.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)

    if target_id_str in FREE_USERS.get(chat_id_str, []):
        FREE_USERS[chat_id_str].remove(target_id_str)
        save_data()
        await m.reply_text(f"✨ {_user_markdown_link(target)} removed from Free List.", parse_mode=PM.MARKDOWN)
    else:
        await m.reply_text("⚠️ User not in Free List.")


# ─── MAIN SCANNER ───
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.animation | filters.document | filters.sticker))
async def nsfw_scanner(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    if not ANTINSFW.get(chat_id_str, False):
        raise ContinuePropagation
    if not m.from_user or m.from_user.is_bot:
        raise ContinuePropagation
    if str(m.from_user.id) in FREE_USERS.get(chat_id_str, []):
        raise ContinuePropagation

    file_path = None
    try:
        file_path = await m.download()
        if not file_path:
            raise ContinuePropagation

        is_nsfw, raw_resp = await scan_nsfw(file_path)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        if is_nsfw:
            try:
                await m.delete()
            except Exception:
                pass

            await c.send_message(
                m.chat.id,
                f"🚨 **Anti-NSFW Alert!** 🚨\n\n👤 {_user_markdown_link(m.from_user)}\n📛 Type: {_content_type_label(m)}\n⚠️ NSFW content detected & removed.",
                parse_mode=PM.MARKDOWN
            )
    except ContinuePropagation:
        raise ContinuePropagation
    except Exception as e:
        print("Anti-NSFW error:", e)
        traceback.print_exc()
    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
    raise ContinuePropagation


# ─── PLUGIN INFO ───
__PLUGIN__ = "anti_nsfw"
_DISABLE_CMDS_ = ["antinsfw", "free", "unfree"]
__HELP__ = """
**Anti-NSFW (Free HuggingFace API)**
• /antinsfw → Enable/disable scanner (admin only)
• /free (reply) → Free user from scans (admin only)
• /unfree (reply) → Remove user from free list (admin only)
"""
