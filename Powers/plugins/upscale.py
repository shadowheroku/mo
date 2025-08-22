import os
import replicate
import requests
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Load Replicate API key
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN" , "r8_V7pQfVBxlIzmvviUEkiYJxCcDqAAbhk1rq4Jn")

import os
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message
from replicate import Client as ReplicateClient

# Load your Replicate API token

replicate = ReplicateClient(api_token=REPLICATE_API_TOKEN)

@Client.on_message(filters.command("upscale"))
async def upscale_image(c: Client, m: Message):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("⚠️ Reply to an image to upscale it.")

    try:
        # Download image to memory
        photo_path = await m.reply_to_message.download()
        async with aiohttp.ClientSession() as session:
            with open(photo_path, "rb") as f:
                image_bytes = f.read()

        # Run ESRGAN model on Replicate
        output = replicate.run(
            "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
            input={
                "image": image_bytes,  # Directly send raw bytes
                "scale": 2
            },
        )

        if not output:
            return await m.reply_text("❌ Upscale failed. No output received.")

        # Send result back
        await m.reply_photo(photo=output, caption="✅ Upscaled successfully!")

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
