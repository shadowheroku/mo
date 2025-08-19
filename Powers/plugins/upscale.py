import os
import requests
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from pyrogram.errors import BadRequest

# Picsart configuration
PICSART_API_URL = "https://api.picsart.io/tools/1.0/upscale"
PICSART_API_KEY = "eyJraWQiOiI5NzIxYmUzNi1iMjcwLTQ5ZDUtOTc1Ni05ZDU5N2M4NmIwNTEiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhdXRoLXNlcnZpY2UtOGQ0ZGQyMTEtZTUyNy00NWQ4LWI2NDItMjRlZTBhOGM2NThiIiwiYXVkIjoiNDI5NDQzMDk2MDE0MTAxIiwibmJmIjoxNzQ3NzU2MTU0LCJzY29wZSI6WyJiMmItYXBpLmltYWdlX2FwaSJdLCJpc3MiOiJodHRwczovL2FwaS5waWNzYXJ0LmNvbS90b2tlbi1zZXJ2aWNlIiwib3duZXJJZCI6IjQyOTQ0MzA5NjAxNDEwMSIsImlhdCI6MTc0Nzc1NjE1NCwianRpIjoiYzI1NTUyNjQtYzM4Yy00MjlmLWE5ZTEtNGI1MWQ1YzljMzE4In0.bbn1xeZQkWV2LUr-R6c1eKmK1Q8Bh3xZrVuh9-trLwsE3226ywEkQux3EjmnQLoq7V5_hy132oFOsDlLoVMSF16WinCqtNcF9AdlAu950-Uc8snl11EsrYc5BXxOVmOPhZT_ba1Op3oA8CM2fVmCoOJgB65mHX5UiuRL3bs3PhXPUVmFPNKnkxAr7D1uZcis0YM3enTqcQGIzTDudAlDfe3mD8TSy7b3aTe9XLzYRMEsZCT6RNOcRK4vNRzgdtNKnZ4KsgOjCPyTZAVKAADllJQ-totdI07O0vAsrdXtigU-oWz1x8e3T98D7FmctC7-kyLWu99XiMcO2I-_N5v_Tg"  # Replace with your actual API key
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

@Gojo.on_message(command("upscale"))
async def upscale_with_picsart(c: Gojo, m: Message):
    if not m.reply_to_message or not (m.reply_to_message.photo or m.reply_to_message.document):
        return await m.reply_text("❌ Please reply to an image file to upscale it!")

    msg = await m.reply_text("📥 Downloading image...")
    try:
        # Download the file
        img_path = await m.reply_to_message.download()
        
        # Check file size
        file_size = os.path.getsize(img_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(img_path)
            return await msg.edit_text(f"🚫 File is too large! Max allowed is {MAX_FILE_SIZE//(1024*1024)} MB")
        
        # Check file extension
        ext = os.path.splitext(img_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            os.remove(img_path)
            return await msg.edit_text("⚠️ Unsupported file format! Only JPG, PNG, WEBP allowed.")
        
        await msg.edit_text("⚙️ Upscaling image with Picsart AI...")
        
        # Prepare the request with correct parameter name
        with open(img_path, "rb") as image_file:
            files = {"image": image_file}
            data = {"upscale_factor": 2}  # Correct parameter name (can be 2, 4, 6, or 8)
            
            headers = {
                "accept": "application/json",
                "X-Picsart-API-Key": PICSART_API_KEY
            }
            
            response = requests.post(
                PICSART_API_URL,
                headers=headers,
                files=files,
                data=data
            )
        
        # Clean up the downloaded file
        os.remove(img_path)
        
        # Process the response
        if response.status_code == 200:
            result = response.json()
            if "output_url" in result:
                await msg.edit_text(
                    "✅ Image upscaled successfully!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("View Image", url=result["output_url"])],
                        [InlineKeyboardButton("Share", url=f"https://t.me/share/url?url={result['output_url']}")]
                    ])
                )
            else:
                await msg.edit_text("❌ Upscaling failed - no output URL received")
        else:
            await msg.edit_text(f"❌ Upscaling failed with status {response.status_code}: {response.text}")
    
    except BadRequest as e:
        await msg.edit_text(f"❌ Telegram error: {e}")
    except requests.exceptions.RequestException as e:
        await msg.edit_text(f"❌ Network error: {str(e)}")
    except Exception as e:
        await msg.edit_text(f"❌ An error occurred: {str(e)}")
    finally:
        # Ensure the file is deleted even if an error occurs
        if "img_path" in locals() and os.path.exists(img_path):
            os.remove(img_path)

__PLUGIN__ = "upscale"
__HELP__ = """
**🖼 AI Image Upscaler (Picsart)**
`/upscale` - Reply to an image to enhance its quality using AI

**Features:**
- Increases image resolution up to 8x
- Supports JPG, PNG, WEBP formats
- Max file size: 20MB
"""
