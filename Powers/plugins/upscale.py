import os
import cv2
import tempfile
import numpy as np
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo


def enhance_image(input_path, output_path):
    # Read image
    img = cv2.imread(input_path)

    # Upscale using Lanczos
    upscale_factor = 2
    upscaled = cv2.resize(img, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_LANCZOS4)

    # Smooth colors but keep edges (bilateral filter is softer than denoise)
    smooth = cv2.bilateralFilter(upscaled, d=9, sigmaColor=75, sigmaSpace=75)

    # Gentle Unsharp Mask
    gaussian = cv2.GaussianBlur(smooth, (0, 0), 2)  # blur base
    sharpened = cv2.addWeighted(smooth, 1.25, gaussian, -0.25, 0)  # soft sharpening

    # Save final result
    cv2.imwrite(output_path, sharpened)


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Processing image...")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    try:
        enhance_image(temp_file.name, out_file.name)

        await m.reply_document(out_file.name, caption="✨ Upscaled (Sharp but Smooth)")

        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
    finally:
        try: os.remove(temp_file.name)
        except: pass
        try: os.remove(out_file.name)
        except: pass


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 Local Image Enhancer**
`/upscale` or `/hd` - Reply to an image to upscale & enhance

**Features:**
- 2x resolution boost (offline)
- Soft sharpening (no harsh destruction)
- Smooth colors while keeping line clarity
- Works well for anime, art & photos
"""
