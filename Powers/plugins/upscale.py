import os, mimetypes, requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Picsart configuration
PICSART_API_URL = "https://api.picsart.io/tools/1.0/upscale"
PICSART_API_KEY = "eyJraWQiOiI5NzIxYmUzNi1iMjcwLTQ5ZDUtOTc1Ni05ZDU5N2M4NmIwNTEiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhdXRoLXNlcnZpY2UtOGQ0ZGQyMTEtZTUyNy00NWQ4LWI2NDItMjRlZTBhOGM2NThiIiwiYXVkIjoiNDI5NDQzMDk2MDE0MTAxIiwibmJmIjoxNzQ3NzU2MTU0LCJzY29wZSI6WyJiMmItYXBpLmltYWdlX2FwaSJdLCJpc3MiOiJodHRwczovL2FwaS5waWNzYXJ0LmNvbS90b2tlbi1zZXJ2aWNlIiwib3duZXJJZCI6IjQyOTQ0MzA5NjAxNDEwMSIsImlhdCI6MTc0Nzc1NjE1NCwianRpIjoiYzI1NTUyNjQtYzM4Yy00MjlmLWE5ZTEtNGI1MWQ1YzljMzE4In0.bbn1xeZQkWV2LUr-R6c1eKmK1Q8Bh3xZrVuh9-trLwsE3226ywEkQux3EjmnQLoq7V5_hy132oFOsDlLoVMSF16WinCqtNcF9AdlAu950-Uc8snl11EsrYc5BXxOVmOPhZT_ba1Op3oA8CM2fVmCoOJgB65mHX5UiuRL3bs3PhXPUVmFPNKnkxAr7D1uZcis0YM3enTqcQGIzTDudAlDfe3mD8TSy7b3aTe9XLzYRMEsZCT6RNOcRK4vNRzgdtNKnZ4KsgOjCPyTZAVKAADllJQ-totdI07O0vAsrdXtigU-oWz1x8e3T98D7FmctC7-kyLWu99XiMcO2I-_N5v_Tg"  # Keep this safe!
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
SUPPORTED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

@Gojo.on_message(command("upscale"))
async def upscale_with_picsart(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("❌ **Reply to a photo to upscale it!**")

    msg = await m.reply_text("📥 **Step 1:** Downloading image…")
    try:
        img_path = await m.reply_to_message.download()
        if os.path.getsize(img_path) > MAX_FILE_SIZE:
            os.remove(img_path)
            return await msg.edit_text(f"🚫 **Too large!** Max allowed is {MAX_FILE_SIZE//(1024*1024)} MB")

        mime_type, _ = mimetypes.guess_type(img_path)
        if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
            os.remove(img_path)
            return await msg.edit_text("⚠️ Unsupported format! Only JPG, PNG, WEBP allowed.")

        await msg.edit_text("⚙️ **Step 2:** Sending to Picsart for AI upscale…")
        with open(img_path, "rb") as f:
            response = requests.post(
                PICSART_API_URL,
                headers={
                    "accept": "application/json",
                    "X-Picsart-API-Key": PICSART_API_KEY
                },
                files={"image": f},
                data={"scale": 2}  # You can use 2, 4, 6, or 8
            )

        os.remove(img_path)

        if response.status_code == 200 and "output_url" in response.json():
            output_url = response.json()["output_url"]
            await msg.edit_text(
                "✅ **Upscale complete!** Your enhanced image:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Open Image", url=output_url)],
                    [InlineKeyboardButton("Share", url=f"https://t.me/share/url?url={output_url}")]
                ])
            )
        else:
            await msg.edit_text(
                f"❌ **Failed to upscale.** HTTP {response.status_code}\n{response.text}"
            )

    except Exception as e:
        await msg.edit_text(f"⚠️ **Error:** `{e}`")
    finally:
        if "img_path" in locals() and os.path.exists(img_path):
            os.remove(img_path)

__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (Picsart)**
`/upscale` — Reply to a photo to upscale with AI (up to 8×).

**Highlights:**
 • Sharper lines & smoother colors via Picsart’s AI  
 • Supports JPG, PNG, WEBP  
 • Max file size: 20 MB  
 • Requires valid Picsart API key in header
"""
