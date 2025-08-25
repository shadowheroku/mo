from random import choice
from traceback import format_exc
import os
from pyrogram.enums import ChatAction
from pyrogram import filters
from pyrogram.errors import (
    PeerIdInvalid, ShortnameOccupyFailed, StickerEmojiInvalid,
    StickerPngDimensions, StickerPngNopng, StickerTgsNotgs,
    StickerVideoNowebm, UserIsBlocked, StickersetInvalid
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
📛 File name: {st_in.file_name}
🔐 Unique ID: `{st_in.file_unique_id}`
📅 Created: `{st_in.date}`
🎨 Type: `{st_type}`
😀 Emoji: {st_in.emoji}
📦 Pack: {st_in.set_name}
"""
    kb = IKM([[IKB("➕ Add to Pack", url=f"https://t.me/addstickers/{st_in.set_name}")]])
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

import os
import asyncio
from random import choice
from traceback import format_exc
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatAction
from pyrogram.errors import (
    PeerIdInvalid, UserIsBlocked, StickersetInvalid, StickerEmojiInvalid,
    StickerPngNopng, StickerPngDimensions, StickerTgsNotgs, StickerVideoNowebm,
    ShortnameOccupyFailed
)

# Constants
MAX_STICKERS_PER_PACK = 120
MAX_PACKS_PER_USER = 50
MAX_STICKER_SIZE = 261120  # 255KB in bytes
MAX_PHOTO_SIZE_MB = 10

@Gojo.on_message(command(["kang", "steal"]))
async def kang_sticker(c: Client, m: Message):
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
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✨ Start Me", url=f"https://t.me/{c.me.username}")]])
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
        emoji_ranges = [
            "\U0001F600-\U0001F64F",  # emoticons
            "\U0001F300-\U0001F5FF",  # symbols & pictographs
            "\U0001F680-\U0001F6FF",  # transport & map symbols
            "\U0001F1E0-\U0001F1FF",  # flags (iOS)
            "\U00002702-\U000027B0",   # dingbats
            "\U000024C2-\U0001F251", 
        ]
        
        if not any(char in sticker_emoji for char in emoji_ranges):
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
                sticker_set = await get_sticker_set_by_name(c, packname)
            except StickersetInvalid:
                sticker_set = None

            if not sticker_set:
                # Create new sticker set
                try:
                    sticker_set = await create_sticker_set(
                        client=c,
                        owner=m.from_user.id,
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
                if sticker_set.set.count >= MAX_STICKERS_PER_PACK:
                    packnum += 1
                    continue
                
                # Add to existing set
                try:
                    await add_sticker_to_set(c, sticker_set, sticker)
                    packname_found = True
                except StickerEmojiInvalid:
                    return await msg.edit_text("❌ Invalid emoji provided.")
                except StickersetInvalid:
                    # Sticker set might have been deleted, try creating a new one
                    packnum += 1
                    continue

        if not packname_found:
            return await msg.edit_text("❌ You've reached the 50 pack limit.")

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Pack", url=f"t.me/addstickers/{packname}")]])
        await msg.delete()
        success_msg = await m.reply_text(
            f"✅ Sticker added!\n📦 Pack: `{kangpack}`\n😀 Emoji: {sticker_emoji}",
            reply_markup=kb
        )
        
        # Delete success message after 30 seconds
        await asyncio.sleep(30)
        await success_msg.delete()

    except (PeerIdInvalid, UserIsBlocked):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✨ Start Me", url=f"t.me/{c.me.username}")]])
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


async def create_video_sticker(client: Client, message: Message) -> str:
    """Create video sticker from media with proper error handling"""
    try:
        # Download the video
        video_path = await download_media(message)
        if not video_path or not os.path.exists(video_path):
            return None
            
        # Process video to sticker format (implementation depends on your Vsticker function)
        # This is a placeholder - implement your actual video processing logic here
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
    Implement your actual video processing logic here
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


@Gojo.on_message(command(["rmsticker", "removesticker"]))
async def remove_sticker_from_pack(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.sticker:
        return await m.reply_text(
            "Reply to a sticker to remove it from the pack."
        )

    sticker = m.reply_to_message.sticker

    to_modify = await m.reply_text("Removing the sticker from your pack")
    sticker_set = await get_sticker_set_by_name(c, sticker.set_name)

    if not sticker_set:
        await to_modify.edit_text("This sticker is not part for your pack")
        return

    try:
        await remove_sticker(c, sticker.file_id)
        await to_modify.edit_text(
            f"Successfully removed [sticker]({m.reply_to_message.link}) from {sticker_set.set.title}")
    except Exception as e:
        await to_modify.delete()
        await m.reply_text(f"Failed to remove sticker due to:\n{e}\nPlease report this bug using `/bug`")
        LOGGER.error(e)
        LOGGER.error(format_exc())
    return


@Gojo.on_message(command(["mmfb", "mmfw", "mmf"]))
async def memify_it(c: Gojo, m: Message):
    if not m.reply_to_message:
        await m.reply_text("Invalid type.")
        return
    rep_to = m.reply_to_message
    if not (rep_to.sticker or rep_to.photo or (rep_to.document and "image" in rep_to.document.mime_type.split("/"))):
        await m.reply_text("I only support memifying of normal sticker and photos for now")
        return
    if rep_to.sticker and (rep_to.sticker.is_animated or rep_to.sticker.is_video):
        await m.reply_text("I only support memifying of normal sticker and photos for now")
        return
    kb = IKM(
        [
            [
                IKB("You might like", url="https://t.me/me_and_ghost")
            ]
        ]
    )
    if len(m.command) == 1:
        await m.reply_text("Give me something to write")
        return
    filll = m.command[0][-1]
    fiil = "black" if filll == "b" else "white"
    x = await m.reply_text("Memifying...")
    meme = m.text.split(None, 1)[1].strip()
    name = f"@memesofdank_{m.id}.png"
    path = await rep_to.download(name)
    is_sticker = bool(rep_to.sticker)
    output = await draw_meme(path, meme, is_sticker, fiil)
    await x.delete()
    xNx = await m.reply_photo(output[0], reply_markup=kb)
    await xNx.reply_sticker(output[1], reply_markup=kb)
    try:
        os.remove(output[0])
        os.remove(output[1])
    except Exception as e:
        LOGGER.error(e)
        LOGGER.error(format_exc())
    return


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
            or repl.document.mime_type.split("/")[0] not in ["image", "video"]
    )
    ):
        await m.reply_text("I only support conversion of plain stickers, images, videos and animation for now")
        return
    to_vid = bool(
        repl.animation
        or repl.video
        or (repl.document and repl.document.mime_type.split("/")[0] == "video")
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
        os.remove(up)
        return
    elif repl.photo:
        upp = await repl.download()
        up = tosticker(upp, is_direc=True)
        await x.delete()
        await m.reply_sticker(up)
        os.remove(up)
        return

    elif to_vid:
        up = await Vsticker(c, repl)
        await x.delete()
        await m.reply_sticker(up)
        os.remove(up)
        return


@Gojo.on_message(command(["rmsticker", "rmst", "removesticker"]))
async def remove_from_MY_pack(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.sticker:
        await m.reply_text("Please reply to a sticker to remove it from your pack")
        return

    sticker = m.reply_to_message.sticker
    sticker_set = await get_sticker_set_by_name(c, sticker.set_name)

    if not sticker_set:
        await m.reply_text("This sticker is not part of your pack")
        return

    try:
        await remove_sticker(c, sticker.file_id)
        await m.reply_text(f"Deleted [this]({m.reply_to_message.link}) from pack: {sticker_set.et.title}")
        return
    except Exception as e:
        await m.reply_text(f"Error\n{e}\nReport it using /bug")
        LOGGER.error(e)
        LOGGER.error(format_exc(e))
        return


@Gojo.on_message(command(["getmypacks", "mypacks", "mysets", "stickerset", "stset"]))
async def get_my_sticker_sets(c: Gojo, m: Message):
    to_del = await m.reply_text("Please wait while I fetch all the sticker set I have created for you.")

    txt, kb = await get_all_sticker_packs(c, m.from_user.id)

    await to_del.delete()
    if not txt:
        await m.reply_text("Looks like you haven't made any sticker using me...")
        return
    await m.reply_text(txt, reply_markup=kb)


@Gojo.on_message(command(["q", "ss"]))
async def quote_the_msg(_, m: Message):
    if not m.reply_to_message:
        await m.reply_text("Reply to a message to quote it")
        return

    to_edit = await m.reply_text("Genrating quote...")

    if len(m.command) > 1 and m.command[1].lower() == "r":
        reply_msg = m.reply_to_message.reply_to_message
        if not reply_msg or not reply_msg.text:
            reply_message = {}
        else:
            to_edit = await to_edit.edit_text("Genrating quote with reply to the message...")
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


__PLUGIN__ = "sticker"
__alt_name__ = [
    "sticker",
    "kang"
]
__HELP__ = """
**User Commands:**
• /kang (/steal) <emoji>: Reply to a sticker or any supported media
• /stickerinfo (/stinfo) : Reply to any sticker to get it's info
• /getsticker (/getst) : Get sticker as photo, gif or vice versa.
• /stickerid (/stid) : Reply to any sticker to get it's id
• /mypacks : Get all of your current sticker pack you have made via me.
• /q(/ss) <reply to message> : Will quote the replied message
• /q(/ss) r <reply to message> : Will quote the replied message and message it was replied to.
• /mmf <your text>: Reply to a normal sticker or a photo or video file to memify it. If you want to right text at bottom use `;right your message`
    ■ For e.g. 
    ○ /mmfb <text>: To fill text with black colour
    ○ /mmfw or /mmf <text>: To fill it with white colour

**Note**
mmf and getsticker only support photo and normal stickers for now.

"""
