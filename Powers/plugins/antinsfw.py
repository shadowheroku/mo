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
# Get these from https://sightengine.com/ after registering
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "862487500")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")

# Database path
DB_PATH = "antinsfw.db"

# Initialize database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS antinsfw (chat_id INTEGER PRIMARY KEY, enabled INTEGER DEFAULT 0, strict_mode INTEGER DEFAULT 0)"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS nsfw_warnings (user_id INTEGER, chat_id INTEGER, warnings INTEGER DEFAULT 0, PRIMARY KEY (user_id, chat_id))"
)
conn.commit()

def set_antinsfw(chat_id: int, enabled: bool, strict_mode: bool = False):
    if strict_mode is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO antinsfw (chat_id, enabled, strict_mode) VALUES (?, ?, ?)", 
            (chat_id, 1 if enabled else 0, 1 if strict_mode else 0)
        )
    else:
        cursor.execute(
            "INSERT OR REPLACE INTO antinsfw (chat_id, enabled) VALUES (?, ?)", 
            (chat_id, 1 if enabled else 0)
        )
    conn.commit()

def get_antinsfw(chat_id: int) -> tuple:
    cursor.execute("SELECT enabled, strict_mode FROM antinsfw WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return bool(row[0]), bool(row[1])
    return False, False  # Default to disabled and non-strict

def add_warning(user_id: int, chat_id: int):
    cursor.execute(
        "INSERT INTO nsfw_warnings (user_id, chat_id, warnings) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, chat_id) DO UPDATE SET warnings = warnings + 1",
        (user_id, chat_id)
    )
    conn.commit()

def get_warnings(user_id: int, chat_id: int) -> int:
    cursor.execute("SELECT warnings FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    row = cursor.fetchone()
    return row[0] if row else 0

def reset_warnings(user_id: int, chat_id: int):
    cursor.execute(
        "DELETE FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id)
    )
    conn.commit()

# ======================
# NSFW DETECTION FUNCTION
# ======================
def detect_nsfw(image_path: str) -> tuple:
    """
    Detect NSFW content using SightEngine API
    Returns (is_nsfw, confidence, models) tuple
    """
    try:
        response = requests.post(
            'https://api.sightengine.com/1.0/check.json',
            files={'media': open(image_path, 'rb')},
            data={
                'models': 'nudity-2.1,wad,offensive,text-content,gore',
                'api_user': SIGHTENGINE_API_USER,
                'api_secret': SIGHTENGINE_API_SECRET
            }
        )
        result = response.json()
        
        if response.status_code != 200 or 'status' not in result or result['status'] != 'success':
            LOGGER.error(f"SightEngine API error: {result.get('error', {}).get('message', 'Unknown error')}")
            return False, 0, {}
        
        # Check different models for NSFW content
        nudity_score = result.get('nudity', {}).get('sexual_activity', 0) + result.get('nudity', {}).get('sexual_display', 0)
        offensive_score = result.get('offensive', {}).get('prob', 0)
        weapon_score = result.get('weapon', 0)
        alcohol_score = result.get('alcohol', 0)
        drugs_score = result.get('drugs', 0)
        
        # Combined score with weights
        total_score = (
            nudity_score * 0.5 + 
            offensive_score * 0.2 + 
            weapon_score * 0.1 + 
            alcohol_score * 0.1 + 
            drugs_score * 0.1
        )
        
        # Consider it NSFW if score exceeds threshold
        is_nsfw = total_score > 0.7 or nudity_score > 0.8
        
        return is_nsfw, total_score, result
        
    except Exception as e:
        LOGGER.error(f"Error in NSFW detection: {e}")
        return False, 0, {}

# ======================
# HELP TEXT
# ======================
__HELP__ = """
🔞 **Anti-NSFW System**

Protects your group by detecting & removing NSFW content automatically using AI detection.

**Commands:**
- `/antinsfw [on/off]` → Enable or disable Anti-NSFW in group
- `/antinsfw strict [on/off]` → Enable or disable strict mode (deletes suggestive content too)
- `/nsfwscan` → Reply to a media message to scan it manually
- `/nsfwwarns [user]` → Check NSFW warnings for a user (admins only)
- `/resetnsfwwarns [user]` → Reset NSFW warnings for a user (admins only)

**Strict Mode:** When enabled, also deletes suggestive content and alcohol/drug references.

When enabled, NSFW media is deleted instantly, the sender is warned, and repeat offenders may be banned.
"""

__MODULE__ = "Anti-NSFW"

# ======================
# TOGGLE COMMAND
# ======================
@Gojo.on_message(filters.command("antinsfw") & filters.group)
async def toggle_antinsfw(client: Gojo, message: Message):
    if not await client.is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an admin to use this command.", quote=True)
    
    if len(message.command) < 2:
        status, strict = get_antinsfw(message.chat.id)
        mode_text = "ON" if status else "OFF"
        strict_text = "ON" if strict else "OFF"
        return await message.reply_text(
            f"⚙️ Anti-NSFW Settings:\n\nStatus: {mode_text}\nStrict Mode: {strict_text}\n\n"
            "Usage: `/antinsfw on/off` or `/antinsfw strict on/off`",
            quote=True
        )

    arg1 = message.command[1].lower()
    
    if arg1 == "strict" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 == "on":
            set_antinsfw(message.chat.id, True, True)
            await message.reply_text("✅ Anti-NSFW strict mode **enabled**!")
        elif arg2 == "off":
            set_antinsfw(message.chat.id, True, False)
            await message.reply_text("✅ Anti-NSFW strict mode **disabled**!")
        else:
            await message.reply_text("⚙️ Usage: `/antinsfw strict on/off`", quote=True)
    else:
        if arg1 == "on":
            set_antinsfw(message.chat.id, True)
            await message.reply_text("✅ Anti-NSFW system **enabled** in this group!")
        elif arg1 == "off":
            set_antinsfw(message.chat.id, False)
            await message.reply_text("❌ Anti-NSFW system **disabled** in this group!")
        else:
            await message.reply_text("⚙️ Usage: `/antinsfw on/off` or `/antinsfw strict on/off`", quote=True)

# ======================
# WARNINGS COMMANDS
# ======================
@Gojo.on_message(filters.command("nsfwwarns") & filters.group)
async def check_nsfw_warns(client: Gojo, message: Message):
    if not await client.is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an admin to use this command.", quote=True)
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found.", quote=True)
    else:
        return await message.reply_text("❌ Reply to a user or specify their ID/username.", quote=True)
    
    warnings = get_warnings(target_user.id, message.chat.id)
    await message.reply_text(
        f"⚠️ User {target_user.mention} has {warnings} NSFW warning(s) in this group.",
        quote=True
    )

@Gojo.on_message(filters.command("resetnsfwwarns") & filters.group)
async def reset_nsfw_warns(client: Gojo, message: Message):
    if not await client.is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You need to be an admin to use this command.", quote=True)
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            target_user = await client.get_users(message.command[1])
        except:
            return await message.reply_text("❌ User not found.", quote=True)
    else:
        return await message.reply_text("❌ Reply to a user or specify their ID/username.", quote=True)
    
    reset_warnings(target_user.id, message.chat.id)
    await message.reply_text(
        f"✅ NSFW warnings for {target_user.mention} have been reset.",
        quote=True
    )

# ======================
# MANUAL SCAN COMMAND
# ======================
@Gojo.on_message(filters.command("nsfwscan") & filters.group)
async def scan_nsfw_command(client: Gojo, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a media message to scan it.")
    
    target = message.reply_to_message
    file = None
    file_path = None

    try:
        if target.photo:
            file_path = await target.download()
        elif target.video:
            file_path = await target.download()
        elif target.document and target.document.mime_type.startswith(("image/", "video/")):
            file_path = await target.download()
        elif target.sticker and not target.sticker.is_animated:
            file_path = await target.download()
        elif target.animation:
            file_path = await target.download()

        if not file_path:
            return await message.reply_text("⚠️ This file type is not supported for scanning.")

        # Scan for NSFW content
        await message.reply_text("🔍 Scanning media for NSFW content...")
        is_nsfw, confidence, details = detect_nsfw(file_path)
        
        if is_nsfw:
            await message.reply_text(
                f"🚨 NSFW content detected with {confidence*100:.1f}% confidence!\n\n"
                f"Details:\n"
                f"Nudity: {details.get('nudity', {}).get('sexual_activity', 0)*100:.1f}%\n"
                f"Offensive: {details.get('offensive', {}).get('prob', 0)*100:.1f}%\n"
                f"Weapons: {details.get('weapon', 0)*100:.1f}%",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⚠️ Delete Message", callback_data=f"del_nsfw_{target.id}")]]
                ),
            )
        else:
            await message.reply_text("✅ This media appears to be safe.")
            
    except Exception as e:
        LOGGER.error(f"Error in NSFW scan: {e}")
        await message.reply_text("❌ Error scanning media. Please try again later.")
    
    finally:
        # Clean up downloaded file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# AUTO-SCAN ON NEW MESSAGES
# ======================
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.document | filters.animation | filters.sticker))
async def auto_scan_nsfw(client: Gojo, message: Message):
    enabled, strict_mode = get_antinsfw(message.chat.id)
    if not enabled:
        return  # Feature disabled

    file_path = None
    try:
        # Download the media
        file_path = await message.download()
        
        # Scan for NSFW content
        is_nsfw, confidence, details = detect_nsfw(file_path)
        
        # Apply strict mode checks if enabled
        if strict_mode and not is_nsfw:
            # Check for suggestive content in strict mode
            nudity_score = details.get('nudity', {}).get('sexual_display', 0)
            suggestive_score = details.get('nudity', {}).get('suggestive', 0)
            alcohol_score = details.get('alcohol', 0)
            drugs_score = details.get('drugs', 0)
            
            if nudity_score > 0.5 or suggestive_score > 0.7 or alcohol_score > 0.7 or drugs_score > 0.7:
                is_nsfw = True
                confidence = max(nudity_score, suggestive_score, alcohol_score, drugs_score)
        
        if is_nsfw:
            # Delete the NSFW message
            try:
                await message.delete()
            except:
                pass  # Might not have permission to delete
            
            # Add warning for the user
            add_warning(message.from_user.id, message.chat.id)
            warnings = get_warnings(message.from_user.id, message.chat.id)
            
            # Send warning message
            warning_msg = await message.reply_text(
                f"🚫 NSFW content removed!\n"
                f"👤 User: {message.from_user.mention}\n"
                f"⚠️ Warning {warnings}/3 - Repeated violations may result in a ban.",
                quote=True
            )
            
            # Ban user after 3 warnings
            if warnings >= 3:
                try:
                    await client.ban_chat_member(message.chat.id, message.from_user.id)
                    await warning_msg.edit_text(
                        f"🚫 User {message.from_user.mention} has been banned for repeated NSFW violations."
                    )
                except:
                    await warning_msg.edit_text(
                        f"🚫 User {message.from_user.mention} has 3+ NSFW warnings but I couldn't ban them."
                    )
    
    except Exception as e:
        LOGGER.error(f"Error in auto NSFW scan: {e}")
    
    finally:
        # Clean up downloaded file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# CALLBACK QUERY HANDLER
# ======================
@Gojo.on_callback_query(filters.regex(r"^del_nsfw_"))
async def delete_nsfw_callback(client: Gojo, callback_query):
    message_id = int(callback_query.data.split("_")[2])
    try:
        await client.delete_messages(callback_query.message.chat.id, message_id)
        await callback_query.message.edit_text("✅ NSFW message deleted.")
    except:
        await callback_query.message.edit_text("❌ Could not delete the message.")
    await callback_query.answer()

# ======================
# ERROR HANDLING
# ======================
@Gojo.on_errors()
async def nsfw_error_handler(client: Gojo, error: Exception, message: Message):
    if "nsfw" in str(error).lower():
        LOGGER.error(f"Anti-NSFW error: {error}")
        await message.reply_text("❌ An error occurred in the Anti-NSFW system. Please try again later.")



__PLUGIN__ = "Anti-NSFW"

