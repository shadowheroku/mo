import pyfiglet
from random import choice
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Store last text temporarily for "Change" button
last_figlet_text = {}

# Function to generate random figlet
def figle(text: str):
    fonts = pyfiglet.getFonts()
    font = choice(fonts)
    figled = pyfiglet.figlet_format(text, font=font)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Change", callback_data="figlet_change"),
                InlineKeyboardButton("❌ Close", callback_data="figlet_close")
            ]
        ]
    )
    return figled, keyboard

# Command to create figlet
@Gojo.on_message(command("figlet"))
async def figlet_cmd(c: Gojo, m: Message):
    try:
        text = m.text.split(" ", 1)[1]
    except IndexError:
        return await m.reply_text("Example:\n\n`/figlet Hello World`")

    fig_text, keyboard = figle(text)
    last_figlet_text[m.chat.id] = text  # Save for "Change" button
    await m.reply_text(
        f"🎨 **Here’s your Figlet:**\n<pre>{fig_text}</pre>",
        reply_markup=keyboard,
        quote=True
    )

# Callback handler for "Change"
@Gojo.on_callback_query(filters.regex("^figlet_change$"))
async def figlet_change_callback(c: Gojo, q: CallbackQuery):
    text = last_figlet_text.get(q.message.chat.id)
    if not text:
        return await q.answer("⚠️ No text stored. Send /figlet again.", show_alert=True)

    fig_text, keyboard = figle(text)
    await q.message.edit_text(
        f"🎨 **Here’s your Figlet:**\n<pre>{fig_text}</pre>",
        reply_markup=keyboard
    )

# Callback handler for "Close"
@Gojo.on_callback_query(filters.regex("^figlet_close$"))
async def figlet_close_callback(c: Gojo, q: CallbackQuery):
    await q.message.delete()

__PLUGIN__ = "figlet"
__HELP__ = """
🎨 **Figlet Text Art**

`/figlet <text>` — Create cool ASCII art text.

Example:
`/figlet PRINCE PAPA`

You can also click **Change** to get a different random style.
"""
