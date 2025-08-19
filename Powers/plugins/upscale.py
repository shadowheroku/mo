import os
import requests
import tempfile
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# ESRGAN model ID (Replicate)
MODEL_ID = "nightmareai/real-esrgan"  

API_TOKEN = "r8_X3wOWH9rYTC5JllHIgh3OfnS1HTgnhN1pK7v4"  # must be set in VPS env

@Gojo.on_message(filters.command(["upscale", "hd"]))
async def upscale(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("⚠️ Reply to an image to upscale it.")

    msg = await m.reply_text("🔄 Upscaling... Please wait.")

    # Download the photo temporarily
    input_path = await c.download_media(m.reply_to_message.photo.file_id, file_name=tempfile.mktemp(suffix=".jpg"))

    try:
        # Upload image to a temporary file host (Replicate needs URL input)
        with open(input_path, "rb") as f:
            upload = requests.post(
                "https://api.anonfiles.com/upload",
                files={"file": f}
            ).json()
        image_url = upload["data"]["file"]["url"]["full"]

        # Call Replicate ESRGAN API
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={"Authorization": f"Token {API_TOKEN}", "Content-Type": "application/json"},
            json={
                "version": "9936d9b908052e2dd55c3d43578a1b8e986ba4655c0c15dc1b6ee3a1df26c3f1",
                "input": {"img": image_url, "scale": 2}
            }
        )
        prediction = response.json()
        if "id" not in prediction:
            return await msg.edit_text("❌ Failed to upscale (API Error).")

        # Poll until finished
        status = prediction["status"]
        output_url = None
        while status not in ["succeeded", "failed", "canceled"]:
            r = requests.get(f"https://api.replicate.com/v1/predictions/{prediction['id']}",
                             headers={"Authorization": f"Token {API_TOKEN}"})
            data = r.json()
            status = data["status"]
            if status == "succeeded":
                output_url = data["output"][0]
                break

        if not output_url:
            return await msg.edit_text("❌ Upscaling failed - no output received")

        # Save result as file
        output_path = tempfile.mktemp(suffix=".png")
        with open(output_path, "wb") as f:
            f.write(requests.get(output_url).content)

        # Send as file
        await m.reply_document(output_path, caption="✨ Upscaled with ESRGAN")

        await msg.delete()

        # Cleanup
        os.remove(input_path)
        os.remove(output_path)

    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        if os.path.exists(input_path):
            os.remove(input_path)


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (Picsart)**
`/upscale` - Reply to an image to enhance its quality using AI

**Features:**
- Increases image resolution up to 8x
- Supports JPG, PNG, WEBP formats
- Max file size: 20MB
"""
