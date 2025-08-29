import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from pyrogram import filters, enums
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
        
        # Check if it's a sticker and if it's animated
        is_animated = False
        if reply_message.sticker:
            is_animated = reply_message.sticker.is_animated
        
        if is_animated:
            meme = await drawTextAnimated(file, text)
            await c.send_sticker(chat_id, sticker=meme)
        else:
            meme = await drawText(file, text)
            if reply_message.sticker:
                await c.send_sticker(chat_id, sticker=meme)
            else:
                await c.send_document(chat_id, document=meme)
        
        await msg.delete()
        os.remove(meme)
        os.remove(file)
        
    except Exception as e:
        await msg.edit_text(f"**Error: {str(e)}**")
        if 'file' in locals() and os.path.exists(file):
            os.remove(file)
        if 'meme' in locals() and os.path.exists(meme):
            os.remove(meme)


async def drawText(image_path, text):
    img = Image.open(image_path)
    
    # Convert to RGB if needed (for PNG transparency)
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    
    i_width, i_height = img.size

    # Try multiple font options
    font_paths = [
        "./Powers/assets/default.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf",
        "Arial.ttf"
    ]

    font_size = max(20, int((70 / 640) * i_width))  # Minimum font size of 20
    font = None

    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (OSError, IOError):
            continue

    # If no font found, use default font
    if font is None:
        try:
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

    if ";" in text:
        upper_text, lower_text = text.split(";")
    else:
        upper_text = text
        lower_text = ""

    draw = ImageDraw.Draw(img)
    current_h, pad = 10, 5

    # Function to draw text with outline
    def draw_text_with_outline(x, y, text, font, fill_color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=2):
        # Draw outline
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        # Draw main text
        draw.text((x, y), text, font=font, fill=fill_color)

    if upper_text:
        for u_text in textwrap.wrap(upper_text, width=15):
            try:
                bbox = draw.textbbox((0, 0), u_text, font=font)
                u_width = bbox[2] - bbox[0]
                u_height = bbox[3] - bbox[1]
            except:
                u_width, u_height = 100, 20

            x = (i_width - u_width) / 2
            y = int((current_h / 640) * i_width)
            
            draw_text_with_outline(x, y, u_text, font)
            current_h += u_height + pad

    if lower_text:
        for l_text in textwrap.wrap(lower_text, width=15):
            try:
                bbox = draw.textbbox((0, 0), l_text, font=font)
                u_width = bbox[2] - bbox[0]
                u_height = bbox[3] - bbox[1]
            except:
                u_width, u_height = 100, 20

            x = (i_width - u_width) / 2
            y = i_height - u_height - int((20 / 640) * i_width)
            
            draw_text_with_outline(x, y, l_text, font)
            current_h += u_height + pad

    image_name = "memify.webp"
    img.save(image_name, "WEBP")
    return image_name


async def drawTextAnimated(image_path, text):
    # Open the animated WebP
    img = Image.open(image_path)
    
    frames = []
    durations = []
    
    # Get font (same as static version)
    font_paths = [
        "./Powers/assets/default.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf",
        "Arial.ttf"
    ]
    
    # Use first frame to determine font size
    first_frame = img.copy()
    if first_frame.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', first_frame.size, (255, 255, 255))
        background.paste(first_frame, mask=first_frame.split()[-1])
        first_frame = background
    
    i_width, i_height = first_frame.size
    font_size = max(20, int((70 / 640) * i_width))
    font = None

    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (OSError, IOError):
            continue

    if font is None:
        try:
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

    if ";" in text:
        upper_text, lower_text = text.split(";")
    else:
        upper_text = text
        lower_text = ""

    # Process each frame
    for frame in ImageSequence.Iterator(img):
        frame = frame.convert('RGBA')
        
        # Create a copy to draw on
        frame_draw = frame.copy()
        draw = ImageDraw.Draw(frame_draw)
        
        current_h, pad = 10, 5

        # Function to draw text with outline (for animated)
        def draw_text_with_outline_anim(x, y, text, font, fill_color=(255, 255, 255, 255), outline_color=(0, 0, 0, 255), outline_width=2):
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
            draw.text((x, y), text, font=font, fill=fill_color)

        if upper_text:
            for u_text in textwrap.wrap(upper_text, width=15):
                try:
                    bbox = draw.textbbox((0, 0), u_text, font=font)
                    u_width = bbox[2] - bbox[0]
                    u_height = bbox[3] - bbox[1]
                except:
                    u_width, u_height = 100, 20

                x = (i_width - u_width) / 2
                y = int((current_h / 640) * i_width)
                
                draw_text_with_outline_anim(x, y, u_text, font)
                current_h += u_height + pad

        if lower_text:
            for l_text in textwrap.wrap(lower_text, width=15):
                try:
                    bbox = draw.textbbox((0, 0), l_text, font=font)
                    u_width = bbox[2] - bbox[0]
                    u_height = bbox[3] - bbox[1]
                except:
                    u_width, u_height = 100, 20

                x = (i_width - u_width) / 2
                y = i_height - u_height - int((20 / 640) * i_width)
                
                draw_text_with_outline_anim(x, y, l_text, font)
                current_h += u_height + pad
        
        frames.append(frame_draw)
        durations.append(frame.info.get('duration', 100))  # Default 100ms
    
    # Save as animated WebP
    image_name = "memify_animated.webp"
    if len(frames) > 1:
        frames[0].save(
            image_name,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=80
        )
    else:
        frames[0].save(image_name, "WEBP")
    
    return image_name
