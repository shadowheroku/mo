import os
import time
import tempfile
import requests
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# 🔑 Replicate API Key (set here or from environment)
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "r8_V7pQfVBxlIzmvviUEkiYJxCcDqAAbhk1rq4Jn")

# ESRGAN model version on Replicate
ESRGAN_MODEL = "nightmareai/real-esrgan:4c8f2e0005091fc46c0e3538fe9826f65381b3cc55e1c6b03dc4cfa5d8bd7f4f"

PREDICTION_URL = "https://api.replicate.com/v1/predictions"


def upscale_with_replicate(image_path: str) -> str:
    """Send image to Replicate ESRGAN API and return output URL"""

    # Upload to file hosting since Replicate needs a URL
    # Here we use file.io (temp free file host, expires after 1 download)
    with open(image_path, "rb") as f:
        upload = requests.post("https://file.io", files={"file": f}).json()
    if "link" not in upload:
        raise Exception("Failed to upload image for processing")
    image_url = upload["link"]

    # Create prediction
    response = requests.post(
        PREDICTION_URL,
        headers={
            "Authorization": f"Token {REPLICATE_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "version": ESRGAN_MODEL,
            "input": {"image": image_url}
        },
        timeout=60
    )
    prediction = response.json()
    if "id" not in prediction:
        raise Exception(prediction.get("error", "Failed to start prediction"))

    prediction_id = prediction["id"]

    # Poll until complete
    while True:
        poll = requests.get(
            f"{PREDICTION_URL}/{prediction_id}",
            headers={"Authorization": f"Token {REPLICATE_API_KEY}"}
        ).json()

        if poll["status"] in ["succeeded", "failed", "canceled"]:
            break
        time.sleep(5)

    if poll["status"] != "succeeded":
        raise Exception("Upscaling failed")

    return poll["output"][0]  # URL of upscaled image


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Uploading & processing with Real-ESRGAN...")

    # Download input image
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    try:
        # Call API
        upscaled_url = upscale_with_replicate(temp_file.name)

        # Download result
        out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        r = requests.get(upscaled_url, timeout=120)
        with open(out_file.name, "wb") as f:
            f.write(r.content)

        # Send result
        await m.reply_document(out_file.name, caption="✨ Upscaled with Real-ESRGAN (Replicate)")
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
**🖼 AI Image Upscaler (Replicate Real-ESRGAN)**
`/upscale` or `/hd` - Reply to an image to upscale with AI

**Features:**
- Uses Replicate's Real-ESRGAN model
- 4× high-quality enhancement
- Returns file directly in Telegram

⚠️ Requires `REPLICATE_API_KEY`
Get one at [replicate.com](https://replicate.com/account/api-tokens).
"""
