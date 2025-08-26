import os
import sqlite3
import time
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Tuple, Dict, List, Optional, Union
from Powers.bot_class import Gojo
from Powers import LOGGER

# ======================
# CONFIGURATION
# ======================
class Config:
    SIGHTENGINE_API_USER: str = os.getenv("SIGHTENGINE_API_USER", "862487500")
    SIGHTENGINE_API_SECRET: str = os.getenv("SIGHTENGINE_API_SECRET", "sc2VeSyJYzKciVhP8X57GtmQvA8kyzCb")
    DEEPAI_API_KEY: str = os.getenv("DEEPAI_API_KEY", "79eb379a-337c-4258-9957-a0c25195b6da")
    HOLARA_API_KEY: str = os.getenv("HOLARA_API_KEY", "d2d272f0-6489-4fc1-a32d-fa4a27190f7e")
    DB_PATH: str = "antinsfw.db"
    NSFW_THRESHOLD: float = 0.75
    STRICT_THRESHOLD: float = 0.65
    SUGGESTIVE_THRESHOLD: float = 0.6
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

# ======================
# DATABASE MANAGER
# ======================
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        """Initialize all required tables."""
        self.cursor.execute("""
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
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS nsfw_warnings (
                user_id INTEGER,
                chat_id INTEGER,
                warnings INTEGER DEFAULT 0,
                last_warning_time INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        self.cursor.execute("""
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
        self.cursor.execute("""
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
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS nsfw_whitelist (
                user_id INTEGER,
                chat_id INTEGER,
                added_by INTEGER,
                added_at INTEGER DEFAULT (strftime('%s', 'now')),
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        self.conn.commit()

    def set_antinsfw(
        self,
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
        self.cursor.execute(
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
        self.conn.commit()

    def get_antinsfw(self, chat_id: int) -> Tuple[bool, bool, str, int, int, bool, bool, bool]:
        """Get anti-NSFW configuration for a chat."""
        self.cursor.execute(
            """
            SELECT enabled, strict_mode, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents
            FROM antinsfw WHERE chat_id = ?
            """,
            (chat_id,),
        )
        row = self.cursor.fetchone()
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

    def add_warning(self, user_id: int, chat_id: int):
        """Add a warning for a user in a chat."""
        current_time = int(time.time())
        self.cursor.execute(
            """
            INSERT INTO nsfw_warnings (user_id, chat_id, warnings, last_warning_time)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, chat_id)
            DO UPDATE SET warnings = warnings + 1, last_warning_time = ?
            """,
            (user_id, chat_id, current_time, current_time),
        )
        self.conn.commit()

    def get_warnings(self, user_id: int, chat_id: int) -> int:
        """Get number of warnings for a user in a chat."""
        self.cursor.execute(
            "SELECT warnings FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def reset_warnings(self, user_id: int, chat_id: int):
        """Reset warnings for a user in a chat."""
        self.cursor.execute(
            "DELETE FROM nsfw_warnings WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        self.conn.commit()

    def log_nsfw_action(
        self,
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
        self.cursor.execute(
            """
            INSERT INTO nsfw_logs
            (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details, service_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, message_id, media_type, confidence, timestamp, action_taken, details, service_used),
        )
        today = time.strftime("%Y-%m-%d")
        self.cursor.execute(
            """
            INSERT INTO nsfw_stats (chat_id, date, detected_count)
            VALUES (?, ?, 1)
            ON CONFLICT(chat_id, date) DO UPDATE SET detected_count = detected_count + 1
            """,
            (chat_id, today),
        )
        if action_taken == "deleted":
            self.cursor.execute(
                "UPDATE nsfw_stats SET deleted_count = deleted_count + 1 WHERE chat_id = ? AND date = ?",
                (chat_id, today),
            )
        self.conn.commit()

    def add_to_whitelist(self, chat_id: int, user_id: int, added_by: int):
        """Add user to whitelist in a chat."""
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO nsfw_whitelist (user_id, chat_id, added_by)
            VALUES (?, ?, ?)
            """,
            (user_id, chat_id, added_by),
        )
        self.conn.commit()

    def is_whitelisted(self, chat_id: int, user_id: int) -> bool:
        """Check if user is whitelisted in a chat."""
        self.cursor.execute(
            "SELECT 1 FROM nsfw_whitelist WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        )
        return self.cursor.fetchone() is not None

# ======================
# NSFW DETECTION
# ======================
class NSFWDetector:
    @staticmethod
    async def detect_nsfw_sightengine(image_path: str) -> Tuple[bool, float, Dict, str]:
        """Detect NSFW content using SightEngine API."""
        try:
            if not Config.SIGHTENGINE_API_USER or not Config.SIGHTENGINE_API_SECRET:
                LOGGER.error("SightEngine API credentials not configured")
                return False, 0, {}, "sightengine"

            async with aiofiles.open(image_path, "rb") as media:
                file_content = await media.read()

            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field("media", file_content, filename="media.jpg")
                form_data.add_field("models", "nudity-2.1,wad,offensive,text-content,gore")
                form_data.add_field("api_user", Config.SIGHTENGINE_API_USER)
                form_data.add_field("api_secret", Config.SIGHTENGINE_API_SECRET)

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
            total_score = nudity_score * 0.6 + result.get("nudity", {}).get("suggestive", 0) * 0.2 + result.get("offensive", {}).get("prob", 0) * 0.1
            is_nsfw = total_score > Config.NSFW_THRESHOLD or nudity_score > Config.NSFW_THRESHOLD
            return is_nsfw, total_score, result, "sightengine"
        except Exception as e:
            LOGGER.error(f"Error in SightEngine NSFW detection: {e}")
            return False, 0, {}, "sightengine"

    @staticmethod
    async def detect_nsfw(image_path: str) -> Tuple[bool, float, Dict, str]:
        """Main NSFW detection function with multiple fallbacks."""
        services = [NSFWDetector.detect_nsfw_sightengine]
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
class Utilities:
    @staticmethod
    async def is_user_admin(client: Gojo, chat_id: int, user_id: int) -> bool:
        """Check if user is admin in the chat."""
        try:
            member = await client.get_chat_member(chat_id, user_id)
            return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        except:
            return False

    @staticmethod
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
class Handlers:
    @staticmethod
    async def take_action(
        client: Gojo,
        message: Message,
        action_type: str,
        warn_threshold: int,
        confidence: float,
        details: Dict,
        service_used: str,
        db: DatabaseManager,
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
        db.log_nsfw_action(
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
            db.add_warning(message.from_user.id, message.chat.id)
            warnings = db.get_warnings(message.from_user.id, message.chat.id)
            warn_msg_text = (
                f"🚫 NSFW content detected and removed!\n"
                f"👤 User: {message.from_user.mention}\n"
                f"⚠️ Warning {warnings}/{warn_threshold}\n"
                f"🔞 Confidence: {confidence*100:.1f}%"
            )
            keyboard = []
            if await Utilities.is_user_admin(client, message.chat.id, (await client.get_me()).id):
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

    @staticmethod
    async def process_media_in_background(client: Gojo, message: Message, db: DatabaseManager):
        """Process media in background without blocking."""
        enabled, strict, action_type, log_channel, warn_threshold, scan_photos, scan_videos, scan_documents = db.get_antinsfw(
            message.chat.id
        )
        if not enabled:
            return

        if not message.from_user or await Utilities.is_user_admin(client, message.chat.id, message.from_user.id):
            return

        if db.is_whitelisted(message.chat.id, message.from_user.id):
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

            if file_size > Config.MAX_FILE_SIZE:
                LOGGER.info(f"Skipping large file ({message.id}, {file_size} bytes) in chat {message.chat.id}")
                return

            file_path = await message.download()
            if not file_path:
                return

            is_nsfw, confidence, details, service_used = await NSFWDetector.detect_nsfw(file_path)
            if strict and not is_nsfw:
                nudity = details.get("nudity", {})
                nudity_score = max(
                    nudity.get("sexual_activity", 0),
                    nudity.get("sexual_display", 0),
                    nudity.get("erotica", 0),
                )
                if nudity_score > Config.STRICT_THRESHOLD:
                    is_nsfw = True
                    confidence = nudity_score

            if is_nsfw:
                await Handlers.take_action(
                    client, message, action_type, warn_threshold, confidence, details, service_used, db
                )
        except Exception as e:
            LOGGER.error(f"Auto NSFW scan error: {e}")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

# ======================
# COMMANDS
# ======================
class Commands:
    @staticmethod
    @Gojo.on_message(filters.command("antinsfw") & filters.group)
    async def toggle_antinsfw(client: Gojo, message: Message):
        if not await Utilities.is_user_admin(client, message.chat.id, message.from_user.id):
            return await message.reply_text("❌ Only admins can use this command.")
        # ... (rest of the command logic)

    @staticmethod
    @Gojo.on_message(filters.command("nsfwscan") & filters.group)
    async def scan_nsfw_command(client: Gojo, message: Message):
        if not message.reply_to_message or not (
            message.reply_to_message.photo or message.reply_to_message.video or message.reply_to_message.document
        ):
            return await message.reply_text("⚠️ Reply to a media message (photo/video/document) to scan.")
        # ... (rest of the command logic)

# ======================
# INITIALIZATION
# ======================
db = DatabaseManager()
executor = ThreadPoolExecutor(max_workers=10)
LOGGER.info("Anti-NSFW module loaded successfully!")
