import os
import cv2
import tempfile
import numpy as np
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo


def enhance_image(input_path, output_path):
    # Read image with OpenCV
    img = cv2.imread(input_path)

    # Upscale using OpenCV's super-resize (Lanczos)
    upscale_factor = 2
    upscaled = cv2.resize(img, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_LANCZOS4)

    # Denoise (smooth colors without blurring edges too much)
    smooth = cv2.fastNlMeansDenoisingColored(upscaled, None, 10, 10, 7, 21)

    # ----- Unsharp Mask -----
    gaussian = cv2.GaussianBlur(smooth, (0, 0), 3)
    unsharp = cv2.addWeighted(smooth, 1.5, gaussian, -0.5, 0)

    # ----- High-Pass Filter (extra edge clarity) -----
    gray = cv2.cvtColor(unsharp, cv2.COLOR_BGR2GRAY)
    highpass = gray - cv2.GaussianBlur(gray, (0, 0), 7)
    highpass = cv2.normalize(highpass, None, 0, 255, cv2.NORM_MINMAX)

    # Merge highpass detail back to color image
    highpass_colored = cv2.cvtColor(highpass, cv2.COLOR_GRAY2BGR)
    sharp = cv2.addWeighted(unsharp, 1.0, highpass_colored, 0.7, 0)

    # Save result
    cv2.imwrite(output_path, sharp)


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Processing image...")

    # Download image to temp
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    try:
        # Enhance image locally
        enhance_image(temp_file.name, out_file.name)

        # Send back result as file
        await m.reply_document(out_file.name, caption="✨ Ultra-Sharpened (Lines Enhanced + Colors Smoothed)")

        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
    finally:
        try:
            os.remove(temp_file.name)
        except:
            pass
        try:
            os.remove(out_file.name)
        except:
            pass


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 Local Image Enhancer**
`/upscale` or `/hd` - Reply to an image to upscale & enhance

**Features:**
- 2x resolution boost (offline)
- Ultra sharp line detailing (Unsharp Mask + High-Pass filter)
- Smooths colors (denoised without blur)
- Returns file directly in Telegram
"""
