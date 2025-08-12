from pyrogram import filters
from pyrogram.types import Message
import qrcode
from PIL import Image
import io

import asyncio
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
# Function to create a QR code
def generate_qr_code(text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="white", back_color="black")

    # Save the QR code to a bytes object to send with Pyrogram
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)  # Go to the start of the bytes object

    return img_bytes


@Gojo.on_message(filters.command("qr"))
async def qr_handler(client, message: Message):
    # Extracting the text passed after the command
    if len(message.command) > 1:
        input_text = " ".join(message.command[1:])
        qr_image = generate_qr_code(input_text)
        await message.reply_photo(qr_image, caption="Here's your QR Code 🌀")
    else:
        await message.reply_text(
            "⚠️ Please provide text after the command.\n\nExample:\n`/qr Hello World`"
        )

__PLUGIN__ = "QrCode"
__HELP__ = """
⏳ **Reminder**

`/qr <text/links>` — Creates qrcode of text or links.

Example:
`/qr t.me/MonicRobot`
"""
