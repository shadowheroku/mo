import os
import replicate
import requests
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Load Replicate API key
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN" , "r8_V7pQfVBxlIzmvviUEkiYJxCcDqAAbhk1rq4Jn")

if not REPLICATE_API_TOKEN:
    raise ValueError("⚠️ Please set the REPLICATE_API_TOKEN environment variable.")

# Init Replicate client
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)


@Gojo.on_message(command("upscale"))
async def upscale_image(c: Gojo, m: Message):
    """Upscale an image using Real-ESRGAN (Replicate)"""
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("⚠️ Reply to an image to upscale it!")

    try:
        # Get file from Telegram
        photo = await m.reply_to_message.download()
        await m.reply_text("⏳ Upscaling image, please wait...")

        # Upload image to Replicate delivery server
        image_url = replicate_client.files.upload(photo)

        # Run Real-ESRGAN model
        output = replicate_client.run(
            "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
            input={"image": image_url, "scale": 2}
        )

        # output is usually a list of image URLs, take the first one
        if isinstance(output, list):
            result_url = output[0]
        else:
            result_url = output

        # Download result image
        result = requests.get(result_url)
        filename = "upscaled.png"
        with open(filename, "wb") as f:
            f.write(result.content)

        # Send back upscaled image
        await m.reply_photo(filename, caption="✨ Upscaled with Real-ESRGAN")

        # Cleanup
        os.remove(photo)
        os.remove(filename)

    except Exception as e:
        await m.reply_text(f"❌ Upscale failed: {e}")



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
