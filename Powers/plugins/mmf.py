import os
import textwrap
import subprocess
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Global thread pool for I/O-bound operations
io_executor = ThreadPoolExecutor(max_workers=4)
# Global process pool for CPU-bound operations
cpu_executor = ProcessPoolExecutor(max_workers=2)

@Gojo.on_message(filters.command("mmf"))
async def mmf(c: Gojo, m: Message):
    chat_id = m.chat.id
    reply_message = m.reply_to_message

    if not reply_message or (not reply_message.photo and not reply_message.document and not reply_message.sticker):
        await m.reply_text("**Please reply to an image or sticker to memify it.**")
        return

    if len(m.text.split()) < 2:
        await m.reply_text("**Give me text after /mmf to memify.**\nExample: `/mmf Hello;World`")
        return

    msg = await m.reply_text("**Memifying this image! ✊🏻**")
    text = m.text.split(None, 1)[1]

    try:
        file = await c.download_media(reply_message)

        # Detect type
        is_animated = False
        is_video_sticker = False

        if reply_message.sticker:
            is_animated = reply_message.sticker.is_animated
            if file.endswith(".webm"):
                is_video_sticker = True
                is_animated = False

        if is_video_sticker:
            meme = await drawTextVideoSticker(file, text)
            await c.send_sticker(chat_id, sticker=meme)

        elif is_animated:
            meme = await drawTextAnimated(file, text)
            await c.send_sticker(chat_id, sticker=meme)

        else:
            meme = await drawText(file, text)
            if reply_message.sticker:
                await c.send_sticker(chat_id, sticker=meme)
            else:
                await c.send_document(chat_id, document=meme)

        await msg.delete()
        # Clean up files asynchronously
        asyncio.create_task(cleanup_files(file, meme))

    except Exception as e:
        await msg.edit_text(f"**Error: {str(e)}**")
        asyncio.create_task(cleanup_files(file, meme if 'meme' in locals() else None))


async def cleanup_files(*files):
    """Clean up files asynchronously"""
    for file in files:
        if file and os.path.exists(file):
            try:
                await asyncio.get_event_loop().run_in_executor(io_executor, os.remove, file)
            except:
                pass


# -----------------------
# STATIC IMAGE / STICKER
# -----------------------
async def drawText(image_path, text):
    # Process image in thread pool
    return await asyncio.get_event_loop().run_in_executor(
        cpu_executor, _process_static_image, image_path, text
    )


def _process_static_image(image_path, text):
    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        i_width, i_height = img.size
        font = get_font(i_width)

        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text, lower_text = text, ""

        draw = ImageDraw.Draw(img)
        current_h, pad = 10, 5

        def draw_text_with_outline(x, y, text, font, fill=(255, 255, 255), outline=(0, 0, 0)):
            # Draw outline first (more efficient method)
            draw.text((x-2, y-2), text, font=font, fill=outline)
            draw.text((x+2, y-2), text, font=font, fill=outline)
            draw.text((x-2, y+2), text, font=font, fill=outline)
            draw.text((x+2, y+2), text, font=font, fill=outline)
            # Draw main text
            draw.text((x, y), text, font=font, fill=fill)

        # Pre-calculate text positions and sizes
        text_lines = []
        if upper_text:
            for u_text in textwrap.wrap(upper_text, width=15):
                bbox = draw.textbbox((0, 0), u_text, font=font)
                u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (i_width - u_width) / 2
                y = current_h
                text_lines.append((x, y, u_text))
                current_h += u_height + pad

        if lower_text:
            for l_text in textwrap.wrap(lower_text, width=15):
                bbox = draw.textbbox((0, 0), l_text, font=font)
                u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (i_width - u_width) / 2
                y = i_height - u_height - 20
                text_lines.append((x, y, l_text))

        # Draw all text at once
        for x, y, t_text in text_lines:
            draw_text_with_outline(x, y, t_text, font)

        image_name = "memify.webp"
        img.save(image_name, "WEBP", quality=95, optimize=True)
        return image_name


# -----------------------
# ANIMATED STICKER (GIF/TGS)
# -----------------------
async def drawTextAnimated(image_path, text):
    return await asyncio.get_event_loop().run_in_executor(
        cpu_executor, _process_animated_image, image_path, text
    )


def _process_animated_image(image_path, text):
    with Image.open(image_path) as img:
        frames, durations = [], []

        first_frame = next(ImageSequence.Iterator(img)).copy()
        if first_frame.mode in ("RGBA", "LA", "P"):
            if first_frame.mode == "P":
                first_frame = first_frame.convert("RGBA")
            bg = Image.new("RGB", first_frame.size, (255, 255, 255))
            bg.paste(first_frame, mask=first_frame.split()[-1])
            first_frame = bg

        i_width, i_height = first_frame.size
        font = get_font(i_width)

        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text, lower_text = text, ""

        # Pre-calculate text positions
        upper_pos, lower_pos = None, None
        
        if upper_text:
            bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), upper_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            upper_pos = ((i_width - u_width) / 2, 10)
            
        if lower_text:
            bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), lower_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            lower_pos = ((i_width - u_width) / 2, i_height - u_height - 20)

        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGBA")
            frame_draw = frame.copy()
            draw = ImageDraw.Draw(frame_draw)

            def draw_text_with_outline(x, y, text, font, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255)):
                # More efficient outline drawing
                draw.text((x-1, y-1), text, font=font, fill=outline)
                draw.text((x+1, y-1), text, font=font, fill=outline)
                draw.text((x-1, y+1), text, font=font, fill=outline)
                draw.text((x+1, y+1), text, font=font, fill=outline)
                draw.text((x, y), text, font=font, fill=fill)

            if upper_text and upper_pos:
                draw_text_with_outline(upper_pos[0], upper_pos[1], upper_text, font)

            if lower_text and lower_pos:
                draw_text_with_outline(lower_pos[0], lower_pos[1], lower_text, font)

            frames.append(frame_draw)
            durations.append(frame.info.get("duration", 100))

        out = "memify_animated.webp"
        frames[0].save(
            out, format="WEBP", save_all=True, 
            append_images=frames[1:], duration=durations, 
            loop=0, quality=80, optimize=True
        )
        return out


# -----------------------
# VIDEO STICKER (WEBM)
# -----------------------
async def drawTextVideoSticker(video_path, text):
    return await asyncio.get_event_loop().run_in_executor(
        io_executor, _process_video_sticker, video_path, text
    )


def _process_video_sticker(video_path, text):
    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = os.path.join(tmpdir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        # Extract frames with faster settings
        subprocess.run([
            "ffmpeg", "-i", video_path, "-vsync", "0", 
            "-compression_level", "0", f"{frames_dir}/frame_%04d.png"
        ], check=True, capture_output=True)

        # Get first frame to calculate text positions
        first_frame_path = os.path.join(frames_dir, sorted(os.listdir(frames_dir))[0])
        with Image.open(first_frame_path) as first_img:
            i_width, i_height = first_img.size
            font = get_font(i_width)

        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text, lower_text = text, ""

        # Pre-calculate text positions
        upper_pos, lower_pos = None, None
        
        if upper_text:
            with Image.new("RGB", (1, 1)) as dummy_img:
                dummy_draw = ImageDraw.Draw(dummy_img)
                bbox = dummy_draw.textbbox((0, 0), upper_text, font=font)
                u_width = bbox[2] - bbox[0]
                upper_pos = ((i_width - u_width) / 2, 10)
                
        if lower_text:
            with Image.new("RGB", (1, 1)) as dummy_img:
                dummy_draw = ImageDraw.Draw(dummy_img)
                bbox = dummy_draw.textbbox((0, 0), lower_text, font=font)
                u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                lower_pos = ((i_width - u_width) / 2, i_height - u_height - 20)

        # Process frames in parallel
        frame_files = sorted(os.listdir(frames_dir))
        
        # Use ThreadPool for I/O bound frame processing
        with ThreadPoolExecutor() as executor:
            list(executor.map(
                lambda f: _process_video_frame(f, frames_dir, upper_text, upper_pos, lower_text, lower_pos, font),
                frame_files
            ))

        output_path = os.path.join(tmpdir, "meme.webm")
        subprocess.run([
            "ffmpeg", "-framerate", "30", "-i", f"{frames_dir}/frame_%04d.png",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "500K", 
            "-speed", "4", "-row-mt", "1", "-threads", "4", "-y", output_path
        ], check=True, capture_output=True)

        final = "memify_video.webm"
        os.rename(output_path, final)
        return final


def _process_video_frame(frame_file, frames_dir, upper_text, upper_pos, lower_text, lower_pos, font):
    frame_path = os.path.join(frames_dir, frame_file)
    with Image.open(frame_path) as img:
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)

        def draw_text_with_outline(x, y, text, font, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255)):
            # Efficient outline drawing
            draw.text((x-1, y-1), text, font=font, fill=outline)
            draw.text((x+1, y-1), text, font=font, fill=outline)
            draw.text((x-1, y+1), text, font=font, fill=outline)
            draw.text((x+1, y+1), text, font=font, fill=outline)
            draw.text((x, y), text, font=font, fill=fill)

        if upper_text and upper_pos:
            draw_text_with_outline(upper_pos[0], upper_pos[1], upper_text, font)

        if lower_text and lower_pos:
            draw_text_with_outline(lower_pos[0], lower_pos[1], lower_text, font)

        img.save(frame_path)


# -----------------------
# FONT HELPER
# -----------------------
def get_font(i_width):
    font_paths = [
        "./Powers/assets/default.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "arial.ttf", "Arial.ttf"
    ]
    font_size = max(20, int((70 / 640) * i_width))
    
    # Cache fonts to avoid repeated file access
    if not hasattr(get_font, 'font_cache'):
        get_font.font_cache = {}
    
    cache_key = f"{font_size}"
    if cache_key in get_font.font_cache:
        return get_font.font_cache[cache_key]
    
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                get_font.font_cache[cache_key] = font
                return font
            except:
                continue
    
    # Fallback to default font
    default_font = ImageFont.load_default()
    get_font.font_cache[cache_key] = default_font
    return default_font
