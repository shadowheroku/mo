import os
import sqlite3
import requests
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers import LOGGER

# ======================
# CONFIGURATION
# ======================
# Get your API keys from https://sightengine.com/
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "862487500")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")

DB_PATH = "antinsfw.db"

# ======================
# DATABASE INIT
# ======================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create base table if not exists
cursor.execute(
    """CREATE TABLE IF NOT EXISTS antinsfw (
        chat_id INTEGER PRIMARY KEY,
        enabled INTEGER DEFAULT 0
    )"""
)

# ✅ Add strict_mode column if missing
cursor.execute("PRAGMA table_info(antinsfw)")
columns = [col[1] for col in cursor.fetchall()]
if "strict_mode" not in columns:
    cursor.execute("ALTER TABLE antinsfw ADD COLUMN strict_mode INTEGER DEFAULT 0")

cursor.execute(
    """CREATE TABLE IF NOT EXISTS nsfw_warnings (
        user_id INTEGER,
        chat_id INTEGER,
        warnings INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, chat_id)
    )"""
)

conn.commit()

# ======================
# DATABASE FUNCTIONS
# ======================
def set_antinsfw(chat_id: int, enabled: bool, strict_mode: bool = False):
    cursor.execute(
        "INSERT OR REPLACE INTO antinsfw (chat_id, enabled, strict_mode) VALUES (?, ?, ?)",
        (chat_id, 1 if enabled else 0, 1 if strict_mode else 0),
    )
    conn.commit()


def get_antinsfw(chat_id: int) -> tuple:
    cursor.execute("SELECT enabled, strict_mode FROM antinsfw WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return bool(row[0]), bool(row[1])
    return False, False


def add_warning(user_id: int, chat_id: int):
    cursor.execute(
        """INSERT INTO nsfw_warnings (user_id, chat_id, warnings) VALUES (?, ?, 1)
           ON CONFLICT(user_id, chat_id) DO UPDATE SET warnings = warnings + 1""",
        (user_id, chat_id),
    )
    conn.commit()


def get_warnings(user_id: int, chat_id: int) -> int:
    cursor.execute("SELECT warnings FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    row = cursor.fetchone()
    return row[0] if row else 0


def reset_warnings(user_id: int, chat_id: int):
    cursor.execute("DELETE FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()


def reset_all_warnings(chat_id: int):
    cursor.execute("DELETE FROM nsfw_warnings WHERE chat_id = ?", (chat_id,))
    conn.commit()

# ======================
# NSFW DETECTION
# ======================
def detect_nsfw(image_path: str) -> tuple:
    """
    Detect NSFW content using SightEngine API
    Returns (is_nsfw, score, details)
    """
    try:
        with open(image_path, "rb") as media:
            response = requests.post(
                "https://api.sightengine.com/1.0/check.json",
                files={"media": media},
                data={
                    "models": "nudity-2.1,wad,offensive,text-content,gore",
                    "api_user": SIGHTENGINE_API_USER,
                    "api_secret": SIGHTENGINE_API_SECRET,
                },
            )

        result = response.json()

        if response.status_code != 200 or result.get("status") != "success":
            LOGGER.error(f"SightEngine API error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False, 0, {}

        nudity_score = result.get("nudity", {}).get("sexual_activity", 0) + result.get("nudity", {}).get("sexual_display", 0)
        offensive_score = result.get("offensive", {}).get("prob", 0)
        weapon_score = result.get("weapon", 0)
        alcohol_score = result.get("alcohol", 0)
        drugs_score = result.get("drugs", 0)

        total_score = (
            nudity_score * 0.5
            + offensive_score * 0.2
            + weapon_score * 0.1
            + alcohol_score * 0.1
            + drugs_score * 0.1
        )

        is_nsfw = total_score > 0.7 or nudity_score > 0.8
        return is_nsfw, total_score, result

    except Exception as e:
        LOGGER.error(f"Error in NSFW detection: {e}")
        return False, 0, {}

# ======================
# HELP
# ======================
__HELP__ = """
🛡️ **Anti-NSFW Protection System**

**⭐ Admin Controls**
• `/antinsfw on|off` - Enable/disable protection  
• `/antinsfw strict on|off` - Toggle strict mode  
• `/antinsfw status` - View settings  

**🔍 Manual Scan**
• `/nsfwscan` (reply to media) - Scan file  

**⚠️ Warnings**
• `/nsfwwarns [user]` - Check user warnings  
• `/resetnsfwwarns [user]` - Reset warnings  
• `/resetallnsfwwarns` - Reset all warnings  
• `/mynsfwwarns` - Check your warnings  

**⚡ Auto-Actions**
- Deletes NSFW content  
- Issues warnings  
- Bans after 3 warnings  
"""

__MODULE__ = "Anti-NSFW"

# ======================
# TOGGLE COMMAND
# ======================
@Gojo.on_message(filters.command("antinsfw") & filters.group)
async def toggle_antinsfw(client: Gojo, message: Message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ Only admins can use this command.")
    except:
        return await message.reply_text("❌ Only admins can use this command.")

    if len(message.command) < 2:
        status, strict = get_antinsfw(message.chat.id)
        return await message.reply_text(
            f"⚙️ Anti-NSFW Settings:\n\nStatus: {'ON' if status else 'OFF'}\nStrict Mode: {'ON' if strict else 'OFF'}\n\n"
            "Usage: `/antinsfw on/off` or `/antinsfw strict on/off`",
        )

    arg1 = message.command[1].lower()
    if arg1 == "strict" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 == "on":
            set_antinsfw(message.chat.id, True, True)
            return await message.reply_text("✅ Strict mode enabled!")
        elif arg2 == "off":
            set_antinsfw(message.chat.id, True, False)
            return await message.reply_text("✅ Strict mode disabled!")
        else:
            return await message.reply_text("⚙️ Usage: `/antinsfw strict on/off`")

    elif arg1 == "status":
        status, strict = get_antinsfw(message.chat.id)
        return await message.reply_text(
            f"⚙️ Status: {'ON' if status else 'OFF'}\nStrict Mode: {'ON' if strict else 'OFF'}"
        )

    elif arg1 == "on":
        set_antinsfw(message.chat.id, True)
        return await message.reply_text("✅ Anti-NSFW enabled in this group!")
    elif arg1 == "off":
        set_antinsfw(message.chat.id, False)
        return await message.reply_text("❌ Anti-NSFW disabled in this group!")

    return await message.reply_text("⚙️ Usage: `/antinsfw on/off` or `/antinsfw strict on/off`")

# ======================
# WARNINGS COMMANDS
# ======================
@Gojo.on_message(filters.command("nsfwwarns") & filters.group)
async def check_nsfw_warns(client: Gojo, message: Message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ Only admins can use this command.")
    except:
        return await message.reply_text("❌ Only admins can use this command.")

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found.")
    else:
        return await message.reply_text("⚠️ Reply to a user or provide their ID/username.")

    warnings = get_warnings(target_user.id, message.chat.id)
    await message.reply_text(f"⚠️ {target_user.mention} has {warnings} NSFW warning(s).")


@Gojo.on_message(filters.command("resetnsfwwarns") & filters.group)
async def reset_nsfw_warns(client: Gojo, message: Message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ Only admins can use this command.")
    except:
        return await message.reply_text("❌ Only admins can use this command.")

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found.")
    else:
        return await message.reply_text("⚠️ Reply to a user or provide their ID/username.")

    reset_warnings(target_user.id, message.chat.id)
    await message.reply_text(f"✅ Warnings for {target_user.mention} have been reset.")


@Gojo.on_message(filters.command("resetallnsfwwarns") & filters.group)
async def reset_all_nsfw_warns(client: Gojo, message: Message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply_text("❌ Only admins can use this command.")
    except:
        return await message.reply_text("❌ Only admins can use this command.")

    reset_all_warnings(message.chat.id)
    await message.reply_text("✅ All warnings reset for this group.")


@Gojo.on_message(filters.command("mynsfwwarns") & filters.group)
async def my_nsfw_warns(client: Gojo, message: Message):
    warnings = get_warnings(message.from_user.id, message.chat.id)
    await message.reply_text(f"⚠️ You have {warnings} NSFW warning(s) in this group.")

# ======================
# MANUAL SCAN
# ======================
@Gojo.on_message(filters.command("nsfwscan") & filters.group)
async def scan_nsfw_command(client: Gojo, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a media message to scan.")

    target = message.reply_to_message
    file_path = None

    try:
        file_path = await target.download()
        scan_msg = await message.reply_text("🔍 Scanning...")

        is_nsfw, confidence, details = detect_nsfw(file_path)

        if is_nsfw:
            await scan_msg.edit_text(
                f"🚨 NSFW content detected ({confidence*100:.1f}% confidence)\n"
                f"Nudity: {details.get('nudity', {}).get('sexual_activity', 0)*100:.1f}%\n"
                f"Offensive: {details.get('offensive', {}).get('prob', 0)*100:.1f}%",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⚠️ Delete Message", callback_data=f"del_nsfw_{target.id}")]]
                ),
            )
        else:
            await scan_msg.edit_text("✅ This media appears safe.")

    except Exception as e:
        LOGGER.error(f"Error scanning NSFW: {e}")
        await message.reply_text("❌ Scan failed.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# AUTO SCAN
# ======================
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.document | filters.animation | filters.sticker))
async def auto_scan_nsfw(client: Gojo, message: Message):
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return
    except:
        pass

    enabled, strict = get_antinsfw(message.chat.id)
    if not enabled:
        return

    file_path = None
    try:
        file_path = await message.download()
        is_nsfw, confidence, details = detect_nsfw(file_path)

        if strict and not is_nsfw:
            nudity = details.get("nudity", {}).get("sexual_display", 0)
            suggestive = details.get("nudity", {}).get("suggestive", 0)
            alcohol = details.get("alcohol", 0)
            drugs = details.get("drugs", 0)
            if nudity > 0.5 or suggestive > 0.7 or alcohol > 0.7 or drugs > 0.7:
                is_nsfw = True
                confidence = max(nudity, suggestive, alcohol, drugs)

        if is_nsfw:
            try:
                await message.delete()
            except:
                LOGGER.warning("Could not delete NSFW message (no permissions)")

            add_warning(message.from_user.id, message.chat.id)
            warnings = get_warnings(message.from_user.id, message.chat.id)

            warn_msg = await message.reply_text(
                f"🚫 NSFW content removed!\n👤 {message.from_user.mention}\n⚠️ Warning {warnings}/3"
            )

            if warnings >= 3:
                try:
                    await client.ban_chat_member(message.chat.id, message.from_user.id)
                    await warn_msg.edit_text(f"🚫 {message.from_user.mention} banned (3 warnings).")
                except Exception as ban_error:
                    LOGGER.error(f"Ban failed: {ban_error}")
                    await warn_msg.edit_text(
                        f"🚫 {message.from_user.mention} reached 3 warnings but ban failed."
                    )

    except Exception as e:
        LOGGER.error(f"Auto NSFW scan error: {e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# CALLBACK
# ======================
@Gojo.on_callback_query(filters.regex(r"^del_nsfw_"))
async def delete_nsfw_callback(client: Gojo, cq):
    try:
        member = await client.get_chat_member(cq.message.chat.id, cq.from_user.id)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await cq.answer("❌ Only admins can delete messages.", show_alert=True)
    except:
        return await cq.answer("❌ Only admins can delete messages.", show_alert=True)

    try:
        msg_id = int(cq.data.split("_")[2])
        await client.delete_messages(cq.message.chat.id, msg_id)
        await cq.message.edit_text("✅ NSFW message deleted.")
    except:
        await cq.message.edit_text("❌ Could not delete the message.")
    await cq.answer()
