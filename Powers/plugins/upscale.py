import os
import requests
import tempfile
import time
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Replicate ESRGAN model version ID (Real-ESRGAN 4x)
MODEL_VERSION = "9936d9b908052e2dd55c3d43578a1b8e986ba4655c0c15dc1b6ee3a1df26c3f1"

# API Token (store in VPS env)
API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "r8_X3wOWH9rYTC5JllHIgh3OfnS1HTgnhN1pK7v4")

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

@Gojo.on_message(filters.command(["upscale", "hd"]))
async def upscale(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("⚠️ Reply to an image to upscale it.")

    msg = await m.reply_text("🔄 Upscaling... Please wait.")

    # Download input image to a temp file
    input_path = await c.download_media(
        m.reply_to_message.photo.file_id,
        file_name=tempfile.mktemp(suffix=".jpg")
    )

    try:
        # Step 1: Upload image to Replicate's file storage
        with open(input_path, "rb") as f:
            upload = requests.post(
                "https://api.replicate.com/v1/files",
                headers={"Authorization": f"Token {API_TOKEN}"},
                files={"file": f}
            )
        upload.raise_for_status()
        image_url = upload.json()["urls"]["get"]

        # Step 2: Create upscale prediction
        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=HEADERS,
            json={
                "version": MODEL_VERSION,
                "input": {"image": image_url, "scale": 2}
            }
        )
        r.raise_for_status()
        prediction = r.json()
        prediction_url = prediction["urls"]["get"]

        # Step 3: Poll until finished
        output_url = None
        for _ in range(40):  # ~200s max wait
            status = requests.get(prediction_url, headers=HEADERS).json()
            if status["status"] == "succeeded":
                output_url = status["output"][0]
                break
            elif status["status"] in ["failed", "canceled"]:
                return await msg.edit("❌ Upscaling failed.")
            time.sleep(5)

        if not output_url:
            return await msg.edit("❌ Upscaling timed out - no result.")

        # Step 4: Download final image
        output_path = tempfile.mktemp(suffix=".png")
        with open(output_path, "wb") as f:
            f.write(requests.get(output_url).content)

        # Step 5: Send file back
        await m.reply_photo(output_path, caption="✅ Upscaled & Sharpened")
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

    finally:
        # Cleanup files
        if os.path.exists(input_path):
            os.remove(input_path)
        if "output_path" in locals() and os.path.exists(output_path):
            os.remove(output_path)


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler**
`/upscale` or `/hd` - Reply to an image to enhance its quality using AI

**Features:**
- Increases resolution up to 4x
- Sharpens lines, smooths colors
- Supports JPG, PNG, WEBP
- Returns file directly in Telegram
"""
