import os
import requests
import tempfile
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "r8_X3wOWH9rYTC5JllHIgh3OfnS1HTgnhN1pK7v4")

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


@Gojo.on_message(filters.command(["upscale", "hd"], prefixes=["/", "!", "."]))
async def upscale_image(client: Gojo, m: Message):
    if not REPLICATE_API_TOKEN:
        return await m.reply_text("❌ API Token missing! Please set REPLICATE_API_TOKEN.")

    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.sticker or m.reply_to_message.document):
        return await m.reply_text("⚠️ Reply to an image or sticker to upscale.")

    msg = await m.reply_text("🔄 Uploading image to Replicate...")

    # Download image to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    await m.reply_to_message.download(temp_file.name)

    try:
        # Upload image to replicate
        file_id = upload_to_replicate(temp_file.name)

        # Run advanced ESRGAN model with better parameters
        model_payload = {
            "version": "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
            "input": {
                "image": f"file-{file_id}",
                "scale": 4,  # Higher scale factor
                "face_enhance": True,  # Better for portraits
                "tile": 0,  # No tiling for better quality
                "tile_pad": 10,
                "pre_pad": 0,
                "half": False,  # Full precision
                "denoise_strength": 0.5,  # Moderate denoising
                "suffix": "out"  # Output suffix
            }
        }

        r = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=HEADERS,
            json=model_payload
        )
        r.raise_for_status()
        prediction = r.json()

        # Poll until finished with timeout
        status = prediction["status"]
        attempts = 0
        max_attempts = 30  # ~3 minutes timeout
        while status not in ["succeeded", "failed", "canceled"] and attempts < max_attempts:
            r = requests.get(
                f"https://api.replicate.com/v1/predictions/{prediction['id']}",
                headers=HEADERS
            )
            r.raise_for_status()
            prediction = r.json()
            status = prediction["status"]
            attempts += 1
            await asyncio.sleep(6)  # Check every 6 seconds

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

        # Send file with better compression
        await m.reply_document(
            out_file.name,
            caption="✨ Upscaled with Advanced ESRGAN\n🔍 Sharpened lines & smoothed colors",
            force_document=True
        )

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

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
- Sharpens lines while maintaining smooth edges
- Smart color smoothing without oversaturation
- Advanced face enhancement for portraits
- Noise reduction while preserving details
- Supports JPG, PNG, WEBP
- Returns high-quality PNG file directly in Telegram

**Tips:**
- Works best with clear source images
- For anime/artwork, use higher scale factors
- Portraits benefit from face enhancement
"""
