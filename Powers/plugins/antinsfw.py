import os
import json
import asyncio
import tempfile
import traceback
import time
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
import io

from pyrogram import filters, ContinuePropagation
from pyrogram.enums import ParseMode as PM, ChatMemberStatus
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── CONFIG ───
DATA_FILE = os.path.join(os.getcwd(), "antinsfw.json")
MODEL_PATH = os.path.join(os.getcwd(), "nsfw_model")

# Rate limiting
MAX_SCANS_PER_HOUR = 100  # Local model can handle more
RATE_LIMIT = {}

# ─── LOAD/SAVE DATA ───
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"antinsfw": {}, "free_users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize data
        ant = {str(k): bool(v) for k, v in data.get("antinsfw", {}).items()}
        free = {str(k): [str(uid) for uid in v] for k, v in data.get("free_users", {}).items()}
        return {"antinsfw": ant, "free_users": free}
    except Exception:
        return {"antinsfw": {}, "free_users": {}}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"antinsfw": ANTINSFW, "free_users": FREE_USERS}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")

# Load initial data
_data = load_data()
ANTINSFW = _data.get("antinsfw", {})
FREE_USERS = _data.get("free_users", {})

# ─── SIMPLE NSFW DETECTION (No external API) ───
class SimpleNSFWDetector:
    def __init__(self):
        self.initialized = False
        self.model = None
        self.labels = ['drawings', 'hentai', 'neutral', 'porn', 'sexy']
        
    async def initialize(self):
        """Initialize the detector - will use simple heuristics if TensorFlow fails"""
        try:
            # Try to import TensorFlow
            import tensorflow as tf
            from tensorflow.keras.models import load_model
            from tensorflow.keras.preprocessing import image
            
            # Check if model exists
            if os.path.exists(MODEL_PATH):
                self.model = load_model(MODEL_PATH)
                print("✅ Loaded TensorFlow NSFW model")
            else:
                print("⚠️ No local model found, using heuristic detection")
            
            self.initialized = True
            return True
            
        except ImportError:
            print("⚠️ TensorFlow not available, using heuristic detection")
            self.initialized = True
            return True
        except Exception as e:
            print(f"⚠️ Model loading failed: {e}, using heuristic detection")
            self.initialized = True
            return True
    
    async def detect_nsfw(self, image_path: str) -> Tuple[bool, float]:
        """Detect NSFW content using multiple methods"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Method 1: Try TensorFlow model if available
            if self.model:
                return await self._detect_with_model(image_path)
            
            # Method 2: Simple heuristic detection (no dependencies)
            return await self._detect_heuristic(image_path)
            
        except Exception as e:
            print(f"NSFW detection error: {e}")
            return False, 0.0
    
    async def _detect_with_model(self, image_path: str) -> Tuple[bool, float]:
        """Use TensorFlow model for detection"""
        try:
            from tensorflow.keras.preprocessing import image as tf_image
            import tensorflow as tf
            
            # Load and preprocess image
            img = tf_image.load_img(image_path, target_size=(299, 299))
            img_array = tf_image.img_to_array(img)
            img_array = tf.expand_dims(img_array, axis=0)
            img_array = tf.keras.applications.inception_v3.preprocess_input(img_array)
            
            # Predict
            predictions = self.model.predict(img_array)
            confidence = float(np.max(predictions))
            predicted_class = self.labels[np.argmax(predictions)]
            
            # Consider porn, hentai, sexy as NSFW
            is_nsfw = predicted_class in ['porn', 'hentai', 'sexy'] and confidence > 0.6
            
            return is_nsfw, confidence
            
        except Exception as e:
            print(f"Model detection failed: {e}")
            # Fallback to heuristic
            return await self._detect_heuristic(image_path)
    
    async def _detect_heuristic(self, image_path: str) -> Tuple[bool, float]:
        """Simple heuristic-based NSFW detection"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get image data
                img_array = np.array(img)
                
                # Simple heuristics (can be expanded)
                nsfw_score = 0.0
                
                # 1. Check for skin tone pixels
                skin_pixels = self._detect_skin_tone(img_array)
                skin_ratio = skin_pixels / (img_array.shape[0] * img_array.shape[1])
                
                if skin_ratio > 0.3:  # More than 30% skin tones
                    nsfw_score += 0.4
                
                # 2. Check image brightness (dark images often indicate NSFW)
                brightness = np.mean(img_array) / 255.0
                if brightness < 0.4:  # Dark image
                    nsfw_score += 0.3
                
                # 3. Check color saturation
                saturation = self._calculate_saturation(img_array)
                if saturation > 0.6:  # Highly saturated
                    nsfw_score += 0.3
                
                # Cap score at 1.0
                nsfw_score = min(nsfw_score, 1.0)
                
                return nsfw_score > 0.6, nsfw_score
                
        except Exception as e:
            print(f"Heuristic detection failed: {e}")
            return False, 0.0
    
    def _detect_skin_tone(self, img_array: np.array) -> int:
        """Detect skin tone pixels using simple color ranges"""
        # Simple skin tone detection in RGB
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        
        # Skin tone conditions (can be adjusted)
        skin_mask = (
            (r > 120) & (g > 80) & (b > 60) & 
            (np.abs(r - g) > 20) & (r > g) & (r > b)
        )
        
        return np.sum(skin_mask)
    
    def _calculate_saturation(self, img_array: np.array) -> float:
        """Calculate average saturation of image"""
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        max_val = np.maximum.reduce([r, g, b])
        min_val = np.minimum.reduce([r, g, b])
        saturation = np.where(max_val == 0, 0, (max_val - min_val) / max_val)
        return np.mean(saturation)

# Initialize detector
nsfw_detector = SimpleNSFWDetector()

# ─── RATE LIMITING ───
def check_rate_limit(chat_id: int) -> bool:
    """Check if chat has exceeded rate limit"""
    current_hour = int(time.time()) // 3600
    chat_key = f"{chat_id}_{current_hour}"
    
    if chat_key not in RATE_LIMIT:
        RATE_LIMIT[chat_key] = 0
    
    if RATE_LIMIT[chat_key] >= MAX_SCANS_PER_HOUR:
        return False
    
    RATE_LIMIT[chat_key] += 1
    return True

# ─── HELPERS ───
async def is_chat_admin(c: Gojo, chat_id: int, user_id: int) -> bool:
    """Check if user is owner or admin with 'can_promote_members' rights."""
    try:
        member = await c.get_chat_member(chat_id, user_id)
        if member.status == ChatMemberStatus.OWNER:
            return True
        if member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member.privileges, "can_promote_members", False):
            return True
        return False
    except Exception:
        return False

def _content_type_label(m: Message) -> str:
    if m.photo: return "📸 Photo"
    if m.video: return "🎥 Video"
    if m.animation: return "🎞️ GIF"
    if m.document: return "📂 Document"
    if m.sticker: return "🖼️ Sticker"
    return "📦 Media"

def _user_markdown_link(user) -> str:
    name = user.first_name or "User"
    if getattr(user, "last_name", None):
        name = f"{name} {user.last_name}"
    return f"[{name}](tg://user?id={user.id})"

# ─── COMMANDS ───
@Gojo.on_message(command(["antinsfw"]) & filters.group)
async def toggle_antinsfw(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    if len(m.command) == 1:
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Enable", callback_data=f"antinsfw:on:{chat_id_str}"),
                    InlineKeyboardButton("❌ Disable", callback_data=f"antinsfw:off:{chat_id_str}")
                ],
                [InlineKeyboardButton("⚙️ View Status", callback_data=f"antinsfw:status:{chat_id_str}")]
            ]
        )
        await m.reply_text(
            f"🚨 **Anti-NSFW System** 🚨\n\nCurrent status: **{status}**\n\n"
            f"✅ **Local Detection:** No external APIs\n"
            f"⚡ **Fast & Free:** No rate limits\n"
            f"🔒 **Privacy:** All processing local",
            reply_markup=kb,
            parse_mode=PM.MARKDOWN
        )
    else:
        await m.reply_text("ℹ️ Use `/antinsfw` without arguments")

@Gojo.on_callback_query(filters.regex(r"^antinsfw:(on|off|status):(-?\d+)$"))
async def antinsfw_callback(c: Gojo, q: CallbackQuery):
    action, chat_id_str = q.data.split(":", 2)[1:]
    chat_id = int(chat_id_str)
    user_id = q.from_user.id

    if action != "status" and not await is_chat_admin(c, chat_id, user_id):
        return await q.answer("Admins with 'add admin' rights only.", show_alert=True)

    if action == "on":
        ANTINSFW[chat_id_str] = True
        save_data()
        await q.message.edit_text(
            "🚨 Anti-NSFW is now **ENABLED ✅**\n\n"
            "✅ Using local detection\n"
            "⚡ No external API limits\n"
            "🔒 All processing done locally",
            parse_mode=PM.MARKDOWN
        )
        await q.answer("Enabled")
    elif action == "off":
        ANTINSFW[chat_id_str] = False
        save_data()
        await q.message.edit_text("⚠️ Anti-NSFW is now **DISABLED ❌**", parse_mode=PM.MARKDOWN)
        await q.answer("Disabled")
    else:
        status = "✅ ENABLED" if ANTINSFW.get(chat_id_str, False) else "❌ DISABLED"
        scans_this_hour = RATE_LIMIT.get(f"{chat_id}_{int(time.time()) // 3600}", 0)
        await q.answer(f"Status: {status}\nScans this hour: {scans_this_hour}", show_alert=True)

# ─── FREE USERS ───
@Gojo.on_message(command(["free"]) & filters.group)
async def free_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /free them.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("❌ Admins only.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)
    FREE_USERS.setdefault(chat_id_str, [])

    if target_id_str not in FREE_USERS[chat_id_str]:
        FREE_USERS[chat_id_str].append(target_id_str)
        save_data()
        await m.reply_text(
            f"✅ {_user_markdown_link(target)} has been *freed* from Anti-NSFW scans.",
            parse_mode=PM.MARKDOWN
        )
    else:
        await m.reply_text(f"⚡ {_user_markdown_link(target)} is already free.", parse_mode=PM.MARKDOWN)

@Gojo.on_message(command(["unfree"]) & filters.group)
async def unfree_user(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)
    if not m.reply_to_message or not m.reply_to_message.from_user:
        return await m.reply_text("⚠️ Reply to a user's message to /unfree them.")

    if not await is_chat_admin(c, m.chat.id, m.from_user.id):
        return await m.reply_text("🚫 Admins only.")

    target = m.reply_to_message.from_user
    target_id_str = str(target.id)

    if target_id_str in FREE_USERS.get(chat_id_str, []):
        FREE_USERS[chat_id_str].remove(target_id_str)
        save_data()
        await m.reply_text(f"✨ {_user_markdown_link(target)} removed from Free List.", parse_mode=PM.MARKDOWN)
    else:
        await m.reply_text("⚠️ User not in Free List.")

# ─── MAIN SCANNER ───
@Gojo.on_message(filters.group & (filters.photo | filters.video | filters.animation | filters.document | filters.sticker))
async def nsfw_scanner(c: Gojo, m: Message):
    chat_id_str = str(m.chat.id)

    # Skip if not enabled or should be skipped
    if not ANTINSFW.get(chat_id_str, False):
        raise ContinuePropagation
    if not m.from_user or m.from_user.is_bot:
        raise ContinuePropagation
    if str(m.from_user.id) in FREE_USERS.get(chat_id_str, []):
        raise ContinuePropagation
    
    # Skip videos and large files for heuristic detection
    if m.video or (m.document and m.document.file_size and m.document.file_size > 10 * 1024 * 1024):
        raise ContinuePropagation

    file_path = None
    try:
        file_path = await m.download()
        if not file_path:
            raise ContinuePropagation

        # Use local NSFW detection
        is_nsfw, confidence = await nsfw_detector.detect_nsfw(file_path)

        if is_nsfw:
            try:
                await m.delete()
            except Exception:
                pass

            await c.send_message(
                m.chat.id,
                f"🚨 **Anti-NSFW Alert!** 🚨\n\n"
                f"👤 {_user_markdown_link(m.from_user)}\n"
                f"📛 Type: {_content_type_label(m)}\n"
                f"⚠️ NSFW content detected & removed.\n"
                f"🔍 Confidence: {confidence:.2f}",
                parse_mode=PM.MARKDOWN
            )
            
    except ContinuePropagation:
        raise ContinuePropagation
    except Exception as e:
        print(f"Anti-NSFW error: {e}")
        traceback.print_exc()
    finally:
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
**Anti-NSFW (Local Detection)**
• /antinsfw → Enable/disable scanner (admin only)
• /free (reply) → Free user from scans (admin only)
• /unfree (reply) → Remove user from free list (admin only)

✅ **Features:**
- Local processing (no external APIs)
- No rate limits
- Privacy focused
- Fast detection
"""

# Initialize the detector when plugin loads
async def initialize_detector():
    await nsfw_detector.initialize()
    print("✅ NSFW Detector initialized")

# Run initialization
asyncio.create_task(initialize_detector())
