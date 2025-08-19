import os
import httpx
import asyncio
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN") or "r8_X3wOWH9rYTC5JllHIgh3OfnS1HTgnhN1pK7v4"
API_URL = "https://api.replicate.com/v1/predictions"

HEADERS = {
    "Authorization": f"Token {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json"
}

@Gojo.on_message(filters.command("upscale") & filters.reply)
async def upscale_image(c: Gojo, m: Message):
    if not m.reply_to_message.photo:
        return await m.reply_text("❌ Reply to a photo to upscale it.")

    msg = await m.reply_text("🔄 Upscaling image... please wait")

    # Get photo file path
    photo = await m.reply_to_message.download()

    # Upload photo to Replicate's hosted file service
    async with httpx.AsyncClient() as client:
        with open(photo, "rb") as f:
            upload = await client.post(
                "https://api.replicate.com/v1/files",
                headers={"Authorization": f"Token {REPLICATE_API_TOKEN}"},
                files={"file": f}
            )
        upload.raise_for_status()
        uploaded_url = upload.json()["urls"]["get"]

        # Request upscale (factor 2)
        data = {
            "version": "8a1f2e5b1b4dbfdfa2b5a146dd0dfd5c2e018e1d98f9a9dbf17d91e4b6fb4ec8",  # Real-ESRGAN model
            "input": {"image": uploaded_url, "scale": 2}
        }
        r = await client.post(API_URL, headers=HEADERS, json=data)
        r.raise_for_status()
        prediction = r.json()
        prediction_url = prediction["urls"]["get"]

        # Poll until finished
        result = None
        for _ in range(30):
            status = await client.get(prediction_url, headers=HEADERS)
            status.raise_for_status()
            status_data = status.json()
            if status_data["status"] == "succeeded":
                result = status_data["output"]
                break
            elif status_data["status"] == "failed":
                return await msg.edit("❌ Upscaling failed.")
            await asyncio.sleep(5)

    if not result:
        return await msg.edit("❌ Upscaling timed out.")

    # Download final upscaled image
    out_file = "upscaled.png"
    async with httpx.AsyncClient() as client:
        res = await client.get(result[0])
        with open(out_file, "wb") as f:
            f.write(res.content)

    # Send and delete local file
    await m.reply_photo(out_file, caption="✨ Here’s your upscaled image")
    os.remove(out_file)
    os.remove(photo)
    await msg.delete()


__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (Picsart)**
`/upscale` - Reply to an image to enhance its quality using AI

**Features:**
- Increases image resolution up to 8x
- Supports JPG, PNG, WEBP formats
- Max file size: 20MB
"""
