import os
import tempfile
import requests
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# 🔑 Get API Key from https://a1d.ai/ (free tier available)
A1D_API_KEY = os.getenv("A1D_API_KEY", "beY2gutIgr-iWfl_VFToB")

UPSCALE_API_URL = "https://api.a1d.ai/api/image-upscaler"


def upscale_via_api(image_path: str, scale: int = 4) -> str:
    """Send image to A1D AI Upscaler API and return output URL"""
    with open(image_path, "rb") as f:
        response = requests.post(
            UPSCALE_API_URL,
            headers={
                "Authorization": f"Bearer {A1D_API_KEY}"
            },
            files={"image": f},
            data={"scale": str(scale)},  # 2, 4, 8, 16
            timeout=120
        )

    data = response.json()
    if "url" not in data:
        raise Exception(data.get("error", "Unknown API error"))

    return data["url"]


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Uploading to AI Upscaler...")

    # Download input image
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    try:
        # Call API (default 4× upscale)
        upscaled_url = upscale_via_api(temp_file.name, scale=4)

        # Download result
        out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        r = requests.get(upscaled_url, timeout=120)
        with open(out_file.name, "wb") as f:
            f.write(r.content)

        # Send result
        await m.reply_document(out_file.name, caption="✨ Upscaled with AI (A1D AI, 4×)")
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
`/upscale` or `/hd` - Reply to an image to upscale with AI

**Features:**
- Uses A1D AI Image Upscaler API
- Supports upscale 2×, 4×, 8×, 16×
- Returns file directly in Telegram

⚠️ Requires `A1D_API_KEY`
Get one free at [a1d.ai](https://a1d.ai/).
"""
