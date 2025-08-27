import os
import requests
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# ✅ Free DeepAI API key
DEEP_AI_KEY = os.getenv("DEEP_AI_KEY", "79eb379a-337c-4258-9957-a0c25195b6da")  # get free at https://deepai.org/

@Gojo.on_message(filters.command(["upscale", "hd"]))
async def upscale_image(c: Gojo, m: Message):
    # Get image URL from command or replied photo
    if len(m.command) == 2:
        image_url = m.command[1]
    elif m.reply_to_message and m.reply_to_message.photo:
        file_path = await c.download_media(m.reply_to_message.photo.file_id)
        # upload to temporary free host to get URL
        with open(file_path, "rb") as f:
            resp = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": "5a0b3d4d4d27e3f33ef5e9df0b3e1abc"},
                files={"image": f}
            )
        data = resp.json()
        if not data.get("success"):
            return await m.reply_text("❌ Upload failed, try again.")
        image_url = data["data"]["url"]
    else:
        return await m.reply_text("📸 Reply to an image or use `/upscale <url>`.")

    msg = await m.reply_text("🔄 Upscaling your image with AI...")

    try:
        # Call DeepAI SRGAN API
        response = requests.post(
            "https://api.deepai.org/api/torch-srgan",
            headers={"api-key": DEEP_AI_KEY},
            data={"image": image_url},
        )
        result = response.json()
        if not result.get("output_url"):
            return await msg.edit_text("❌ Upscaling failed, try again later.")

        await msg.delete()
        await m.reply_photo(result["output_url"], caption="✅ Here is your upscaled image!")
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
