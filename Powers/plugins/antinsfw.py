import os
import json
import asyncio
import tempfile
import traceback

from datetime import datetime

# try async HTTP first, fallback to requests in a thread
try:
    import httpx
    HAS_HTTPX = True
except Exception:
    import requests
    HAS_HTTPX = False

from pyrogram import filters, ContinuePropagation
from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.msg_types import Types

# ─── CONFIG ───
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "862487500")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")

DATA_FILE = os.path.join(os.getcwd(), "antinsfw.json")  # file will be created next to cwd

# ─── UTIL: load/save JSON (atomic save) ───
def _normalize_loaded(d):
    ant = {}
    free = {}
    for k, v in d.get("antinsfw", {}).items():
        ant[str(k)] = bool(v)
    for k, v in d.get("free_users", {}).items():
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
from pyrogram.enums import ChatMemberStatus
from Powers.bot_class import Gojo

async def is_chat_admin(c: Gojo, chat_id: int, user_id: int) -> bool:
    """Return True if user is admin or owner in the chat."""
    try:
        member = await c.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False


async def scan_nsfw(file_path: str):
    """
    Scan file via Sightengine.
    Returns (is_nsfw: bool, raw_response: dict or None)
    Uses httpx.AsyncClient if available, else runs requests.post in executor.
    """
    url = "https://api.sightengine.com/1.0/check.json"
    payload = {
        "models": "nudity",
        "api_user": SIGHTENGINE_API_USER,
        "api_secret": SIGHTENGINE_API_SECRET,
    }

    try:
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=20) as client:
                with open(file_path, "rb") as fh:
                    files = {"media": ("file", fh, "application/octet-stream")}
                    resp = await client.post(url, data=payload, files=files)
                resp.raise_for_status()
                j = resp.json()
        else:
            loop = asyncio.get_event_loop()
            def _sync_post():
                with open(file_path, "rb") as fh:
                    return requests.post(url, data=payload, files={"media": fh}, timeout=20)
            resp = await loop.run_in_executor(None, _sync_post)
            j = resp.json()
    except Exception as e:
        # print stack to console for debugging (don't spam chat)
        print("Anti-NSFW: scan error:", e)
        traceback.print_exc()
        return False, None

    # parse safe/nudity heuristics (Sightengine returns a "nudity" dict)
    nudity = j.get("nudity", {}) or {}
    try:
        raw = float(nudity.get("raw", 0))
        partial = float(nudity.get("partial", 0))
        safe = float(nudity.get("safe", 1))
        sexual_activity = float(nudity.get("sexual_activity", 0))
        sexual_display = float(nudity.get("sexual_display", 0))
    except Exception:
        raw = partial = sexual_activity = sexual_display = 0.0
        safe = 1.0

    # Heuristics - tweak thresholds if you want to be stricter/looser
    if raw >= 0.6 or partial >= 0.6 or sexual_activity >= 0.5 or sexual_display >= 0.5 or safe <= 0.3:
        return True, j
    return False, j


def _content_type_label(m: Message) -> str:
    if m.photo:
        return "Photo"
    if m.video:
        return "Video"
    if m.animation:
        return "GIF"
    if m.sticker:
        return "Sticker"
    if m.document:
        return "Document"
    return "Media"


# ─── /antinsfw on|off (admin only) ───
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Gojo.on_message(command(["antinsfw"]) & filters.group)
async def toggle_antinsfw(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    # show status if no arg
    if len(m.command) == 1:
        status = "✅ ON" if ANTINSFW.get(chat_id_str, False) else "❌ OFF"
        kb = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw_on:{chat_id_str}"),
                InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw_off:{chat_id_str}")
            ]]
        )
        return await m.reply_text(
            f"🚨 **Anti-NSFW System**\n\nCurrent status: **{status}**",
            reply_markup=kb
        )

    await m.reply_text("ℹ️ Use the buttons below to toggle Anti-NSFW.")


# =============================
# CALLBACK HANDLER FOR BUTTONS
# =============================
@Gojo.on_callback_query(filters.regex(r"^antinsfw_(on|off):"))
async def antinsfw_callback(c: Gojo, q):
    action, chat_id_str = q.data.split(":")
    user_id = q.from_user.id

    # require admin
    if not await is_chat_admin(c, int(chat_id_str), user_id):
        return await q.answer("Only admins can change Anti-NSFW settings.", show_alert=True)

    if action == "on":
        ANTINSFW[chat_id_str] = True
        save_data()
        await q.message.edit_text(
            "🚨 Anti-NSFW is now **ENABLED ✅**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw_off:{chat_id_str}")]]
            )
        )
    elif action == "off":
        ANTINSFW[chat_id_str] = False
        save_data()
        await q.message.edit_text(
            "⚠️ Anti-NSFW is now **DISABLED ❌**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw_on:{chat_id_str}")]]
            )
        )


# ─── /free (reply) - mark user exempt (admin only) ───
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Gojo.on_message(command(["free"]) & filters.group)
async def free_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /free them from scans.")

    # require admin to free others (avoid misuse)
    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only group admins can free users.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)
    FREE_USERS.setdefault(chat_id_str, [])

    if target_id_str not in FREE_USERS[chat_id_str]:
        FREE_USERS[chat_id_str].append(target_id_str)
        save_data()
        await m.reply_text(
            f"✅ {target.mention} has been **freed from Anti-NSFW scans!**",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🛑 Remove Free", callback_data=f"unfree:{chat_id_str}:{target_id_str}")
                    ],
                    [
                        InlineKeyboardButton("ℹ️ Check Status", callback_data=f"status:{chat_id_str}:{target_id_str}")
                    ]
                ]
            )
        )
    else:
        await m.reply_text(
            f"⚡ {target.mention} is **already free**.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🛑 Remove Free", callback_data=f"unfree:{chat_id_str}:{target_id_str}")
                    ],
                    [
                        InlineKeyboardButton("ℹ️ Check Status", callback_data=f"status:{chat_id_str}:{target_id_str}")
                    ]
                ]
            )
        )

@Gojo.on_callback_query(filters.regex(r"^(unfree|status):"))
async def free_buttons(c: Gojo, q):
    action, chat_id_str, target_id_str = q.data.split(":")
    user_id = q.from_user.id

    # ensure only admins can press buttons
    if not await is_chat_admin(c, int(chat_id_str), user_id):
        return await q.answer("Only admins can use this button!", show_alert=True)

    if action == "unfree":
        if target_id_str in FREE_USERS.get(chat_id_str, []):
            FREE_USERS[chat_id_str].remove(target_id_str)
            save_data()
            await q.edit_message_text("🛑 User has been removed from Free list.")
        else:
            await q.answer("User is not free.", show_alert=True)

    elif action == "status":
        if target_id_str in FREE_USERS.get(chat_id_str, []):
            await q.answer("✅ User is free from scans.", show_alert=True)
        else:
            await q.answer("⚠️ User is NOT free from scans.", show_alert=True)


# ─── /unfree (reply) - remove exemption (admin only) ───
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Gojo.on_message(command(["unfree"]) & filters.group)
async def unfree_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    # Must reply to a user
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /unfree them.")

    # Check if sender is admin
    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("🚫 Only group admins can unfree users.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)

    # If user is in FREE list
    if target_id_str in FREE_USERS.get(chat_id_str, []):
        FREE_USERS[chat_id_str].remove(target_id_str)
        save_data()

        # Buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Done", callback_data="unfree_done"),
                    InlineKeyboardButton("❌ Close", callback_data="unfree_close"),
                ]
            ]
        )

        await m.reply_text(
            f"✨ {target.mention} has been **removed from Free List**!",
            reply_markup=keyboard,
        )
    else:
        await m.reply_text("⚠️ That user is not on the Free List.")
        

# Handle button presses
@Gojo.on_callback_query(filters.regex("^unfree_"))
async def unfree_buttons(c: Gojo, q):
    if q.data == "unfree_done":
        await q.answer("✅ User removed successfully!", show_alert=True)
    elif q.data == "unfree_close":
        await q.message.delete()
        await q.answer()


# ─── MAIN SCANNER: scans common media types in groups ───
def _content_type_label(m: Message) -> str:
    if m.photo: return "📸 Photo"
    if m.video: return "🎥 Video"
    if m.animation: return "🎞️ GIF"
    if m.document: return "📂 Document"
    if m.sticker: return "🖼️ Sticker"
    return "📦 Media"

@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.animation | filters.document | filters.sticker))
async def nsfw_scanner(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    # only active when enabled
    if not ANTINSFW.get(chat_id_str, False):
        raise ContinuePropagation

    # ignore bots / system messages
    if not m.from_user or m.from_user.is_bot:
        raise ContinuePropagation

    # check free list
    if str(m.from_user.id) in FREE_USERS.get(chat_id_str, []):
        raise ContinuePropagation

    file_path = None
    try:
        file_path = await m.download()
        if not file_path:
            raise ContinuePropagation

        is_nsfw, raw_resp = await scan_nsfw(file_path)

        # cleanup
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        if is_nsfw:
            user = m.from_user
            content_type = _content_type_label(m)

            # extract nudity confidence scores
            nsfw_score = 0
            try:
                nudity = raw_resp.get("nudity", {})
                nsfw_score = max(
                    nudity.get("sexual_activity", 0),
                    nudity.get("sexual_display", 0),
                    nudity.get("suggestive", 0),
                ) * 100  # convert to %
            except Exception:
                pass

            # delete message (if bot has perms)
            try:
                await m.delete()
            except Exception as e:
                print("Anti-NSFW: couldn't delete message:", e)

            # announce in group
            try:
                alert_msg = (
                    f"🚨 **Anti-NSFW Alert!** 🚨\n\n"
                    f"👤 User: {user.mention if user.username else user.first_name}\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"📛 Type: **{content_type}**\n"
                    f"📊 Detected NSFW Probability: **{nsfw_score:.2f}%**\n\n"
                    f"⚠️ NSFW content was detected and removed automatically."
                )
                await c.send_message(
                    m.chat.id,
                    alert_msg,
                    parse_mode=PM.MARKDOWN,
                )
            except Exception as e:
                print("Anti-NSFW: couldn't send alert:", e)

    except ContinuePropagation:
        raise ContinuePropagation
    except Exception as e:
        print("Anti-NSFW: unexpected error in scanner:", e)
        traceback.print_exc()
    finally:
        # ensure file cleanup
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
**Anti-NSFW**
• /antinsfw on/off → Enable or disable NSFW protection in group (admin only)
• /free (reply) → Free a user from restriction (admin only)
• /unfree (reply) → Remove user from free list (admin only)

Notes:
• Bot must be admin with permission to delete messages.
• Ensure SIGHTENGINE_API_USER and SIGHTENGINE_API_SECRET are set in environment.
"""
