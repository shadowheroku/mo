import os
import textwrap
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# -----------------------
# /mmf handler
# -----------------------
@Gojo.on_message(filters.command("mmf"))
async def mmf(c: Gojo, m: Message):
    reply = m.reply_to_message
    if not reply or not (reply.photo or reply.document or reply.sticker):
        await safe_reply(m, "**Please reply to an image, sticker, or video-sticker to memify it.**")
        return

    if len(m.text.split()) < 2:
        await safe_reply(m, "**Give me text after /mmf to memify.**\nExample: `/mmf Top;Bottom`")
        return

    text = m.text.split(None, 1)[1]
    status_msg = await safe_reply(m, "**Memifying...**")

    # Work inside a temp dir for safety and cleanup
    with tempfile.TemporaryDirectory() as workdir:
        try:
            # Download media. Returned value is full file path.
            file_path = await c.download_media(reply)
            if not file_path or not os.path.exists(file_path):
                raise Exception("Failed to download media.")

            # Decide type
            is_video_sticker = file_path.lower().endswith(".webm")
            is_animated = False
            if reply.sticker:
                # pyrogram's is_animated attribute can tell us animated webp/tgs
                is_animated = bool(getattr(reply.sticker, "is_animated", False))
                # note: video stickers are webm -> handled separately
                if is_video_sticker:
                    is_animated = False

            # Process based on type
            if is_video_sticker:
                out_file = await draw_text_video_sticker(file_path, text, workdir)
                # send as sticker (webm)
                await c.send_sticker(m.chat.id, sticker=out_file)
            elif is_animated:
                out_file = await draw_text_animated(file_path, text, workdir)
                # animated webp -> send as sticker
                await c.send_sticker(m.chat.id, sticker=out_file)
            else:
                out_file = await draw_text_static(file_path, text, workdir)
                # If replied message was sticker, send as sticker; else send document (webp)
                if reply.sticker:
                    await c.send_sticker(m.chat.id, sticker=out_file)
                else:
                    await c.send_document(m.chat.id, document=out_file)

            await safe_delete(status_msg)
        except Exception as e:
            # Try to edit status_msg; ignore MessageIdInvalid etc.
            await safe_edit(status_msg, f"**Error:** {e}")
        finally:
            # Clean up the downloaded original if exists
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass


# -----------------------
# helpers: safe message ops (guard against MessageIdInvalid)
# -----------------------
async def safe_reply(m: Message, text: str):
    try:
        return await m.reply_text(text)
    except Exception:
        # last resort: send_message to chat
        try:
            return await m._client.send_message(m.chat.id, text)
        except Exception:
            return None

async def safe_edit(msg, text: str):
    if not msg:
        return
    try:
        await msg.edit_text(text)
    except Exception:
        # ignore errors like MessageIdInvalid
        pass

async def safe_delete(msg):
    if not msg:
        return
    try:
        await msg.delete()
    except Exception:
        pass


# -----------------------
# FONT helper + fit text
# -----------------------
def find_font():
    paths = [
        "./Powers/assets/default.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "arial.ttf", "Arial.ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None  # use default ImageFont later

def fit_font_for_line(draw, text, base_size, max_width):
    """
    Reduce font size until text fits max_width.
    Returns PIL ImageFont instance.
    """
    font_path = find_font()
    size = base_size
    while size > 10:
        try:
            if font_path:
                font = ImageFont.truetype(font_path, size)
            else:
                font = ImageFont.load_default()
                # can't really change size of load_default
                return font
        except Exception:
            font = ImageFont.load_default()
            return font

        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return font
        size -= 2
    return font  # smallest


# -----------------------
# STATIC IMAGE (photos & static stickers)
# -----------------------
async def draw_text_static(input_path: str, text: str, workdir: str) -> str:
    """
    Return path to output webp (static) ready to send.
    """
    img = Image.open(input_path)

    # Convert to RGB background (handle transparency)
    if img.mode in ("RGBA", "LA", "P"):
        if img.mode == "P":
            img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        mask = img.split()[-1] if img.mode == "RGBA" else None
        bg.paste(img, mask=mask)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    i_w, i_h = img.size
    draw = ImageDraw.Draw(img)

    # split upper/lower text at ';' (single split)
    if ";" in text:
        upper_text, lower_text = text.split(";", 1)
    else:
        upper_text, lower_text = text, ""

    base_font_size = max(20, int((70 / 640) * i_w))
    pad = max(6, int(i_w * 0.006))

    # outline drawing helper
    def draw_outline_text(x, y, t, font):
        outline_w = 2
        for dx in range(-outline_w, outline_w + 1):
            for dy in range(-outline_w, outline_w + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), t, font=font, fill=(0, 0, 0))
        draw.text((x, y), t, font=font, fill=(255, 255, 255))

    # upper lines
    cur_y = max(8, int(i_w * 0.015))
    if upper_text.strip():
        lines = textwrap.wrap(upper_text.strip(), width=20)
        for line in lines:
            font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (i_w - w) / 2
            draw_outline_text(x, cur_y, line, font)
            cur_y += h + pad

    # lower lines
    if lower_text.strip():
        lines = textwrap.wrap(lower_text.strip(), width=20)
        # compute height of lower block
        block_h = 0
        fonts = []
        for line in lines:
            font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
            bbox = draw.textbbox((0, 0), line, font=font)
            h = bbox[3] - bbox[1]
            fonts.append(font)
            block_h += h + pad
        cur_y = i_h - block_h - max(8, int(i_w * 0.02))
        # draw
        for idx, line in enumerate(lines):
            font = fonts[idx]
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (i_w - w) / 2
            draw_outline_text(x, cur_y, line, font)
            cur_y += h + pad

    out_path = os.path.join(workdir, "memify.webp")
    img.save(out_path, "WEBP", quality=95)
    return out_path


# -----------------------
# ANIMATED (gif / animated webp)
# -----------------------
async def draw_text_animated(input_path: str, text: str, workdir: str) -> str:
    """
    Opens the animated input (GIF or animated WEBP), overlays text on each frame,
    and returns an animated WEBP path.
    """
    img = Image.open(input_path)
    frames = []
    durations = []

    # Prepare upper/lower text
    if ";" in text:
        upper_text, lower_text = text.split(";", 1)
    else:
        upper_text, lower_text = text, ""

    # Use first frame to decide sizing
    first_frame = next(ImageSequence.Iterator(img)).convert("RGBA").copy()
    i_w, i_h = first_frame.size

    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("RGBA")
        canvas = Image.new("RGBA", frame.size)
        canvas.paste(frame, (0, 0))

        draw = ImageDraw.Draw(canvas)
        base_font_size = max(20, int((70 / 640) * i_w))
        pad = max(6, int(i_w * 0.006))

        # helper
        def draw_outline_text(x, y, t, font):
            o = 2
            for dx in range(-o, o + 1):
                for dy in range(-o, o + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), t, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y), t, font=font, fill=(255, 255, 255, 255))

        # upper
        cur_y = max(8, int(i_w * 0.015))
        if upper_text.strip():
            for line in textwrap.wrap(upper_text.strip(), width=20):
                font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (i_w - w) / 2
                draw_outline_text(x, cur_y, line, font)
                cur_y += h + pad

        # lower
        if lower_text.strip():
            lines = textwrap.wrap(lower_text.strip(), width=20)
            block_h = 0
            fonts = []
            for line in lines:
                font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
                bbox = draw.textbbox((0, 0), line, font=font)
                h = bbox[3] - bbox[1]
                fonts.append(font)
                block_h += h + pad
            cur_y = i_h - block_h - max(8, int(i_w * 0.02))
            for idx, line in enumerate(lines):
                font = fonts[idx]
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (i_w - w) / 2
                draw_outline_text(x, cur_y, line, font)
                cur_y += h + pad

        frames.append(canvas.convert("RGBA"))
        durations.append(getattr(frame, "info", {}).get("duration", 100))

    out_path = os.path.join(workdir, "memify_animated.webp")
    if len(frames) > 1:
        frames[0].save(
            out_path,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=80,
        )
    else:
        frames[0].save(out_path, "WEBP", quality=95)
    return out_path


# -----------------------
# VIDEO STICKER (.webm) - uses ffmpeg
# -----------------------
async def draw_text_video_sticker(input_path: str, text: str, workdir: str) -> str:
    """
    Extract frames with ffmpeg, draw text on each PNG frame, then encode VP9+alpha webm
    using CRF (quality) so Telegram accepts it as video sticker.
    Returns output webm path.
    """
    frames_dir = os.path.join(workdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # Extract frames to PNG (preserve alpha if present)
    # -vsync 0 to avoid frame duplication
    extract_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vsync", "0",
        os.path.join(frames_dir, "frame_%04d.png")
    ]
    subprocess.run(extract_cmd, check=True)

    files = sorted([f for f in os.listdir(frames_dir) if f.startswith("frame_") and f.endswith(".png")])
    if not files:
        raise Exception("No frames extracted from video sticker.")

    # Load first frame to get dimensions
    first_frame_path = os.path.join(frames_dir, files[0])
    img0 = Image.open(first_frame_path).convert("RGBA")
    i_w, i_h = img0.size

    # split upper/lower
    if ";" in text:
        upper_text, lower_text = text.split(";", 1)
    else:
        upper_text, lower_text = text, ""

    base_font_size = max(20, int((70 / 640) * i_w))
    pad = max(6, int(i_w * 0.006))

    # Draw on each frame
    for fname in files:
        fpath = os.path.join(frames_dir, fname)
        img = Image.open(fpath).convert("RGBA")
        draw = ImageDraw.Draw(img)

        def draw_outline_text(x, y, t, font):
            o = 2
            for dx in range(-o, o + 1):
                for dy in range(-o, o + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), t, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y), t, font=font, fill=(255, 255, 255, 255))

        # upper lines
        cur_y = max(8, int(i_w * 0.015))
        if upper_text.strip():
            for line in textwrap.wrap(upper_text.strip(), width=20):
                font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (i_w - w) / 2
                draw_outline_text(x, cur_y, line, font)
                cur_y += h + pad

        # lower lines
        if lower_text.strip():
            lines = textwrap.wrap(lower_text.strip(), width=20)
            block_h = 0
            fonts = []
            for line in lines:
                font = fit_font_for_line(draw, line, base_font_size, i_w - 20)
                bbox = draw.textbbox((0, 0), line, font=font)
                h = bbox[3] - bbox[1]
                fonts.append(font)
                block_h += h + pad
            cur_y = i_h - block_h - max(8, int(i_w * 0.02))
            for idx, line in enumerate(lines):
                font = fonts[idx]
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (i_w - w) / 2
                draw_outline_text(x, cur_y, line, font)
                cur_y += h + pad

        # overwrite frame
        img.save(fpath, "PNG")

    # Rebuild webm with libvpx-vp9 using CRF (quality-controlled)
    output_webm = os.path.join(workdir, "memify_video.webm")
    # Use -r copy? we set fps to 30 default; we can preserve original FPS by probing input, but 30 is safe.
    encode_cmd = [
        "ffmpeg", "-y", "-framerate", "30", "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-b:v", "0", "-crf", "32", "-row-mt", "1",
        "-an", output_webm
    ]
    subprocess.run(encode_cmd, check=True)

    # Final check file exists
    if not os.path.exists(output_webm):
        raise Exception("Failed to create video sticker.")

    return output_webm
