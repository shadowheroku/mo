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
    # atomic save: write to temp and replace
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
    """Return True if user is admin or owner in the chat."""
    try:
        member = await c.get_chat_member(chat_id, user_id)
        # member.status is an enum ChatMemberStatus
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def scan_nsfw(file_path: str):
    """
    Scan file via Sightengine.
    Returns (is_nsfw: bool, raw_response: dict or None)
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
        print("Anti-NSFW: scan error:", e)
        traceback.print_exc()
        return False, None

    # parse nudity info (Sightengine returns a 'nudity' dict)
    nudity = j.get("nudity", {}) or {}
    try:
        raw = float(nudity.get("raw", 0))
        partial = float(nudity.get("partial", 0))
        safe = float(nudity.get("safe", 1))
        sexual_activity = float(nudity.get("sexual_activity", 0))
        sexual_display = float(nudity.get("sexual_display", 0))
        suggestive = float(nudity.get("suggestive", 0)) if nudity.get("suggestive") is not None else 0.0
    except Exception:
        raw = partial = sexual_activity = sexual_display = suggestive = 0.0
        safe = 1.0

    # heuristic thresholds (tweakable)
    if raw >= 0.6 or partial >= 0.6 or sexual_activity >= 0.5 or sexual_display >= 0.5 or safe <= 0.3:
        return True, j
    return False, j

def _content_type_label(m: Message) -> str:
    if m.photo: return "📸 Photo"
    if m.video: return "🎥 Video"
    if m.animation: return "🎞️ GIF"
    if m.document: return "📂 Document"
    if m.sticker: return "🖼️ Sticker"
    return "📦 Media"

def _user_markdown_link(user) -> str:
    # returns [Name](tg://user?id=ID)
    name = user.first_name or "User"
    # include last name if exists
    if getattr(user, "last_name", None):
        name = f"{name} {user.last_name}"
    # escape brackets not necessary for simple names; if you need markdownv2 escaping, adapt.
    return f"[{name}](tg://user?id={user.id})"


# ─── /antinsfw with inline buttons (admin-only toggle) ───
@Gojo.on_message(command(["antinsfw"]) & filters.group)
async def toggle_antinsfw(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    # show status if no arg
    if len(m.command) == 1:
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw:on:{chat_id_str}"),
                    InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw:off:{chat_id_str}")
                ],
                [
                    InlineKeyboardButton("⚙️ View Settings", callback_data=f"antinsfw:status:{chat_id_str}")
                ]
            ]
        )
        return await m.reply_text(
            f"🚨 **Anti-NSFW System** 🚨\n\nCurrent status: **{status}**\n\nUse the buttons below to change settings (admins only).",
            reply_markup=kb,
            parse_mode=PM.MARKDOWN
        )

    await m.reply_text("ℹ️ Use `/antinsfw` (without args) and press the buttons to toggle.")


@Gojo.on_callback_query(filters.regex(r"^antinsfw:(on|off|status):(-?\d+)$"))
async def antinsfw_callback(c: Gojo, q: CallbackQuery):
    action, chat_id_str = q.data.split(":", 2)[1:]
    chat_id = int(chat_id_str)
    user_id = q.from_user.id

    # require admin
    if action != "status" and not await is_chat_admin(c, chat_id, user_id):
        return await q.answer("Only group admins can change Anti-NSFW.", show_alert=True)

    if action == "on":
        ANTINSFW[chat_id_str] = True
        save_data()
        await q.message.edit_text(
            "🚨 Anti-NSFW is now **ENABLED ✅**\n\nDetected NSFW media will be removed automatically.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw:off:{chat_id_str}")]]),
            parse_mode=PM.MARKDOWN
        )
        await q.answer("Anti-NSFW enabled.")
    elif action == "off":
        ANTINSFW[chat_id_str] = False
        save_data()
        await q.message.edit_text(
            "⚠️ Anti-NSFW is now **DISABLED ❌**\n\nThe bot will not scan media until enabled again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw:on:{chat_id_str}")]]),
            parse_mode=PM.MARKDOWN
        )
        await q.answer("Anti-NSFW disabled.")
    else:  # status
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        await q.answer(f"Anti-NSFW status: {status}", show_alert=True)


# ─── /free (reply) - exempt a user (admin only), shows inline remove/status ───
@Gojo.on_message(command(["free"]) & filters.group)
async def free_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /free them from scans.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Only group admins can free users.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)
    FREE_USERS.setdefault(chat_id_str, [])

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛑 Remove Free", callback_data=f"free:unfree:{chat_id_str}:{target_id_str}")],
            [InlineKeyboardButton("ℹ️ Check Status", callback_data=f"free:status:{chat_id_str}:{target_id_str}")]
        ]
    )

    if target_id_str not in FREE_USERS[chat_id_str]:
        FREE_USERS[chat_id_str].append(target_id_str)
        save_data()
        await m.reply_text(
            f"✅ {_user_markdown_link(target)} has been *freed* from Anti-NSFW scans by {_user_markdown_link(m.from_user)}.",
            reply_markup=kb,
            parse_mode=PM.MARKDOWN
        )
    else:
        await m.reply_text(
            f"⚡ {_user_markdown_link(target)} is already free.",
            reply_markup=kb,
            parse_mode=PM.MARKDOWN
        )

@Gojo.on_callback_query(filters.regex(r"^free:(unfree|status):(-?\d+):(\d+)$"))
async def free_buttons(c: Gojo, q: CallbackQuery):
    parts = q.data.split(":")
    action, chat_id_str, target_id_str = parts[1], parts[2], parts[3]
    chat_id = int(chat_id_str)
    user_id = q.from_user.id

    # only admins
    if not await is_chat_admin(c, chat_id, user_id):
        return await q.answer("Only group admins can use this.", show_alert=True)

    if action == "unfree":
        if target_id_str in FREE_USERS.get(chat_id_str, []):
            FREE_USERS[chat_id_str].remove(target_id_str)
            save_data()
            await q.message.edit_text("🛑 User removed from free list.", parse_mode=PM.MARKDOWN)
            await q.answer("User unfreed.")
        else:
            await q.answer("User is not free.", show_alert=True)
    else:  # status
        if target_id_str in FREE_USERS.get(chat_id_str, []):
            await q.answer("✅ User is free from scans.", show_alert=True)
        else:
            await q.answer("⚠️ User is NOT free from scans.", show_alert=True)


# ─── /unfree (reply) - admin only ───
@Gojo.on_message(command(["unfree"]) & filters.group)
async def unfree_user_cmd(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /unfree them.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("🚫 Only group admins can unfree users.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)

    if target_id_str in FREE_USERS.get(chat_id_str, []):
        FREE_USERS[chat_id_str].remove(target_id_str)
        save_data()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done", callback_data="unfree_done"), InlineKeyboardButton("❌ Close", callback_data="unfree_close")]])
        await m.reply_text(f"✨ {_user_markdown_link(target)} has been removed from Free List.", reply_markup=kb, parse_mode=PM.MARKDOWN)
    else:
        await m.reply_text("⚠️ That user is not on the Free List.")


@Gojo.on_callback_query(filters.regex(r"^unfree_"))
async def unfree_buttons(c: Gojo, q: CallbackQuery):
    if q.data == "unfree_done":
        await q.answer("✅ Done.", show_alert=True)
    elif q.data == "unfree_close":
        try:
            await q.message.delete()
        except Exception:
            pass
        await q.answer()


# ─── MAIN SCANNER: scans common media types in groups ───
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
        # download media to temp file
        file_path = await m.download()
        if not file_path:
            raise ContinuePropagation

        is_nsfw, raw_resp = await scan_nsfw(file_path)

        # cleanup (best-effort)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

        if is_nsfw:
            user = m.from_user
            content_type = _content_type_label(m)

            # compute NSFW % from response
            nsfw_score = 0.0
            try:
                nudity = (raw_resp or {}).get("nudity", {}) or {}
                nsfw_score = max(
                    float(nudity.get("sexual_activity", 0) or 0),
                    float(nudity.get("sexual_display", 0) or 0),
                    float(nudity.get("suggestive", 0) or 0),
                    float(nudity.get("raw", 0) or 0),
                    float(nudity.get("partial", 0) or 0)
                ) * 100.0
            except Exception:
                nsfw_score = 0.0

            # try delete
            try:
                await m.delete()
            except Exception as e:
                print("Anti-NSFW: couldn't delete message:", e)

            # nice alert message (clickable name + id)
            try:
                alert_msg = (
                    f"🚨 **Anti-NSFW Alert!** 🚨\n\n"
                    f"👤 User: {_user_markdown_link(user)}\n"
                    f"🆔 ID: `{user.id}`\n"
                    f"📛 Type: **{content_type}**\n"
                    f"📊 Detected NSFW Probability: **{nsfw_score:.2f}%**\n\n"
                    f"⚠️ NSFW content was detected and removed automatically."
                )

                # moderation buttons for admins
                kb = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("👮 Warn", callback_data=f"mod:warn:{chat_id_str}:{user.id}"),
                            InlineKeyboardButton("🔨 Ban", callback_data=f"mod:ban:{chat_id_str}:{user.id}")
                        ],
                        [InlineKeyboardButton("❌ Dismiss", callback_data=f"mod:dismiss:{chat_id_str}:{user.id}")]
                    ]
                )

                await c.send_message(
                    m.chat.id,
                    alert_msg,
                    parse_mode=PM.MARKDOWN,
                    reply_markup=kb
                )
            except Exception as e:
                print("Anti-NSFW: couldn't send alert:", e)

    except ContinuePropagation:
        raise ContinuePropagation
    except Exception as e:
        print("Anti-NSFW: unexpected error in scanner:", e)
        traceback.print_exc()
    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

    raise ContinuePropagation


# ─── Simple moderation callback handlers (warn/ban/dismiss) ───
@Gojo.on_callback_query(filters.regex(r"^mod:(warn|ban|dismiss):(-?\d+):(\d+)$"))
async def mod_buttons(c: Gojo, q: CallbackQuery):
    action, chat_id_str, target_id_str = q.data.split(":")[1:]
    chat_id = int(chat_id_str)
    user_id = q.from_user.id

    # restrict to admins
    if not await is_chat_admin(c, chat_id, user_id):
        return await q.answer("Only admins can use moderation actions.", show_alert=True)

    if action == "dismiss":
        try:
            await q.message.delete()
        except Exception:
            pass
        return await q.answer("Dismissed.", show_alert=False)

    if action == "warn":
        # just send a group message warning (customize as needed)
        try:
            await c.send_message(chat_id, f"⚠️ [User](tg://user?id={int(q.data.split(':')[-1])}) — you were warned for posting NSFW content.", parse_mode=PM.MARKDOWN)
        except Exception:
            pass
        return await q.answer("Warn sent.", show_alert=False)

    if action == "ban":
        target_id = int(target_id_str)
        try:
            # try to ban (kick) user (bot needs ban permissions)
            await c.ban_chat_member(chat_id, target_id)
            await q.answer("User banned.", show_alert=True)
            try:
                await q.message.edit_text("🔨 User has been banned by admin.", parse_mode=PM.MARKDOWN)
            except Exception:
                pass
        except Exception as e:
            print("Anti-NSFW: failed to ban:", e)
            return await q.answer("Failed to ban (check bot perms).", show_alert=True)


# ─── PLUGIN INFO ───
__PLUGIN__ = "anti_nsfw"
_DISABLE_CMDS_ = ["antinsfw", "free", "unfree"]
__HELP__ = """
**Anti-NSFW**
• /antinsfw → Open inline buttons to enable/disable scanner (admin only)
• /free (reply) → Free a user from scans (admin only)
• /unfree (reply) → Remove user from free list (admin only)"""
