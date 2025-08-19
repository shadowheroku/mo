import os, mimetypes
from PIL import Image, ImageFilter
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Settings
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
SUPPORTED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

def upscale_sharp_smooth(img_path: str, scale: int = 2) -> str:
    """Upscale image, sharpen edges, smooth colors"""
    with Image.open(img_path).convert("RGB") as img:
        # Step 1: upscale with LANCZOS for best detail
        new_size = (img.width * scale, img.height * scale)
        upscaled = img.resize(new_size, Image.LANCZOS)

        # Step 2: sharpen edges/lines
        sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))

        # Step 3: smooth colors (reduce harsh noise / gradients)
        smoothed = sharpened.filter(ImageFilter.SMOOTH_MORE)

        # Save output
        out_path = os.path.splitext(img_path)[0] + "_upscaled.png"
        smoothed.save(out_path, "PNG", quality=95)
        return out_path

@Gojo.on_message(command("upscale"))
async def upscale_image(c: Gojo, m: Message):
    if not m.reply_to_message or not m.reply_to_message.photo:
        return await m.reply_text("❌ **Reply to a photo to upscale it!**")

    msg = await m.reply_text("📥 **Step 1:** Downloading image...")
    try:
        # Download
        img_path = await m.reply_to_message.download()
        if os.path.getsize(img_path) > MAX_FILE_SIZE:
            os.remove(img_path)
            return await msg.edit_text(f"🚫 **Image too large!** Max {MAX_FILE_SIZE//(1024*1024)}MB")

        # Validate type
        mime_type, _ = mimetypes.guess_type(img_path)
        if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
            os.remove(img_path)
            return await msg.edit_text("⚠️ **Unsupported format!** Only JPG, PNG, WEBP allowed.")

        # Upscale + enhance
        await msg.edit_text("🔄 **Step 2:** Upscaling (sharp lines + smooth colors)...")
        out_path = upscale_sharp_smooth(img_path, scale=2)

        # Send result
        await m.reply_photo(
            out_path,
            caption="✅ **Upscaled with sharper lines & smoother colors.**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Upscale Again", callback_data="upscale_again")]
            ])
        )

        os.remove(out_path)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ **Error:** `{e}`")
    finally:
        if "img_path" in locals() and os.path.exists(img_path):
            os.remove(img_path)

__PLUGIN__ = "upscale"
__HELP__ = """
**🔍 Image Upscaler**
`/upscale` — Reply to a photo to upscale it.  

✨ **Enhancements:**  
- Sharper edges/lines  
- Smoother colors & gradients  

⚠️ **Supported formats:** JPG, PNG, WEBP  
📦 **Max size:** 20MB
"""
