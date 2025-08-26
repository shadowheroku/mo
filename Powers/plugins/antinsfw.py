import os
import json
import requests
from datetime import datetime

from pyrogram import filters, ContinuePropagation
from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.msg_types import Types

# ─── CONFIG ───
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "862487500")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")

DATA_FILE = "antinsfw.json"

# ─── LOAD / SAVE HELPERS ───
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {"antinsfw": {}, "free_users": {}}
    return {"antinsfw": {}, "free_users": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"antinsfw": ANTINSFW, "free_users": FREE_USERS}, f, indent=2)

data = load_data()
ANTINSFW = data.get("antinsfw", {})       # {chat_id: True/False}
FREE_USERS = data.get("free_users", {})   # {chat_id: [user_ids]}


# ─── HELPERS ───
async def scan_nsfw(file_path: str) -> bool:
    """
    Uploads media to Sightengine API and checks for NSFW.
    Returns True if NSFW is detected, else False.
    """
    try:
        url = "https://api.sightengine.com/1.0/check.json"
        with open(file_path, "rb") as f:
            r = requests.post(
                url,
                files={"media": f},
                data={
                    "models": "nudity",
                    "api_user": SIGHTENGINE_API_USER,
                    "api_secret": SIGHTENGINE_API_SECRET,
                },
                timeout=20,
            )
        data = r.json()
        if "nudity" in data:
            if data["nudity"]["sexual_activity"] > 0.5 or data["nudity"]["sexual_display"] > 0.5:
                return True
        return False
    except Exception:
        return False


# ─── TOGGLE ANTINSFW ───
@Gojo.on_message(command(["antinsfw"]) & filters.group)
async def toggle_antinsfw(c: Gojo, m: Message):
    chat = str(m.chat.id)
    if len(m.command) == 1:
        status = "ON ✅" if ANTINSFW.get(chat, False) else "OFF ❌"
        return await m.reply_text(f"Anti-NSFW is currently **{status}**")

    arg = m.command[1].lower()
    if arg == "on":
        ANTINSFW[chat] = True
        save_data()
        await m.reply_text("🚨 Anti-NSFW enabled in this group.")
    elif arg == "off":
        ANTINSFW[chat] = False
        save_data()
        await m.reply_text("⚠️ Anti-NSFW disabled in this group.")


# ─── FREE USER ───
@Gojo.on_message(command(["free"]) & filters.group)
async def free_user(c: Gojo, m: Message):
    chat = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("Reply to a user to free them from NSFW restrictions.")
    user_id = str(m.reply_to_message.from_user.id)

    FREE_USERS.setdefault(chat, [])
    if user_id not in FREE_USERS[chat]:
        FREE_USERS[chat].append(user_id)

    save_data()
    await m.reply_text(f"✅ {m.reply_to_message.from_user.mention} is now free from Anti-NSFW.")


# ─── SCAN MEDIA ───
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.animation | filters.document | filters.sticker))
async def nsfw_scanner(c: Gojo, m: Message):
    chat = str(m.chat.id)
    if not ANTINSFW.get(chat, False):
        raise ContinuePropagation

    if not m.from_user or str(m.from_user.id) in FREE_USERS.get(chat, []):
        raise ContinuePropagation

    try:
        # download media
        file_path = await m.download()
        is_nsfw = await scan_nsfw(file_path)
        os.remove(file_path)

        if is_nsfw:
            content_type = (
                "Photo" if m.photo else
                "Video" if m.video else
                "GIF" if m.animation else
                "Document" if m.document else
                "Sticker" if m.sticker else
                "Media"
            )
            await m.delete()
            await m.chat.send_message(
                f"🚫 {m.from_user.mention} tried to send NSFW content (**{content_type}**)!",
                parse_mode=PM.MARKDOWN,
            )
    except Exception:
        pass

    raise ContinuePropagation


# ─── PLUGIN INFO ───
__PLUGIN__ = "anti_nsfw"
_DISABLE_CMDS_ = ["antinsfw", "free"]

__HELP__ = """
**Anti-NSFW**
• /antinsfw on/off → Enable or disable NSFW protection in group
• /free (reply) → Free a user from restriction (their media won’t be scanned)

The bot deletes any NSFW media and alerts the group.
"""
