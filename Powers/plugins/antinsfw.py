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
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "")

# Alternative NSFW detection using DeepAI (fallback)
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY", "")

DB_PATH = "antinsfw.db"

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=5)

# ======================
# DATABASE INIT
# ======================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    # Create base table if not exists
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS antinsfw (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            strict_mode INTEGER DEFAULT 0,
            action_type TEXT DEFAULT 'delete',
            log_channel INTEGER DEFAULT 0
        )"""
    )

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
            action_taken TEXT
        )"""
    )

    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ======================
# DATABASE FUNCTIONS
# ======================
def set_antinsfw(chat_id: int, enabled: bool, strict_mode: bool = False, action_type: str = "delete", log_channel: int = 0):
    cursor.execute(
        "INSERT OR REPLACE INTO antinsfw (chat_id, enabled, strict_mode, action_type, log_channel) VALUES (?, ?, ?, ?, ?)",
        (chat_id, 1 if enabled else 0, 1 if strict_mode else 0, action_type, log_channel),
    )
    conn.commit()


def get_antinsfw(chat_id: int) -> tuple:
    cursor.execute("SELECT enabled, strict_mode, action_type, log_channel FROM antinsfw WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    if row:
        return bool(row[0]), bool(row[1]), row[2], row[3]
    return False, False, "delete", 0


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


def log_nsfw_action(chat_id: int, user_id: int, message_id: int, media_type: str, confidence: float, action_taken: str):
    timestamp = int(time.time())
    cursor.execute(
        "INSERT INTO nsfw_logs (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken)
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
                timeout=30
            )

        result = response.json()

        if response.status_code != 200 or result.get("status") != "success":
            error_msg = result.get('error', {}).get('message', 'Unknown error')
            LOGGER.error(f"SightEngine API error: {error_msg}")
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
                timeout=30
            )

        result = response.json()
        
        if response.status_code != 200:
            LOGGER.error(f"DeepAI API error: {result.get('err', 'Unknown error')}")
            return False, 0, {}
            
        nsfw_score = result.get("output", {}).get("nsfw_score", 0)
        is_nsfw = nsfw_score > 0.7
        return is_nsfw, nsfw_score, result

    except Exception as e:
        LOGGER.error(f"Error in DeepAI NSFW detection: {e}")
        return False, 0, {}


def detect_nsfw(image_path: str) -> tuple:
    """
    Main NSFW detection function with fallback
    """
    # Try SightEngine first
    is_nsfw, score, details = detect_nsfw_sightengine(image_path)
    
    # If SightEngine fails or not configured, try DeepAI
    if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET or (not is_nsfw and score == 0):
        is_nsfw, score, details = detect_nsfw_deepai(image_path)
        
    return is_nsfw, score, details

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


async def log_nsfw_event(client: Gojo, chat_id: int, log_channel: int, message: Message, confidence: float, action: str):
    """Log NSFW event to the specified channel"""
    if not log_channel:
        return
        
    try:
        log_text = (
            f"🚨 **NSFW Content Detected**\n\n"
            f"**Chat:** {message.chat.title} (`{message.chat.id}`)\n"
            f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
            f"**Confidence:** {confidence*100:.1f}%\n"
            f"**Action:** {action}\n"
            f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
        )
        
        # Try to forward the media if possible
        if message.photo or message.video or message.document:
            try:
                forwarded = await message.forward(log_channel)
                await forwarded.reply_text(log_text)
            except:
                await client.send_message(log_channel, log_text)
        else:
            await client.send_message(log_channel, log_text)
    except Exception as e:
        LOGGER.error(f"Failed to log NSFW event: {e}")

# ======================
# BACKGROUND PROCESSING
# ======================
async def process_media_in_background(client: Gojo, message: Message):
    """Process media in background without blocking"""
    enabled, strict, action_type, log_channel = get_antinsfw(message.chat.id)
    if not enabled:
        return

    # Skip processing for admins and anonymous channel posts
    if not message.from_user or await is_user_admin(client, message.chat.id, message.from_user.id):
        return

    file_path = None
    try:
        # Check file size limit (max 5MB for API calls)
        if message.document and message.document.file_size > 5 * 1024 * 1024:
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
            nudity = details.get("nudity", {}).get("sexual_display", 0)
            suggestive = details.get("nudity", {}).get("suggestive", 0)
            alcohol = details.get("alcohol", 0)
            drugs = details.get("drugs", 0)
            if nudity > 0.5 or suggestive > 0.7 or alcohol > 0.7 or drugs > 0.7:
                is_nsfw = True
                confidence = max(nudity, suggestive, alcohol, drugs)

        if is_nsfw:
            action_taken = "none"
            
            # Take action based on settings
            if action_type == "delete":
                try:
                    await message.delete()
                    action_taken = "deleted"
                except Exception as e:
                    LOGGER.warning(f"Could not delete NSFW message: {e}")
                    action_taken = "delete_failed"
            
            # Log the action
            media_type = "photo" if message.photo else "video" if message.video else "document" if message.document else "unknown"
            log_nsfw_action(message.chat.id, message.from_user.id, message.id, media_type, confidence, action_taken)
            
            # Log to channel if configured
            await log_nsfw_event(client, message.chat.id, log_channel, message, confidence, action_taken)
            
            # Only warn if message was successfully deleted
            if action_taken == "deleted":
                add_warning(message.from_user.id, message.chat.id)
                warnings = get_warnings(message.from_user.id, message.chat.id)

                warn_msg_text = (
                    f"🚫 NSFW content detected and removed!\n"
                    f"👤 User: {message.from_user.mention}\n"
                    f"⚠️ Warning {warnings}/3\n"
                    f"🔞 Confidence: {confidence*100:.1f}%"
                )
                
                # Add button to disable warnings for user if admin
                keyboard = []
                if await is_user_admin(client, message.chat.id, (await client.get_me()).id):
                    keyboard.append([InlineKeyboardButton("❌ Ban User", callback_data=f"ban_nsfw_{message.from_user.id}")])
                    keyboard.append([InlineKeyboardButton("⚠️ Reset Warnings", callback_data=f"reset_warn_{message.from_user.id}")])
                
                warn_msg = await client.send_message(
                    message.chat.id,
                    warn_msg_text,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )

                if warnings >= 3:
                    try:
                        await client.ban_chat_member(message.chat.id, message.from_user.id)
                        await warn_msg.edit_text(
                            f"🚫 {message.from_user.mention} has been banned for sending NSFW content (3 warnings)."
                        )
                    except Exception as ban_error:
                        LOGGER.error(f"Ban failed: {ban_error}")
                        await warn_msg.edit_text(
                            f"🚫 {message.from_user.mention} reached 3 warnings but ban failed (insufficient permissions)."
                        )

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
- Bans after 3 warnings  
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
        status, strict, action_type, log_channel = get_antinsfw(message.chat.id)
        log_info = f"Log channel: {log_channel}" if log_channel else "Logging: disabled"
        return await message.reply_text(
            f"⚙️ Anti-NSFW Settings:\n\n"
            f"Status: {'ON' if status else 'OFF'}\n"
            f"Strict Mode: {'ON' if strict else 'OFF'}\n"
            f"Action: {action_type}\n"
            f"{log_info}\n\n"
            "Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`",
        )

    arg1 = message.command[1].lower()
    
    if arg1 == "strict" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["on", "off"]:
            enabled, _, action_type, log_channel = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, arg2 == "on", action_type, log_channel)
            return await message.reply_text(f"✅ Strict mode {'enabled' if arg2 == 'on' else 'disabled'}!")
        else:
            return await message.reply_text("⚙️ Usage: `/antinsfw strict on/off`")
            
    elif arg1 == "action" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["delete", "warn"]:
            enabled, strict, _, log_channel = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, arg2, log_channel)
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
        
        enabled, strict, action_type, _ = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel)
        return await message.reply_text(f"✅ Log channel set to {log_channel}!")

    elif arg1 == "status":
        status, strict, action_type, log_channel = get_antinsfw(message.chat.id)
        log_info = f"Log channel: {log_channel}" if log_channel else "Logging: disabled"
        return await message.reply_text(
            f"⚙️ Status: {'ON' if status else 'OFF'}\n"
            f"Strict Mode: {'ON' if strict else 'OFF'}\n"
            f"Action: {action_type}\n"
            f"{log_info}"
        )

    elif arg1 == "on":
        _, strict, action_type, log_channel = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, True, strict, action_type, log_channel)
        return await message.reply_text("✅ Anti-NSFW enabled in this group!")
        
    elif arg1 == "off":
        _, strict, action_type, log_channel = get_antinsfw(message.chat.id)
        set_antinsfw(message.chat.id, False, strict, action_type, log_channel)
        return await message.reply_text("❌ Anti-NSFW disabled in this group!")

    return await message.reply_text("⚙️ Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`")

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
    await message.reply_text(f"⚠️ {target_user.mention} has {warnings} NSFW warning(s).")


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
    await message.reply_text(f"⚠️ You have {warnings} NSFW warning(s) in this group.")

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
    
    await message.reply_text(
        f"📊 NSFW Detection Stats (Last 7 days):\n\n"
        f"• Detected incidents: {count}\n"
        f"• Unique users: {unique_users}\n"
        f"• Average confidence: {avg_confidence*100:.1f}%"
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
        if target.document and target.document.file_size > 5 * 1024 * 1024:
            return await message.reply_text("❌ File is too large (max 5MB).")
            
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
                response_text += f"• Nudity: {nudity.get('sexual_activity', 0)*100:.1f}%\n"
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
        LOGGER.error(f"Error scanning NSFW: {e}")
        await message.reply_text("❌ Scan failed. Please try again.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# AUTO SCAN - BACKGROUND PROCESSING
# ======================
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.document))
async def auto_scan_nsfw(client: Gojo, message: Message):
    # Process media in background without blocking
    asyncio.create_task(process_media_in_background(client, message))

# ======================
# CALLBACK HANDLERS
# ======================
@Gojo.on_callback_query(filters.regex(r"^del_nsfw_"))
async def delete_nsfw_callback(client: Gojo, cq):
    if not await is_user_admin(client, cq.message.chat.id, cq.from_user.id):
        return await cq.answer("❌ Only admins can delete messages.", show_alert=True)

    try:
        msg_id = int(cq.data.split("_")[2])
        await client.delete_messages(cq.message.chat.id, msg_id)
        await cq.message.edit_text("✅ NSFW message deleted.")
    except:
        await cq.message.edit_text("❌ Could not delete the message.")
    await cq.answer()


@Gojo.on_callback_query(filters.regex(r"^ban_nsfw_"))
async def ban_user_callback(client: Gojo, cq):
    if not await is_user_admin(client, cq.message.chat.id, cq.from_user.id):
        return await cq.answer("❌ Only admins can ban users.", show_alert=True)

    try:
        user_id = int(cq.data.split("_")[2])
        await client.ban_chat_member(cq.message.chat.id, user_id)
        await cq.message.edit_text(f"✅ User has been banned.")
    except Exception as e:
        LOGGER.error(f"Ban from callback failed: {e}")
        await cq.message.edit_text("❌ Could not ban user.")
    await cq.answer()


@Gojo.on_callback_query(filters.regex(r"^reset_warn_"))
async def reset_warnings_callback(client: Gojo, cq):
    if not await is_user_admin(client, cq.message.chat.id, cq.from_user.id):
        return await cq.answer("❌ Only admins can reset warnings.", show_alert=True)

    try:
        user_id = int(cq.data.split("_")[2])
        reset_warnings(user_id, cq.message.chat.id)
        await cq.message.edit_text(f"✅ Warnings for user have been reset.")
    except Exception as e:
        LOGGER.error(f"Reset warnings failed: {e}")
        await cq.message.edit_text("❌ Could not reset warnings.")
    await cq.answer()
