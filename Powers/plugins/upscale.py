import os
import replicate
import requests
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# ✅ Set Replicate API key
os.environ["REPLICATE_API_TOKEN"] = "r8_V7pQfVBxlIzmvviUEkiYJxCcDqAAbhk1rq4Jn"

# Replicate model (Real-ESRGAN for upscaling)
MODEL = "nightmareai/real-esrgan"

@Gojo.on_message(filters.command(["upscale"]))
async def upscale_image(c: Gojo, m: Message):
    if len(m.command) == 2:  # Case 1: /upscale <url>
        image_url = m.command[1]
    elif m.reply_to_message and m.reply_to_message.photo:  # Case 2: replied photo
        photo = m.reply_to_message.photo
        file_path = await c.download_media(photo.file_id)
        # Upload to a free file host to get a URL
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": "5a0b3d4d4d27e3f33ef5e9df0b3e1abc"},  # Public demo key
                files={"image": f},
            )
        data = response.json()
        if not data.get("success"):
            return await m.reply_text("❌ Upload failed, try again.")
        image_url = data["data"]["url"]
    else:
        return await m.reply_text("📸 Reply to an image or use `/upscale <url>`.")

    msg = await m.reply_text("🔄 Upscaling your image, please wait...")

    try:
        output = replicate.run(
            f"{MODEL}:latest",
            input={"image": image_url, "scale": 2}  # You can change scale: 2, 4, etc.
        )
        await msg.delete()
        await m.reply_photo(output, caption="✅ Here is your upscaled image!")
    except Exception as e:
        await msg.edit_text(f"❌ Upscale failed: {e}")



__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (Replicate Real-ESRGAN)**
`/upscale` or `/hd` - Reply to an image to upscale with AI

**Features:**
- Uses Replicate's Real-ESRGAN model
- 4× high-quality enhancement
- Returns file directly in Telegram

⚠️ Requires `REPLICATE_API_KEY`
Get one at [replicate.com](https://replicate.com/account/api-tokens).
"""
