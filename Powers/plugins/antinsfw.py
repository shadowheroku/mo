import os
import sqlite3
import time
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from typing import Tuple, Dict, List, Optional
from Powers.bot_class import Gojo
from Powers import LOGGER

# ======================
# CONFIGURATION
# ======================
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "862487500")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY", "79eb379a-337c-4258-9957-a0c25195b6da")
HOLARA_API_KEY = os.getenv("HOLARA_API_KEY", "d2d272f0-6489-4fc1-a32d-fa4a27190f7e")
DB_PATH = "antinsfw.db"
NSFW_THRESHOLD = 0.75
STRICT_THRESHOLD = 0.65
SUGGESTIVE_THRESHOLD = 0.6
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# ======================
# DATABASE
# ======================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Initialize all required tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS antinsfw (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            strict_mode INTEGER DEFAULT 0,
            action_type TEXT DEFAULT 'delete',
            log_channel INTEGER DEFAULT 0,
            warn_threshold INTEGER DEFAULT 3,
            scan_photos INTEGER DEFAULT 1,
            scan_videos INTEGER DEFAULT 1,
            scan_documents INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at INTEGER DEFAULT (strftime('%s', 'now'))
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nsfw_warnings (
            user_id INTEGER,
            chat_id INTEGER,
            warnings INTEGER DEFAULT 0,
            last_warning_time INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nsfw_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message_id INTEGER,
            media_type TEXT,
            confidence REAL,
            timestamp INTEGER,
            action_taken TEXT,
            details TEXT,
            service_used TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nsfw_stats (
            chat_id INTEGER,
            date TEXT,
            detected_count INTEGER DEFAULT 0,
            deleted_count INTEGER DEFAULT 0,
            warned_count INTEGER DEFAULT 0,
            banned_count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, date)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nsfw_whitelist (
            user_id INTEGER,
            chat_id INTEGER,
            added_by INTEGER,
            added_at INTEGER DEFAULT (strftime('%s', 'now')),
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    conn.commit()

def set_antinsfw(
    chat_id: int,
    enabled: bool,
    strict_mode: bool = False,
    action_type: str = "delete",
    log_channel: int = 0,
    warn_threshold: int = 3,
    scan_photos: bool = True,
    scan_videos: bool = True,
    scan_documents: bool = False,
):
    """Set anti-NSFW configuration for a chat."""
    cursor.execute(
        """
        INSERT OR REPLACE INTO antinsfw
        (chat_id, enabled, strict_mode, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            chat_id,
            1 if enabled else 0,
            1 if strict_mode else 0,
            action_type,
            log_channel,
            warn_threshold,
            1 if scan_photos else 0,
            1 if scan_videos else 0,
            1 if scan_documents else 0,
            int(time.time()),
        ),
    )
    conn.commit()

def get_antinsfw(chat_id: int) -> Tuple[bool, bool, str, int, int, bool, bool, bool]:
    """Get anti-NSFW configuration for a chat."""
    cursor.execute(
        """
        SELECT enabled, strict_mode, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents
        FROM antinsfw WHERE chat_id = ?
        """,
        (chat_id,),
    )
    row = cursor.fetchone()
    if row:
        return (
            bool(row[0]),
            bool(row[1]),
            row[2],
            row[3],
            row[4],
            bool(row[5]),
            bool(row[6]),
            bool(row[7]),
        )
    return False, False, "delete", 0, 3, True, True, False

def add_warning(user_id: int, chat_id: int):
    """Add a warning for a user in a chat."""
    current_time = int(time.time())
    cursor.execute(
        """
        INSERT INTO nsfw_warnings (user_id, chat_id, warnings, last_warning_time)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(user_id, chat_id)
        DO UPDATE SET warnings = warnings + 1, last_warning_time = ?
        """,
        (user_id, chat_id, current_time, current_time),
    )
    conn.commit()

def get_warnings(user_id: int, chat_id: int) -> int:
    """Get number of warnings for a user in a chat."""
    cursor.execute(
        "SELECT warnings FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    row = cursor.fetchone()
    return row[0] if row else 0

def reset_warnings(user_id: int, chat_id: int):
    """Reset warnings for a user in a chat."""
    cursor.execute(
        "DELETE FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    conn.commit()

def reset_all_warnings(chat_id: int):
    """Reset all warnings in a chat."""
    cursor.execute(
        "DELETE FROM nsfw_warnings WHERE chat_id = ?",
        (chat_id,),
    )
    conn.commit()

def log_nsfw_action(
    chat_id: int,
    user_id: int,
    message_id: int,
    media_type: str,
    confidence: float,
    action_taken: str,
    details: str = "",
    service_used: str = "unknown",
):
    """Log NSFW detection action."""
    timestamp = int(time.time())
    cursor.execute(
        """
        INSERT INTO nsfw_logs
        (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details, service_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details, service_used),
    )
    today = time.strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO nsfw_stats (chat_id, date, detected_count)
        VALUES (?, ?, 1)
        ON CONFLICT(chat_id, date) DO UPDATE SET detected_count = detected_count + 1
        """,
        (chat_id, today),
    )
    if action_taken == "deleted":
        cursor.execute(
            "UPDATE nsfw_stats SET deleted_count = deleted_count + 1 WHERE chat_id = ? AND date = ?",
            (chat_id, today),
        )
    conn.commit()

def add_to_whitelist(chat_id: int, user_id: int, added_by: int):
    """Add user to whitelist in a chat."""
    cursor.execute(
        """
        INSERT OR REPLACE INTO nsfw_whitelist (user_id, chat_id, added_by)
        VALUES (?, ?, ?)
        """,
        (user_id, chat_id, added_by),
    )
    conn.commit()

def remove_from_whitelist(chat_id: int, user_id: int):
    """Remove user from whitelist in a chat."""
    cursor.execute(
        "DELETE FROM nsfw_whitelist WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    conn.commit()

def get_whitelist(chat_id: int) -> List[int]:
    """Get whitelisted users for a chat."""
    cursor.execute(
        "SELECT user_id FROM nsfw_whitelist WHERE chat_id = ?",
        (chat_id,),
    )
    return [row[0] for row in cursor.fetchall()]

def is_whitelisted(chat_id: int, user_id: int) -> bool:
    """Check if user is whitelisted in a chat."""
    cursor.execute(
        "SELECT 1 FROM nsfw_whitelist WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    return cursor.fetchone() is not None

# ======================
# NSFW DETECTION
# ======================
async def detect_nsfw_sightengine(image_path: str) -> Tuple[bool, float, Dict, str]:
    """Detect NSFW content using SightEngine API."""
    try:
        if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
            LOGGER.error("SightEngine API credentials not configured")
            return False, 0, {}, "sightengine"

        async with aiofiles.open(image_path, "rb") as media:
            file_content = await media.read()

        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field("media", file_content, filename="media.jpg")
            form_data.add_field("models", "nudity-2.1,wad,offensive,text-content,gore")
            form_data.add_field("api_user", SIGHTENGINE_API_USER)
            form_data.add_field("api_secret", SIGHTENGINE_API_SECRET)

            async with session.post(
                "https://api.sightengine.com/1.0/check.json",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                result = await response.json()

        if response.status != 200 or result.get("status") != "success":
            error_msg = result.get("error", {}).get("message", "Unknown error")
            LOGGER.error(f"SightEngine API error: {error_msg}")
            return False, 0, {}, "sightengine"

        nudity_score = max(
            result.get("nudity", {}).get("sexual_activity", 0),
            result.get("nudity", {}).get("sexual_display", 0),
            result.get("nudity", {}).get("erotica", 0),
        )
        total_score = (
            nudity_score * 0.6
            + result.get("nudity", {}).get("suggestive", 0) * 0.2
            + result.get("offensive", {}).get("prob", 0) * 0.1
        )
        is_nsfw = total_score > NSFW_THRESHOLD or nudity_score > NSFW_THRESHOLD
        return is_nsfw, total_score, result, "sightengine"
    except Exception as e:
        LOGGER.error(f"Error in SightEngine NSFW detection: {e}")
        return False, 0, {}, "sightengine"

async def detect_nsfw(image_path: str) -> Tuple[bool, float, Dict, str]:
    """Main NSFW detection function with multiple fallbacks."""
    services = [detect_nsfw_sightengine]
    best_score = 0
    best_result = {}
    best_service = "none"
    any_nsfw = False

    for service in services:
        try:
            is_nsfw, score, details, service_name = await service(image_path)
            if is_nsfw and score > best_score:
                best_score = score
                best_result = details
                best_service = service_name
                any_nsfw = True
            elif score > best_score:
                best_score = score
                best_result = details
                best_service = service_name
        except Exception as e:
            LOGGER.warning(f"NSFW detection service failed: {e}")
            continue

    return any_nsfw, best_score, best_result, best_service

# ======================
# UTILITY FUNCTIONS
# ======================
async def is_user_admin(client: Gojo, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in the chat."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except:
        return False

async def log_nsfw_event(
    client: Gojo,
    chat_id: int,
    log_channel: int,
    message: Message,
    confidence: float,
    action: str,
    details: Dict = None,
    service_used: str = "unknown",
):
    """Log NSFW event to the specified channel."""
    if not log_channel:
        return

    log_text = (
        f"🚨 **NSFW Content Detected**\n\n"
        f"**Chat:** {message.chat.title} (`{message.chat.id}`)\n"
        f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
        f"**Confidence:** {confidence*100:.1f}%\n"
        f"**Action:** {action}\n"
        f"**Service:** {service_used}\n"
        f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
    )

    if details and "nudity" in details:
        nudity = details["nudity"]
        log_text += f"**Nudity Score:** {max(nudity.get('sexual_activity', 0), nudity.get('sexual_display', 0))*100:.1f}%\n"

    try:
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

# ======================
# HANDLERS
# ======================
async def take_action(
    client: Gojo,
    message: Message,
    action_type: str,
    warn_threshold: int,
    confidence: float,
    details: Dict,
    service_used: str,
):
    """Take appropriate action based on settings."""
    action_taken = "none"
    if action_type == "delete":
        try:
            await message.delete()
            action_taken = "deleted"
            LOGGER.info(f"Deleted NSFW message from {message.from_user.id} in chat {message.chat.id}")
        except Exception as e:
            LOGGER.warning(f"Could not delete NSFW message: {e}")
            action_taken = "delete_failed"

    media_type = "photo" if message.photo else "video" if message.video else "document" if message.document else "unknown"
    log_nsfw_action(
        message.chat.id,
        message.from_user.id,
        message.id,
        media_type,
        confidence,
        action_taken,
        str(details),
        service_used,
    )

    if action_taken == "deleted":
        add_warning(message.from_user.id, message.chat.id)
        warnings = get_warnings(message.from_user.id, message.chat.id)
        warn_msg_text = (
            f"🚫 NSFW content detected and removed!\n"
            f"👤 User: {message.from_user.mention}\n"
            f"⚠️ Warning {warnings}/{warn_threshold}\n"
            f"🔞 Confidence: {confidence*100:.1f}%"
        )
        keyboard = []
        if await is_user_admin(client, message.chat.id, (await client.get_me()).id):
            keyboard.append([InlineKeyboardButton("❌ Ban User", callback_data=f"ban_nsfw_{message.from_user.id}")])
            keyboard.append([InlineKeyboardButton("⚠️ Reset Warnings", callback_data=f"reset_warn_{message.from_user.id}")])

        try:
            warn_msg = await client.send_message(
                message.chat.id,
                warn_msg_text,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            )
            await asyncio.sleep(30)
            await warn_msg.delete()
        except Exception as e:
            LOGGER.error(f"Failed to send warning message: {e}")

        if warnings >= warn_threshold:
            try:
                await client.ban_chat_member(message.chat.id, message.from_user.id)
                ban_msg = await client.send_message(
                    message.chat.id,
                    f"🚫 {message.from_user.mention} has been banned for sending NSFW content ({warn_threshold} warnings).",
                )
                await asyncio.sleep(30)
                await ban_msg.delete()
            except Exception as ban_error:
                LOGGER.error(f"Ban failed: {ban_error}")

    return action_taken

async def process_media_in_background(client: Gojo, message: Message):
    """Process media in background without blocking."""
    enabled, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(
        message.chat.id
    )
    if not enabled:
        return

    if not message.from_user or await is_user_admin(client, message.chat.id, message.from_user.id):
        return

    if is_whitelisted(message.chat.id, message.from_user.id):
        return

    if message.photo and not scan_photos:
        return
    if message.video and not scan_videos:
        return
    if message.document and not scan_documents:
        return

    file_path = None
    try:
        file_size = 0
        if message.document:
            file_size = message.document.file_size
        elif message.video:
            file_size = message.video.file_size
        elif message.photo:
            largest_photo = max(message.photo, key=lambda p: p.file_size if hasattr(p, "file_size") else 0)
            file_size = largest_photo.file_size if hasattr(largest_photo, "file_size") else 0

        if file_size > MAX_FILE_SIZE:
            LOGGER.info(f"Skipping large file ({message.id}, {file_size} bytes) in chat {message.chat.id}")
            return

        file_path = await message.download()
        if not file_path:
            return

        is_nsfw, confidence, details, service_used = await detect_nsfw(file_path)
        if strict and not is_nsfw:
            nudity = details.get("nudity", {})
            nudity_score = max(
                nudity.get("sexual_activity", 0),
                nudity.get("sexual_display", 0),
                nudity.get("erotica", 0),
            )
            if nudity_score > STRICT_THRESHOLD:
                is_nsfw = True
                confidence = nudity_score

        if is_nsfw:
            await take_action(
                client, message, action_type, warn_threshold, confidence, details, service_used
            )
    except Exception as e:
        LOGGER.error(f"Auto NSFW scan error: {e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ======================
# COMMANDS
# ======================
@Gojo.on_message(filters.command("antinsfw") & filters.group)
async def toggle_antinsfw(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

    if len(message.command) < 2:
        status, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
        media_types = []
        if scan_photos:
            media_types.append("📷 Photos")
        if scan_videos:
            media_types.append("🎥 Videos")
        if scan_documents:
            media_types.append("📄 Documents")
        media_status = ", ".join(media_types) if media_types else "None"
        log_info = f"Log channel: {log_channel}" if log_channel else "Logging: disabled"
        return await message.reply_text(
            f"⚙️ Anti-NSFW Settings:\n\n"
            f"Status: {'✅ ON' if status else '❌ OFF'}\n"
            f"Strict Mode: {'✅ ON' if strict else '❌ OFF'}\n"
            f"Action: {action_type}\n"
            f"Warning Threshold: {warn_threshold}\n"
            f"Media Types: {media_status}\n"
            f"{log_info}\n\n"
            "Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`, `/antinsfw warnthreshold [number]`, `/antinsfw media photos|videos|documents on/off`",
        )

    arg1 = message.command[1].lower()
    if arg1 == "on":
        set_antinsfw(message.chat.id, True)
        return await message.reply_text("✅ Anti-NSFW enabled in this group!")
    elif arg1 == "off":
        set_antinsfw(message.chat.id, False)
        return await message.reply_text("❌ Anti-NSFW disabled in this group!")
    elif arg1 == "strict" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["on", "off"]:
            enabled, _, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, arg2 == "on", action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents)
            return await message.reply_text(f"✅ Strict mode {'enabled' if arg2 == 'on' else 'disabled'}!")
    elif arg1 == "action" and len(message.command) > 2:
        arg2 = message.command[2].lower()
        if arg2 in ["delete", "warn"]:
            enabled, strict, _, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, arg2, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents)
            return await message.reply_text(f"✅ Action type set to '{arg2}'!")
    elif arg1 == "logchannel" and len(message.command) > 2:
        try:
            log_channel = int(message.command[2])
            enabled, strict, action_type, _, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents)
            return await message.reply_text(f"✅ Log channel set to {log_channel}!")
        except ValueError:
            return await message.reply_text("❌ Invalid channel ID. Please provide a numeric channel ID.")
    elif arg1 == "warnthreshold" and len(message.command) > 2:
        try:
            threshold = int(message.command[2])
            if threshold < 1 or threshold > 10:
                return await message.reply_text("❌ Warning threshold must be between 1 and 10.")
            enabled, strict, action_type, log_channel, _, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
            set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel, threshold, scan_photos, scan_videos, scan_documents)
            return await message.reply_text(f"✅ Warning threshold set to {threshold}!")
        except ValueError:
            return await message.reply_text("❌ Please provide a valid number for the warning threshold.")
    elif arg1 == "media" and len(message.command) > 3:
        media_type = message.command[2].lower()
        state = message.command[3].lower()
        if state not in ["on", "off"]:
            return await message.reply_text("⚙️ Usage: `/antinsfw media photos|videos|documents on/off`")
        enabled, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = get_antinsfw(message.chat.id)
        if media_type == "photos":
            scan_photos = state == "on"
        elif media_type == "videos":
            scan_videos = state == "on"
        elif media_type == "documents":
            scan_documents = state == "on"
        else:
            return await message.reply_text("⚙️ Usage: `/antinsfw media photos|videos|documents on/off`")
        set_antinsfw(message.chat.id, enabled, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents)
        return await message.reply_text(f"✅ {media_type.capitalize()} scanning {'enabled' if state == 'on' else 'disabled'}!")
    elif arg1 == "whitelist" and len(message.command) > 2:
        action = message.command[2].lower()
        if action == "list":
            whitelisted = get_whitelist(message.chat.id)
            if not whitelisted:
                return await message.reply_text("❌ No users are whitelisted in this chat.")
            user_list = []
            for user_id in whitelisted:
                try:
                    user = await client.get_users(user_id)
                    user_list.append(f"{user.mention} (`{user.id}`)")
                except:
                    user_list.append(f"Unknown User (`{user_id}`)")
            return await message.reply_text("✅ Whitelisted users:\n\n" + "\n".join(user_list))
        elif action in ["add", "remove"] and message.reply_to_message:
            target_user = message.reply_to_message.from_user
            if action == "add":
                add_to_whitelist(message.chat.id, target_user.id, message.from_user.id)
                return await message.reply_text(f"✅ {target_user.mention} has been added to the whitelist!")
            else:
                remove_from_whitelist(message.chat.id, target_user.id)
                return await message.reply_text(f"✅ {target_user.mention} has been removed from the whitelist!")
    else:
        return await message.reply_text("⚙️ Usage: `/antinsfw on/off`, `/antinsfw strict on/off`, `/antinsfw action delete/warn`, `/antinsfw logchannel`, `/antinsfw warnthreshold [number]`, `/antinsfw media photos|videos|documents on/off`")

@Gojo.on_message(filters.command("nsfwscan") & filters.group)
async def scan_nsfw_command(client: Gojo, message: Message):
    if not message.reply_to_message or not (message.reply_to_message.photo or message.reply_to_message.video or message.reply_to_message.document):
        return await message.reply_text("⚠️ Reply to a media message (photo/video/document) to scan.")

    target = message.reply_to_message
    file_path = None
    try:
        if target.document and target.document.file_size > MAX_FILE_SIZE:
            return await message.reply_text("❌ File is too large (max 10MB).")

        file_path = await target.download()
        scan_msg = await message.reply_text("🔍 Scanning...")
        is_nsfw, confidence, details, service_used = await detect_nsfw(file_path)
        if is_nsfw:
            response_text = (
                f"🚨 NSFW content detected ({confidence*100:.1f}% confidence)\n"
                f"**Service:** {service_used}\n"
            )
            if details.get("nudity"):
                nudity = details.get("nudity", {})
                response_text += f"• Nudity: {max(nudity.get('sexual_activity', 0), nudity.get('sexual_display', 0))*100:.1f}%\n"
                response_text += f"• Suggestive: {nudity.get('suggestive', 0)*100:.1f}%\n"
            if details.get("offensive", {}).get("prob", 0) > 0:
                response_text += f"• Offensive: {details.get('offensive', {}).get('prob', 0)*100:.1f}%\n"
            if details.get("weapon", 0) > 0:
                response_text += f"• Weapon: {details.get('weapon', 0)*100:.1f}%\n"
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
        LOGGER.error(f"Manual NSFW scan error: {e}")
        await scan_msg.edit_text("❌ Error scanning media. Please try again.")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

@Gojo.on_message(filters.command("nsfwwarns") & filters.group)
async def check_nsfw_warns(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

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
    _, _, _, _, warn_threshold, _, _, _ = get_antinsfw(message.chat.id)
    await message.reply_text(f"⚠️ {target_user.mention} has {warnings}/{warn_threshold} NSFW warning(s).")

@Gojo.on_message(filters.command("resetnsfwwarns") & filters.group)
async def reset_nsfw_warns(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

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
    _, _, _, _, warn_threshold, _, _, _ = get_antinsfw(message.chat.id)
    await message.reply_text(f"⚠️ You have {warnings}/{warn_threshold} NSFW warning(s) in this group.")

@Gojo.on_message(filters.command("nsfwstats") & filters.group)
async def nsfw_stats(client: Gojo, message: Message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can use this command.")

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
# CALLBACK HANDLERS
# ======================
@Gojo.on_callback_query(filters.regex(r"^del_nsfw_"))
async def delete_nsfw_callback(client: Gojo, callback_query: CallbackQuery):
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
async def ban_user_callback(client: Gojo, callback_query: CallbackQuery):
    try:
        user_id = int(callback_query.data.split("_")[2])
        if await is_user_admin(client, callback_query.message.chat.id, callback_query.from_user.id):
            await client.ban_chat_member(callback_query.message.chat.id, user_id)
            await callback_query.answer("User banned!")
            await callback_query.message.edit_text("✅ User has been banned.")
        else:
            await callback_query.answer("You need to be admin to ban users.", show_alert=True)
    except Exception as e:
        LOGGER.error(f"Ban callback error: {e}")
        await callback_query.answer("Error banning user.", show_alert=True)

@Gojo.on_callback_query(filters.regex(r"^reset_warn_"))
async def reset_warnings_callback(client: Gojo, callback_query: CallbackQuery):
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
    enabled, _, _, _, _, _, _, _ = get_antinsfw(message.chat.id)
    if not enabled:
        return
    asyncio.create_task(process_media_in_background(client, message))

# ======================
# INITIALIZATION
# ======================
init_db()
executor = ThreadPoolExecutor(max_workers=10)
LOGGER.info("Anti-NSFW module loaded successfully!")
