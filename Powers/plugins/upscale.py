import os
import cv2
import tempfile
import numpy as np
from pyrogram import filters
from pyrogram.types import Message
from PIL import Image, ImageFilter
from Powers.bot_class import Gojo


def enhance_image(input_path, output_path):
    # Read image
    img = cv2.imread(input_path)

    # Upscale with Lanczos
    upscale_factor = 2
    upscaled = cv2.resize(img, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_LANCZOS4)

    # Denoise (smooth colors, keep structure)
    smooth = cv2.fastNlMeansDenoisingColored(upscaled, None, 10, 10, 7, 21)

    # Unsharp mask (more controlled sharpening)
    gaussian = cv2.GaussianBlur(smooth, (0, 0), 2)
    unsharp = cv2.addWeighted(smooth, 1.4, gaussian, -0.4, 0)

    # Extra sharpening kernel (a bit stronger than before)
    kernel = np.array([[0, -0.5, 0],
                       [-0.5, 3.0, -0.5],
                       [0, -0.5, 0]])
    sharpened = cv2.filter2D(unsharp, -1, kernel)

    # Blend to avoid overkill (keep 80% sharpen, 20% smooth)
    final = cv2.addWeighted(unsharp, 0.8, sharpened, 0.2, 0)

    # Save result
    cv2.imwrite(output_path, final)



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
        await m.reply_document(out_file.name, caption="✨ Upscaled (Sharpened + Smoothed)")

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
**🖼 AI Image Enhancer (Local)**
`/upscale` or `/hd` - Reply to an image to upscale & enhance

**Features:**
- 2x resolution boost (offline, no API needed)
- Sharpens lines & fixes edges
- Smooths colors (no harsh noise)
- Returns file directly in Telegram
"""
