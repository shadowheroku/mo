import os
import sqlite3
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo

# ======================
# DATABASE
# ======================
DB_PATH = "antinsfw.db"

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS antinsfw (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0)"
)
conn.commit()

def set_antinsfw(chat_id: int, enabled: bool):
    cursor.execute("INSERT OR REPLACE INTO antinsfw (chat_id, enabled) VALUES (?, ?)", (chat_id, 1 if enabled else 0))
    conn.commit()

def get_antinsfw(chat_id: int) -> bool:
    cursor.execute("SELECT enabled FROM antinsfw WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    return row and row[0] == 1


# ======================
# HELP TEXT
# ======================
__HELP__ = """
🔞 **Anti-NSFW System**

Protects your group by detecting & removing NSFW content automatically.

**Commands:**
- `/antinsfw [on/off]` → Enable or disable Anti-NSFW in group.
- `/nsfwscan` → Reply to a message to scan it manually.

When enabled, NSFW media is deleted instantly & the sender is warned.
"""

__MODULE__ = "Anti-NSFW"


# ======================
# TOGGLE COMMAND
# ======================
@Gojo.on_message(filters.command("antinsfw") & filters.group)
async def toggle_antinsfw(client: Gojo, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("⚙️ Usage: `/antinsfw on` or `/antinsfw off`", quote=True)

    arg = message.command[1].lower()
    if arg == "on":
        set_antinsfw(message.chat.id, True)
        await message.reply_text("✅ Anti-NSFW system **enabled** in this group!")
    elif arg == "off":
        set_antinsfw(message.chat.id, False)
        await message.reply_text("❌ Anti-NSFW system **disabled** in this group!")
    else:
        await message.reply_text("⚙️ Usage: `/antinsfw on` or `/antinsfw off`", quote=True)


# ======================
# MANUAL SCAN COMMAND
# ======================
@Gojo.on_message(filters.command("nsfwscan") & filters.group)
async def scan_nsfw_command(client: Gojo, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a media message to scan it.")
    
    target = message.reply_to_message
    file = None

    if target.photo:
        file = await target.download()
    elif target.video:
        file = await target.download()
    elif target.document and target.document.mime_type.startswith("image/"):
        file = await target.download()

    if not file:
        return await message.reply_text("⚠️ This file type is not supported for scanning.")

    # 🔍 Dummy NSFW detection (replace with real model/API)
    nsfw_detected = True  # <--- integrate real API like DeepAI / NSFW.js / OpenAI Vision

    if nsfw_detected:
        await message.reply_text(
            "🚨 NSFW content detected in this media!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⚠️ Delete File", callback_data="del_nsfw")]]
            ),
        )
    else:
        await message.reply_text("✅ This media is safe.")


# ======================
# AUTO-SCAN ON NEW MESSAGES
# ======================
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.document | filters.animation | filters.sticker))
async def auto_scan_nsfw(client: Gojo, message: Message):
    if not get_antinsfw(message.chat.id):
        return  # Feature disabled

    file = None
    if message.photo:
        file = await message.download()
    elif message.video:
        file = await message.download()
    elif message.document and message.document.mime_type.startswith("image/"):
        file = await message.download()

    if not file:
        return

    # 🔍 Dummy NSFW detection
    nsfw_detected = True  # Replace with real API

    if nsfw_detected:
        try:
            await message.delete()
            await message.reply_text(
                f"🚫 NSFW content removed!\n👤 User: {message.from_user.mention}",
                quote=True
            )
        except Exception:
            pass
