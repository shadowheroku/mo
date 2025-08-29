from random import choice
from traceback import format_exc
import os
import asyncio
import tempfile
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyrogram.enums import ChatAction
from pyrogram import filters
from pyrogram.errors import (
    PeerIdInvalid, ShortnameOccupyFailed, StickerEmojiInvalid,
    StickerPngDimensions, StickerPngNopng, StickerTgsNotgs,
    StickerVideoNowebm, UserIsBlocked, StickersetInvalid,
    FloodWait, UserNotParticipant, ChannelPrivate, ChatAdminRequired
)
from pyrogram.types import (
    InlineKeyboardButton as IKB,
    InlineKeyboardMarkup as IKM,
    Message,
    CallbackQuery
)

from Powers import LOGGER
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.sticker_help import *
from Powers.utils.string import encode_decode
from Powers.utils.web_helpers import get_file_size

# Constants
MAX_STICKERS_PER_PACK = 120
MAX_PACKS_PER_USER = 50
MAX_STICKER_SIZE = 261120  # 255KB in bytes
MAX_PHOTO_SIZE_MB = 10

# ================================================
#               STICKER INFORMATION
# ================================================

@Gojo.on_message(command(["stickerinfo", "stinfo"]))
async def give_st_info(c: Gojo, m: Message):
    """Get information about a sticker"""
    if not m.reply_to_message or not m.reply_to_message.sticker:
        return await m.reply_text("Reply to a sticker")
    
    st_in = m.reply_to_message.sticker
    st_type = "Normal"
    if st_in.is_animated:
        st_type = "Animated"
    elif st_in.is_video:
        st_type = "Video"
    
    st_to_gib = f"""📌 [Sticker]({m.reply_to_message.link}) info:
🆔 File ID: `{st_in.file_id}`
📛 File name: {st_in.file_name if st_in.file_name else 'N/A'}
🔐 Unique ID: `{st_in.file_unique_id}`
📅 Created: `{st_in.date}`
🎨 Type: `{st_type}`
😀 Emoji: {st_in.emoji if st_in.emoji else 'N/A'}
📦 Pack: {st_in.set_name if st_in.set_name else 'N/A'}
"""
    kb = IKM([[IKB("➕ Add to Pack", url=f"https://t.me/addstickers/{st_in.set_name}")]]) if st_in.set_name else None
    await m.reply_text(st_to_gib, reply_markup=kb)

@Gojo.on_message(command(["stickerid", "stid"]))
async def sticker_id_gib(c: Gojo, m: Message):
    """Get sticker ID"""
    if not m.reply_to_message or not m.reply_to_message.sticker:
        return await m.reply_text("Reply to a sticker")
    
    st_in = m.reply_to_message.sticker
    await m.reply_text(
        f"🆔 Sticker ID: `{st_in.file_id}`\n"
        f"🔐 Unique ID: `{st_in.file_unique_id}`"
    )

# ================================================
#               STICKER KANGING
# ================================================

@Gojo.on_message(command(["kang", "steal"]))
async def kang_sticker(c: Gojo, m: Message):
    """Kang a sticker into your pack with enhanced file handling"""
    # Validate input
    if not m.reply_to_message:
        return await m.reply_text("❌ Reply to a sticker/image/video to kang it.")

    # Check media type
    media_types = {
        "sticker": m.reply_to_message.sticker,
        "photo": m.reply_to_message.photo,
        "animation": m.reply_to_message.animation,
        "video": m.reply_to_message.video,
        "document": (
            m.reply_to_message.document and 
            m.reply_to_message.document.mime_type and 
            m.reply_to_message.document.mime_type.split("/")[0] in ["image", "video"]
        )
    }
    
    media_type = next((k for k, v in media_types.items() if v), None)
    if not media_type:
        return await m.reply_text("❌ Unsupported media type.")

    if not m.from_user:
        return await m.reply_text("⚠️ Anonymous admins can't kang stickers.")

    # Check if user started bot
    try:
        await c.send_chat_action(m.from_user.id, ChatAction.TYPING)
    except (PeerIdInvalid, UserIsBlocked):
        kb = IKM([[IKB("✨ Start Me", url=f"https://t.me/{c.me.username}")]])
        return await m.reply_text(
            "⚠️ Please start me in PM first!",
            reply_markup=kb
        )

    msg = await m.reply_text("⏳ Processing...")

    # Determine emoji
    args = m.text.split()
    if len(args) > 1:
        sticker_emoji = args[1].strip()
        # Validate emoji (at least one emoji character)
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"   # dingbats
            "\U000024C2-\U0001F251" 
            "]+", flags=re.UNICODE
        )
        
        if not emoji_pattern.match(sticker_emoji):
            sticker_emoji = "🤔"  # Default if invalid
    elif m.reply_to_message.sticker and m.reply_to_message.sticker.emoji:
        sticker_emoji = m.reply_to_message.sticker.emoji
    else:
        ran = ["🤣", "😁", "👍", "🔥", "😍", "😱", "🤖", "👀", "💀", "🫶", "🙌", "😎"]
        sticker_emoji = choice(ran)
    
    # Limit to 2 emojis max
    sticker_emoji = "".join(sticker_emoji.split())[:2]

    await msg.edit_text(f"🖌️ Creating sticker with {sticker_emoji} emoji...")

    # Process media
    path = None
    sticker = None
    
    try:
        is_video = media_type in ["animation", "video"] or (
            media_type == "document" and m.reply_to_message.document.mime_type.split("/")[0] == "video"
        )
        
        if is_video:
            # Create video sticker
            path = await create_video_sticker(c, m.reply_to_message)
            if path and os.path.exists(path) and os.path.getsize(path) > MAX_STICKER_SIZE:
                await msg.edit_text("❌ File too large for sticker.")
                return
        elif media_type in ["photo", "document"]:
            # Download and process image
            path = await download_media(m.reply_to_message)
            if not path or not os.path.exists(path):
                await msg.edit_text("❌ Failed to download media.")
                return
                
            # Check file size
            file_size = os.path.getsize(path)
            if file_size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
                await msg.edit_text("❌ File too large.")
                return
                
            # Resize to sticker dimensions
            path = await resize_file_to_sticker_size(path)
        elif media_type == "sticker":
            # Directly use the sticker
            sticker_file = await get_document_from_file_id(m.reply_to_message.sticker.file_id)
            sticker = await create_sticker(sticker_file, sticker_emoji)
        else:
            return await msg.edit_text("❌ Unsupported media type.")

        # For non-sticker media, create a sticker
        if path and os.path.exists(path):
            try:
                uploaded_file = await upload_document(c, path, m.chat.id)
                sticker = await create_sticker(uploaded_file, sticker_emoji)
            except Exception as upload_error:
                await msg.edit_text(f"❌ Failed to process media: {str(upload_error)}")
                return

    except ShortnameOccupyFailed:
        return await msg.edit_text("❌ Change your Telegram username and try again.")
    except Exception as e:
        await msg.edit_text(f"⚠️ Error processing media: {str(e)}")
        LOGGER.error(f"Kang error: {format_exc()}")
        return
    finally:
        # Clean up temporary file
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    if not sticker:
        return await msg.edit_text("❌ Failed to create sticker.")

    # Manage sticker packs
    packnum = 0
    packname_found = False

    try:
        while not packname_found and packnum < MAX_PACKS_PER_USER:
            packname = f"CE{m.from_user.id}{packnum}_by_{c.me.username}"
            kangpack = (
                f"{('@' + m.from_user.username) if m.from_user.username else m.from_user.first_name[:10]}"
                f" {f'Vol {packnum+1}' if packnum > 0 else ''} by @{c.me.username}"
            )

            try:
                sticker_set = await c.get_sticker_set(packname)
            except StickersetInvalid:
                sticker_set = None

            if not sticker_set:
                # Create new sticker set
                try:
                    sticker_set = await c.create_new_sticker_set(
                        user_id=m.from_user.id,
                        title=kangpack,
                        short_name=packname,
                        stickers=[sticker],
                    )
                    packname_found = True
                except StickerEmojiInvalid:
                    return await msg.edit_text("❌ Invalid emoji provided.")
                except Exception as e:
                    await msg.edit_text(f"❌ Failed to create sticker set: {str(e)}")
                    return
            else:
                # Check if sticker set is full
                if len(sticker_set.stickers) >= MAX_STICKERS_PER_PACK:
                    packnum += 1
                    continue
                
                # Add to existing set
                try:
                    await c.add_sticker_to_set(
                        user_id=m.from_user.id,
                        name=packname,
                        sticker=sticker
                    )
                    packname_found = True
                except StickerEmojiInvalid:
                    return await msg.edit_text("❌ Invalid emoji provided.")
                except StickersetInvalid:
                    # Sticker set might have been deleted, try creating a new one
                    packnum += 1
                    continue

        if not packname_found:
            return await msg.edit_text("❌ You've reached the 50 pack limit.")

        kb = IKM([[IKB("➕ Add Pack", url=f"t.me/addstickers/{packname}")]])
        await msg.delete()
        success_msg = await m.reply_text(
            f"✅ Sticker added!\n📦 Pack: `{kangpack}`\n😀 Emoji: {sticker_emoji}",
            reply_markup=kb
        )
        
        # Delete success message after 30 seconds
        await asyncio.sleep(30)
        await success_msg.delete()

    except (PeerIdInvalid, UserIsBlocked):
        kb = IKM([[IKB("✨ Start Me", url=f"t.me/{c.me.username}")]])
        await msg.delete()
        await m.reply_text("⚠️ Please start me in PM first!", reply_markup=kb)
    except StickerPngNopng:
        await msg.edit_text("❌ Stickers must be PNG files.")
    except StickerPngDimensions:
        await msg.edit_text("❌ Invalid PNG dimensions.")
    except StickerTgsNotgs:
        await msg.edit_text("❌ Requires TGS file.")
    except StickerVideoNowebm:
        await msg.edit_text("❌ Requires WEBM file.")
    except Exception as e:
        await msg.edit_text(f"⚠️ Unexpected error: {str(e)}")
        LOGGER.error(f"Unexpected kang error: {format_exc()}")

async def download_media(message: Message) -> str:
    """Download media with proper error handling"""
    try:
        # Create downloads directory if it doesn't exist
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        # Generate a unique filename
        file_ext = ".jpg" if message.photo else ".mp4" if message.video else ".webm" if message.animation else ""
        file_name = f"{downloads_dir}/{message.id}_{message.from_user.id if message.from_user else 'unknown'}{file_ext}"
        
        # Download the file
        path = await message.download(file_name=file_name)
        return path
    except Exception as e:
        LOGGER.error(f"Download error: {str(e)}")
        return None

async def create_video_sticker(client: Gojo, message: Message) -> str:
    """Create video sticker from media with proper error handling"""
    try:
        # Download the video
        video_path = await download_media(message)
        if not video_path or not os.path.exists(video_path):
            return None
            
        # Process video to sticker format
        sticker_path = await process_video_to_webm(video_path)
        
        # Clean up original video
        if os.path.exists(video_path):
            os.remove(video_path)
            
        return sticker_path
    except Exception as e:
        LOGGER.error(f"Video sticker creation error: {str(e)}")
        return None

async def process_video_to_webm(video_path: str) -> str:
    """
    Process video to WEBM format for stickers
    """
    try:
        # Placeholder implementation - replace with your actual video processing
        import subprocess
        webm_path = video_path + ".webm"
        
        # Example FFmpeg command to convert to WEBM
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", "scale=512:512:force_original_aspect_ratio=decrease,format=rgba,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000",
            "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "128K",
            "-an", "-t", "3", "-y", webm_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            LOGGER.error(f"FFmpeg error: {stderr.decode()}")
            return None
            
        return webm_path
    except Exception as e:
        LOGGER.error(f"Video processing error: {str(e)}")
        return None

# ================================================
#               STICKER REMOVAL
# ================================================

@Gojo.on_message(command(["rmsticker", "rmst", "removesticker"]))
async def remove_from_my_pack(c: Gojo, m: Message):
    """Remove a sticker from user's pack"""
    if not m.reply_to_message or not m.reply_to_message.sticker:
        await m.reply_text("Please reply to a sticker to remove it from your pack")
        return

    sticker = m.reply_to_message.sticker
    
    try:
        sticker_set = await c.get_sticker_set(sticker.set_name)
    except StickersetInvalid:
        await m.reply_text("This sticker is not part of your pack")
        return

    # Check if user owns this sticker set
    if not sticker_set.set_name.startswith(f"CE{m.from_user.id}"):
        await m.reply_text("This sticker is not part of your pack")
        return

    try:
        await c.delete_sticker_from_set(sticker.file_id)
        await m.reply_text(f"Deleted [this]({m.reply_to_message.link}) from pack: {sticker_set.set.title}")
    except Exception as e:
        await m.reply_text(f"Error\n{e}\nReport it using /bug")
        LOGGER.error(f"Remove sticker error: {str(e)}\n{format_exc()}")

# ================================================
#               MEME GENERATION
# ================================================

# Font configuration
FONTS = ["arialbd.ttf", "arial.ttf"]  # Try bold, then regular
DEFAULT_FONT_SIZE = 42

@Gojo.on_message(command(["mmf", "mmfb", "mmfw"]))
async def memify_it(c: Gojo, m: Message):
    """
    Memify images/stickers with text overlay
    Supports black (/mmfb) and white (/mmfw) text
    """
    try:
        # Must reply to media
        if not m.reply_to_message:
            return await m.reply_text("❌ Reply to an image/sticker with some text.")

        rep_to = m.reply_to_message

        # Supported media: photo, static sticker, or image document
        valid_media = (
            (rep_to.photo) or
            (rep_to.sticker and not rep_to.sticker.is_animated and not rep_to.sticker.is_video) or
            (rep_to.document and rep_to.document.mime_type and rep_to.document.mime_type.startswith("image/"))
        )
        if not valid_media:
            return await m.reply_text("❌ Only static images & stickers are supported.")

        # Text to put on meme
        if len(m.command) == 1:
            return await m.reply_text("❌ Give me some text!\nExample: `/mmfb Hello World`")

        meme_text = m.text.split(None, 1)[1].strip()
        if not meme_text:
            return await m.reply_text("❌ Meme text cannot be empty.")

        if len(meme_text) > 200:
            return await m.reply_text("❌ Text too long! (max 200 chars)")

        # Determine color
        fill_color = "black" if m.command[0].endswith("b") else "white"

        # Check if text contains semicolon for top/bottom text
        if ";" in meme_text:
            upper_text, lower_text = meme_text.split(";", 1)
        else:
            upper_text = meme_text
            lower_text = ""

        # Processing notice
        status = await m.reply_text("🖌️ Memifying...")

        # Temp workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, f"in_{m.id}")
            await rep_to.download(input_path)

            if not os.path.exists(input_path) or os.path.getsize(input_path) == 0:
                return await status.edit_text("❌ Failed to download media.")

            output_paths = await draw_meme(input_path, upper_text, lower_text, bool(rep_to.sticker), fill_color, tmpdir)

            if not output_paths:
                return await status.edit_text("❌ Failed to generate meme.")

            await status.delete()

            # Send as photo
            photo_msg = await m.reply_photo(
                output_paths[0],
                caption=f"🖼️ Meme: `{meme_text}`",
                reply_markup=IKM(
                    [[IKB("🔥 Channel", url="https://t.me/me_and_ghost")]]
                )
            )

            # Delay → send as sticker
            await asyncio.sleep(1)
            sticker_msg = await m.reply_sticker(output_paths[1])

            # Cleanup (optional auto-delete after 5 mins)
            await asyncio.sleep(300)
            try:
                await photo_msg.delete()
                await sticker_msg.delete()
            except:
                pass

    except Exception as e:
        await m.reply_text(f"❌ Error: {str(e)}")
        LOGGER.error(f"Memify error: {str(e)}\n{format_exc()}")

async def draw_meme(input_path: str, upper_text: str, lower_text: str, is_sticker: bool, fill_color: str, tmpdir: str) -> list:
    try:
        with Image.open(input_path) as img:
            # Ensure RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize
            max_size = (512, 512) if is_sticker else (1024, 1024)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Prepare drawing
            draw = ImageDraw.Draw(img)
            w, h = img.size
            
            # Load font
            font_size = max(15, min(60, h // 12))
            font = None
            for f in FONTS:
                try:
                    font = ImageFont.truetype(f, font_size)
                    break
                except:
                    continue
            if not font:
                font = ImageFont.load_default()

            # Draw upper text
            if upper_text:
                await draw_text_with_outline(draw, upper_text, font, w, h, "top", fill_color)
            
            # Draw lower text
            if lower_text:
                await draw_text_with_outline(draw, lower_text, font, w, h, "bottom", fill_color)

            # Save outputs
            photo_out = os.path.join(tmpdir, "out_photo.jpg")
            sticker_out = os.path.join(tmpdir, "out_sticker.webp")

            img.save(photo_out, "JPEG", quality=95)

            if is_sticker:
                s_img = ImageOps.fit(img, (512, 512), method=Image.Resampling.LANCZOS)
                s_img.save(sticker_out, "WEBP", quality=95)
            else:
                img.save(sticker_out, "WEBP", quality=95)

            return [photo_out, sticker_out]

    except Exception as e:
        LOGGER.error(f"Draw meme error: {str(e)}\n{format_exc()}")
        return []

async def draw_text_with_outline(draw, text, font, width, height, position, fill_color):
    """Draw text with outline at specified position"""
    # Wrap text
    max_chars = int(width / (font.size * 0.6))
    wrapped = textwrap.wrap(text, width=max(max_chars, 10))
    
    # Calculate position
    line_h = font.size * 1.2
    total_h = len(wrapped) * line_h
    
    if position == "top":
        y = 10
    else:  # bottom
        y = height - total_h - 10
    
    # Outline color (opposite of fill color)
    outline_color = "white" if fill_color == "black" else "black"
    
    # Draw each line
    for line in wrapped:
        # Get text dimensions
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) / 2

        # Draw outline (shadow effect)
        for dx in [-2, 2]:
            for dy in [-2, 2]:
                draw.text((x + dx, y + dy), line, font=font, fill=outline_color)

        # Draw main text
        draw.text((x, y), line, font=font, fill=fill_color)
        y += line_h

# ================================================
#               STICKER CONVERSION
# ================================================

@Gojo.on_message(command(["getsticker", "getst"]))
async def get_sticker_from_file(c: Gojo, m: Message):
    Caption = f"Converted by:\n@{c.me.username}"
    repl = m.reply_to_message
    if not repl:
        await m.reply_text("Reply to a sticker or file")
        return
    if (
            not repl.animation
            and not repl.video
            and not repl.sticker
            and not repl.photo
            and (
            not repl.document
            or (repl.document.mime_type and repl.document.mime_type.split("/")[0] not in ["image", "video"])
    )
    ):
        await m.reply_text("I only support conversion of plain stickers, images, videos and animation for now")
        return
    to_vid = bool(
        repl.animation
        or repl.video
        or (repl.document and repl.document.mime_type and repl.document.mime_type.split("/")[0] == "video")
    )
    x = await m.reply_text("Converting...")
    if repl.sticker:
        if repl.sticker.is_animated:
            upp = await repl.download()
            up = await tgs_to_gif(upp, True)
            await x.delete()
            await m.reply_animation(up, caption=Caption)
        elif repl.sticker.is_video:
            upp = await repl.download()
            up = await webm_to_gif(upp)
            await x.delete()
            await m.reply_animation(up, caption=Caption)
        else:
            upp = await repl.download()
            up = toimage(upp, is_direc=True)
            await x.delete()
            await m.reply_document(up, caption=Caption)
        if os.path.exists(up):
            os.remove(up)
        return
    elif repl.photo:
        upp = await repl.download()
        up = tosticker(upp, is_direc=True)
        await x.delete()
        await m.reply_sticker(up)
        if os.path.exists(up):
            os.remove(up)
        return

    elif to_vid:
        up = await Vsticker(c, repl)
        await x.delete()
        await m.reply_sticker(up)
        if os.path.exists(up):
            os.remove(up)
        return

# ================================================
#               STICKER PACK MANAGEMENT
# ================================================

@Gojo.on_message(command(["getmypacks", "mypacks", "mysets", "stickerset", "stset"]))
async def get_my_sticker_sets(c: Gojo, m: Message):
    """Get all sticker packs created by the user using the kang system"""
    if not m.from_user:
        return await m.reply_text("❌ Cannot identify user. Please try again.")
    
    to_del = await m.reply_text("⏳ Please wait while I fetch all the sticker sets I have created for you...")
    
    try:
        txt, kb = await get_all_sticker_packs(c, m.from_user.id, c.me.username)
        
        await to_del.delete()
        
        if not txt:
            no_packs_msg = await m.reply_text(
                "📭 Looks like you haven't made any stickers using me yet!\n\n"
                "Use /kang command to create your first sticker pack."
            )
            await asyncio.sleep(10)
            await no_packs_msg.delete()
            return
            
        # Split long messages (Telegram has 4096 character limit)
        if len(txt) > 4000:
            parts = [txt[i:i+4000] for i in range(0, len(txt), 4000)]
            for part in parts:
                await m.reply_text(part, reply_markup=kb if part == parts[-1] else None)
                await asyncio.sleep(0.5)
        else:
            await m.reply_text(txt, reply_markup=kb)
            
    except Exception as e:
        await to_del.delete()
        error_msg = await m.reply_text(f"❌ Error fetching sticker packs: {str(e)}")
        LOGGER.error(f"Sticker pack error: {str(e)}\n{format_exc()}")
        await asyncio.sleep(10)
        await error_msg.delete()

async def get_all_sticker_packs(client: Gojo, user_id: int, bot_username: str):
    """Get all sticker packs created for a user using the kang naming convention"""
    packs = []
    keyboard = []
    pack_count = 0
    
    try:
        # Search for packs with the naming pattern used in kang
        packnum = 0
        found_packs = []
        
        while packnum < MAX_PACKS_PER_USER:
            packname = f"CE{user_id}{packnum}_by_{bot_username}"
            
            try:
                sticker_set = await client.get_sticker_set(packname)
                found_packs.append((packname, sticker_set))
            except StickersetInvalid:
                # This pack doesn't exist, move to next
                pass
            except FloodWait as e:
                raise Exception(f"Please wait {e.value} seconds before trying again.")
            except Exception as e:
                LOGGER.error(f"Error checking pack {packname}: {str(e)}")
            
            packnum += 1
        
        # Process found packs
        for packname, sticker_set in found_packs:
            if pack_count >= MAX_PACKS_PER_USER:
                break
                
            pack_title = sticker_set.set.title
            stickers_count = len(sticker_set.stickers)
            is_animated = sticker_set.is_animated
            is_video = sticker_set.is_video
            
            # Format pack info
            pack_type = ""
            if is_video:
                pack_type = "🎥 Video"
            elif is_animated:
                pack_type = "✨ Animated"
            else:
                pack_type = "🖼️ Static"
            
            # Check if pack is full
            is_full = stickers_count >= MAX_STICKERS_PER_PACK
            full_status = " ✅" if not is_full else " ❌ (FULL)"
            
            pack_info = f"• **{pack_title}**\n  └ {pack_type} | {stickers_count}/{MAX_STICKERS_PER_PACK} stickers{full_status}\n  └ `{packname}`\n\n"
            packs.append(pack_info)
            pack_count += 1
            
            # Add inline button for quick access
            if len(keyboard) < 3:
                keyboard.append([
                    IKB(
                        f"Add {pack_title[:12]}...", 
                        url=f"t.me/addstickers/{packname}"
                    )
                ])
                    
    except (PeerIdInvalid, UserNotParticipant, ChannelPrivate, ChatAdminRequired):
        return None, None
    except FloodWait as e:
        LOGGER.warning(f"Flood wait: {e.value} seconds")
        raise Exception(f"Please wait {e.value} seconds before trying again.")
    except Exception as e:
        LOGGER.error(f"Error getting sticker sets: {str(e)}")
        return None, None
    
    if not packs:
        return None, None
    
    # Format final message
    total_packs = len(packs)
    header = f"📦 **Your Sticker Packs** ({total_packs})\n\n"
    footer = f"\n✨ **Total:** {total_packs} packs"
    
    if total_packs >= MAX_PACKS_PER_USER:
        footer += f"\n⚠️ Showing first {MAX_PACKS_PER_USER} packs only"
    
    message = header + "".join(packs) + footer
    
    # Add a "View All" button if there are many packs
    if total_packs > 3:
        keyboard.append([
            IKB(
                "📋 View All Packs", 
                callback_data=f"view_all_packs_{user_id}"
            )
        ])
    
    # Add kang button for convenience
    keyboard.append([
        IKB(
            "🔄 Create New Pack", 
            switch_inline_query_current_chat="kang"
        )
    ])
    
    reply_markup = IKM(keyboard) if keyboard else None
    
    return message, reply_markup

# Callback handler for viewing all packs
@Gojo.on_callback_query(filters.regex(r"^view_all_packs_"))
async def view_all_packs_callback(c: Gojo, q: CallbackQuery):
    """Handle callback for viewing all packs"""
    user_id = int(q.data.split("_")[-1])
    
    # Verify the callback is from the same user
    if q.from_user.id != user_id:
        await q.answer("❌ This is not for you!", show_alert=True)
        return
    
    await q.answer("⏳ Loading all packs...")
    
    # Edit message to show all packs
    txt, kb = await get_all_sticker_packs(c, user_id, c.me.username)
    
    if not txt:
        await q.message.edit_text("❌ No sticker packs found.")
        return
    
    try:
        await q.message.edit_text(txt, reply_markup=kb)
    except Exception as e:
        LOGGER.error(f"Error editing message: {str(e)}")
        await q.message.reply_text("❌ Error displaying packs. Please try again.")

# Additional command to refresh packs
@Gojo.on_message(command(["refreshpacks", "updatepacks"]))
async def refresh_sticker_packs(c: Gojo, m: Message):
    """Refresh and update sticker packs list"""
    if not m.from_user:
        return await m.reply_text("❌ Cannot identify user.")
    
    progress_msg = await m.reply_text("🔄 Refreshing your sticker packs...")
    
    try:
        # Get updated packs
        txt, kb = await get_all_sticker_packs(c, m.from_user.id, c.me.username)
        
        await progress_msg.delete()
        
        if not txt:
            await m.reply_text("❌ No sticker packs found after refresh.")
            return
        
        await m.reply_text("✅ Packs refreshed!\n\n" + txt, reply_markup=kb)
        
    except Exception as e:
        await progress_msg.delete()
        error_msg = await m.reply_text(f"❌ Error refreshing packs: {str(e)}")
        await asyncio.sleep(10)
        await error_msg.delete()

# Helper function to check if a user has any packs
async def user_has_packs(client: Gojo, user_id: int, bot_username: str) -> bool:
    """Check if a user has any sticker packs"""
    try:
        # Check just the first pack to see if user has any
        packname = f"CE{user_id}0_by_{bot_username}"
        await client.get_sticker_set(packname)
        return True
    except StickersetInvalid:
        return False
    except Exception:
        return False

# ================================================
#               QUOTE GENERATION
# ================================================

@Gojo.on_message(command(["q", "ss"]))
async def quote_the_msg(_, m: Message):
    if not m.reply_to_message:
        await m.reply_text("Reply to a message to quote it")
        return

    to_edit = await m.reply_text("Generating quote...")

    if len(m.command) > 1 and m.command[1].lower() == "r":
        reply_msg = m.reply_to_message.reply_to_message
        if not reply_msg or not reply_msg.text:
            reply_message = {}
        else:
            to_edit = await to_edit.edit_text("Generating quote with reply to the message...")
            replied_name = reply_msg.from_user.first_name
            if reply_msg.from_user.last_name:
                replied_name += f" {reply_msg.from_user.last_name}"

            reply_message = {
                "chatId": reply_msg.from_user.id,
                "entities": get_msg_entities(reply_msg),
                "name": replied_name,
                "text": reply_msg.text,
            }
    else:
        reply_message = {}

    name = m.reply_to_message.from_user.first_name
    if m.reply_to_message.from_user.last_name:
        name += f" {m.reply_to_message.from_user.last_name}"

    emoji_status = None
    if m.reply_to_message.from_user.emoji_status:
        emoji_status = str(m.reply_to_message.from_user.emoji_status.custom_emoji_id)

    msg_data = [
        {
            "entities": get_msg_entities(m.reply_to_message),
            "avatar": True,
            "from": {
                "id": m.reply_to_message.from_user.id,
                "name": name,
                "emoji_status": emoji_status,
            },
            "text": m.reply_to_message.text,
            "replyMessage": reply_message,
        }
    ]
    status, path = quotify(msg_data)

    if not status:
        await to_edit.edit_text(path)
        return

    await m.reply_sticker(path)
    await to_edit.delete()
    os.remove(path)




@Gojo.on_callback_query(filters.regex(r"^stickers_.*"))
async def sticker_callbacks(c: Gojo, q: CallbackQuery):
    data = q.data.split("_")
    decoded = await encode_decode(data[-1], "decode")
    user = int(decoded.split("_")[-1])
    if q.from_user.id != user:
        await q.answer("This is not for you")
    else:
        offset = int(decoded.split("_")[0])

        txt, kb = await get_all_sticker_packs(c, q.from_user.id, offset)
        if not txt:
            await q.answer("No sticker pack found....")
        else:
            await q.answer("Showing your sticker set")
            await q.edit_message_text(txt, reply_markup=kb)

    return


__PLUGIN__ = "sᴛɪᴄᴋᴇʀ"
__alt_name__ = [
    "sticker",
    "kang"
]

__HELP__ = """
**ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs:**
• /kang (/steal) <emoji>: ʀᴇᴘʟʏ ᴛᴏ ᴀ sᴛɪᴄᴋᴇʀ ᴏʀ ᴀɴʏ sᴜᴘᴘᴏʀᴛᴇᴅ ᴍᴇᴅɪᴀ
• /stickerinfo (/stinfo) : ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ sᴛɪᴄᴋᴇʀ ᴛᴏ ɢᴇᴛ ɪᴛ's ɪɴғᴏ
• /getsticker (/getst) : ɢᴇᴛ sᴛɪᴄᴋᴇʀ ᴀs ᴘʜᴏᴛᴏ, ɢɪғ ᴏʀ ᴠɪᴄᴇ ᴠᴇʀsᴀ.
• /stickerid (/stid) : ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ sᴛɪᴄᴋᴇʀ ᴛᴏ ɢᴇᴛ ɪᴛ's ɪᴅ
• /mypacks : ɢᴇᴛ ᴀʟʟ ᴏꜰ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ sᴛɪᴄᴋᴇʀ ᴘᴀᴄᴋs ʏᴏᴜ ʜᴀᴠᴇ ᴍᴀᴅᴇ ᴠɪᴀ ᴍᴇ.
• /q(/ss) <ʀᴇᴘʟʏ ᴛᴏ ᴍᴇssᴀɢᴇ> : ᴡɪʟʟ ǫᴜᴏᴛᴇ ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ
• /q(/ss) r <ʀᴇᴘʟʏ ᴛᴏ ᴍᴇssᴀɢᴇ> : ᴡɪʟʟ ǫᴜᴏᴛᴇ ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ᴀɴᴅ ᴛʜᴇ ᴍᴇssᴀɢᴇ ɪᴛ ᴡᴀs ʀᴇᴘʟɪᴇᴅ ᴛᴏ.
• /mmf <ʏᴏᴜʀ ᴛᴇxᴛ>: ʀᴇᴘʟʏ ᴛᴏ ᴀ ɴᴏʀᴍᴀʟ sᴛɪᴄᴋᴇʀ ᴏʀ ᴀ ᴘʜᴏᴛᴏ ᴏʀ ᴠɪᴅᴇᴏ ғɪʟᴇ ᴛᴏ ᴍᴇᴍɪꜰʏ ɪᴛ. ɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʀɪɢʜᴛ ᴛᴇxᴛ ᴀᴛ ʙᴏᴛᴛᴏᴍ ᴜsᴇ `;right ʏᴏᴜʀ ᴍᴇssᴀɢᴇ`
    ■ ғᴏʀ ᴇ.ɢ. 
    ○ /mmfb <text>: ᴛᴏ ꜰɪʟʟ ᴛᴇxᴛ ᴡɪᴛʜ ʙʟᴀᴄᴋ ᴄᴏʟᴏᴜʀ
    ○ /mmfw or /mmf <text>: ᴛᴏ ꜰɪʟʟ ɪᴛ ᴡɪᴛʜ ᴡʜɪᴛᴇ ᴄᴏʟᴏᴜʀ

**ɴᴏᴛᴇ**
mmf ᴀɴᴅ getsticker ᴏɴʟʏ sᴜᴘᴘᴏʀᴛ ᴘʜᴏᴛᴏ ᴀɴᴅ ɴᴏʀᴍᴀʟ sᴛɪᴄᴋᴇʀs ғᴏʀ ɴᴏᴡ.
"""

