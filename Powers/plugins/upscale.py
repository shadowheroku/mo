import os
import tempfile
import requests
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# 🔑 Get your key from https://rapidapi.com/developer
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "db695f9a31msh317d0f72b049ab7p1c6935jsn65e8560b2087
")

UPSCALE_API_URL = "rapidapi.com"


def upscale_via_api(image_path: str, scale: int = 2) -> str:
    """Send image to Upscale.media API and return output URL"""
    with open(image_path, "rb") as f:
        response = requests.post(
            UPSCALE_API_URL,
            files={"image": f},
            data={"scale": str(scale)},  # 2x or 4x
            headers={
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "upscale-media-image-super-resolution.p.rapidapi.com"
            },
            timeout=120
        )

    data = response.json()
    if "output_url" not in data:
        raise Exception(data.get("message", "Unknown API error"))

    return data["output_url"]


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Uploading to AI Upscaler...")

    # Download input
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    try:
        # Call API (default 2x, change to 4x if you want super HD)
        upscaled_url = upscale_via_api(temp_file.name, scale=4)

        # Download result
        out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        r = requests.get(upscaled_url, timeout=120)
        with open(out_file.name, "wb") as f:
            f.write(r.content)

        # Send result
        await m.reply_document(out_file.name, caption="✨ Upscaled with AI (Upscale.media 4x)")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ API Error: {e}")

    finally:
        try:
            os.remove(temp_file.name)
        except:
            pass


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (API)**
`/upscale` or `/hd` - Reply to an image to upscale & enhance using AI

**Features:**
- Uses Upscale.media AI (via RapidAPI)
- Supports 2x and 4x upscale
- Preserves details better than OpenCV
- Returns file directly in Telegram

⚠️ Requires `RAPIDAPI_KEY`
Get one free at [RapidAPI](https://rapidapi.com/).
"""
