import os
import requests
import tempfile
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN" , "r8_X3wOWH9rYTC5JllHIgh3OfnS1HTgnhN1pK7v4")

HEADERS = {
    "Authorization": f"Token {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json"
}

# Upload file to Replicate first
def upload_to_replicate(file_path):
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.replicate.com/v1/files",
            headers={"Authorization": f"Token {REPLICATE_API_TOKEN}"},
            files={"file": f}
        )
    resp.raise_for_status()
    return resp.json()["id"]  # Replicate returns file ID


@Gojo.on_message(filters.command("upscale", prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not REPLICATE_API_TOKEN:
        return await m.reply_text("❌ API Token missing! Please set REPLICATE_API_TOKEN.")

    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Uploading image to Replicate...")

    # Download image to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    try:
        # Upload image to replicate
        file_id = upload_to_replicate(temp_file.name)

        # Run ESRGAN model
        model_payload = {
            "version": "nightmareai/real-esrgan:7de2ea26c616d5bf2245ad0d5e24f0c8db15e21db8f3d46e5718b0d33bdc4e6a",
            "input": {"image": f"file-{file_id}", "scale": 2}  # upscale factor
        }

        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=HEADERS,
            json=model_payload
        )
        r.raise_for_status()
        prediction = r.json()

        # Poll until finished
        status = prediction["status"]
        while status not in ["succeeded", "failed", "canceled"]:
            r = requests.get(
                f"https://api.replicate.com/v1/predictions/{prediction['id']}",
                headers=HEADERS
            )
            r.raise_for_status()
            prediction = r.json()
            status = prediction["status"]

        if status != "succeeded":
            return await msg.edit_text(f"❌ Upscaling failed! Status: {status}")

        output_url = prediction["output"]
        if not output_url:
            return await msg.edit_text("❌ Upscaling failed - no output received.")

        # Download upscaled result
        out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        with requests.get(output_url, stream=True) as r:
            r.raise_for_status()
            with open(out_file.name, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

        # Send file
        await m.reply_document(out_file.name, caption="✨ Upscaled with ESRGAN")

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
**🖼 AI Image Upscaler**
`/upscale` or `/hd` - Reply to an image to enhance its quality using AI

**Features:**
- Increases resolution up to 4x
- Sharpens lines, smooths colors
- Supports JPG, PNG, WEBP
- Returns file directly in Telegram
"""
