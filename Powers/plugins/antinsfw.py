import os
import sqlite3
import requests
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
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

# Alternative NSFW detection using DeepAI (fallback)
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY", "")

# Additional NSFW detection service
HOLARA_API_KEY = os.getenv("HOLARA_API_KEY", "")

DB_PATH = "antinsfw.db"

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=10)

# Detection thresholds
NSFW_THRESHOLD = 0.75  # Default threshold for NSFW detection
STRICT_THRESHOLD = 0.65  # Threshold for strict mode
SUGGESTIVE_THRESHOLD = 0.6  # Threshold for suggestive content in strict mode

# ======================
# DATABASE INIT & MIGRATION
# ======================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    # Create base table if not exists
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS antinsfw (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            strict_mode INTEGER DEFAULT 0
        )"""
    )

    # Check and add missing columns
    cursor.execute("PRAGMA table_info(antinsfw)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "action_type" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN action_type TEXT DEFAULT 'delete'")
        LOGGER.info("Added action_type column to antinsfw table")
    
    if "log_channel" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN log_channel INTEGER DEFAULT 0")
        LOGGER.info("Added log_channel column to antinsfw table")
    
    if "warn_threshold" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN warn_threshold INTEGER DEFAULT 3")
        LOGGER.info("Added warn_threshold column to antinsfw table")

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS nsfw_warnings (
            user_id INTEGER,
            chat_id INTEGER,
            warnings INTEGER DEFAULT 0,
            last_warning_time INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS nsfw_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message_id INTEGER,
            media_type TEXT,
            confidence REAL,
            timestamp INTEGER,
            action_taken TEXT,
            details TEXT
        )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS nsfw_stats (
            chat_id INTEGER,
            date TEXT,
            detected_count INTEGER DEFAULT 0,
            deleted_count INTEGER DEFAULT 0,
            warned_count INTEGER DEFAULT 0,
            banned_count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, date)
        )"""
    )

    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ======================
# DATABASE FUNCTIONS
# ======================
def set_antinsfw(chat_id: int, enabled: bool, strict_mode: bool = False, 
                action_type: str = "delete", log_channel: int = 0, warn_threshold: int = 3):
    cursor.execute(
        "INSERT OR REPLACE INTO antinsfw (chat_id, enabled, strict_mode, action_type, log_channel, warn_threshold) VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, 1 if enabled else 0, 1 if strict_mode else 0, action_type, log_channel, warn_threshold),
    )
    conn.commit()


def get_antinsfw(chat_id: int) -> tuple:
    cursor.execute("SELECT enabled, strict_mode, action_type, log_channel, warn_threshold FROM antinsfw WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return bool(row[0]), bool(row[1]), row[2], row[3], row[4]
    return False, False, "delete", 0, 3


def add_warning(user_id: int, chat_id: int):
    current_time = int(time.time())
    cursor.execute(
        """INSERT INTO nsfw_warnings (user_id, chat_id, warnings, last_warning_time) VALUES (?, ?, 1, ?)
           ON CONFLICT(user_id, chat_id) DO UPDATE SET warnings = warnings + 1, last_warning_time = ?""",
        (user_id, chat_id, current_time, current_time),
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


def log_nsfw_action(chat_id: int, user_id: int, message_id: int, media_type: str, 
                   confidence: float, action_taken: str, details: str = ""):
    timestamp = int(time.time())
    cursor.execute(
        "INSERT INTO nsfw_logs (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details)
    )
    
    # Update stats
    today = time.strftime("%Y-%m-%d")
    cursor.execute(
        """INSERT INTO nsfw_stats (chat_id, date, detected_count) 
           VALUES (?, ?, 1)
           ON CONFLICT(chat_id, date) DO UPDATE SET detected_count = detected_count + 1""",
        (chat_id, today)
    )
    
    if action_taken == "deleted":
        cursor.execute(
            "UPDATE nsfw_stats SET deleted_count = deleted_count + 1 WHERE chat_id = ? AND date = ?",
            (chat_id, today)
        )
    
    conn.commit()


def update_stats(chat_id: int, field: str):
    today = time.strftime("%Y-%m-%d")
    cursor.execute(
        f"""INSERT INTO nsfw_stats (chat_id, date, {field}) 
           VALUES (?, ?, 1)
           ON CONFLICT(chat_id, date) DO UPDATE SET {field} = {field} + 1""",
        (chat_id, today)
    )
    conn.commit()

# ======================
# NSFW DETECTION
# ======================
def detect_nsfw_sightengine(image_path: str) -> tuple:
    """
    Detect NSFW content using SightEngine API
    Returns (is_nsfw, score, details)
    """
    try:
        if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
            LOGGER.error("SightEngine API credentials not configured")
            return False, 0, {}
            
        with open(image_path, "rb") as media:
            response = requests.post(
                "https://api.sightengine.com/1.0/check.json",
                files={"media": media},
                data={
                    "models": "nudity-2.1,wad,offensive,text-content,gore",
                    "api_user": SIGHTENGINE_API_USER,
                    "api_secret": SIGHTENGINE_API_SECRET,
                },
                timeout=15
            )

        result = response.json()

        if response.status_code != 200 or result.get("status") != "success":
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            LOGGER.error(f"SightEngine API error: {error_msg}")
            return False, 0, {}

        nudity_score = max(
            result.get("nudity", {}).get("sexual_activity", 0),
            result.get("nudity", {}).get("sexual_display", 0),
            result.get("nudity", {}).get("erotica", 0)
        )
        
        suggestive_score = result.get("nudity", {}).get("suggestive", 0)
        offensive_score = result.get("offensive", {}).get("prob", 0)
        weapon_score = result.get("weapon", 0)
        alcohol_score = result.get("alcohol", 0)
        drugs_score = result.get("drugs", 0)

        # Weighted total score with nudity having highest priority
        total_score = (
            nudity_score * 0.6
            + suggestive_score * 0.2
            + offensive_score * 0.1
            + max(weapon_score, alcohol_score, drugs_score) * 0.1
        )

        is_nsfw = total_score > NSFW_THRESHOLD or nudity_score > NSFW_THRESHOLD
        return is_nsfw, total_score, result

    except Exception as e:
        LOGGER.error(f"Error in SightEngine NSFW detection: {e}")
        return False, 0, {}


def detect_nsfw_deepai(image_path: str) -> tuple:
    """
    Fallback NSFW detection using DeepAI API
    """
    try:
        if not DEEPAI_API_KEY:
            LOGGER.error("DeepAI API key not configured")
            return False, 0, {}
            
        with open(image_path, "rb") as media:
            response = requests.post(
                "https://api.deepai.org/api/nsfw-detector",
                files={"image": media},
                headers={"api-key": DEEPAI_API_KEY},
                timeout=15
            )

        result = response.json()
        
        if response.status_code != 200:
            LOGGER.error(f"DeepAI API error: {result.get('err', 'Unknown error')}")
            return False, 0, {}
            
        nsfw_score = result.get("output", {}).get("nsfw_score", 0)
        is_nsfw = nsfw_score > NSFW_THRESHOLD
        return is_nsfw, nsfw_score, result

    except Exception as e:
        LOGGER.error(f"Error in DeepAI NSFW detection: {e}")
        return False, 0, {}


def detect_nsfw_holara(image_path: str) -> tuple:
    """
    Alternative NSFW detection using Holara API
    """
    try:
        if not HOLARA_API_KEY:
            LOGGER.error("Holara API key not configured")
            return False, 0, {}
            
        with open(image_path, "rb") as media:
            response = requests.post(
                "https://api.holara.ai/nsfw-detection",
                files={"image": media},
                headers={"Authorization": f"Bearer {HOLARA_API_KEY}"},
                timeout=15
            )

        result = response.json()
        
        if response.status_code != 200:
            LOGGER.error(f"Holara API error: {result.get('error', 'Unknown error')}")
            return False, 0, {}
            
        nsfw_score = result.get("nsfw_probability", 0)
        is_nsfw = nsfw_score > NSFW_THRESHOLD
        return is_nsfw, nsfw_score, result

    except Exception as e:
        LOGGER.error(f"Error in Holara NSFW detection: {e}")
        return False, 0, {}


def detect_nsfw(image_path: str) -> tuple:
    """
    Main NSFW detection function with multiple fallbacks
    """
    detection_services = [
        detect_nsfw_sightengine,
        detect_nsfw_deepai,
        detect_nsfw_holara
    ]
    
    best_score = 0
    best_result = {}
    any_nsfw = False
    
    for service in detection_services:
        try:
            is_nsfw, score, details = service(image_path)
            if is_nsfw and score > best_score:
                best_score = score
                best_result = details
                any_nsfw = True
            elif score > best_score:
                best_score = score
                best_result = details
        except Exception as e:
            LOGGER.warning(f"NSFW detection service failed: {e}")
            continue
    
    return any_nsfw, best_score, best_result

# ======================
# UTILITY FUNCTIONS
# ======================
async def is_user_admin(client: Gojo, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in the chat"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False


async def log_nsfw_event(client: Gojo, chat_id: int, log_channel: int, message: Message, confidence: float, action: str, details: dict = None):
    """Log NSFW event to the specified channel"""
    if not log_channel:
        return
        
    try:
        # Create detailed log text
        log_text = (
            f"🚨 **NSFW Content Detected**\n\n"
            f"**Chat:** {message.chat.title} (`{message.chat.id}`)\n"
            f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
            f"**Confidence:** {confidence*100:.1f}%\n"
            f"**Action:** {action}\n"
            f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
        )
        
        # Add details if available
        if details and 'nudity' in details:
            nudity = details['nudity']
            log_text += f"**Nudity Score:** {max(nudity.get('sexual_activity', 0), nudity.get('sexual_display', 0))*100:.1f}%\n"
        
        # Try to forward the media if possible
        if message.photo or message.video or message.document:
            try:
                forwarded = await message.forward(log_channel)
                await forwarded.reply_text(log_text, parse_mode=enums.ParseMode.MARKDOWN)
            except:
                await client.send_message(log_channel, log_text, parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await client.send_message(log_channel, log_text, parse_mode=enums.ParseMode.MARKDOWN)
    except Exception as e:
        LOGGER.error(f"Failed to log NSFW event: {e}")


async def take_action(client: Gojo, message: Message, action_type: str, warn_threshold: int, confidence: float, details: dict):
    """Take appropriate action based on settings"""
    action_taken = "none"
    
    # Delete message if action is set to delete
    if action_type == "delete":
        try:
            await message.delete()
            action_taken = "deleted"
            LOGGER.info(f"Deleted NSFW message from {message.from_user.id} in chat {message.chat.id}")
        except Exception as e:
            LOGGER.warning(f"Could not delete NSFW message: {e}")
            action_taken = "delete_failed"
    
    # Log the action
    media_type = "photo" if message.photo else "video" if message.video else "document" if message.document else "unknown"
    log_nsfw_action(message.chat.id, message.from_user.id, message.id, media_type, confidence, action_taken, str(details))
    
    # Log to channel if configured
    enabled, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
    await log_nsfw_event(client, message.chat.id, log_channel, message, confidence, action_taken, details)
    
    # Only warn if message was successfully deleted
    if action_taken == "deleted":
        add_warning(message.from_user.id, message.chat.id)
        warnings = get_warnings(message.from_user.id, message.chat.id)
        update_stats(message.chat.id, "warned_count")

        warn_msg_text = (
            f"🚫 NSFW content detected and removed!\n"
            f"👤 User: {message.from_user.mention}\n"
            f"⚠️ Warning {warnings}/{warn_threshold}\n"
            f"🔞 Confidence: {confidence*100:.1f}%"
        )
        
        # Add button to disable warnings for user if admin
        keyboard = []
        if await is_user_admin(client, message.chat.id, (await client.get_me()).id):
            keyboard.append([InlineKeyboardButton("❌ Ban User", callback_data=f"ban_nsfw_{message.from_user.id}")])
            keyboard.append([InlineKeyboardButton("⚠️ Reset Warnings", callback_data=f"reset_warn_{message.from_user.id}")])
        
        try:
            warn_msg = await client.send_message(
                message.chat.id,
                warn_msg_text,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            
            # Auto-delete warning message after 30 seconds
            await asyncio.sleep(30)
            await warn_msg.delete()
        except Exception as e:
            LOGGER.error(f"Failed to send warning message: {e}")

        if warnings >= warn_threshold:
            try:
                await client.ban_chat_member(message.chat.id, message.from_user.id)
                update_stats(message.chat.id, "banned_count")
                ban_msg = await client.send_message(
                    message.chat.id,
                    f"🚫 {message.from_user.mention} has been banned for sending NSFW content ({warn_threshold} warnings)."
                )
                # Auto-delete ban message after 30 seconds
                await asyncio.sleep(30)
                await ban_msg.delete()
            except Exception as ban_error:
                LOGGER.error(f"Ban failed: {ban_error}")
                try:
                    ban_fail_msg = await client.send_message(
                        message.chat.id,
                        f"🚫 {message.from_user.mention} reached {warn_threshold} warnings but ban failed (insufficient permissions)."
                    )
                    # Auto-delete ban failure message after 30 seconds
                    await asyncio.sleep(30)
                    await ban_fail_msg.delete()
                except:
                    pass
    
    return action_taken

# ======================
# BACKGROUND PROCESSING
# ======================
async def process_media_in_background(client: Gojo, message: Message):
    """Process media in background without blocking"""
    enabled, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
    if not enabled:
        return

    # Skip processing for admins and anonymous channel posts
    if not message.from_user or await is_user_admin(client, message.chat.id, message.from_user.id):
        return

    file_path = None
    try:
        # Check file size limit (max 10MB for API calls)
        max_size = 10 * 1024 * 1024
        if (message.document and message.document.file_size > max_size) or \
           (message.video and message.video.file_size > max_size) or \
           (message.photo and message.photo.file_size > max_size if hasattr(message.photo, 'file_size') else False):
            LOGGER.info(f"Skipping large file ({message.id}) in chat {message.chat.id}")
            return
            
        file_path = await message.download()
        
        if not file_path:
            return
            
        # Run detection in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        is_nsfw, confidence, details = await loop.run_in_executor(
            executor, detect_nsfw, file_path
        )

        # Apply strict mode if enabled
        if strict and not is_nsfw:
            nudity = details.get("nudity", {})
            nudity_score = max(
                nudity.get("sexual_activity", 0),
                nudity.get("sexual_display", 0),
                nudity.get("erotica", 0)
            )
            suggestive = nudity.get("suggestive", 0)
            alcohol = details.get("alcohol", 0)
            drugs = details.get("drugs", 0)
            
            if nudity_score > STRICT_THRESHOLD or suggestive > SUGGESTIVE_THRESHOLD or alcohol > 0.7 or drugs > 0.7:
                is_nsfw = True
                confidence = max(nudity_score, suggestive, alcohol, drugs)

        if is_nsfw:
            await take_action(client, message, action_type, warn_threshold, confidence, details)

    except Exception as e:
        LOGGER.error(f"Auto NSFW scan error: {e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# HELP
# ======================
__HELP__ = """
🛡️ **Anti-NSFW Protection System**

**⭐ Admin Controls**
• `/antinsfw on|off` - Enable/disable protection  
• `/antinsfw strict on|off` - Toggle strict mode  
• `/antinsfw action delete|warn` - Set action type
• `/antinsfw logchannel` - Set log channel
• `/antinsfw warnthreshold [number]` - Set warning threshold (default: 3)
• `/antinsfw status` - View settings  

**🔍 Manual Scan**
• `/nsfwscan` (reply to media) - Scan file  

**⚠️ Warnings**
• `/nsfwwarns [user]` - Check user warnings  
• `/resetnsfwwarns [user]` - Reset warnings  
• `/resetallnsfwwarns` - Reset all warnings  
• `/mynsfwwarns` - Check your warnings  

**📊 Stats**
• `/nsfwstats` - View detection statistics

**⚡ Auto-Actions**
- Automatically scans all media in background
- Deletes NSFW content  
- Issues warnings  
- Bans after configured warnings  
"""

__MODULE__ = "Anti-NSFW"

# ======================
# TOGGLE COMMAND
# ======================
@Gojo.on_message(filters.command("antinsfw") & filters.group)
async def toggle_antinsfw(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

    if len(message.command) < 2:
        status, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
        log_info = f"Log channel: {log_channel}" if log_channel else "Logging: disabled"
        return await message.reply_text(
            f"⚙️ Anti-NSFW Settings:\n\n"
            f"Status: {'ON' if status else 'OFF'}\n"
            f"Strict Mode: {'ON' if strict else 'OFF'}\n"
            f"Action: {action_type}\n"
            f"Warning Threshold: {warn_threshold}\n"
            f"{log_info}\n\n"
            "Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`, `/antinsfw warnthreshold [number]`",
        )

    arg1 = message.command[1].lower()
    
    if arg1 == "strict" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["on", "off"]:
            enabled, _, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, arg2 == "on", action_type, log_channel, warn_threshold)
            return await message.reply_text(f"✅ Strict mode {'enabled' if arg2 == 'on' else 'disabled'}!")
        else:
            return await message.reply_text("⚙️ Usage: `/antinsfw strict on/off`")
            
    elif arg1 == "action" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["delete", "warn"]:
            enabled, strict, _, log_channel, warn_threshold = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, arg2, log_channel, warn_threshold)
            return await message.reply_text(f"✅ Action type set to '{arg2}'!")
        else:
            return await message.reply_text("⚙️ Usage: `/antinsfw action delete/warn`")
            
    elif arg1 == "logchannel":
        if message.reply_to_message and message.reply_to_message.forward_from_chat:
            log_channel = message.reply_to_message.forward_from_chat.id
        elif len(message.command) > 2:
            try:
                log_channel = int(message.command[2])
            except ValueError:
                return await message.reply_text("❌ Invalid channel ID. Please provide a numeric channel ID.")
        else:
            return await message.reply_text("⚙️ Usage: Reply to a channel message or provide channel ID: `/antinsfw logchannel [channel_id]`")
        
        enabled, strict, action_type, _, warn_threshold = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel, warn_threshold)
        return await message.reply_text(f"✅ Log channel set to {log_channel}!")
    
    elif arg1 == "warnthreshold" and len(message.command) > 2:
        try:
            threshold = int(message.command[2])
            if threshold < 1 or threshold > 10:
                return await message.reply_text("❌ Warning threshold must be between 1 and 10.")
            
            enabled, strict, action_type, log_channel, _ = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel, threshold)
            return await message.reply_text(f"✅ Warning threshold set to {threshold}!")
        except ValueError:
            return await message.reply_text("❌ Please provide a valid number for the warning threshold.")

    elif arg1 == "status":
        status, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
        log_info = f"Log channel: {log_channel}" if log_channel else "Logging: disabled"
        return await message.reply_text(
            f"⚙️ Status: {'ON' if status else 'OFF'}\n"
            f"Strict Mode: {'ON' if strict else 'OFF'}\n"
            f"Action: {action_type}\n"
            f"Warning Threshold: {warn_threshold}\n"
            f"{log_info}"
        )

    elif arg1 == "on":
        _, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, True, strict, action_type, log_channel, warn_threshold)
        return await message.reply_text("✅ Anti-NSFW enabled in this group!")
        
    elif arg1 == "off":
        _, strict, action_type, log_channel, warn_threshold = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, False, strict, action_type, log_channel, warn_threshold)
        return await message.reply_text("❌ Anti-NSFW disabled in this group!")

    return await message.reply_text("⚙️ Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`, `/antinsfw warnthreshold [number]`")

# ======================
# WARNINGS COMMANDS
# ======================
@Gojo.on_message(filters.command("nsfwwarns") & filters.group)
async def check_nsfw_warns(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
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
    _, _, _, _, warn_threshold = get_antinsfw(message.chat.id)
    await message.reply_text(f"⚠️ {target_user.mention} has {warnings}/{warn_threshold} NSFW warning(s).")


@Gojo.on_message(filters.command("resetnsfwwarns") & filters.group)
async def reset_nsfw_warns(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
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
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

    reset_all_warnings(message.chat.id)
    await message.reply_text("✅ All warnings reset for this group.")


@Gojo.on_message(filters.command("mynsfwwarns") & filters.group)
async def my_nsfw_warns(client: Gojo, message: Message):
    warnings = get_warnings(message.from_user.id, message.chat.id)
    _, _, _, _, warn_threshold = get_antinsfw(message.chat.id)
    await message.reply_text(f"⚠️ You have {warnings}/{warn_threshold} NSFW warning(s) in this group.")

# ======================
# STATS COMMAND
# ======================
@Gojo.on_message(filters.command("nsfwstats") & filters.group)
async def nsfw_stats(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")
    
    # Get stats from the last 7 days
    seven_days_ago = int(time.time()) - (7 * 24 * 60 * 60)
    
    cursor.execute(
        "SELECT COUNT(*), AVG(confidence) FROM nsfw_logs WHERE chat_id = ? AND timestamp > ?",
        (message.chat.id, seven_days_ago)
    )
    stats = cursor.fetchone()
    
    count = stats[0] or 0
    avg_confidence = stats[1] or 0
    
    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM nsfw_logs WHERE chat_id = ? AND timestamp > ?",
        (message.chat.id, seven_days_ago)
    )
    unique_users = cursor.fetchone()[0] or 0
    
    # Get today's stats
    today = time.strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT detected_count, deleted_count, warned_count, banned_count FROM nsfw_stats WHERE chat_id = ? AND date = ?",
        (message.chat.id, today)
    )
    today_stats = cursor.fetchone() or (0, 0, 0, 0)
    
    await message.reply_text(
        f"📊 NSFW Detection Stats:\n\n"
        f"**Last 7 days:**\n"
        f"• Detected incidents: {count}\n"
        f"• Unique users: {unique_users}\n"
        f"• Average confidence: {avg_confidence*100:.1f}%\n\n"
        f"**Today ({today}):**\n"
        f"• Detected: {today_stats[0]}\n"
        f"• Deleted: {today_stats[1]}\n"
        f"• Warned: {today_stats[2]}\n"
        f"• Banned: {today_stats[3]}"
    )

# ======================
# MANUAL SCAN
# ======================
@Gojo.on_message(filters.command("nsfwscan") & filters.group)
async def scan_nsfw_command(client: Gojo, message: Message):
    if not message.reply_to_message or not (message.reply_to_message.photo or message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply_text("⚠️ Reply to a media message (photo/video/document) to scan.")

    target = message.reply_to_message
    file_path = None

    try:
        # Check file size limit
        if target.document and target.document.file_size > 10 * 1024 * 1024:
            return await message.reply_text("❌ File is too large (max 10MB).")
            
        file_path = await target.download()
        scan_msg = await message.reply_text("🔍 Scanning...")

        # Run detection in thread pool
        loop = asyncio.get_event_loop()
        is_nsfw, confidence, details = await loop.run_in_executor(
            executor, detect_nsfw, file_path
        )

        if is_nsfw:
            response_text = (
                f"🚨 NSFW content detected ({confidence*100:.1f}% confidence)\n"
            )
            
            # Add details if available
            if details.get("nudity"):
                nudity = details.get("nudity", {})
                response_text += f"• Nudity: {max(nudity.get('sexual_activity', 0), nudity.get('sexual_display', 0))*100:.1f}%\n"
                response_text += f"• Suggestive: {nudity.get('suggestive', 0)*100:.1f}%\n"
                
            if details.get("offensive", {}).get("prob", 0) > 0:
                response_text += f"• Offensive: {details.get('offensive', {}).get('prob', 0)*100:.1f}%\n"
                
            if details.get("weapon", 0) > 0:
                response_text += f"• Weapon: {details.get('weapon', 0)*100:.1f}%\n"
                
            # Add delete button for admins
            if await is_user_admin(client, message.chat.id, message.from_user.id):
                await scan_msg.edit_text(
                    response_text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("⚠️ Delete Message", callback_data=f"del_nsfw_{target.id}")]]
                    ),
                )
            else:
                await scan_msg.edit_text(response_text)
        else:
            await scan_msg.edit_text("✅ This media appears safe.")

    except Exception as e:
        LOGGER
                LOGGER.error(f"Manual NSFW scan error: {e}")
        await scan_msg.edit_text("❌ Error scanning media. Please try again.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# CALLBACK HANDLERS
# ======================
@Gojo.on_callback_query(filters.regex(r"^del_nsfw_"))
async def delete_nsfw_callback(client: Gojo, callback_query):
    """Callback for manual delete button"""
    try:
        message_id = int(callback_query.data.split("_")[2])
        if await is_user_admin(client, callback_query.message.chat.id, callback_query.from_user.id):
            await client.delete_messages(callback_query.message.chat.id, message_id)
            await callback_query.answer("Message deleted!")
            await callback_query.message.edit_text("✅ Message deleted successfully.")
        else:
            await callback_query.answer("You need to be admin to delete messages.", show_alert=True)
    except Exception as e:
        LOGGER.error(f"Delete callback error: {e}")
        await callback_query.answer("Error deleting message.", show_alert=True)


@Gojo.on_callback_query(filters.regex(r"^ban_nsfw_"))
async def ban_user_callback(client: Gojo, callback_query):
    """Callback for banning user"""
    try:
        user_id = int(callback_query.data.split("_")[2])
        if await is_user_admin(client, callback_query.message.chat.id, callback_query.from_user.id):
            await client.ban_chat_member(callback_query.message.chat.id, user_id)
            update_stats(callback_query.message.chat.id, "banned_count")
            await callback_query.answer("User banned!")
            await callback_query.message.edit_text("✅ User has been banned.")
        else:
            await callback_query.answer("You need to be admin to ban users.", show_alert=True)
    except Exception as e:
        LOGGER.error(f"Ban callback error: {e}")
        await callback_query.answer("Error banning user.", show_alert=True)


@Gojo.on_callback_query(filters.regex(r"^reset_warn_"))
async def reset_warnings_callback(client: Gojo, callback_query):
    """Callback for resetting warnings"""
    try:
        user_id = int(callback_query.data.split("_")[2])
        if await is_user_admin(client, callback_query.message.chat.id, callback_query.from_user.id):
            reset_warnings(user_id, callback_query.message.chat.id)
            await callback_query.answer("Warnings reset!")
            await callback_query.message.edit_text("✅ User warnings have been reset.")
        else:
            await callback_query.answer("You need to be admin to reset warnings.", show_alert=True)
    except Exception as e:
        LOGGER.error(f"Reset warnings callback error: {e}")
        await callback_query.answer("Error resetting warnings.", show_alert=True)

# ======================
# MESSAGE HANDLERS
# ======================
@Gojo.on_message(
    (filters.photo | filters.video | filters.document) & filters.group,
    group=5
)
async def auto_nsfw_check(client: Gojo, message: Message):
    """Automatically check media for NSFW content"""
    # Skip if anti-NSFW is not enabled
    enabled, _, _, _, _ = get_antinsfw(message.chat.id)
    if not enabled:
        return
    
    # Skip processing for admins and anonymous channel posts
    if not message.from_user or await is_user_admin(client, message.chat.id, message.from_user.id):
        return
    
    # Process in background to avoid blocking
    asyncio.create_task(process_media_in_background(client, message))

# ======================
# MIGRATION ON STARTUP
# ======================
async def migrate_database():
    """Run database migrations on startup"""
    # Check if we need to add any new columns
    cursor.execute("PRAGMA table_info(antinsfw)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add any missing columns that might have been added in updates
    if "action_type" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN action_type TEXT DEFAULT 'delete'")
        LOGGER.info("Added action_type column to antinsfw table")
    
    if "log_channel" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN log_channel INTEGER DEFAULT 0")
        LOGGER.info("Added log_channel column to antinsfw table")
    
    if "warn_threshold" not in columns:
        cursor.execute("ALTER TABLE antinsfw ADD COLUMN warn_threshold INTEGER DEFAULT 3")
        LOGGER.info("Added warn_threshold column to antinsfw table")
    
    conn.commit()

# Run migration on import
asyncio.create_task(migrate_database())

LOGGER.info("Anti-NSFW module loaded successfully!")

coninue after this
