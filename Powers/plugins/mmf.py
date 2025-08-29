import os
import textwrap
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo


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
        os.remove(file)
        if os.path.exists(meme):
            os.remove(meme)

    except Exception as e:
        await msg.edit_text(f"**Error: {str(e)}**")
        if "file" in locals() and os.path.exists(file):
            os.remove(file)
        if "meme" in locals() and os.path.exists(meme):
            os.remove(meme)


# -----------------------
# STATIC IMAGE / STICKER
# -----------------------
async def drawText(image_path, text):
    img = Image.open(image_path)

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
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((x+dx, y+dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    # Upper text
    if upper_text:
        for u_text in textwrap.wrap(upper_text, width=15):
            bbox = draw.textbbox((0, 0), u_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (i_width - u_width) / 2
            y = current_h
            draw_text_with_outline(x, y, u_text, font)
            current_h += u_height + pad

    # Lower text
    if lower_text:
        for l_text in textwrap.wrap(lower_text, width=15):
            bbox = draw.textbbox((0, 0), l_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (i_width - u_width) / 2
            y = i_height - u_height - 20
            draw_text_with_outline(x, y, l_text, font)

    image_name = "memify.webp"
    img.save(image_name, "WEBP", quality=95)
    return image_name


# -----------------------
# ANIMATED STICKER (GIF/TGS)
# -----------------------
async def drawTextAnimated(image_path, text):
    img = Image.open(image_path)
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

    for frame in ImageSequence.Iterator(img):
        frame = frame.convert("RGBA")
        frame_draw = frame.copy()
        draw = ImageDraw.Draw(frame_draw)

        def draw_text_with_outline(x, y, text, font, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255)):
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), text, font=font, fill=outline)
            draw.text((x, y), text, font=font, fill=fill)

        if upper_text:
            bbox = draw.textbbox((0, 0), upper_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw_text_with_outline((i_width - u_width) / 2, 10, upper_text, font)

        if lower_text:
            bbox = draw.textbbox((0, 0), lower_text, font=font)
            u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw_text_with_outline((i_width - u_width) / 2, i_height - u_height - 20, lower_text, font)

        frames.append(frame_draw)
        durations.append(frame.info.get("duration", 100))

    out = "memify_animated.webp"
    frames[0].save(out, format="WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=0, quality=80)
    return out


# -----------------------
# VIDEO STICKER (WEBM)
# -----------------------
async def drawTextVideoSticker(video_path, text):
    with tempfile.TemporaryDirectory() as tmpdir:
        frames_dir = os.path.join(tmpdir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        # Extract frames
        subprocess.run(["ffmpeg", "-i", video_path, f"{frames_dir}/frame_%04d.png"], check=True)

        # Font
        first_frame_path = os.path.join(frames_dir, sorted(os.listdir(frames_dir))[0])
        first_img = Image.open(first_frame_path)
        i_width, i_height = first_img.size
        font = get_font(i_width)

        if ";" in text:
            upper_text, lower_text = text.split(";")
        else:
            upper_text, lower_text = text, ""

        for frame_file in sorted(os.listdir(frames_dir)):
            frame_path = os.path.join(frames_dir, frame_file)
            img = Image.open(frame_path).convert("RGBA")
            draw = ImageDraw.Draw(img)

            def draw_text_with_outline(x, y, text, font, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255)):
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if dx != 0 or dy != 0:
                            draw.text((x+dx, y+dy), text, font=font, fill=outline)
                draw.text((x, y), text, font=font, fill=fill)

            if upper_text:
                bbox = draw.textbbox((0, 0), upper_text, font=font)
                u_width = bbox[2] - bbox[0]
                draw_text_with_outline((i_width - u_width) / 2, 10, upper_text, font)

            if lower_text:
                bbox = draw.textbbox((0, 0), lower_text, font=font)
                u_width, u_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw_text_with_outline((i_width - u_width) / 2, i_height - u_height - 20, lower_text, font)

            img.save(frame_path)

        output_path = os.path.join(tmpdir, "meme.webm")
        subprocess.run([
            "ffmpeg", "-framerate", "30", "-i", f"{frames_dir}/frame_%04d.png",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "500K", "-y", output_path
        ], check=True)

        final = "memify_video.webm"
        os.rename(output_path, final)
        return final


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
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, font_size)
            except:
                continue
    return ImageFont.load_default()
