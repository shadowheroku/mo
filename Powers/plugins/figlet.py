import pyfiglet
from random import choice
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Function to generate random figlet
def figle(text: str):
    fonts = pyfiglet.getFonts()
    font = choice(fonts)
    figled = pyfiglet.figlet_format(text, font=font)
    return figled

# Command to create figlet
@Gojo.on_message(command("figlet"))
async def figlet_cmd(c: Gojo, m: Message):
    try:
        text = m.text.split(" ", 1)[1]
    except IndexError:
        return await m.reply_text("Example:\n\n`/figlet Hello World`")

    fig_text = figle(text)
    await m.reply_text(
        f"🎨 **Here’s your Figlet:**\n<pre>{fig_text}</pre>",
        quote=True
    )

__PLUGIN__ = "figlet"
__HELP__ = """
🎨 **Figlet Text Art**

`/figlet <text>` — Create cool ASCII art text.

Example:
`/figlet Monic Bot`
"""
